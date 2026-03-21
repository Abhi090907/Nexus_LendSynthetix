import os
import sys
import time
from functools import lru_cache
from typing import Any

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_settings


class SimpleChatLLM:
    def __init__(self, base_url: str, api_key: str, model: str, temperature: float):
        self.base_url    = base_url.rstrip("/")
        self.api_key     = api_key
        self.model       = model
        self.temperature = temperature

    def invoke(self, prompt: str) -> Any:
        for attempt in range(5):  # retry up to 5 times
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model":       self.model,
                    "temperature": self.temperature,
                    "messages":    [{"role": "user", "content": prompt}],
                },
                timeout=60,
            )

            if response.status_code == 429:
                wait = 10 * (attempt + 1)  # 10s, 20s, 30s, 40s, 50s
                print(f"Rate limited. Waiting {wait}s before retry {attempt + 1}/5...")
                time.sleep(wait)
                continue

            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]

            class _Msg:
                pass
            msg         = _Msg()
            msg.content = content
            return msg

        raise RuntimeError("Groq rate limit exceeded after 5 retries. Wait a minute and try again.")


@lru_cache(maxsize=1)
def get_llm() -> SimpleChatLLM:
    s = get_settings()
    return SimpleChatLLM(
        base_url    = s.llm_base_url or "http://localhost:11434/v1",
        api_key     = s.llm_api_key  or "ollama",
        model       = s.llm_model,
        temperature = 0.3,
    )