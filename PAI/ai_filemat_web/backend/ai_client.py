"""
backend/ai_client.py - AI integration for Gemini and other AI services
Ported from desktop tool with full functionality
"""

import os
import re
import json
import mimetypes
import threading
from pathlib import Path
from typing import List, Dict, Optional, Callable

# Try to import AI packages
try:
    from google import genai
    from google.genai import types as genai_types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

def _api_model(name: str) -> str:
    """Ensure model name has the required 'models/' prefix for the new SDK."""
    if not name:
        return "models/gemini-2.0-flash"
    return name if name.startswith("models/") else f"models/{name}"

SYSTEM_PROMPT = """You are an AI assistant embedded inside "AI FileMat" —
a web-based tool for converting, splitting, merging, organising,
stamping, protecting, compressing and extracting content from files
(PDF, Word, Excel, PowerPoint, CSV, images, audio, video).

Your job:
1. Answer questions about the user's loaded files.
2. Understand natural-language commands and map them to tool actions.
3. Summarise, analyse, and explain file content when asked.
4. Suggest the best output format for a given task.
5. Always be concise and precise — this is a professional productivity tool.

When the user gives a file-operation command, respond with a JSON block
like this (inside ```json ... ``` fences):
{
  "action": "convert",
  "files": ["report.pdf"],
  "format": "docx",
  "pages": null,
  "params": {},
  "message": "I'll convert report.pdf to Word format."
}

Supported actions: convert, split, merge, organise, compress, protect, stamp,
                   summarise, analyse, chat, unknown

If the user is just asking a question or chatting, set action to "chat" and
skip the JSON — just reply in plain text.
"""

class GeminiClient:
    """Wraps the Gemini API for all AI features."""

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self._client = None
        self._model_name = None
        self.history: List[Dict] = []
        self._ready = False
        self._error = ""

        if api_key:
            self._init_model(api_key, model_name)

    def _init_model(self, api_key: str, model_name: str):
        """Initialize the Gemini model"""
        if not HAS_GENAI:
            self._error = "google-genai not installed.\nRun: pip install google-genai"
            return
        try:
            self._client = genai.Client(api_key=api_key)
            self._model_name = _api_model(model_name)
            self._ready = True
            self._error = ""
        except Exception as e:
            self._ready = False
            self._error = str(e)

    def reconfigure(self, api_key: str, model_name: str):
        """Reconfigure the client with new credentials"""
        self.api_key = api_key
        self.model_name = model_name
        self._init_model(api_key, model_name)
        self.history.clear()

    @property
    def is_ready(self) -> bool:
        """Check if the client is ready"""
        return self._ready and HAS_GENAI

    @property
    def error(self) -> str:
        """Get the current error"""
        if not HAS_GENAI:
            return "google-genai not installed.\nRun: pip install google-genai"
        return self._error

    def chat(self, user_message: str,
             context: str = "",
             on_done: Optional[Callable[[str], None]] = None,
             on_error: Optional[Callable[[str], None]] = None):
        """Send a message to the AI"""
        if not self.is_ready:
            if on_error: on_error(self.error)
            return

        prompt = user_message
        if context:
            prompt = f"[Context about loaded files]\n{context}\n\n[User]\n{user_message}"

        # Build conversation history
        contents = [genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=SYSTEM_PROMPT)]
        )]
        for turn in self.history[-20:]:
            role = "user" if turn["role"] == "user" else "model"
            contents.append(genai_types.Content(
                role=role,
                parts=[genai_types.Part.from_text(text=turn["text"])]
            ))
        contents.append(genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=prompt)]
        ))

        def _worker():
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=contents,
                )
                text = response.text
                self.history.append({"role": "user", "text": user_message})
                self.history.append({"role": "assistant", "text": text})
                if on_done: on_done(text)
            except Exception as e:
                err = f"Gemini error: {e}"
                if on_error: on_error(err)

        threading.Thread(target=_worker, daemon=True).start()

    def analyse_image(self, image_path: str,
                      prompt: str = "Describe this image in detail.",
                      on_done: Optional[Callable[[str], None]] = None,
                      on_error: Optional[Callable[[str], None]] = None):
        """Analyze an image using Gemini Vision"""
        if not self.is_ready:
            if on_error: on_error(self.error); return

        def _worker():
            try:
                with open(image_path, "rb") as f:
                    img_bytes = f.read()
                mime, _ = mimetypes.guess_type(image_path)
                mime = mime or "image/png"
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=[
                        genai_types.Part.from_bytes(data=img_bytes, mime_type=mime),
                        genai_types.Part.from_text(text=prompt),
                    ],
                )
                text = response.text
                if on_done: on_done(text)
            except Exception as e:
                err = f"Gemini error: {e}"
                if on_error: on_error(err)

        threading.Thread(target=_worker, daemon=True).start()

    def parse_intent(self, user_message: str,
                    on_done: Optional[Callable[[Dict], None]] = None,
                    on_error: Optional[Callable[[str], None]] = None):
        """Parse user intent from natural language"""
        if not self.is_ready:
            if on_error: on_error(self.error); return

        prompt = f"{user_message}\n\nParse this as a file operation command. Return JSON with action, files, format, pages, params, and message."

        def _worker():
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=[
                        genai_types.Content(
                            role="user",
                            parts=[genai_types.Part.from_text(text=prompt)]
                        ),
                    ],
                )
                text = response.text
                
                # Extract JSON from response
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
                if json_match:
                    try:
                        intent = json.loads(json_match.group(1))
                        if on_done: on_done(intent)
                    except json.JSONDecodeError:
                        if on_error: on_error("Failed to parse intent JSON")
                else:
                    # Try to find bare JSON object
                    json_match = re.search(r'\{[\s\S]*?\}', text)
                    if json_match:
                        try:
                            intent = json.loads(json_match.group(0))
                            if on_done: on_done(intent)
                        except json.JSONDecodeError:
                            if on_error: on_error("Failed to parse intent JSON")
                    else:
                        # No JSON found, treat as chat
                        intent = {
                            "action": "chat",
                            "files": [],
                            "format": None,
                            "pages": None,
                            "params": {},
                            "message": text
                        }
                        if on_done: on_done(intent)
            except Exception as e:
                err = f"Gemini error: {e}"
                if on_error: on_error(err)

        threading.Thread(target=_worker, daemon=True).start()

class OpenAIClient:
    """Wraps the OpenAI API for AI features"""

    def __init__(self, api_key: str, model_name: str = "gpt-4"):
        self.api_key = api_key
        self.model_name = model_name
        self.client = None
        self.history: List[Dict] = []
        self._ready = False
        self._error = ""

        if api_key:
            self._init_client(api_key)

    def _init_client(self, api_key: str):
        """Initialize the OpenAI client"""
        if not HAS_OPENAI:
            self._error = "openai not installed.\nRun: pip install openai"
            return
        try:
            self.client = openai.OpenAI(api_key=api_key)
            self._ready = True
            self._error = ""
        except Exception as e:
            self._ready = False
            self._error = str(e)

    @property
    def is_ready(self) -> bool:
        """Check if the client is ready"""
        return self._ready and HAS_OPENAI

    @property
    def error(self) -> str:
        """Get the current error"""
        if not HAS_OPENAI:
            return "openai not installed.\nRun: pip install openai"
        return self._error

    def chat(self, user_message: str,
             context: str = "",
             on_done: Optional[Callable[[str], None]] = None,
             on_error: Optional[Callable[[str], None]] = None):
        """Send a message to the AI"""
        if not self.is_ready:
            if on_error: on_error(self.error)
            return

        prompt = user_message
        if context:
            prompt = f"[Context about loaded files]\n{context}\n\n[User]\n{user_message}"

        # Build conversation history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in self.history[-20:]:
            messages.append({"role": turn["role"], "content": turn["text"]})
        messages.append({"role": "user", "content": prompt})

        def _worker():
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                )
                text = response.choices[0].message.content
                self.history.append({"role": "user", "text": user_message})
                self.history.append({"role": "assistant", "text": text})
                if on_done: on_done(text)
            except Exception as e:
                err = f"OpenAI error: {e}"
                if on_error: on_error(err)

        threading.Thread(target=_worker, daemon=True).start()

class AIClient:
    """Unified AI client that can use multiple providers"""

    def __init__(self, provider: str = "gemini", **kwargs):
        self.provider = provider
        self.client = None
        self._ready = False
        self._error = ""

        if provider == "gemini":
            self.client = GeminiClient(kwargs.get("api_key"), kwargs.get("model", "gemini-1.5-flash"))
        elif provider == "openai":
            self.client = OpenAIClient(kwargs.get("api_key"), kwargs.get("model", "gpt-4"))
        else:
            self._error = f"Unsupported provider: {provider}"

    @property
    def is_ready(self) -> bool:
        """Check if the client is ready"""
        return self.client.is_ready if self.client else False

    @property
    def error(self) -> str:
        """Get the current error"""
        if self.client:
            return self.client.error
        return self._error

    def chat(self, user_message: str, **kwargs):
        """Send a message to the AI"""
        if self.client:
            return self.client.chat(user_message, **kwargs)
        elif self._error and kwargs.get("on_error"):
            kwargs["on_error"](self._error)

    def analyse_image(self, image_path: str, **kwargs):
        """Analyze an image"""
        if self.client and hasattr(self.client, 'analyse_image'):
            return self.client.analyse_image(image_path, **kwargs)
        elif self._error and kwargs.get("on_error"):
            kwargs["on_error"](self._error)

    def parse_intent(self, user_message: str, **kwargs):
        """Parse user intent"""
        if self.client and hasattr(self.client, 'parse_intent'):
            return self.client.parse_intent(user_message, **kwargs)
        elif self._error and kwargs.get("on_error"):
            kwargs["on_error"](self._error)

# ── AI Factory ───────────────────────────────────────────────────────────────

def create_ai_client(provider: str, **kwargs) -> AIClient:
    """Create an AI client for the specified provider"""
    return AIClient(provider, **kwargs)

def get_available_providers():
    """Get list of available AI providers"""
    providers = {}
    if HAS_GENAI:
        providers["gemini"] = {
            "name": "Google Gemini",
            "models": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
            "features": ["chat", "image_analysis", "intent_parsing"]
        }
    if HAS_OPENAI:
        providers["openai"] = {
            "name": "OpenAI",
            "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "features": ["chat", "intent_parsing"]
        }
    return providers
