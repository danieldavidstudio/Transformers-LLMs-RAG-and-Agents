"""OpenAI-compatible chat provider."""

from openai import OpenAI

from config import MODEL, OPENAI_API_KEY, OPENAI_ENDPOINT


_client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_ENDPOINT,
)


def generate_chat(system_prompt: str, user_prompt: str) -> str:
    """Generate one response through the configured chat-completions API."""

    response = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content or ""
