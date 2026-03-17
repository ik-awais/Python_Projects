"""
ai/gemini.py — Gemini multimodal AI integration layer

Capabilities:
  • Text generation / chat
  • Document understanding (PDF, DOCX, XLSX, PPTX text extraction → AI)
  • Image analysis (send image bytes to Gemini Vision)
  • Natural language → file operation intent parsing
  • Smart format suggestion
  • Document summarisation
  • Batch operation planning
"""

import os
import re
import json
import mimetypes
import threading
from pathlib import Path
from typing import List, Dict, Optional, Callable

# Gemini SDK — new google.genai package
try:
    from google import genai
    from google.genai import types as genai_types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# Import model name helper — inline it here to avoid circular import
def _api_model(name: str) -> str:
    """Ensure model name has the required 'models/' prefix for the new SDK."""
    if not name:
        return "models/gemini-2.0-flash"
    return name if name.startswith("models/") else f"models/{name}"


# ─── Intent schema returned by parse_intent() ─────────────────────────────────
#
#  {
#    "action":   "convert" | "split" | "merge" | "organise" | "compress"
#                | "protect" | "stamp" | "summarise" | "analyse" | "chat" | "unknown"
#    "files":    ["name hints from the sentence"],
#    "format":   "pdf" | "docx" | ... | None,
#    "pages":    "1,3,5-8" | None,
#    "params":   { extra action-specific params },
#    "message":  "human-readable explanation of what was understood"
#  }

SYSTEM_PROMPT = """You are an AI assistant embedded inside "File Workshop" —
a local desktop tool for converting, splitting, merging, organising,
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
    """Wraps the Gemini API for all AI features in the workshop."""

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.api_key   = api_key
        self.model_name = model_name
        self.model     = None
        self.chat_session = None
        self.history: List[Dict] = []
        self._ready    = False
        self._error    = ""

        if api_key:
            self._init_model(api_key, model_name)

    # ─── Initialisation ───────────────────────────────────────────────────────

    def _init_model(self, api_key: str, model_name: str):
        if not HAS_GENAI:
            self._error = "google-genai not installed.\nRun: pip install google-genai"
            return
        try:
            self._client = genai.Client(api_key=api_key)
            self._model_name = _api_model(model_name)  # ensures "models/" prefix
            self._ready = True
            self._error = ""
        except Exception as e:
            self._ready = False
            self._error = str(e)

    def reconfigure(self, api_key: str, model_name: str):
        self.api_key     = api_key
        self.model_name  = model_name
        self._init_model(api_key, model_name)
        self.history.clear()

    @property
    def is_ready(self) -> bool:
        return self._ready and HAS_GENAI

    @property
    def error(self) -> str:
        if not HAS_GENAI:
            return "google-genai not installed.\nRun: pip install google-genai"
        return self._error

    # ─── Core text chat ───────────────────────────────────────────────────────

    def chat(self, user_message: str,
             context: str = "",
             on_done: Optional[Callable[[str], None]] = None,
             on_error: Optional[Callable[[str], None]] = None):
        """
        Send a message. Calls on_done(response_text) or on_error(msg).
        Runs in a background thread so GUI stays responsive.
        """
        if not self.is_ready:
            if on_error: on_error(self.error)
            return

        prompt = user_message
        if context:
            prompt = f"[Context about loaded files]\n{context}\n\n[User]\n{user_message}"

        # Build conversation history for the API
        contents = [genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=SYSTEM_PROMPT)]
        )]
        for turn in self.history[-20:]:  # keep last 10 exchanges (20 messages)
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
                self.history.append({"role": "user",      "text": user_message})
                self.history.append({"role": "assistant", "text": text})
                if on_done: on_done(text)
            except Exception as e:
                err = f"Gemini error: {e}"
                if on_error: on_error(err)

        threading.Thread(target=_worker, daemon=True).start()

    # ─── Image analysis ───────────────────────────────────────────────────────

    def analyse_image(self, image_path: str,
                      prompt: str = "Describe this image in detail.",
                      on_done: Optional[Callable[[str], None]] = None,
                      on_error: Optional[Callable[[str], None]] = None):
        """Send an image to Gemini Vision for analysis."""
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
                if on_done: on_done(response.text)
            except Exception as e:
                if on_error: on_error(f"Image analysis error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    # ─── Document understanding ───────────────────────────────────────────────

    def summarise_document(self, file_path: str,
                           text_content: str,
                           on_done: Optional[Callable[[str], None]] = None,
                           on_error: Optional[Callable[[str], None]] = None):
        """Summarise a document given its extracted text."""
        if not self.is_ready:
            if on_error: on_error(self.error); return

        fname = Path(file_path).name
        prompt = (
            f"Please provide a comprehensive summary of this document: '{fname}'\n\n"
            f"Include:\n"
            f"- Main topic / purpose\n"
            f"- Key points (bullet list)\n"
            f"- Important data, numbers or conclusions\n"
            f"- Suggested action items if any\n\n"
            f"Document content:\n{text_content[:12000]}"
        )

        def _worker():
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                )
                if on_done: on_done(response.text)
            except Exception as e:
                if on_error: on_error(f"Summarisation error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def ask_document(self, file_path: str,
                     text_content: str,
                     question: str,
                     on_done: Optional[Callable[[str], None]] = None,
                     on_error: Optional[Callable[[str], None]] = None):
        """Answer a question about a document."""
        if not self.is_ready:
            if on_error: on_error(self.error); return

        fname = Path(file_path).name
        prompt = (
            f"Document: '{fname}'\n\n"
            f"Content:\n{text_content[:12000]}\n\n"
            f"Question: {question}\n\n"
            f"Answer based only on the document content above. "
            f"If the answer is not in the document, say so."
        )

        def _worker():
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                )
                if on_done: on_done(response.text)
            except Exception as e:
                if on_error: on_error(f"Q&A error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    # ─── Intent parsing ───────────────────────────────────────────────────────

    def parse_intent(self, user_message: str,
                     file_names: List[str],
                     on_done: Optional[Callable] = None,
                     on_error: Optional[Callable[[str], None]] = None):
        """
        Parse a natural-language command into a structured intent.
        Calls on_done(intent_dict, raw_text).
        """
        if not self.is_ready:
            if on_error: on_error(self.error); return

        files_ctx = "\n".join(f"  - {f}" for f in file_names) if file_names else "  (none loaded)"
        prompt = (
            f"The user has these files loaded:\n{files_ctx}\n\n"
            f"User command: \"{user_message}\"\n\n"
            f"Parse this into a JSON intent block. "
            f"If it's just a question or chat, set action to 'chat' and reply normally."
        )

        def _worker():
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                )
                text = response.text
                intent = _extract_json(text)
                if on_done: on_done(intent, text)
            except Exception as e:
                if on_error: on_error(f"Intent parsing error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    # ─── Format suggestion ────────────────────────────────────────────────────

    def suggest_format(self, file_path: str,
                       goal: str,
                       on_done: Optional[Callable[[str], None]] = None,
                       on_error: Optional[Callable[[str], None]] = None):
        """Suggest the best output format given a file and a stated goal."""
        if not self.is_ready:
            if on_error: on_error(self.error); return

        fname = Path(file_path).name
        ext   = Path(file_path).suffix.lower()
        prompt = (
            f"File: {fname} (extension: {ext})\n"
            f"User's goal: {goal}\n\n"
            f"Recommend the single best output format and explain why in 2-3 sentences. "
            f"Be specific about which format to choose and why."
        )

        def _worker():
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                )
                if on_done: on_done(response.text)
            except Exception as e:
                if on_error: on_error(f"Suggestion error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def plan_batch(self, file_list: List[str],
                   goal: str,
                   on_done: Optional[Callable[[str], None]] = None,
                   on_error: Optional[Callable[[str], None]] = None):
        """Given a list of files and a goal, plan a sequence of operations."""
        if not self.is_ready:
            if on_error: on_error(self.error); return

        files_str = "\n".join(f"  {i+1}. {Path(f).name}" for i, f in enumerate(file_list))
        prompt = (
            f"I have these files:\n{files_str}\n\n"
            f"My goal: {goal}\n\n"
            f"Plan a step-by-step sequence of file operations to achieve this goal. "
            f"Be specific: for each step, name the file(s), the operation "
            f"(convert/split/merge/organise/compress/protect/stamp), "
            f"and the expected output. Format as a numbered list."
        )

        def _worker():
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                )
                if on_done: on_done(response.text)
            except Exception as e:
                if on_error: on_error(f"Batch planning error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def reset_chat(self):
        """Clear conversation history for a fresh session."""
        self.history.clear()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> Optional[Dict]:
    """Extract the first JSON block from a Gemini response."""
    pattern = r"```json\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    # fallback: try bare JSON object
    match2 = re.search(r'\{[^{}]+\}', text, re.DOTALL)
    if match2:
        try:
            return json.loads(match2.group(0))
        except Exception:
            pass
    return None
