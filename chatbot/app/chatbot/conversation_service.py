import time
import logging
from typing import List, Dict, Any, Generator, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.conversation import Conversation, Message, Tag
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.memory_repository import MemoryRepository
from app.prompts.builder import PromptBuilder
from app.chatbot.ollama_service import OllamaService
from app.memory.extractor import MemoryExtractor
from app.memory.summarizer import ConversationSummarizer
from app.utils.logger import log_event

logger = logging.getLogger(__name__)

class ConversationService:
    """
    Core orchestration service for managing chat sessions, executing the memory retrieval pipeline,
    streaming LLM responses, extracting long-term user memories, auto-titling, and auto-tagging.
    """
    def __init__(self, db: Session, ollama_service: Optional[OllamaService] = None):
        self.db = db
        self.conv_repo = ConversationRepository(db)
        self.memory_repo = MemoryRepository(db)
        self.ollama_service = ollama_service or OllamaService()
        self.memory_extractor = MemoryExtractor(db, self.ollama_service)
        self.summarizer = ConversationSummarizer(db, self.ollama_service)

    def start_new_conversation(self, user_id: str, model_used: str = "llama3") -> Conversation:
        conv = self.conv_repo.create_conversation(user_id=user_id, title="New Chat", model_used=model_used)
        log_event(self.db, "CONVERSATION_CREATED", f"New conversation started: {conv.id}", user_id=user_id)
        return conv

    def send_message_and_stream_response(
        self,
        user: User,
        conversation_id: str,
        user_message_text: str,
        model_used: str = "llama3",
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> Generator[str, None, str]:
        """
        Executes memory retrieval pipeline, records user message, streams Ollama response token-by-token,
        and runs post-generation hooks (memory extraction, auto-titling, tagging, and summarization).
        Yields tokens to UI and returns the full accumulated assistant text.
        """
        # 1. Record user message in database immediately
        self.conv_repo.add_message(
            conversation_id=conversation_id,
            user_id=user.id,
            role="user",
            content=user_message_text,
            model_used=model_used
        )

        # 2. Run Memory Retrieval Pipeline
        long_term_memories = self.memory_repo.get_user_memories(user.id)
        conversation_summary = self.conv_repo.get_latest_summary(conversation_id)
        recent_messages = self.conv_repo.get_messages(conversation_id, limit=12)

        # Build combined messages payload for Ollama
        messages_payload = PromptBuilder.build_messages_payload(
            user=user,
            memories=long_term_memories,
            recent_messages=recent_messages,
            latest_message=user_message_text,
            summary=conversation_summary
        )

        # 3. Stream response from Ollama while tracking timing
        start_time = time.time()
        accumulated_tokens: List[str] = []

        token_generator = self.ollama_service.generate_stream(
            messages=messages_payload,
            model=model_used,
            temperature=temperature,
            max_tokens=max_tokens
        )

        for token in token_generator:
            accumulated_tokens.append(token)
            yield token

        response_time_ms = round((time.time() - start_time) * 1000.0, 2)
        full_assistant_response = "".join(accumulated_tokens).strip()

        # 4. Record assistant message and timing
        self.conv_repo.add_message(
            conversation_id=conversation_id,
            user_id=user.id,
            role="assistant",
            content=full_assistant_response if full_assistant_response else "[Empty Response / Offline Notice]",
            model_used=model_used,
            response_time_ms=response_time_ms
        )
        log_event(
            self.db,
            "OLLAMA_RESPONSE",
            f"Generated response using {model_used} in {response_time_ms}ms",
            user_id=user.id,
            metadata={"conversation_id": conversation_id, "model": model_used, "time_ms": response_time_ms}
        )

        # 5. Post-Turn Background/Orchestrated Hooks:
        # A. Long-term memory extraction from the user's latest message
        self.memory_extractor.extract_and_store(user.id, user_message_text, model_used)

        # B. Auto-Generate Title and Tags if conversation is still "New Chat" and has at least 1-2 exchanges
        conv = self.conv_repo.get_by_id(conversation_id)
        if conv and conv.title == "New Chat":
            self.auto_generate_title_and_tags(conv, user_message_text, model_used)

        # C. Check for auto-summarization
        self.summarizer.check_and_summarize(conversation_id, model_used)

        return full_assistant_response

    def auto_generate_title_and_tags(self, conversation: Conversation, first_user_message: str, model_used: str) -> None:
        """
        Automatically generates a clean, descriptive title (e.g. 'Python decorators explanation')
        and assigns relevant tags from predefined categories.
        """
        try:
            prompt = (
                "Given the following user query, generate a concise, descriptive title (maximum 5 words) "
                "and select 1 or 2 relevant tags from this exact list: [Programming, SQL, AI, Travel, Finance, Education, Personal].\n\n"
                f"User Query: \"{first_user_message}\"\n\n"
                "Return ONLY valid JSON in this exact format:\n"
                "{\"title\": \"Python decorators explanation\", \"tags\": [\"Programming\"]}"
            )
            resp = self.ollama_service.generate_sync(
                prompt=prompt,
                model=model_used,
                system_prompt="You are an expert taxonomy and title classifier. Return pure JSON only.",
                temperature=0.2,
                max_tokens=128
            )
            if resp:
                clean_json = resp.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()

                data = json.loads(clean_json)
                new_title = data.get("title", "").strip()
                tags_list = data.get("tags", [])

                if new_title and len(new_title) > 2:
                    self.conv_repo.update_title(conversation.id, new_title[:100])

                if isinstance(tags_list, list) and tags_list:
                    valid_categories = ["Programming", "SQL", "AI", "Travel", "Finance", "Education", "Personal"]
                    matched_tags = [t for t in tags_list if any(t.lower() == v.lower() for v in valid_categories)]
                    if matched_tags:
                        self.conv_repo.add_tags_to_conversation(conversation.id, matched_tags)
        except Exception as e:
            # Fallback keyword-based titling and tagging if offline/error
            fallback_title = (first_user_message[:35] + "...") if len(first_user_message) > 35 else first_user_message
            self.conv_repo.update_title(conversation.id, fallback_title.capitalize())

            # Fallback tag detection
            kw_tags = []
            lower_msg = first_user_message.lower()
            if any(k in lower_msg for k in ["python", "code", "bug", "function", "api", "react"]): kw_tags.append("Programming")
            if any(k in lower_msg for k in ["sql", "database", "postgres", "query", "table"]): kw_tags.append("SQL")
            if any(k in lower_msg for k in ["ai", "llm", "chatgpt", "ollama", "model", "neural"]): kw_tags.append("AI")
            if any(k in lower_msg for k in ["trip", "flight", "hotel", "japan", "travel"]): kw_tags.append("Travel")
            if kw_tags:
                self.conv_repo.add_tags_to_conversation(conversation.id, kw_tags)

    def get_debug_prompt_display(self, user: User, conversation_id: str, latest_query: str) -> str:
        """
        Returns the human-readable prompt string showing how memories, profile, and history are combined.
        """
        long_term_memories = self.memory_repo.get_user_memories(user.id)
        conversation_summary = self.conv_repo.get_latest_summary(conversation_id)
        recent_messages = self.conv_repo.get_messages(conversation_id, limit=10)

        return PromptBuilder.build_full_prompt_debug_string(
            user=user,
            memories=long_term_memories,
            recent_messages=recent_messages,
            latest_message=latest_query,
            summary=conversation_summary
        )
