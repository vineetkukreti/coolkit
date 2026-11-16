"""Centralized LLM client — Ollama primary (local), NVIDIA primary cloud, Gemini fallback."""

import json
import os
import urllib.request
import requests
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "minimaxai/minimax-m3.1-flash")
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash-lite"


def call_nvidia(prompt: str, system_prompt: str = "", max_tokens: int = 1000, temperature: float = 0.5, model: str | None = None) -> str:
    """Direct call to NVIDIA NIM API."""
    api_key = os.getenv("NVIDIA_API_KEY") or NVIDIA_API_KEY
    if not api_key:
        raise ValueError("NVIDIA_API_KEY not set")

    model_name = model or os.getenv("NVIDIA_MODEL") or NVIDIA_MODEL
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Ensure enough headroom for reasoning models
    token_limit = max(max_tokens, 800)

    resp = requests.post(
        NVIDIA_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_name,
            "messages": messages,
            "max_tokens": token_limit,
            "temperature": temperature,
        },
        timeout=45,
    )
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices")
    if not choices or not isinstance(choices, list) or len(choices) == 0:
        raise ValueError("NVIDIA API returned no choices")

    msg = choices[0].get("message", {})
    content = msg.get("content")
    if not content:
        # Fallback to reasoning_content if content is empty
        content = msg.get("reasoning_content") or ""
    return content.strip()


def call_cloud_llm(prompt: str, system_prompt: str = "", max_tokens: int = 1000, temperature: float = 0.5) -> str:
    """Call cloud LLM: NVIDIA primary, fallback to Gemini."""
    nvidia_key = os.getenv("NVIDIA_API_KEY") or NVIDIA_API_KEY
    gemini_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY

    if nvidia_key:
        try:
            return call_nvidia(prompt, system_prompt=system_prompt, max_tokens=max_tokens, temperature=temperature)
        except Exception as e:
            console.print(f"  [yellow]NVIDIA NIM call failed ({e}), attempting fallback...[/]")
            if not gemini_key:
                raise

    if gemini_key:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={gemini_key}",
            json={
                "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}" if system_prompt else prompt}]}],
                "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens, "topP": 0.9},
            },
            timeout=45,
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    raise ValueError("Neither NVIDIA_API_KEY nor GEMINI_API_KEY is configured")


class LLMClient:
    """Singleton LLM client. Ollama primary (local), NVIDIA primary cloud, Gemini fallback."""

    def __init__(self):
        self._ollama_ok = None
        self._nvidia_ok = None
        self._gemini_ok = None
        self._gemini_client = None

    def _get_gemini_client(self):
        key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
        if self._gemini_client is None and key:
            from google import genai
            self._gemini_client = genai.Client(api_key=key)
        return self._gemini_client

    def ollama_available(self) -> bool:
        if self._ollama_ok is None:
            try:
                req = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
                self._ollama_ok = req.status == 200
                if self._ollama_ok:
                    console.print(f"  [green]LLM: Ollama ({OLLAMA_MODEL}) — local, free[/]")
                else:
                    console.print(f"  [yellow]LLM: Ollama not available, will use cloud fallback[/]")
            except Exception:
                self._ollama_ok = False
                console.print(f"  [yellow]LLM: Ollama not running, will use cloud fallback[/]")
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

    def call_nvidia(self, prompt: str, max_tokens: int = 800, temperature: float = 0, system_prompt: str = "") -> str:
        """Call NVIDIA NIM API."""
        try:
            res = call_nvidia(prompt, system_prompt=system_prompt, max_tokens=max_tokens, temperature=temperature)
            self._nvidia_ok = True
            return res
        except Exception as e:
            if self._nvidia_ok is None:
                console.print(f"  [yellow]NVIDIA NIM failed: {e}[/]")
                self._nvidia_ok = False
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
        """Try Ollama first, then NVIDIA cloud, then Gemini fallback. Returns raw text."""
        result = self.call_ollama(prompt, max_tokens, temperature)
        if result:
            return result

        nvidia_key = os.getenv("NVIDIA_API_KEY") or NVIDIA_API_KEY
        if nvidia_key and self._nvidia_ok is not False:
            res = self.call_nvidia(prompt, max_tokens=max_tokens, temperature=temperature)
            if res:
                return res

        gemini_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
        if gemini_key and self._gemini_ok is not False:
            return self.call_gemini(prompt, max_tokens, temperature)

        return ""

    @property
    def nvidia_ok(self):
        return self._nvidia_ok

    @nvidia_ok.setter
    def nvidia_ok(self, val):
        self._nvidia_ok = val

    @property
    def gemini_ok(self):
        return self._gemini_ok

    @gemini_ok.setter
    def gemini_ok(self, val):
        self._gemini_ok = val


# Module-level singleton
llm = LLMClient()
