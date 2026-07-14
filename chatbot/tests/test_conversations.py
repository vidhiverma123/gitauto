import pytest
from app.prompts.builder import PromptBuilder

def test_conversation_management_and_search(auth_service, conv_repo):
    user, _ = auth_service.register_user("Alice Smith", "alice", "alice@example.com", "secretpw")
    conv1 = conv_repo.create_conversation(user.id, title="Python Decorators Explanation", model_used="llama3")
    conv2 = conv_repo.create_conversation(user.id, title="Trip Planning to Japan", model_used="qwen")

    # Add messages
    conv_repo.add_message(conv1.id, user.id, "user", "Can you explain Python decorators?")
    conv_repo.add_message(conv1.id, user.id, "assistant", "A decorator is a function that takes another function and extends its behavior.")

    conv_repo.add_message(conv2.id, user.id, "user", "What are the best places in Tokyo?")
    conv_repo.add_message(conv2.id, user.id, "assistant", "Check out Shibuya and Shinjuku.")

    # Add tags
    conv_repo.add_tags_to_conversation(conv1.id, ["Programming"])
    conv_repo.add_tags_to_conversation(conv2.id, ["Travel"])

    # Test Pinning
    conv_repo.toggle_pin(conv2.id, is_pinned=True)
    user_convs = conv_repo.get_user_conversations(user.id)
    assert user_convs[0].id == conv2.id  # Pinned conversation should come first

    # Test Keyword Search on title
    search_res = conv_repo.search_conversations(user.id, keyword="Decorators")
    assert len(search_res) == 1
    assert search_res[0].id == conv1.id

    # Test Keyword Search on message content
    search_msg = conv_repo.search_conversations(user.id, keyword="Shibuya")
    assert len(search_msg) == 1
    assert search_msg[0].id == conv2.id

    # Test Tag Filtering
    tag_res = conv_repo.search_conversations(user.id, tag_name="Travel")
    assert len(tag_res) == 1
    assert tag_res[0].id == conv2.id

    # Test Analytics
    stats = conv_repo.get_user_analytics(user.id)
    assert stats["total_conversations"] == 2
    assert stats["total_messages"] == 4
    assert stats["avg_messages_per_conversation"] == 2.0

def test_prompt_builder(auth_service, conv_repo, memory_repo):
    user, _ = auth_service.register_user("Bob Jones", "bobj", "bob@example.com", "pass123")
    conv = conv_repo.create_conversation(user.id, "Test Chat")
    memory_repo.create_or_update_memory(user.id, "favorite food", "Pizza")
    memory_repo.create_or_update_memory(user.id, "location", "Bangalore")

    messages = [
        conv_repo.add_message(conv.id, user.id, "user", "Hello there!"),
        conv_repo.add_message(conv.id, user.id, "assistant", "Hi Bob! How can I help you today?")
    ]

    payload = PromptBuilder.build_messages_payload(user, memory_repo.get_user_memories(user.id), messages, "Where do I live?")
    assert len(payload) >= 2
    assert payload[0]["role"] == "system"
    assert "Bob Jones" in payload[0]["content"]
    assert "Favorite food: Pizza" in payload[0]["content"] or "favorite food: Pizza" in payload[0]["content"]
    assert "Location: Bangalore" in payload[0]["content"] or "location: Bangalore" in payload[0]["content"]
    assert payload[-1]["role"] == "user"
    assert payload[-1]["content"] == "Where do I live?"
