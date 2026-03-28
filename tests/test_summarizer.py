from unittest.mock import MagicMock, patch

from data_pipeline.config import Settings
from data_pipeline.summarizer import SummarizerClient

SYSTEM_PROMPT = "Summarize the following content in 2-3 concise sentences. Focus on the key topics, insights, and takeaways."


def _make_settings() -> Settings:
    return Settings(
        SUPABASE_DB_URL="postgresql://localhost/test",
        DATASET_ROOT_DIR="/tmp/fake",
        SUMMARIZE_API_BASE="https://api.example.com/v1",
        SUMMARIZE_API_KEY="sk-test",
        SUMMARIZE_MODEL="gpt-4o-mini",
        SUMMARIZE_MAX_CHARS=100,
    )


def test_summarize_calls_openai_and_returns_text() -> None:
    settings = _make_settings()
    with patch("data_pipeline.summarizer.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a summary."
        mock_client.chat.completions.create.return_value = mock_response

        client = SummarizerClient(settings)
        result = client.summarize("Some long text about product management.")

        assert result == "This is a summary."
        mock_openai_cls.assert_called_once_with(
            base_url="https://api.example.com/v1",
            api_key="sk-test",
        )
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4o-mini"
        messages = call_kwargs.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == SYSTEM_PROMPT
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Some long text about product management."


def test_summarize_strips_whitespace() -> None:
    settings = _make_settings()
    with patch("data_pipeline.summarizer.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "  Summary with whitespace.  \n"
        mock_client.chat.completions.create.return_value = mock_response

        client = SummarizerClient(settings)
        result = client.summarize("text")
        assert result == "Summary with whitespace."


def test_summarize_handles_none_content() -> None:
    settings = _make_settings()
    with patch("data_pipeline.summarizer.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = mock_response

        client = SummarizerClient(settings)
        result = client.summarize("text")
        assert result == ""
