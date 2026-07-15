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

def test_top_conversations_retrieval(auth_service, conv_repo):
    user, _ = auth_service.register_user("Charlie Brown", "charlie", "charlie@example.com", "mypassword")
    
    # Create 3 conversations
    c1 = conv_repo.create_conversation(user.id, title="Chat One")
    c2 = conv_repo.create_conversation(user.id, title="Chat Two")
    c3 = conv_repo.create_conversation(user.id, title="Chat Three")

    # Add messages to Chat One (4 messages, avg response time: 200ms)
    conv_repo.add_message(c1.id, user.id, "user", "User message 1")
    conv_repo.add_message(c1.id, user.id, "assistant", "Assistant reply 1", response_time_ms=100.0)
    conv_repo.add_message(c1.id, user.id, "user", "User message 2")
    conv_repo.add_message(c1.id, user.id, "assistant", "Assistant reply 2", response_time_ms=300.0)

    # Add messages to Chat Two (2 messages, avg response time: 500ms)
    conv_repo.add_message(c2.id, user.id, "user", "Hi")
    conv_repo.add_message(c2.id, user.id, "assistant", "Hello there", response_time_ms=500.0)

    # Add messages to Chat Three (1 message, no response time)
    conv_repo.add_message(c3.id, user.id, "user", "Hello")

    # 1. Test condition: most_messages
    res_msgs = conv_repo.get_top_conversations(user.id, condition="most_messages", limit=3)
    assert len(res_msgs) == 3
    assert res_msgs[0]["conversation"].id == c1.id
    assert res_msgs[1]["conversation"].id == c2.id
    assert res_msgs[2]["conversation"].id == c3.id

    # 2. Test condition: longest_avg_response
    res_avg = conv_repo.get_top_conversations(user.id, condition="longest_avg_response", limit=3)
    assert len(res_avg) == 2
    assert res_avg[0]["conversation"].id == c2.id
    assert res_avg[1]["conversation"].id == c1.id

    # 3. Test condition: shortest_avg_response
    res_short = conv_repo.get_top_conversations(user.id, condition="shortest_avg_response", limit=3)
    assert len(res_short) == 2
    assert res_short[0]["conversation"].id == c1.id
    assert res_short[1]["conversation"].id == c2.id

    # 4. Test condition: longest_content
    res_content = conv_repo.get_top_conversations(user.id, condition="longest_content", limit=3)
    assert len(res_content) == 3
    assert res_content[0]["conversation"].id == c1.id
    assert res_content[1]["conversation"].id == c2.id
    assert res_content[2]["conversation"].id == c3.id

    # 5. Test condition: most_recent
    res_recent = conv_repo.get_top_conversations(user.id, condition="most_recent", limit=3)
    assert len(res_recent) == 3
    assert res_recent[0]["conversation"].id == c3.id

