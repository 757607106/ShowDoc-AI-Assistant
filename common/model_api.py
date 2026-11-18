"""OpenAI-compatible vision calls shared by the existing document connectors."""
from openai import OpenAI


def chat_completion(*, base_url, api_key, timeout, **payload):
    with OpenAI(base_url=base_url.rstrip('/').removesuffix('/chat/completions'), api_key=api_key, timeout=timeout) as client:
        return client.chat.completions.create(**payload).model_dump()
