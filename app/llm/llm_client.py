
import requests

from app.core.config import (
    LLM_PROVIDER,
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
)


# Connection timeout: 10 seconds
# Response timeout: 300 seconds
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 300

# Limit response length to avoid unnecessarily long generations.
DEFAULT_MAX_TOKENS = 700


def generate_response(
    prompt: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """
    Generate a response using the configured LLM provider.

    Compatible with existing calls:
        generate_response(prompt)

    Optional shorter/longer response:
        generate_response(prompt, max_tokens=500)
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("The LLM prompt cannot be empty.")

    if LLM_PROVIDER != "ollama":
        raise ValueError(
            f"Unsupported LLM provider: {LLM_PROVIDER}"
        )

    base_url = OLLAMA_BASE_URL.rstrip("/")
    endpoint = f"{base_url}/api/chat"

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt.strip(),
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": max(1, int(max_tokens)),
        },
    }

    try:
        response = requests.post(
            endpoint,
            json=payload,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )

        response.raise_for_status()

    except requests.exceptions.ConnectTimeout as exc:
        raise RuntimeError(
            "Ollama connection timed out. Check that Ollama is running "
            f"at {base_url}."
        ) from exc

    except requests.exceptions.ReadTimeout as exc:
        raise RuntimeError(
            f"Ollama model '{OLLAMA_MODEL}' took longer than "
            f"{READ_TIMEOUT} seconds to respond. The prompt may be too "
            "large, the model may be slow, or the system may be under "
            "heavy load. Try a smaller prompt or a faster model."
        ) from exc

    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            "Could not connect to Ollama. Make sure Ollama is running "
            f"and the configured URL is correct: {base_url}"
        ) from exc

    except requests.exceptions.HTTPError as exc:
        detail = response.text[:1000] if response is not None else str(exc)
        raise RuntimeError(
            f"Ollama returned an HTTP error: {detail}"
        ) from exc

    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"An Ollama request failed: {exc}"
        ) from exc

    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError(
            "Ollama returned a response that was not valid JSON."
        ) from exc

    message = result.get("message")

    if not isinstance(message, dict):
        raise RuntimeError(
            f"Ollama response did not contain a valid message: "
            f"{str(result)[:500]}"
        )

    content = message.get("content")

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(
            "Ollama returned an empty response. Check the model and "
            "Ollama logs for errors."
        )

    return content.strip()
