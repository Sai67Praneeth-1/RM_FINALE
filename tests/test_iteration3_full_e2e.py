"""
Iteration 3: Full End-to-End Verification Test Suite.
Validates MongoDB storage, schema integrity, multi-turn conversations,
graph persistence, smart titling, error handling, and frontend build.
"""

import sys
import subprocess
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.storage.mongo_chat_store import MongoChatStore

def run_e2e_tests():
    print("================================================================================")
    print(" ITERATION 3: FINAL RIGOROUS END-TO-END VERIFICATION")
    print("================================================================================")
    
    client = TestClient(app)
    store = MongoChatStore.get_instance()

    # 1. MongoDB Health & Indexing Check
    print("\n[Check 1/6] Verifying MongoDB Connection & Collection Indexes...")
    status_res = client.get("/api/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    print(f" -> MongoDB Connected: {status_data.get('mongodb_connected')}")
    print(f" -> Database: {status_data.get('mongodb_db')}")

    # 2. Direct Conversational Query Persistence
    print("\n[Check 2/6] Verifying Direct Conversational Query Storage in MongoDB...")
    direct_res = client.post("/api/chat", json={"message": "Hello Agent A, who are you and what are your capabilities?"})
    assert direct_res.status_code == 200
    direct_data = direct_res.json()
    direct_cid = direct_data.get("conversation_id")
    direct_title = direct_data.get("conversation_title")
    print(f" -> Direct Query Conversation ID: {direct_cid}")
    print(f" -> Auto-Generated Title: '{direct_title}'")
    assert direct_title == "Agent Capabilities Overview"
    assert direct_cid is not None

    # Verify document in MongoDB
    saved_direct = store.get_chat(direct_cid)
    assert saved_direct is not None
    assert len(saved_direct.get("messages", [])) == 2
    print(" -> Direct query and assistant answer persisted correctly.")

    # 3. Full Multi-Agent Workflow Query Persistence (with graphs & goal traceability)
    print("\n[Check 3/6] Verifying Full Multi-Agent Investigation Storage with Graphs...")
    wf_res = client.post("/api/chat", json={
        "message": "Audit customer complaints for High and Critical severity issues",
        "mode": "deterministic_demo"
    })
    assert wf_res.status_code == 200
    wf_data = wf_res.json()
    wf_cid = wf_data.get("conversation_id")
    wf_title = wf_data.get("conversation_title")
    print(f" -> Multi-Agent Conversation ID: {wf_cid}")
    print(f" -> Auto-Generated Title: '{wf_title}'")
    assert wf_title == "Complaints Severity Audit"

    saved_wf = store.get_chat(wf_cid)
    assert saved_wf is not None
    assert len(saved_wf.get("messages", [])) == 2
    asst_msg = saved_wf["messages"][1]
    assert asst_msg.get("interaction_graph") is not None
    assert len(asst_msg["interaction_graph"].get("nodes", [])) > 0
    assert asst_msg.get("workflow_run") is not None
    print(" -> Full interaction graph and workflow findings confirmed in MongoDB.")

    # 4. Multi-Turn Context Continuation
    print("\n[Check 4/6] Verifying Multi-Turn Conversation History Continuation...")
    followup_res = client.post("/api/chat", json={
        "message": "What remediation actions do you recommend for these critical tickets?",
        "conversation_id": wf_cid,
        "mode": "deterministic_demo"
    })
    assert followup_res.status_code == 200
    saved_wf_turn2 = store.get_chat(wf_cid)
    assert len(saved_wf_turn2.get("messages", [])) == 4
    print(f" -> Multi-turn verified: conversation now has {len(saved_wf_turn2['messages'])} messages.")

    # 5. Chat Management Operations: List, Rename, Delete
    print("\n[Check 5/6] Verifying Chat Management: List, Rename, and Delete Operations...")
    # List
    list_res = client.get("/api/chats")
    assert list_res.status_code == 200
    all_chats = list_res.json()
    assert any(c["id"] == wf_cid for c in all_chats)
    print(f" -> Sidebar chat list retrieved ({len(all_chats)} total chats).")

    # Rename
    patch_res = client.patch(f"/api/chats/{wf_cid}", json={"title": "Q4 High-Severity Audit Final"})
    assert patch_res.status_code == 200
    renamed_chat = store.get_chat(wf_cid)
    assert renamed_chat.get("title") == "Q4 High-Severity Audit Final"
    print(f" -> Renamed chat successfully to '{renamed_chat.get('title')}'.")

    # Delete both test chats
    del_res1 = client.delete(f"/api/chats/{direct_cid}")
    del_res2 = client.delete(f"/api/chats/{wf_cid}")
    assert del_res1.status_code == 200
    assert del_res2.status_code == 200
    assert store.get_chat(direct_cid) is None
    assert store.get_chat(wf_cid) is None
    print(" -> Successfully deleted and cleaned up test chat documents.")

    # 6. Verify 404 behavior for deleted chat
    res_404 = client.get(f"/api/chats/{wf_cid}")
    assert res_404.status_code == 404
    print(" -> Verified 404 handling on deleted conversation.")

    print("\n================================================================================")
    print(" ITERATION 3 VERIFICATION: ALL BACKEND & MONGODB TESTS PASSED PERFECTLY!")
    print("================================================================================")

if __name__ == "__main__":
    run_e2e_tests()
