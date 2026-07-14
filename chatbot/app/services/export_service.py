import io
import json
from typing import List, Dict, Any
from app.models.conversation import Conversation, Message

class ExportService:
    @staticmethod
    def to_markdown(conversation: Conversation, messages: List[Message]) -> str:
        lines = [
            f"# {conversation.title}",
            f"- **Conversation ID:** `{conversation.id}`",
            f"- **Created At:** {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"- **Model Used:** `{conversation.ollama_model_used}`",
            "",
            "---",
            ""
        ]
        for msg in messages:
            speaker = "🧑 **User**" if msg.role == "user" else "🤖 **Assistant**" if msg.role == "assistant" else "⚙️ **System**"
            time_str = msg.timestamp.strftime('%H:%M:%S') if msg.timestamp else ""
            lines.append(f"### {speaker} ({time_str})")
            lines.append("")
            lines.append(msg.content)
            lines.append("")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def to_json(conversation: Conversation, messages: List[Message]) -> str:
        data = {
            "conversation_id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "ollama_model_used": conversation.ollama_model_used,
            "is_pinned": conversation.is_pinned,
            "tags": [tag.name for tag in conversation.tags],
            "messages": [
                {
                    "message_id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    "ollama_model_used": msg.ollama_model_used,
                    "response_time_ms": msg.response_time_ms
                }
                for msg in messages
            ]
        }
        return json.dumps(data, indent=2)

    @staticmethod
    def to_pdf_bytes(conversation: Conversation, messages: List[Message]) -> bytes:
        """
        Generate clean PDF bytes using ReportLab.
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1f2937'),
                spaceAfter=10
            )
            meta_style = ParagraphStyle(
                'CustomMeta',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#6b7280'),
                spaceAfter=15
            )
            user_header_style = ParagraphStyle(
                'UserHeader',
                parent=styles['Heading3'],
                fontSize=12,
                textColor=colors.HexColor('#2563eb'),
                spaceBefore=10,
                spaceAfter=4
            )
            assistant_header_style = ParagraphStyle(
                'AssistantHeader',
                parent=styles['Heading3'],
                fontSize=12,
                textColor=colors.HexColor('#10b981'),
                spaceBefore=10,
                spaceAfter=4
            )
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#374151'),
                leading=14,
                spaceAfter=10
            )

            story = []
            story.append(Paragraph(f"<b>{conversation.title}</b>", title_style))
            meta_text = f"ID: {conversation.id} | Model: {conversation.ollama_model_used} | Created: {conversation.created_at.strftime('%Y-%m-%d %H:%M')}"
            story.append(Paragraph(meta_text, meta_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb'), spaceAfter=10))

            for msg in messages:
                # Replace markdown linebreaks and basic formatting for ReportLab paragraph
                clean_content = msg.content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')
                if msg.role == "user":
                    story.append(Paragraph("<b>User:</b>", user_header_style))
                else:
                    story.append(Paragraph("<b>AI Assistant:</b>", assistant_header_style))
                story.append(Paragraph(clean_content, body_style))
                story.append(Spacer(1, 8))

            doc.build(story)
            pdf_data = buffer.getvalue()
            buffer.close()
            return pdf_data
        except Exception as e:
            # Fallback text as bytes if ReportLab encounters any font/layout issue
            fallback_text = ExportService.to_markdown(conversation, messages)
            return fallback_text.encode('utf-8')
