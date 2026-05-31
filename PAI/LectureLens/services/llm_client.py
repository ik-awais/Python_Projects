"""LLM client for NVIDIA API (primary)."""
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class NVIDIAClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://integrate.api.nvidia.com/v1/chat/completions"
        # Use a reliable model from your list (you confirmed it works)
        self.model = "meta/llama-3.3-70b-instruct"

    def generate(self, prompt: str, timeout: int = 30) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 500
        }
        try:
            response = requests.post(self.url, json=payload, headers=headers, timeout=timeout)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                logger.error("NVIDIA API error: %s", response.text)
                return None
        except Exception as e:
            logger.error("NVIDIA API exception: %s", e)
            return None