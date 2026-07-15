from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, func, or_, distinct
from sqlalchemy.orm import Session
from app.models.conversation import Conversation, Message, ConversationSummary, Tag
from app.config.settings import settings

class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_conversation(self, user_id: str, title: str = "New Chat", model_used: str = "llama3") -> Conversation:
        conv = Conversation(
            user_id=user_id,
            title=title,
            ollama_model_used=model_used
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(Conversation.id == conversation_id).first()

    def get_user_conversations(self, user_id: str) -> List[Conversation]:
        """
        Get all conversations for a user, ordered by pinned status first, then most recently updated.
        """
        return self.db.query(Conversation).filter(Conversation.user_id == user_id).order_by(
            desc(Conversation.is_pinned),
            desc(Conversation.updated_at)
        ).all()

    def update_title(self, conversation_id: str, title: str) -> Optional[Conversation]:
        conv = self.get_by_id(conversation_id)
        if conv:
            conv.title = title
            conv.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(conv)
        return conv

    def toggle_pin(self, conversation_id: str, is_pinned: Optional[bool] = None) -> Optional[Conversation]:
        conv = self.get_by_id(conversation_id)
        if conv:
            if is_pinned is not None:
                conv.is_pinned = is_pinned
            else:
                conv.is_pinned = not conv.is_pinned
            conv.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(conv)
        return conv

    def delete_conversation(self, conversation_id: str) -> bool:
        conv = self.get_by_id(conversation_id)
        if conv:
            self.db.delete(conv)
            self.db.commit()
            return True
        return False

    def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        model_used: Optional[str] = None,
        response_time_ms: Optional[float] = None
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            ollama_model_used=model_used,
            response_time_ms=response_time_ms
        )
        self.db.add(msg)
        
        # Update conversation timestamp and last model used
        conv = self.get_by_id(conversation_id)
        if conv:
            conv.updated_at = datetime.now(timezone.utc)
            if model_used:
                conv.ollama_model_used = model_used

        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_messages(self, conversation_id: str, limit: Optional[int] = None) -> List[Message]:
        query = self.db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp.asc())
        if limit:
            # Get the most recent `limit` messages
            all_msgs = query.all()
            return all_msgs[-limit:] if len(all_msgs) > limit else all_msgs
        return query.all()

    def search_conversations(self, user_id: str, keyword: Optional[str] = None, tag_name: Optional[str] = None) -> List[Conversation]:
        """
        Search conversations by keyword across titles and message contents (Full-Text Search / ILIKE)
        and optionally filter by tag.
        """
        query = self.db.query(Conversation).filter(Conversation.user_id == user_id)

        if tag_name and tag_name != "All":
            query = query.join(Conversation.tags).filter(Tag.name == tag_name)

        if keyword and keyword.strip():
            kw = keyword.strip()
            # If PostgreSQL, leverage text search or ILIKE across titles and messages
            # We use distinct outer join on messages so matches in either title or message text return the conversation
            query = query.outerjoin(Message, Conversation.id == Message.conversation_id).filter(
                or_(
                    Conversation.title.ilike(f"%{kw}%"),
                    Message.content.ilike(f"%{kw}%")
                )
            ).distinct()

        return query.order_by(desc(Conversation.is_pinned), desc(Conversation.updated_at)).all()

    def add_summary(self, conversation_id: str, summary_text: str, count: int) -> ConversationSummary:
        summary = ConversationSummary(
            conversation_id=conversation_id,
            summary_text=summary_text,
            messages_summarized_count=count
        )
        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)
        return summary

    def get_latest_summary(self, conversation_id: str) -> Optional[ConversationSummary]:
        return self.db.query(ConversationSummary).filter(
            ConversationSummary.conversation_id == conversation_id
        ).order_by(desc(ConversationSummary.created_at)).first()

    def add_tags_to_conversation(self, conversation_id: str, tag_names: List[str]) -> List[Tag]:
        conv = self.get_by_id(conversation_id)
        if not conv or not tag_names:
            return []

        tags_added = []
        for name in tag_names:
            clean_name = name.strip().capitalize()
            if not clean_name:
                continue
            tag = self.db.query(Tag).filter(Tag.name.ilike(clean_name)).first()
            if not tag:
                tag = Tag(name=clean_name)
                self.db.add(tag)
                self.db.commit()
                self.db.refresh(tag)
            if tag not in conv.tags:
                conv.tags.append(tag)
                tags_added.append(tag)

        self.db.commit()
        self.db.refresh(conv)
        return tags_added

    def get_all_tags(self) -> List[Tag]:
        return self.db.query(Tag).order_by(Tag.name.asc()).all()

    def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """
        Calculate total conversations, total messages, average messages per conversation,
        most active day, most frequently used Ollama model, and average response time.
        """
        total_convs = self.db.query(Conversation).filter(Conversation.user_id == user_id).count()
        
        user_messages_query = self.db.query(Message).filter(Message.user_id == user_id)
        total_msgs = user_messages_query.count()

        avg_msgs_per_conv = round(total_msgs / total_convs, 1) if total_convs > 0 else 0.0

        # Most frequently used Ollama model for this user's messages
        model_counts = self.db.query(
            Message.ollama_model_used, func.count(Message.id)
        ).filter(
            Message.user_id == user_id,
            Message.ollama_model_used.isnot(None),
            Message.role == "assistant"
        ).group_by(Message.ollama_model_used).order_by(desc(func.count(Message.id))).first()

        most_used_model = model_counts[0] if model_counts and model_counts[0] else "None"

        # Average assistant response time
        avg_time = self.db.query(
            func.avg(Message.response_time_ms)
        ).filter(
            Message.user_id == user_id,
            Message.role == "assistant",
            Message.response_time_ms.isnot(None)
        ).scalar()
        avg_response_time_ms = round(avg_time, 1) if avg_time else 0.0

        # Most active day
        all_msgs = user_messages_query.all()
        most_active_day = "No activity yet"
        if all_msgs:
            days_count: Dict[str, int] = {}
            for m in all_msgs:
                if m.timestamp:
                    day_str = m.timestamp.strftime("%Y-%m-%d (%A)")
                    days_count[day_str] = days_count.get(day_str, 0) + 1
            if days_count:
                most_active_day = max(days_count, key=days_count.get)

        return {
            "total_conversations": total_convs,
            "total_messages": total_msgs,
            "avg_messages_per_conversation": avg_msgs_per_conv,
            "most_active_day": most_active_day,
            "most_frequently_used_model": most_used_model,
            "avg_assistant_response_time_ms": avg_response_time_ms
        }

    def get_top_conversations(self, user_id: str, condition: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve top conversations for a user based on a specific metric condition.
        Returns a list of dictionaries with conversation fields and calculated metric info.
        """
        from sqlalchemy import desc, asc, func

        # Choose the query based on the condition
        if condition == "most_messages":
            # Group by Conversation.id and count Message.id
            query = (
                self.db.query(
                    Conversation,
                    func.count(Message.id).label("metric")
                )
                .join(Message, Conversation.id == Message.conversation_id)
                .filter(Conversation.user_id == user_id)
                .group_by(Conversation.id)
                .order_by(desc("metric"))
                .limit(limit)
            )
            metric_label = "Messages"
            formatter = lambda val: f"{int(val) if val is not None else 0} messages"
        
        elif condition == "most_recent":
            # Just order by updated_at
            query = (
                self.db.query(
                    Conversation,
                    Conversation.updated_at.label("metric")
                )
                .filter(Conversation.user_id == user_id)
                .order_by(desc(Conversation.updated_at))
                .limit(limit)
            )
            metric_label = "Last Active"
            formatter = lambda val: val.strftime("%Y-%m-%d %H:%M UTC") if val else "Never"
            
        elif condition == "longest_avg_response":
            # Average assistant response time
            query = (
                self.db.query(
                    Conversation,
                    func.avg(Message.response_time_ms).label("metric")
                )
                .join(Message, Conversation.id == Message.conversation_id)
                .filter(
                    Conversation.user_id == user_id,
                    Message.role == "assistant",
                    Message.response_time_ms.isnot(None)
                )
                .group_by(Conversation.id)
                .order_by(desc("metric"))
                .limit(limit)
            )
            metric_label = "Avg Response Time"
            formatter = lambda val: f"{round(val, 1) if val is not None else 0.0} ms"

        elif condition == "shortest_avg_response":
            # Shortest average assistant response time
            query = (
                self.db.query(
                    Conversation,
                    func.avg(Message.response_time_ms).label("metric")
                )
                .join(Message, Conversation.id == Message.conversation_id)
                .filter(
                    Conversation.user_id == user_id,
                    Message.role == "assistant",
                    Message.response_time_ms.isnot(None)
                )
                .group_by(Conversation.id)
                .order_by(asc("metric"))
                .limit(limit)
            )
            metric_label = "Avg Response Time"
            formatter = lambda val: f"{round(val, 1) if val is not None else 0.0} ms"

        elif condition == "longest_content":
            # Sum of character length of messages
            query = (
                self.db.query(
                    Conversation,
                    func.sum(func.length(Message.content)).label("metric")
                )
                .join(Message, Conversation.id == Message.conversation_id)
                .filter(Conversation.user_id == user_id)
                .group_by(Conversation.id)
                .order_by(desc("metric"))
                .limit(limit)
            )
            metric_label = "Total Characters"
            formatter = lambda val: f"{int(val) if val is not None else 0} characters"
        
        else:
            # Fallback to most recent
            return self.get_top_conversations(user_id, "most_recent", limit)

        results = query.all()
        output = []
        for conv, metric_val in results:
            output.append({
                "conversation": conv,
                "metric_name": metric_label,
                "metric_value": formatter(metric_val)
            })
        return output

