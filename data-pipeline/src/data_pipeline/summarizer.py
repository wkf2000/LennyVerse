from __future__ import annotations

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from data_pipeline.config import Settings

SYSTEM_PROMPT = (
    "Summarize the following content in 2-3 concise sentences. "
    "Focus on the key topics, insights, and takeaways."
)


class SummarizerClient:
    def __init__(self, settings: Settings) -> None:
        base, key, model = settings.require_summarize_config()
        self._client = OpenAI(base_url=base, api_key=key)
        self._model = model

    @retry(wait=wait_exponential(multiplier=1, min=1, max=15), stop=stop_after_attempt(3), reraise=True)
    def summarize(self, text: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""
