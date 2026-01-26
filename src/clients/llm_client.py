import os
from typing import Optional

from openai import OpenAI

from src.utils.logging import get_logger

logger = get_logger(__name__)


def _extract_output_text(response) -> str:
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text
    if isinstance(response, dict) and response.get("output_text"):
        return response["output_text"]
    if hasattr(response, "choices") and response.choices:
        return response.choices[0].message.content
    raise ValueError("Unable to extract text from LLM response")


class OpenAILLMClient:
    def __init__(self, model: str, api_key: Optional[str] = None):
        if not api_key:
            api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise ValueError("Missing LLM_API_KEY for OpenAI client")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, prompt: str, max_output_tokens: Optional[int] = None) -> str:
        kwargs = {"model": self.model, "input": prompt}
        if max_output_tokens is not None:
            kwargs["max_output_tokens"] = max_output_tokens
        response = self.client.responses.create(**kwargs)
        return _extract_output_text(response)


def build_llm_client(config: dict) -> OpenAILLMClient:
    provider = config.get("provider")
    if provider != "openai":
        raise NotImplementedError(f"Provider not supported: {provider}")
    return OpenAILLMClient(model=config.get("model", "gpt-5-mini"))
