import logging
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.user import Setting
from app.repositories.conversation_repository import ConversationRepository
from app.config.settings import settings
from app.utils.logger import log_event

logger = logging.getLogger(__name__)

class ConversationSummarizer:
    """
    Handles automatic summarization of long conversations to preserve historical context
    without exceeding context limits or slowing down LLM responses.
    """
    def __init__(self, db: Session, ollama_service: Any):
        self.db = db
        self.conv_repo = ConversationRepository(db)
        self.ollama_service = ollama_service

    def check_and_summarize(self, conversation_id: str, model_used: str = "llama3") -> bool:
        """
        Check if the total message count exceeds the summarization threshold compared to
        already summarized messages. If so, summarize older parts and save the summary.
        Returns True if a new summary was generated.
        """
        # Fetch user settings to determine LLM routing (local vs cloud API)
        conv = self.conv_repo.get_by_id(conversation_id)
        llm_provider = "ollama"
        api_key = None
        api_base_url = None
        if conv:
            setting = self.db.query(Setting).filter(Setting.user_id == conv.user_id).first()
            if setting:
                llm_provider = setting.llm_provider
                api_key = setting.api_key
                api_base_url = setting.api_base_url

        all_messages = self.conv_repo.get_messages(conversation_id)
        total_count = len(all_messages)

        latest_summary = self.conv_repo.get_latest_summary(conversation_id)
        already_summarized_count = latest_summary.messages_summarized_count if latest_summary else 0

        unsummarized_count = total_count - already_summarized_count
        if unsummarized_count < settings.SUMMARIZATION_MESSAGE_THRESHOLD:
            return False

        # Determine which messages to summarize (keep the last RECENT_MESSAGES_WINDOW unsummarized)
        messages_to_summarize = all_messages[already_summarized_count : -settings.RECENT_MESSAGES_WINDOW]
        if not messages_to_summarize:
            return False

        new_summarized_count = already_summarized_count + len(messages_to_summarize)

        # Build transcript of messages to summarize
        transcript_lines = []
        for msg in messages_to_summarize:
            speaker = "User" if msg.role == "user" else "Assistant" if msg.role == "assistant" else "System"
            transcript_lines.append(f"{speaker}: {msg.content}")
        transcript = "\n".join(transcript_lines)

        previous_summary_text = latest_summary.summary_text if latest_summary else "None."

        prompt = (
            "Please summarize the following section of a conversation between a User and an AI Assistant. "
            "Integrate any important facts, technical decisions, preferences, and key context with any previous summary provided below.\n\n"
            f"Previous Summary:\n{previous_summary_text}\n\n"
            f"New Messages to Summarize:\n{transcript}\n\n"
            "Provide a clear, concise, objective summary (3-5 bullet points or concise paragraphs) capturing all critical points discussed:"
        )

        try:
            summary_result = self.ollama_service.generate_sync(
                prompt=prompt,
                model=model_used,
                system_prompt="You are an expert conversation summarizer. Be accurate, concise, and preserve key context.",
                temperature=0.3,
                max_tokens=512,
                llm_provider=llm_provider,
                api_key=api_key,
                api_base_url=api_base_url
            )
            if not summary_result or not summary_result.strip():
                # Fallback simple text summary if Ollama offline
                summary_result = f"Summary of {new_summarized_count} messages up to {messages_to_summarize[-1].timestamp.strftime('%Y-%m-%d %H:%M')}."

            self.conv_repo.add_summary(conversation_id, summary_result.strip(), new_summarized_count)
            log_event(
                self.db,
                "CONVERSATION_SUMMARIZED",
                f"Generated summary up to message count {new_summarized_count}",
                metadata={"conversation_id": conversation_id, "messages_summarized": new_summarized_count}
            )
            return True
        except Exception as e:
            logger.error(f"Error during conversation summarization: {e}")
            return False
