import json
import logging
import time
from typing import List, Dict, Any, Generator, Optional
import requests
from app.config.settings import settings

logger = logging.getLogger(__name__)

class OllamaService:
    """
    Service client for interacting with local Ollama LLM server.
    Supports both synchronous generation and streaming token-by-token responses.
    """
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = settings.OLLAMA_TIMEOUT

    def check_connection(self) -> bool:
        """
        Check if the local Ollama server is up and responsive.
        """
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3.0)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama connection check failed at {self.base_url}: {e}")
            return False

    def list_available_models(self) -> List[str]:
        """
        Return list of model names available in local Ollama installation.
        If offline, returns the default configured list.
        """
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                models = [model["name"].split(":")[0] for model in data.get("models", [])]
                # Ensure distinct and sorted
                unique_models = sorted(list(set(models)))
                if unique_models:
                    return unique_models
        except Exception:
            pass
        return settings.SUPPORTED_OLLAMA_MODELS

    def generate_sync(
        self,
        prompt: str,
        model: str = "llama3",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """
        Synchronous non-streaming generation via /api/generate.
        Useful for internal tasks like memory extraction and summarization.
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "").strip()
            else:
                logger.error(f"Ollama returned error {resp.status_code}: {resp.text}")
                return ""
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {url}. Is Ollama running?")
            return ""
        except Exception as e:
            logger.error(f"Exception calling Ollama generate_sync: {e}")
            return ""

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama3",
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> Generator[str, None, None]:
        """
        Generator that streams response tokens in real-time from Ollama /api/chat endpoint.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        start_time = time.time()
        try:
            with requests.post(url, json=payload, stream=True, timeout=self.timeout) as resp:
                if resp.status_code != 200:
                    err_msg = f"\n\n**Ollama Server Error ({resp.status_code}):** `{resp.text}`\nPlease verify that the model `{model}` is pulled (`ollama pull {model}`)."
                    yield err_msg
                    return

                for line in resp.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except requests.exceptions.ConnectionError:
            # Provide helpful offline explanation so user is never stuck
            yield (
                f"\n\n> **Notice: Cannot connect to local Ollama server at `{self.base_url}`.**\n\n"
                f"To power live LLM responses with **{model}** locally, please start your Ollama engine:\n"
                "```bash\n"
                f"ollama run {model}\n"
                "```\n"
                "*(Or check out our README for full setup instructions!)*"
            )
        except Exception as e:
            logger.error(f"Error streaming from Ollama: {e}")
            yield f"\n\n**Error during streaming generation:** `{str(e)}`"
