import pytest
from app.memory.extractor import MemoryExtractor

def test_create_and_update_memory_fact(auth_service, memory_repo):
    user, _ = auth_service.register_user("Test User", "testuser", "test@example.com", "pass123")
    assert user is not None

    mem1 = memory_repo.create_or_update_memory(user.id, "favorite programming language", "Python")
    assert mem1.fact_key == "favorite programming language"
    assert mem1.fact_value == "Python"

    # Update the same fact
    mem2 = memory_repo.create_or_update_memory(user.id, "favorite programming language", "Python & Rust")
    assert mem2.id == mem1.id
    assert mem2.fact_value == "Python & Rust"

    all_memories = memory_repo.get_user_memories(user.id)
    assert len(all_memories) == 1

def test_memory_extractor_regex_fallback(db_session, auth_service, memory_repo):
    user, _ = auth_service.register_user("Varsha Sharma", "varsha", "v@example.com", "pass123")
    extractor = MemoryExtractor(db_session, ollama_service=None)

    # 1. Favorite programming language
    extracted = extractor.extract_and_store(user.id, "My favorite programming language is Python.")
    assert len(extracted) >= 1
    assert any(k == "favorite programming language" and v == "Python" for k, v in extracted)

    # 2. Dog's name
    extracted2 = extractor.extract_and_store(user.id, "I have a dog named Bruno.")
    assert any(k == "dog's name" and v == "Bruno" for k, v in extracted2)

    # Verify retrieval from repository
    mems = memory_repo.get_user_memories(user.id)
    assert len(mems) >= 2
    assert any(m.fact_key == "dog's name" and m.fact_value == "Bruno" for m in mems)
