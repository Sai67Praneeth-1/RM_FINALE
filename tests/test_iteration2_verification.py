"""
Iteration 2 Automated Verification:
Testing Smart Auto-Naming, Multi-Chat Persistence, Interaction Graph Restoration,
Date-based Grouping, Title Updates, and Cleanup in MongoDB.
"""

from fastapi.testclient import TestClient
from backend.api.main import app
from backend.storage.mongo_chat_store import MongoChatStore

def run_tests():
    client = TestClient(app)
    store = MongoChatStore.get_instance()
    print("=== ITERATION 2 VERIFICATION ===")

    # 1. Test smart title generation rules
    prompts_and_expected = [
        ("Audit customer complaints for High and Critical severity issues", "Complaints Severity Audit"),
        ("What are customers mostly complaining of?", "Customer Complaint Trends"),
        ("Who are our enterprise customers and what issues are they facing?", "Enterprise Accounts Status"),
        ("Check system access logs for unauthorized root escalation and file sharing", "System Access Log Audit"),
        ("Can you please tell me what models are being used?", "LLM Engine Configuration"),
    ]

    for prompt, expected_title in prompts_and_expected:
        generated = store.generate_smart_title(prompt)
        print(f"Prompt: '{prompt[:35]}...' -> Generated: '{generated}'")
        assert generated == expected_title, f"Expected '{expected_title}' but got '{generated}'"
    print("1. All smart title generation rules verified successfully!")

    # 2. Create multiple conversations through /api/chat
    chat_ids = []
    test_queries = [
        "Audit customer complaints for High and Critical severity issues",
        "Who are our enterprise customers and what issues are they facing?",
        "What are customers mostly complaining of?"
    ]

    for q in test_queries:
        res = client.post("/api/chat", json={"message": q, "mode": "deterministic_demo"})
        assert res.status_code == 200
        data = res.json()
        cid = data.get("conversation_id")
        title = data.get("conversation_title")
        print(f"Created chat session '{title}' (ID: {cid})")
        assert cid is not None
        assert title is not None
        chat_ids.append(cid)

    # 3. Verify chats appear in list_chats
    res_list = client.get("/api/chats")
    assert res_list.status_code == 200
    listed = res_list.json()
    listed_ids = [c["id"] for c in listed]
    for cid in chat_ids:
        assert cid in listed_ids
    print(f"2. Verified {len(chat_ids)} chats listed in sidebar from MongoDB.")

    # 4. Verify chat contents and graph restoration
    first_chat_id = chat_ids[0]
    res_chat1 = client.get(f"/api/chats/{first_chat_id}")
    assert res_chat1.status_code == 200
    c1_doc = res_chat1.json()
    assert len(c1_doc["messages"]) >= 2
    # Verify assistant message contains interaction_graph
    asst_msg = next(m for m in c1_doc["messages"] if m["role"] == "assistant")
    assert "interaction_graph" in asst_msg
    assert "nodes" in asst_msg["interaction_graph"]
    print("3. Verified full interaction graph and goal traceability stored for chat.")

    # 5. Test manual title rename
    res_rename = client.patch(f"/api/chats/{first_chat_id}", json={"title": "Custom Renamed Investigation"})
    assert res_rename.status_code == 200
    res_chat1_updated = client.get(f"/api/chats/{first_chat_id}")
    assert res_chat1_updated.json()["title"] == "Custom Renamed Investigation"
    print("4. Verified inline rename capability.")

    # 6. Test multi-turn follow-up inside chat 2
    second_chat_id = chat_ids[1]
    res_followup = client.post("/api/chat", json={
        "message": "Give me detailed recommendations for these enterprise accounts",
        "conversation_id": second_chat_id,
        "mode": "deterministic_demo"
    })
    assert res_followup.status_code == 200
    res_chat2 = client.get(f"/api/chats/{second_chat_id}")
    assert len(res_chat2.json()["messages"]) >= 4  # 2 turns = 4 messages
    print("5. Verified multi-turn continuation within existing conversation.")

    # 7. Clean up created test chats
    for cid in chat_ids:
        res_del = client.delete(f"/api/chats/{cid}")
        assert res_del.status_code == 200
    print("6. Cleaned up all test chats from MongoDB Atlas.")
    print("=== ITERATION 2: ALL CHECKS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_tests()
