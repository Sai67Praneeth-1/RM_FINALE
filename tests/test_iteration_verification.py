"""
Automated End-to-End Verification Test for MongoDB Chat Integration.
"""

from fastapi.testclient import TestClient
from backend.api.main import app

def run_tests():
    client = TestClient(app)
    print("=== ITERATION 1 VERIFICATION ===")

    # 1. System status check
    res_status = client.get("/api/status")
    assert res_status.status_code == 200
    status = res_status.json()
    print("1. Backend status: OK, MongoDB connected:", status.get("mongodb_connected"))
    assert status.get("mongodb_connected") is True

    # 2. Start a new chat with a task query
    chat_payload = {
        "message": "Audit consumer complaints for high severity credit reporting issues",
        "mode": "deterministic_demo"
    }
    res_chat = client.post("/api/chat", json=chat_payload)
    assert res_chat.status_code == 200
    data1 = res_chat.json()
    conv_id = data1.get("conversation_id")
    conv_title = data1.get("conversation_title")
    print(f"2. Chat created with ID: {conv_id}, Title: '{conv_title}'")
    assert conv_id is not None
    assert len(data1.get("response")) > 0
    assert data1.get("interaction_graph") is not None

    # 3. Follow up message in the same chat
    res_chat_followup = client.post("/api/chat", json={
        "message": "Can you clarify which specific institutions had the most complaints?",
        "conversation_id": conv_id,
        "mode": "deterministic_demo"
    })
    assert res_chat_followup.status_code == 200
    data2 = res_chat_followup.json()
    assert data2.get("conversation_id") == conv_id
    print("3. Follow-up message appended to conversation.")

    # 4. Fetch the chat session
    res_get = client.get(f"/api/chats/{conv_id}")
    assert res_get.status_code == 200
    chat_doc = res_get.json()
    msg_count = len(chat_doc.get("messages", []))
    print(f"4. Chat retrieved from MongoDB. Total messages: {msg_count}")
    assert msg_count == 4  # 2 user + 2 assistant

    # 5. List all chats
    res_list = client.get("/api/chats")
    assert res_list.status_code == 200
    chats_list = res_list.json()
    print(f"5. Total chats listed in sidebar: {len(chats_list)}")
    assert any(c["id"] == conv_id for c in chats_list)

    # 6. Test rename chat
    res_patch = client.patch(f"/api/chats/{conv_id}", json={"title": "Credit Reporting Severity Audit"})
    assert res_patch.status_code == 200
    res_get_updated = client.get(f"/api/chats/{conv_id}")
    updated_title = res_get_updated.json().get("title")
    print(f"6. Renamed chat title to: '{updated_title}'")
    assert updated_title == "Credit Reporting Severity Audit"

    # 7. Clean up
    res_del = client.delete(f"/api/chats/{conv_id}")
    assert res_del.status_code == 200
    print("7. Successfully deleted verification chat.")
    print("=== ITERATION 1: ALL CHECKS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_tests()
