import json
import logging
import time
from typing import List, Dict, Any, Generator, Optional
import requests
from app.config.settings import settings

logger = logging.getLogger(__name__)

class OllamaService:
    """
    Hybrid Service client supporting both local Ollama LLM and cloud LLM providers
    (OpenAI, Google Gemini, Custom OpenAI-Compatible) based on user settings.
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

    def list_available_models(self, llm_provider: str = "ollama") -> List[str]:
        """
        Return list of model names available for the given LLM provider.
        For Ollama, fetches live pulled models from the local engine.
        """
        if llm_provider == "openai":
            return ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
        elif llm_provider == "gemini":
            return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.0-pro"]
        elif llm_provider == "custom":
            return ["custom-model"]
        
        # Default Ollama behavior
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                models = [model["name"].split(":")[0] for model in data.get("models", [])]
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
        max_tokens: int = 1024,
        llm_provider: str = "ollama",
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None
    ) -> str:
        """
        Synchronous non-streaming generation. Automatically routes to cloud LLMs
        if provider is OpenAI/Gemini/Custom.
        """
        # Create standard message payload for OpenAI/Gemini/Custom
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        if llm_provider == "openai":
            return self._generate_sync_openai("https://api.openai.com/v1", api_key or "", messages, model, temperature, max_tokens)
        elif llm_provider == "gemini":
            return self._generate_sync_openai("https://generativelanguage.googleapis.com/v1beta/openai", api_key or "", messages, model, temperature, max_tokens)
        elif llm_provider == "custom" and api_base_url:
            return self._generate_sync_openai(api_base_url, api_key or "", messages, model, temperature, max_tokens)

        # Local Ollama fallback
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
        max_tokens: int = 1024,
        llm_provider: str = "ollama",
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Generator that streams response tokens in real-time. Routes to cloud APIs if configured.
        """
        if llm_provider == "openai":
            return self._generate_stream_openai("https://api.openai.com/v1", api_key or "", messages, model, temperature, max_tokens)
        elif llm_provider == "gemini":
            return self._generate_stream_openai("https://generativelanguage.googleapis.com/v1beta/openai", api_key or "", messages, model, temperature, max_tokens)
        elif llm_provider == "custom" and api_base_url:
            return self._generate_stream_openai(api_base_url, api_key or "", messages, model, temperature, max_tokens)

        # Local Ollama fallback
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
            yield (
                f"\n\n> **Notice: Cannot connect to local Ollama server at `{self.base_url}`.**\n\n"
                f"To power live LLM responses with **{model}** locally, please start your Ollama engine:\n"
                "```bash\n"
                f"ollama run {model}\n"
                "```\n"
                "*(Or configuration cloud model settings and paste an API key inside the settings view!)*"
            )
        except Exception as e:
            logger.error(f"Error streaming from Ollama: {e}")
            yield f"\n\n**Error during streaming generation:** `{str(e)}`"

    def _generate_sync_openai(
        self,
        base_url: str,
        api_key: str,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            else:
                logger.error(f"OpenAI-compatible API returned error {resp.status_code}: {resp.text}")
                return ""
        except Exception as e:
            logger.error(f"Error calling OpenAI-compatible generate_sync: {e}")
            return ""

    def _generate_stream_openai(
        self,
        base_url: str,
        api_key: str,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Generator[str, None, None]:
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        try:
            with requests.post(url, json=payload, headers=headers, stream=True, timeout=self.timeout) as resp:
                if resp.status_code != 200:
                    yield f"\n\n**API Error ({resp.status_code}):** `{resp.text}`"
                    return

                for line in resp.iter_lines():
                    if line:
                        line_str = line.decode('utf-8').strip()
                        # Some streaming responses prefix the JSON lines with "data: "
                        if line_str.startswith("data: "):
                            data_content = line_str[6:].strip()
                            if data_content == "[DONE]":
                                break
                            try:
                                data = json.loads(data_content)
                                content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"Error streaming from OpenAI-compatible API: {e}")
            yield f"\n\n**Error during streaming generation:** `{str(e)}`"
