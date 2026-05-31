"""LLM clients for Gemini and NVIDIA (fallback)."""
import logging
import requests
import google.generativeai as genai
from typing import Optional

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate(self, prompt: str, timeout: int = 30) -> Optional[str]:
        try:
            response = self.model.generate_content(prompt, request_options={'timeout': timeout})
            return response.text
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            return None

class NVIDIAClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://integrate.api.nvidia.com/v1/chat/completions"  # example endpoint; adjust as needed
    
    def generate(self, prompt: str, timeout: int = 30) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta/llama3-70b-instruct",  # adjust to available model
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