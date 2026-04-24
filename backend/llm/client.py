"""Centralized LLM client — Ollama primary, Gemini fallback."""

import json
import os
import urllib.request

from rich.console import Console

console = Console()

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash-lite"


class LLMClient:
    """Singleton LLM client. Ollama primary, Gemini fallback."""

    def __init__(self):
        self._ollama_ok = None
        self._gemini_ok = None
        self._gemini_client = None

    def _get_gemini_client(self):
        if self._gemini_client is None and GEMINI_API_KEY:
            from google import genai
            self._gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        return self._gemini_client

    def ollama_available(self) -> bool:
        if self._ollama_ok is None:
            try:
                req = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
                self._ollama_ok = req.status == 200
                if self._ollama_ok:
                    console.print(f"  [green]LLM: Ollama ({OLLAMA_MODEL}) — local, free[/]")
                else:
                    console.print(f"  [yellow]LLM: Ollama not available, will use Gemini fallback[/]")
            except Exception:
                self._ollama_ok = False
                console.print(f"  [yellow]LLM: Ollama not running, will use Gemini fallback[/]")
        return self._ollama_ok

    def call_ollama(self, prompt: str, max_tokens: int = 80, temperature: float = 0) -> str:
        """Call Ollama and return raw text response. Empty string on failure."""
        if not self.ollama_available():
            return ""

        payload = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }).encode()

        try:
            req = urllib.request.Request(
                OLLAMA_URL, data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=max(15, max_tokens // 10))
            result = json.loads(resp.read())
            return result.get("response", "").strip()
        except Exception:
            return ""

    def call_gemini(self, prompt: str, max_tokens: int = 150, temperature: float = 0) -> str:
        """Call Gemini and return raw text response. Empty string on failure."""
        client = self._get_gemini_client()
        if not client:
            self._gemini_ok = False
            return ""

        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"temperature": temperature, "max_output_tokens": max_tokens},
            )
            self._gemini_ok = True
            return response.text.strip()
        except Exception as e:
            if self._gemini_ok is None:
                console.print(f"  [yellow]Gemini failed: {e}[/]")
                self._gemini_ok = False
            return ""

    def call(self, prompt: str, max_tokens: int = 150, temperature: float = 0) -> str:
        """Try Ollama first, fall back to Gemini. Returns raw text."""
        result = self.call_ollama(prompt, max_tokens, temperature)
        if result:
            return result

        if GEMINI_API_KEY and self._gemini_ok is not False:
            return self.call_gemini(prompt, max_tokens, temperature)

        return ""

    @property
    def gemini_ok(self):
        return self._gemini_ok

    @gemini_ok.setter
    def gemini_ok(self, val):
        self._gemini_ok = val


# Module-level singleton
llm = LLMClient()
