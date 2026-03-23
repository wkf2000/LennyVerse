from __future__ import annotations

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from data_pipeline.config import Settings


class EmbeddingClient:
    def __init__(self, settings: Settings) -> None:
        self._client = OpenAI(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
        )
        self._model = settings.embedding_model

    @retry(wait=wait_exponential(multiplier=1, min=1, max=15), stop=stop_after_attempt(3), reraise=True)
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]
