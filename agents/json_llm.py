"""
Invoke LLM and parse JSON response without using response_format=json_schema.

Groq (and some other providers) do not support json_schema; this module uses
prompt-based JSON and safe parsing with retry and fallback.
"""

import json
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from .llm import get_llm

T = TypeVar("T", bound=BaseModel)


def _extract_json(text: str) -> str | None:
    """Try to extract a JSON object or array from raw LLM output."""
    text = text.strip()
    # Strip markdown code block if present
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()
    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()
    # Find first { and matching }
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def invoke_json_llm(
    prompt: str,
    default_dict: dict[str, Any],
    model_class: Type[T],
) -> T:
    """
    Invoke the LLM with the prompt, parse JSON from the response, and return a Pydantic model.

    - If JSON parsing fails, retries once (re-invoke LLM, then parse again).
    - If still failing, tries to extract a JSON object from the response text.
    - If still failing, wraps the response into default_dict and validates.
    """
    llm = get_llm()

    def parse_and_validate(content: str) -> T | None:
        try:
            data = json.loads(content)
            return model_class.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            return None

    def try_content(content: str) -> T | None:
        result = parse_and_validate(content)
        if result is not None:
            return result
        extracted = _extract_json(content)
        if extracted:
            return parse_and_validate(extracted)
        return None

    raw = llm.invoke(prompt)
    content = getattr(raw, "content", str(raw))
    result = try_content(content)
    if result is not None:
        return result

    # Retry once: invoke LLM again and parse
    raw = llm.invoke(prompt)
    content = getattr(raw, "content", str(raw))
    result = try_content(content)
    if result is not None:
        return result

    # Fallback: wrap into expected structure so the graph can continue
    fallback = dict(default_dict)
    msg = content[:2000] if content else "Unable to parse agent response."
    for k, v in fallback.items():
        if isinstance(v, str) and not v:
            fallback[k] = msg
            break
    return model_class.model_validate(fallback)
