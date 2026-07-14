import json
import re
import logging
from typing import List, Dict, Tuple, Optional, Any
from sqlalchemy.orm import Session
from app.repositories.memory_repository import MemoryRepository
from app.utils.logger import log_event

logger = logging.getLogger(__name__)

class MemoryExtractor:
    """
    Extracts long-term user memories (e.g. personal facts, preferences, background info)
    from user messages using Ollama structured extraction plus regex fallback.
    """
    def __init__(self, db: Session, ollama_service: Optional[Any] = None):
        self.db = db
        self.memory_repo = MemoryRepository(db)
        self.ollama_service = ollama_service

    def extract_and_store(self, user_id: str, message_text: str, model_used: str = "llama3") -> List[Tuple[str, str]]:
        """
        Extract self-facts from the user's input and store them in PostgreSQL user_memory table.
        Returns a list of tuples (fact_key, fact_value) that were newly extracted or updated.
        """
        extracted_facts: List[Tuple[str, str]] = []

        # 1. First, try rule-based regex extraction for instant high-confidence matching
        regex_facts = self._extract_via_regex(message_text)
        for key, val in regex_facts:
            extracted_facts.append((key, val))

        # 2. Next, if Ollama service is provided, ask LLM for any complex or subtle facts not caught by regex
        if self.ollama_service and len(message_text.split()) > 3:
            llm_facts = self._extract_via_llm(message_text, model_used)
            for key, val in llm_facts:
                if not any(k.lower() == key.lower() for k, _ in extracted_facts):
                    extracted_facts.append((key, val))

        # Store extracted facts
        stored_results = []
        for key, val in extracted_facts:
            try:
                mem = self.memory_repo.create_or_update_memory(
                    user_id=user_id,
                    fact_key=key,
                    fact_value=val,
                    raw_text=message_text
                )
                stored_results.append((mem.fact_key, mem.fact_value))
                log_event(
                    self.db,
                    "MEMORY_EXTRACTED",
                    f"Extracted long-term memory fact [{mem.fact_key}: {mem.fact_value}]",
                    user_id=user_id,
                    metadata={"fact_key": mem.fact_key, "fact_value": mem.fact_value, "source_text": message_text}
                )
            except Exception as e:
                logger.error(f"Error storing extracted memory: {e}")

        return stored_results

    def _extract_via_regex(self, text: str) -> List[Tuple[str, str]]:
        facts = []
        clean_text = text.strip()

        # Patterns matching common user statements
        patterns = [
            (r"(?i)\bmy favorite programming language is\s+([a-zA-Z0-9_\+\-\.\s]+?)(?:\.|$|,|\bbecause\b)", "favorite programming language"),
            (r"(?i)\bmy favorite food is\s+([a-zA-Z0-9_\-\s]+?)(?:\.|$|,|\band\b)", "favorite food"),
            (r"(?i)\bmy birthday is\s+([a-zA-Z0-9\s]+?)(?:\.|$|,)", "birthday"),
            (r"(?i)\bi work as a\s+([a-zA-Z\s]+?)(?:\.|$|,|\bat\b)", "profession"),
            (r"(?i)\bi work as an\s+([a-zA-Z\s]+?)(?:\.|$|,|\bat\b)", "profession"),
            (r"(?i)\bi have a dog named\s+([a-zA-Z]+)(?:\.|$|,)", "dog's name"),
            (r"(?i)\bi have a cat named\s+([a-zA-Z]+)(?:\.|$|,)", "cat's name"),
            (r"(?i)\bi live in\s+([a-zA-Z\s]+?)(?:\.|$|,|\band\b)", "location"),
            (r"(?i)\bi am from\s+([a-zA-Z\s]+?)(?:\.|$|,|\band\b)", "hometown"),
        ]

        for pattern, fact_key in patterns:
            match = re.search(pattern, clean_text)
            if match:
                val = match.group(1).strip()
                if len(val) >= 2 and len(val) <= 100:
                    facts.append((fact_key, val))

        return facts

    def _extract_via_llm(self, text: str, model_used: str) -> List[Tuple[str, str]]:
        try:
            prompt = (
                "Analyze the following user statement and extract any personal facts, attributes, preferences, or background details "
                "about the user (such as favorite things, job/profession, pets, birthday, location, hobbies, etc.).\n\n"
                f"User Statement: \"{text}\"\n\n"
                "Return ONLY a JSON array of objects with keys 'key' and 'value'. Example: [{\"key\": \"favorite programming language\", \"value\": \"Python\"}]\n"
                "If no clear personal fact about the user is present, return exactly []."
            )
            response_text = self.ollama_service.generate_sync(
                prompt=prompt,
                model=model_used,
                system_prompt="You are a precise data extraction specialist. Output valid JSON only, without markdown fences or extra commentary.",
                temperature=0.1,
                max_tokens=256
            )
            if not response_text:
                return []

            # Parse JSON safely from possible markdown fences
            clean_json = response_text.strip()
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0].strip()

            parsed = json.loads(clean_json)
            if isinstance(parsed, list):
                result = []
                for item in parsed:
                    if isinstance(item, dict) and "key" in item and "value" in item:
                        k = str(item["key"]).strip().lower()
                        v = str(item["value"]).strip()
                        if len(k) >= 2 and len(v) >= 1 and len(v) <= 200:
                            result.append((k, v))
                return result
        except Exception as e:
            logger.warning(f"LLM memory extraction fallback encountered minor error or Ollama offline: {e}")
        return []
