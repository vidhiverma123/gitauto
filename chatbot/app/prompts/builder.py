from typing import List, Dict, Any, Optional
from app.models.user import User
from app.models.conversation import Message, ConversationSummary
from app.models.memory import UserMemory
from app.config.settings import settings

class PromptBuilder:
    """
    Dynamically assembles intelligent retrieval-augmented prompts before sending to Ollama.
    Combines:
    1. System instructions
    2. User profile details
    3. Long-term retrieved memories (facts about the user)
    4. Conversation summary (if long history was summarized)
    5. Recent conversation history (last N messages)
    6. Latest user message
    """
    @staticmethod
    def build_system_prompt(
        user: User,
        memories: List[UserMemory],
        summary: Optional[ConversationSummary] = None
    ) -> str:
        lines = [
            "You are an intelligent, helpful, and highly contextual AI Assistant.",
            "You remember facts about the user across sessions and use stored memories to provide personalized, accurate, and insightful responses.",
            "Always render responses using proper Markdown formatting including code blocks, headings, tables, and bulleted lists when appropriate.",
            ""
        ]

        # User Profile Section
        lines.append("### USER PROFILE")
        lines.append(f"- Full Name: {user.full_name}")
        lines.append(f"- Username: {user.username}")
        if user.email:
            lines.append(f"- Email: {user.email}")
        lines.append("")

        # Long-Term Memories Section
        if memories:
            lines.append("### LONG-TERM USER MEMORIES (RETRIEVED FACTS)")
            lines.append("Use these known facts about the user to naturally personalize your response whenever relevant:")
            for mem in memories:
                lines.append(f"- {mem.fact_key.capitalize()}: {mem.fact_value}")
            lines.append("")
        else:
            lines.append("### LONG-TERM USER MEMORIES")
            lines.append("- No specific long-term memories extracted yet.")
            lines.append("")

        # Conversation Summary Section
        if summary and summary.summary_text:
            lines.append("### CONVERSATION SUMMARY (EARLIER MESSAGES)")
            lines.append(summary.summary_text)
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def build_messages_payload(
        user: User,
        memories: List[UserMemory],
        recent_messages: List[Message],
        latest_message: str,
        summary: Optional[ConversationSummary] = None
    ) -> List[Dict[str, str]]:
        """
        Build a list of message objects formatted for Ollama `/api/chat` endpoint.
        """
        system_prompt = PromptBuilder.build_system_prompt(user, memories, summary)
        
        payload: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        # Add recent conversation history (excluding the latest message if already present)
        for msg in recent_messages:
            # Skip if it's the exact same message ID or text as latest_message being appended right now
            if msg.role in ["user", "assistant"]:
                payload.append({"role": msg.role, "content": msg.content})

        # Ensure the latest user input is included at the end
        if not payload or payload[-1].get("content") != latest_message:
            payload.append({"role": "user", "content": latest_message})

        return payload

    @staticmethod
    def build_full_prompt_debug_string(
        user: User,
        memories: List[UserMemory],
        recent_messages: List[Message],
        latest_message: str,
        summary: Optional[ConversationSummary] = None
    ) -> str:
        """
        Returns the exact combined prompt string for debugging, README demonstration, or UI inspection.
        """
        system_part = PromptBuilder.build_system_prompt(user, memories, summary)
        history_lines = ["### RECENT CONVERSATION HISTORY"]
        if recent_messages:
            for msg in recent_messages:
                speaker = "User" if msg.role == "user" else "Assistant"
                history_lines.append(f"{speaker}: {msg.content}")
        else:
            history_lines.append("- No earlier messages in this window.")
        history_lines.append("")
        history_lines.append("### LATEST USER MESSAGE")
        history_lines.append(f"User: {latest_message}")
        history_lines.append("\nAssistant:")

        return system_part + "\n" + "\n".join(history_lines)
