def test_chat_request_accepts_ai_sdk_messages():
    from app.schemas.chat import ChatRequest

    payload = {
        "id": "thread-1",
        "model": "gemma4:e4b",
        "messages": [
            {"id": "u1", "role": "user", "parts": [{"type": "text", "text": "hi"}]},
        ],
    }
    req = ChatRequest.model_validate(payload)
    assert req.id == "thread-1"
    assert req.model == "gemma4:e4b"
    assert req.messages[0].role == "user"
    assert req.messages[0].parts[0].text == "hi"
