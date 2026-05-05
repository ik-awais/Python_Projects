"""
ai/nvidia_nim.py — NVIDIA NIM AI integration
Drop-in replacement for gemini.py using the OpenAI-compatible NIM API.
"""
import threading
import re, json
from pathlib import Path
from typing import List, Dict, Optional, Callable
try:
    from openai import OpenAI
    HAS_NIM = True
except ImportError:
    HAS_NIM = False
NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_MODELS = [
    "meta/llama-3.3-70b-instruct",
    "meta/llama-3.1-70b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "mistralai/mistral-large-2-instruct",
    "qwen/qwen3.5-122b-a10b",
]
SYSTEM_PROMPT = """You are an AI assistant embedded inside File Workshop —
a local desktop tool for converting, splitting, merging, organising,
stamping, protecting, compressing and extracting content from files
(PDF, Word, Excel, PowerPoint, CSV, images, audio, video).
Your job
1. Answer questions about the user's loaded files.
2. Understand natural-language commands and map them to tool actions.
3. Summarise, analyse, and explain file content when asked.
4. Suggest the best output format for a given task.
5. Be concise and precise.
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
Supported actions: convert, split, merge, organise, compress, protect,
                   stamp, summarise, analyse, chat, unknown
If the user is just chatting, set action to "chat" and reply normally.
"""
class NIMClient:
    """NVIDIA NIM client — OpenAI-compatible, drop-in for GeminiClient."""
    def __init__(self, api_key: str, model_name: str = "meta/llama-3.3-70b-instruct"):
        self.api_key    = api_key
        self.model_name = model_name
        self.history: List[Dict] = []
        self._ready  = False
        self._error  = ""
        self._client = None
        if api_key:
            self._init(api_key, model_name)

    def _init(self, api_key: str, model_name: str):
        if not HAS_NIM:
            self._error = "openai not installed.\nRun: pip install openai"
            return
        
        # Debug: Log API key details
        print(f"[DEBUG] NIM _init - API key length: {len(api_key)}, First 10 chars: {api_key[:10] if api_key else 'None'}")
        
        # Validate API key format (NVIDIA NIM keys are typically longer strings)
        if api_key and len(api_key) < 20:
            print(f"[WARNING] NVIDIA API key may be invalid - too short ({len(api_key)} chars)")
        
        try:
            # Initialize OpenAI client with only supported arguments
            self._client = OpenAI(
                api_key=api_key,
                base_url=NIM_BASE_URL
            )
            self.model_name = model_name
            self._ready = True
            self._error = ""
            print(f"[DEBUG] NIM client initialized successfully")
        except Exception as e:
            self._ready = False
            self._error = str(e)
            print(f"[ERROR] NIM client initialization failed: {e}")

    def reconfigure(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.history.clear()
        self._init(api_key, model_name)

    @property
    def is_ready(self) -> bool:
        return self._ready and HAS_NIM

    @property
    def error(self) -> str:
        if not HAS_NIM:
            return "openai package not installed.\nRun: pip install openai"
        return self._error

    def _build_messages(self, user_prompt: str, context: str = "") -> List[Dict]:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        # Add rolling history (last 10 exchanges)
        for turn in self.history[-20:]:
            role = "user" if turn["role"] == "user" else "assistant"
            msgs.append({"role": role, "content": turn["text"]})
        content = user_prompt
        if context:
            content = f"[Loaded files context]\n{context}\n\n[User]\n{user_prompt}"
        msgs.append({"role": "user", "content": content})
        return msgs

    def _call(self, messages: List[Dict], on_done, on_error, label=""):
        def _worker():
            try:
                response = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=2048,
                    temperature=0.6,
                )
                text = response.choices[0].message.content
                if on_done: on_done(text)
            except Exception as e:
                if on_error: on_error(f"NIM error: {e}")
        threading.Thread(target=_worker, daemon=True).start()

    def chat(self, user_message: str, context: str = "",
             on_done=None, on_error=None):
        if not self.is_ready:
            if on_error: on_error(self.error); return
        msgs = self._build_messages(user_message, context)
        def _done(text):
            self.history.append({"role": "user",      "text": user_message})
            self.history.append({"role": "assistant", "text": text})
            if on_done: on_done(text)
        self._call(msgs, _done, on_error)

    def analyse_image(self, image_path: str,
                      prompt: str = "Describe this image in detail.",
                      on_done=None, on_error=None):
        """Image analysis via vision-capable NIM models."""
        if not self.is_ready:
            if on_error: on_error(self.error); return
        import base64, mimetypes
        def _worker():
            try:
                with open(image_path, "rb") as f:
                    data = base64.b64encode(f.read()).decode()
                mime, _ = mimetypes.guess_type(image_path)
                mime = mime or "image/png"
                response = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url",
                             "image_url": {"url": f"data:{mime};base64,{data}"}}
                        ]
                    }],
                    max_tokens=1024,
                )
                if on_done: on_done(response.choices[0].message.content)
            except Exception as e:
                if on_error: on_error(f"Image analysis error: {e}")
        threading.Thread(target=_worker, daemon=True).start()

    def summarise_document(self, file_path: str, text_content: str,
                           on_done=None, on_error=None):
        if not self.is_ready:
            if on_error: on_error(self.error); return
        fname = Path(file_path).name
        prompt = (
            f"Provide a comprehensive summary of this document: '{fname}'\n\n"
            f"Include: main topic, key points (bullet list), "
            f"important data/numbers/conclusions, suggested action items.\n\n"
            f"Document content:\n{text_content[:12000]}"
        )
        self._call([{"role":"system","content":SYSTEM_PROMPT},
                    {"role":"user","content":prompt}], on_done, on_error)

    def ask_document(self, file_path: str, text_content: str,
                     question: str, on_done=None, on_error=None):
        if not self.is_ready:
            if on_error: on_error(self.error); return
        fname = Path(file_path).name
        prompt = (
            f"Document: '{fname}'\n\nContent:\n{text_content[:12000]}\n\n"
            f"Question: {question}\n\n"
            f"Answer based only on the document. If not found, say so."
        )
        self._call([{"role":"system","content":SYSTEM_PROMPT},
                    {"role":"user","content":prompt}], on_done, on_error)

    def suggest_format(self, file_path: str, goal: str,
                       on_done=None, on_error=None):
        if not self.is_ready:
            if on_error: on_error(self.error); return
        fname = Path(file_path).name
        ext   = Path(file_path).suffix.lower()
        prompt = (
            f"File: {fname} ({ext})\nGoal: {goal}\n\n"
            f"Recommend the single best output format and explain why in 2-3 sentences."
        )
        self._call([{"role":"system","content":SYSTEM_PROMPT},
                    {"role":"user","content":prompt}], on_done, on_error)

    def plan_batch(self, file_list: List[str], goal: str,
                   on_done=None, on_error=None):
        if not self.is_ready:
            if on_error: on_error(self.error); return
        files_str = "\n".join(f"  {i+1}. {Path(f).name}" for i,f in enumerate(file_list))
        prompt = (
            f"Files:\n{files_str}\n\nGoal: {goal}\n\n"
            f"Plan step-by-step file operations to achieve this. "
            f"For each step: file name, operation, expected output. Numbered list."
        )
        self._call([{"role":"system","content":SYSTEM_PROMPT},
                    {"role":"user","content":prompt}], on_done, on_error)

    def reset_chat(self):
        self.history.clear()


def _extract_json(text: str):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try: return json.loads(match.group(1))
        except: pass
    match2 = re.search(r'\{[^{}]+\}', text, re.DOTALL)
    if match2:
        try: return json.loads(match2.group(0))
        except: pass
    return None