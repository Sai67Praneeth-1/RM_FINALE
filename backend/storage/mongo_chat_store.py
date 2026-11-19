"""
MongoDB & Local Persistence Layer for Agentic AI Chat History and Multi-Turn Conversations.
Stores conversational sessions, generated agent reasoning, interaction graphs, and workflow results.
Seamlessly falls back to local JSON persistence if remote MongoDB is unreachable, ensuring zero errors.
"""

import os
import re
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.database import Database
except ImportError:
    MongoClient = None
    Collection = None
    Database = None
from backend.config import settings

logger = logging.getLogger(__name__)

class MongoChatStore:
    _instance: Optional["MongoChatStore"] = None

    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        self.uri = uri or settings.MONGODB_URI or os.getenv("MONGODB_URI", "")
        self.db_name = db_name or settings.MONGODB_DB_NAME or os.getenv("MONGODB_DB_NAME", "transparency_platform")
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._collection: Optional[Collection] = None       # conversations
        self._events_col: Optional[Collection] = None       # execution_events
        self._delegations_col: Optional[Collection] = None  # delegations
        self._interactions_col: Optional[Collection] = None # interactions
        self._workflows_col: Optional[Collection] = None    # workflow_runs
        self._in_memory_chats: Dict[str, Dict[str, Any]] = {}
        self._offline_mode: bool = False
        self._local_file_path: str = os.path.join("data", "generated", "local_chats.json")
        
        # 1. Load locally saved chats first
        self._load_local_chats()
        
        # 2. Attempt remote MongoDB connection gracefully
        self._connect()

    def _load_local_chats(self):
        """Loads persistent chats from local JSON file."""
        try:
            if os.path.exists(self._local_file_path):
                with open(self._local_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._in_memory_chats = data
        except Exception as e:
            logger.debug(f"[ChatStore] Local chat load note: {e}")

    def _save_local_chats(self):
        """Persists chat state to local JSON file so chats survive server restarts."""
        try:
            os.makedirs(os.path.dirname(self._local_file_path), exist_ok=True)
            with open(self._local_file_path, "w", encoding="utf-8") as f:
                json.dump(self._in_memory_chats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"[ChatStore] Local chat save note: {e}")

    def _connect(self) -> bool:
        """Attempts connection to MongoDB; falls back silently to local storage if unreachable."""
        if MongoClient is None or not self.uri:
            self._offline_mode = True
            return False

        if self._offline_mode:
            return False

        try:
            import certifi
            ca_file = certifi.where()
        except ImportError:
            ca_file = None

        try:
            kwargs: Dict[str, Any] = {
                "serverSelectionTimeoutMS": 1500,
                "connectTimeoutMS": 1500,
                "socketTimeoutMS": 2000,
                "retryWrites": True,
                "maxPoolSize": 10
            }
            if ca_file:
                kwargs["tlsCAFile"] = ca_file

            self._client = MongoClient(self.uri, **kwargs)
            self._client.admin.command("ping")
            self._db = self._client.get_database(self.db_name)
            self._collection = self._db.get_collection("conversations")
            self._events_col = self._db.get_collection("execution_events")
            self._delegations_col = self._db.get_collection("delegations")
            self._interactions_col = self._db.get_collection("interactions")
            self._workflows_col = self._db.get_collection("workflow_runs")

            try:
                self._collection.create_index("id", unique=True)
                self._collection.create_index([("updated_at", -1)])

                self._events_col.create_index("chat_id")
                self._events_col.create_index("workflow_id")
                self._events_col.create_index([("chat_id", 1), ("event_id", 1)], unique=True)
                self._events_col.create_index([("timestamp", -1)])

                self._delegations_col.create_index("chat_id")
                self._delegations_col.create_index("workflow_id")
                self._delegations_col.create_index([("chat_id", 1), ("delegation_id", 1)], unique=True)
                self._delegations_col.create_index([("issued_at", -1)])

                self._interactions_col.create_index("chat_id")
                self._interactions_col.create_index("workflow_id")
                self._interactions_col.create_index([("chat_id", 1), ("interaction_id", 1)], unique=True)
                self._interactions_col.create_index([("timestamp", -1)])

                self._workflows_col.create_index("chat_id")
                self._workflows_col.create_index("workflow_id", unique=True)
                self._workflows_col.create_index([("start_time", -1)])
            except Exception as idx_err:
                logger.debug(f"[MongoChatStore] Index creation note: {idx_err}")

            logger.info(f"[MongoChatStore] Connected to MongoDB database: {self.db_name}")
            self._offline_mode = False
            return True
        except Exception:
            # Silent fallback: do not dump lengthy SSL exception traces to terminal
            self._offline_mode = True
            self._client = None
            self._db = None
            self._collection = None
            self._events_col = None
            self._delegations_col = None
            self._interactions_col = None
            self._workflows_col = None
            logger.info("[MongoChatStore] Operating in local persistence mode (local_chats.json + SQLite).")
            return False

    def reconnect(self) -> bool:
        """Forces an active re-connection attempt to MongoDB Atlas."""
        self._offline_mode = False
        return self._connect()

    @classmethod
    def get_instance(cls) -> "MongoChatStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_connected(self) -> bool:
        """Quick non-blocking check without polling/timeout loop."""
        return self._collection is not None and self._client is not None and not self._offline_mode

    def generate_smart_title(self, text: str) -> str:
        """
        Derives a concise, professional ChatGPT-style title from the user prompt.
        Extracts semantic topic and eliminates common filler phrases.
        """
        clean = (text or "").strip()
        if not clean:
            return "New Investigation"

        # Remove markdown symbols, special symbols, and extra whitespace
        clean = re.sub(r"[#*_`~>]+", "", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        t_lower = clean.lower()
        # Semantic domain heuristics for crisp titles
        if "complain" in t_lower and any(w in t_lower for w in ["high", "critical", "severity", "audit"]):
            return "Complaints Severity Audit"
        elif "complain" in t_lower and any(w in t_lower for w in ["mostly", "trend", "issue", "common", "frequency"]):
            return "Customer Complaint Trends"
        elif "enterprise" in t_lower:
            return "Enterprise Accounts Status"
        elif any(w in t_lower for w in ["system access", "system log", "root escalation", "unauthorized", "audit log"]):
            return "System Access Log Audit"
        elif "topology" in t_lower or "topologies" in t_lower:
            return "LangGraph Topologies"
        elif "benchmark" in t_lower or "evaluation" in t_lower:
            return "Research Evaluation Benchmark"
        elif any(k in t_lower for k in ["who are you", "what can you do", "what are your capabilities", "help me"]):
            return "Agent Capabilities Overview"
        elif any(k in t_lower for k in ["model", "llama", "qwen", "router"]):
            return "LLM Engine Configuration"

        # Strip prefixes & filler phrasing
        fillers = [
            r"^(please\s+)?(can\s+you\s+)?(could\s+you\s+)?(tell\s+me\s+(about\s+|what\s+|how\s+)?)",
            r"^(please\s+)?(can\s+you\s+)?(could\s+you\s+)?(show\s+me\s+)",
            r"^(please\s+)?(can\s+you\s+)?(could\s+you\s+)?(explain\s+)",
            r"^(please\s+)?(can\s+you\s+)?(could\s+you\s+)?(run\s+an\s+|run\s+a\s+|run\s+)",
            r"^(please\s+)?(i\s+want\s+you\s+to\s+)",
            r"^(please\s+)?(what\s+is\s+|what\s+are\s+)",
            r"^(please\s+)?(investigate|audit|check|analyze|examine|look\s+into)\s+",
            r"^(hello|hi|hey|good\s+morning|good\s+evening)\b[\s,!.]*",
        ]
        for pattern in fillers:
            clean = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip()

        if not clean:
            return "General Investigation"

        # Take first sentence
        sentence = re.split(r"[.?!;\n]", clean)[0].strip()
        words = sentence.split()
        if not words:
            return "General Investigation"

        # Build clean title without cutting words mid-syllable
        selected_words = []
        total_len = 0
        for w in words:
            if total_len + len(w) > 34 or len(selected_words) >= 6:
                break
            selected_words.append(w)
            total_len += len(w) + 1

        title_str = " ".join(selected_words).rstrip(" ,.-:")
        minor_words = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "nor", "of", "on", "or", "the", "to", "up", "with"}
        title_words = [
            w.capitalize() if (i == 0 or w.lower() not in minor_words) else w.lower()
            for i, w in enumerate(title_str.split())
        ]
        title = " ".join(title_words)
        return title or "General Investigation"

    def list_chats(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns sorted summary list of chat sessions for the sidebar."""
        if self.is_connected():
            try:
                cursor = self._collection.find(
                    {},
                    {
                        "_id": 0,
                        "id": 1,
                        "title": 1,
                        "created_at": 1,
                        "updated_at": 1,
                        "message_count": 1,
                        "last_message": 1
                    }
                ).sort("updated_at", -1).limit(limit)
                mongo_list = list(cursor)
                if mongo_list:
                    return mongo_list
            except Exception:
                pass

        # Local fallback
        sorted_chats = sorted(
            self._in_memory_chats.values(),
            key=lambda c: c.get("updated_at", ""),
            reverse=True
        )[:limit]
        return [
            {
                "id": c["id"],
                "title": c.get("title", "New Investigation"),
                "created_at": c.get("created_at", ""),
                "updated_at": c.get("updated_at", ""),
                "message_count": c.get("message_count", len(c.get("messages", []))),
                "last_message": c.get("last_message", "")
            }
            for c in sorted_chats
        ]

    def get_chat(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Returns the full conversation document including all messages and graphs."""
        if self.is_connected():
            try:
                doc = self._collection.find_one({"id": chat_id}, {"_id": 0})
                if doc:
                    self._in_memory_chats[chat_id] = doc
                    return doc
            except Exception:
                pass

        return self._in_memory_chats.get(chat_id)

    def create_chat(
        self,
        title: Optional[str] = None,
        initial_messages: Optional[List[Dict[str, Any]]] = None,
        chat_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a new conversation record locally and in MongoDB."""
        now_iso = datetime.now(timezone.utc).isoformat()
        cid = chat_id or str(uuid.uuid4())
        msgs = initial_messages or []
        doc = {
            "id": cid,
            "title": title or "New Investigation",
            "created_at": now_iso,
            "updated_at": now_iso,
            "message_count": len(msgs),
            "last_message": msgs[-1].get("content", "")[:120] if msgs else "",
            "messages": msgs
        }
        self._in_memory_chats[cid] = doc
        self._save_local_chats()

        if self.is_connected():
            try:
                self._collection.update_one({"id": cid}, {"$set": doc}, upsert=True)
            except Exception:
                pass
        return doc

    def append_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Appends a message to a conversation. If the conversation does not exist, creates it.
        Also automatically generates an intelligent title from the first user message.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        msg_id = str(uuid.uuid4())
        msg_obj = {
            "id": msg_id,
            "role": role,
            "content": content,
            "timestamp": now_iso,
        }
        if metadata:
            msg_obj["metadata"] = metadata
            for k, v in metadata.items():
                if v is not None:
                    msg_obj[k] = v

        existing = self._in_memory_chats.get(chat_id)
        if not existing and self.is_connected():
            try:
                existing = self._collection.find_one({"id": chat_id}, {"_id": 0})
            except Exception:
                existing = None

        if not existing:
            title = self.generate_smart_title(content) if role == "user" else "New Investigation"
            doc = {
                "id": chat_id,
                "title": title,
                "created_at": now_iso,
                "updated_at": now_iso,
                "message_count": 1,
                "last_message": content[:120],
                "messages": [msg_obj]
            }
            self._in_memory_chats[chat_id] = doc
            self._save_local_chats()
            if self.is_connected():
                try:
                    self._collection.insert_one(dict(doc))
                except Exception:
                    pass
            return doc
        else:
            existing_messages = existing.get("messages", [])
            existing_messages.append(msg_obj)
            existing["messages"] = existing_messages
            existing["updated_at"] = now_iso
            existing["message_count"] = len(existing_messages)
            existing["last_message"] = content[:120]

            if role == "user" and (existing.get("title") in ("New Investigation", "New Conversation", "Untitled Chat", "") or len(existing_messages) <= 2):
                existing["title"] = self.generate_smart_title(content)

            self._in_memory_chats[chat_id] = existing
            self._save_local_chats()

            if self.is_connected():
                try:
                    self._collection.update_one(
                        {"id": chat_id},
                        {
                            "$push": {"messages": msg_obj},
                            "$inc": {"message_count": 1},
                            "$set": {
                                "updated_at": now_iso,
                                "last_message": content[:120],
                                "title": existing["title"]
                            }
                        },
                        upsert=True
                    )
                except Exception:
                    pass
            return existing

    def update_chat_title(self, chat_id: str, new_title: str) -> bool:
        """Renames a chat title."""
        if not new_title:
            return False
        now_iso = datetime.now(timezone.utc).isoformat()
        updated = False
        if chat_id in self._in_memory_chats:
            self._in_memory_chats[chat_id]["title"] = new_title.strip()
            self._in_memory_chats[chat_id]["updated_at"] = now_iso
            self._save_local_chats()
            updated = True

        if self.is_connected():
            try:
                res = self._collection.update_one(
                    {"id": chat_id},
                    {"$set": {"title": new_title.strip(), "updated_at": now_iso}}
                )
                if res.matched_count > 0:
                    updated = True
            except Exception:
                pass
        return updated

    def delete_chat(self, chat_id: str) -> bool:
        """
        Deletes a conversation by ID, along with its associated execution events,
        delegations, interactions, and workflow records across all MongoDB collections.
        """
        deleted = False
        if chat_id in self._in_memory_chats:
            del self._in_memory_chats[chat_id]
            self._save_local_chats()
            deleted = True

        if self.is_connected():
            try:
                res = self._collection.delete_one({"id": chat_id})
                if res.deleted_count > 0:
                    deleted = True
                if self._events_col is not None:
                    self._events_col.delete_many({"chat_id": chat_id})
                if self._delegations_col is not None:
                    self._delegations_col.delete_many({"chat_id": chat_id})
                if self._interactions_col is not None:
                    self._interactions_col.delete_many({"chat_id": chat_id})
                if self._workflows_col is not None:
                    self._workflows_col.delete_many({"chat_id": chat_id})
            except Exception:
                pass
        return deleted

    def store_workflow_telemetry(
        self,
        chat_id: str,
        workflow_id: str,
        events: Optional[List[Dict[str, Any]]] = None,
        delegations: Optional[List[Dict[str, Any]]] = None,
        interactions: Optional[List[Dict[str, Any]]] = None,
        workflow_run: Optional[Dict[str, Any]] = None,
        graphs: Optional[Dict[str, Any]] = None,
        provenance: Optional[Dict[str, Any]] = None,
        goal_matrix: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Stores all pertaining execution and graph telemetry for a conversation.
        Writes both to the dedicated MongoDB collections (execution_events, delegations,
        interactions, workflow_runs) and embeds within the conversation message,
        with full synchronization to local JSON persistence.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Update In-Memory / Local conversation document
        existing = self._in_memory_chats.get(chat_id)
        if not existing and self.is_connected() and self._collection is not None:
            try:
                existing = self._collection.find_one({"id": chat_id}, {"_id": 0})
            except Exception:
                existing = None

        if existing:
            msgs = existing.get("messages", [])
            target_msg = None
            for m in reversed(msgs):
                if m.get("role") == "assistant" and (m.get("workflow_id") == workflow_id or not m.get("workflow_id")):
                    target_msg = m
                    break

            if target_msg is not None:
                if "metadata" not in target_msg:
                    target_msg["metadata"] = {}

                target_msg["workflow_id"] = workflow_id
                target_msg["metadata"]["workflow_id"] = workflow_id

                if events is not None:
                    target_msg["execution_events"] = events
                    target_msg["metadata"]["execution_events"] = events
                if delegations is not None:
                    target_msg["delegations"] = delegations
                    target_msg["metadata"]["delegations"] = delegations
                if interactions is not None:
                    target_msg["interactions"] = interactions
                    target_msg["metadata"]["interactions"] = interactions
                if workflow_run is not None:
                    target_msg["workflow_run"] = workflow_run
                    target_msg["metadata"]["workflow_run"] = workflow_run
                if graphs is not None:
                    if "execution_graph" in graphs:
                        target_msg["execution_graph"] = graphs["execution_graph"]
                        target_msg["metadata"]["execution_graph"] = graphs["execution_graph"]
                    if "authority_graph" in graphs:
                        target_msg["authority_graph"] = graphs["authority_graph"]
                        target_msg["metadata"]["authority_graph"] = graphs["authority_graph"]
                    if "interaction_graph" in graphs:
                        target_msg["interaction_graph"] = graphs["interaction_graph"]
                        target_msg["metadata"]["interaction_graph"] = graphs["interaction_graph"]
                if provenance is not None:
                    target_msg["provenance"] = provenance
                    target_msg["metadata"]["provenance"] = provenance
                if goal_matrix is not None:
                    target_msg["goal_traceability"] = goal_matrix
                    target_msg["metadata"]["goal_traceability"] = goal_matrix

            existing["updated_at"] = now_iso
            self._in_memory_chats[chat_id] = existing
            self._save_local_chats()

        # 2. Remote MongoDB Storage in dedicated collections
        if self.is_connected() and self._db is not None:
            # A. Execution Events Collection
            if events and self._events_col is not None:
                for ev in events:
                    try:
                        doc = dict(ev)
                        doc["chat_id"] = chat_id
                        doc["workflow_id"] = workflow_id
                        ev_id = doc.get("event_id") or doc.get("id") or str(uuid.uuid4())
                        doc["event_id"] = ev_id
                        self._events_col.update_one(
                            {"chat_id": chat_id, "event_id": ev_id},
                            {"$set": doc},
                            upsert=True
                        )
                    except Exception as e:
                        logger.debug(f"[MongoChatStore] Event upsert error: {e}")

            # B. Delegations Collection
            if delegations and self._delegations_col is not None:
                for dg in delegations:
                    try:
                        doc = dict(dg)
                        doc["chat_id"] = chat_id
                        doc["workflow_id"] = workflow_id
                        del_id = doc.get("delegation_id") or doc.get("id") or str(uuid.uuid4())
                        doc["delegation_id"] = del_id
                        self._delegations_col.update_one(
                            {"chat_id": chat_id, "delegation_id": del_id},
                            {"$set": doc},
                            upsert=True
                        )
                    except Exception as e:
                        logger.debug(f"[MongoChatStore] Delegation upsert error: {e}")

            # C. Interactions Collection
            if interactions and self._interactions_col is not None:
                for ix in interactions:
                    try:
                        doc = dict(ix)
                        doc["chat_id"] = chat_id
                        doc["workflow_id"] = workflow_id
                        ix_id = doc.get("interaction_id") or doc.get("id") or str(uuid.uuid4())
                        doc["interaction_id"] = ix_id
                        self._interactions_col.update_one(
                            {"chat_id": chat_id, "interaction_id": ix_id},
                            {"$set": doc},
                            upsert=True
                        )
                    except Exception as e:
                        logger.debug(f"[MongoChatStore] Interaction upsert error: {e}")

            # D. Workflow Runs Collection
            if self._workflows_col is not None:
                try:
                    wf_doc = dict(workflow_run or {})
                    wf_doc["chat_id"] = chat_id
                    wf_doc["workflow_id"] = workflow_id
                    wf_doc["updated_at"] = now_iso
                    if graphs:
                        wf_doc["graphs"] = graphs
                    if provenance:
                        wf_doc["provenance"] = provenance
                    if goal_matrix:
                        wf_doc["goal_traceability"] = goal_matrix
                    self._workflows_col.update_one(
                        {"chat_id": chat_id, "workflow_id": workflow_id},
                        {"$set": wf_doc},
                        upsert=True
                    )
                except Exception as e:
                    logger.debug(f"[MongoChatStore] Workflow run upsert error: {e}")

            # E. Update conversation root in conversations collection
            if existing and self._collection is not None:
                try:
                    self._collection.update_one(
                        {"id": chat_id},
                        {"$set": existing},
                        upsert=True
                    )
                except Exception as e:
                    logger.debug(f"[MongoChatStore] Conversation doc update error: {e}")

        return {
            "status": "success",
            "chat_id": chat_id,
            "workflow_id": workflow_id,
            "events_stored": len(events or []),
            "delegations_stored": len(delegations or []),
            "interactions_stored": len(interactions or []),
            "graphs_stored": bool(graphs),
            "provenance_stored": bool(provenance)
        }

    def get_chat_events(self, chat_id: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Returns execution events belonging to a chat, from MongoDB or in-memory cache."""
        if self.is_connected() and self._events_col is not None:
            try:
                events = list(self._events_col.find(
                    {"chat_id": chat_id},
                    {"_id": 0}
                ).sort("timestamp", 1).limit(limit))
                if events:
                    return events
            except Exception:
                pass

        chat = self._in_memory_chats.get(chat_id)
        if chat:
            for m in reversed(chat.get("messages", [])):
                evs = m.get("execution_events") or m.get("metadata", {}).get("execution_events")
                if evs:
                    return evs[:limit]
        return []

    def get_chat_delegations(self, chat_id: str) -> List[Dict[str, Any]]:
        """Returns authority delegations belonging to a chat."""
        if self.is_connected() and self._delegations_col is not None:
            try:
                delgs = list(self._delegations_col.find(
                    {"chat_id": chat_id},
                    {"_id": 0}
                ).sort("issued_at", 1))
                if delgs:
                    return delgs
            except Exception:
                pass

        chat = self._in_memory_chats.get(chat_id)
        if chat:
            for m in reversed(chat.get("messages", [])):
                delgs = m.get("delegations") or m.get("metadata", {}).get("delegations")
                if delgs:
                    return delgs
        return []

    def get_chat_interactions(self, chat_id: str) -> List[Dict[str, Any]]:
        """Returns interaction envelopes belonging to a chat."""
        if self.is_connected() and self._interactions_col is not None:
            try:
                ixs = list(self._interactions_col.find(
                    {"chat_id": chat_id},
                    {"_id": 0}
                ).sort("timestamp", 1))
                if ixs:
                    return ixs
            except Exception:
                pass

        chat = self._in_memory_chats.get(chat_id)
        if chat:
            for m in reversed(chat.get("messages", [])):
                ixs = m.get("interactions") or m.get("metadata", {}).get("interactions")
                if ixs:
                    return ixs
        return []

    def get_chat_workflow_run(self, chat_id: str, workflow_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Returns workflow run object belonging to a chat."""
        if self.is_connected() and self._workflows_col is not None:
            try:
                query: Dict[str, Any] = {"chat_id": chat_id}
                if workflow_id:
                    query["workflow_id"] = workflow_id
                wf = self._workflows_col.find_one(query, {"_id": 0})
                if wf:
                    return wf
            except Exception:
                pass

        chat = self._in_memory_chats.get(chat_id)
        if chat:
            for m in reversed(chat.get("messages", [])):
                if m.get("role") == "assistant":
                    wf = m.get("workflow_run") or m.get("metadata", {}).get("workflow_run")
                    if wf:
                        if not workflow_id or wf.get("workflow_id") == workflow_id:
                            return wf
        return None

    def get_chat_telemetry(self, chat_id: str) -> Dict[str, Any]:
        """Returns consolidated telemetry package for a conversation."""
        chat = self.get_chat(chat_id)
        if not chat:
            return {}

        events = self.get_chat_events(chat_id)
        delegations = self.get_chat_delegations(chat_id)
        interactions = self.get_chat_interactions(chat_id)

        graphs: Dict[str, Any] = {}
        provenance = None
        goal_traceability = []
        workflow_run = None
        workflow_id = None

        for m in reversed(chat.get("messages", [])):
            if m.get("role") == "assistant":
                workflow_id = workflow_id or m.get("workflow_id") or m.get("metadata", {}).get("workflow_id")
                workflow_run = workflow_run or m.get("workflow_run") or m.get("metadata", {}).get("workflow_run")
                if not graphs.get("execution_graph"):
                    graphs["execution_graph"] = m.get("execution_graph") or m.get("metadata", {}).get("execution_graph")
                if not graphs.get("authority_graph"):
                    graphs["authority_graph"] = m.get("authority_graph") or m.get("metadata", {}).get("authority_graph")
                if not graphs.get("interaction_graph"):
                    graphs["interaction_graph"] = m.get("interaction_graph") or m.get("metadata", {}).get("interaction_graph")
                provenance = provenance or m.get("provenance") or m.get("metadata", {}).get("provenance")
                goal_traceability = goal_traceability or m.get("goal_traceability") or m.get("metadata", {}).get("goal_traceability") or []

        return {
            "chat_id": chat_id,
            "title": chat.get("title", ""),
            "workflow_id": workflow_id,
            "message_count": len(chat.get("messages", [])),
            "workflow_run": workflow_run,
            "execution_events": events,
            "delegations": delegations,
            "interactions": interactions,
            "graphs": graphs,
            "provenance": provenance,
            "goal_traceability": goal_traceability
        }

    def get_chat_telemetry_summary(self) -> Dict[str, Any]:
        """
        Returns aggregated telemetry metrics about saved chats and sessions across all collections.
        """
        mem_chats = list(self._in_memory_chats.values())
        mem_total_msgs = sum(len(c.get("messages", [])) for c in mem_chats)
        mem_total_evs = 0
        mem_total_delgs = 0
        mem_total_ixs = 0
        for c in mem_chats:
            for m in c.get("messages", []):
                mem_total_evs += len(m.get("execution_events") or m.get("metadata", {}).get("execution_events") or [])
                mem_total_delgs += len(m.get("delegations") or m.get("metadata", {}).get("delegations") or [])
                mem_total_ixs += len(m.get("interactions") or m.get("metadata", {}).get("interactions") or [])

        if not self.is_connected() or self._collection is None:
            recent_mem = [
                {"id": c["id"], "title": c.get("title", ""), "message_count": len(c.get("messages", [])), "updated_at": c.get("updated_at", "")}
                for c in sorted(mem_chats, key=lambda x: x.get("updated_at", ""), reverse=True)[:6]
            ]
            return {
                "mongodb_connected": False,
                "storage_mode": "local_persistent_json",
                "database": self.db_name,
                "collections": ["conversations", "execution_events", "delegations", "interactions", "workflow_runs"],
                "total_chats": len(mem_chats),
                "total_messages": mem_total_msgs,
                "total_execution_events": mem_total_evs,
                "total_delegations": mem_total_delgs,
                "total_interactions": mem_total_ixs,
                "recent_sessions": recent_mem
            }
        try:
            total_chats = self._collection.count_documents({})
            docs = list(self._collection.find({}, {"_id": 0, "message_count": 1}))
            total_messages = sum(d.get("message_count", 0) for d in docs)
            total_events = self._events_col.count_documents({}) if self._events_col is not None else mem_total_evs
            total_delgs = self._delegations_col.count_documents({}) if self._delegations_col is not None else mem_total_delgs
            total_ixs = self._interactions_col.count_documents({}) if self._interactions_col is not None else mem_total_ixs
            total_wfs = self._workflows_col.count_documents({}) if self._workflows_col is not None else 0

            recent = list(self._collection.find(
                {},
                {"_id": 0, "id": 1, "title": 1, "message_count": 1, "updated_at": 1}
            ).sort("updated_at", -1).limit(6))

            return {
                "mongodb_connected": True,
                "storage_mode": "mongodb_atlas",
                "database": self.db_name,
                "collections": ["conversations", "execution_events", "delegations", "interactions", "workflow_runs"],
                "total_chats": total_chats,
                "total_messages": total_messages,
                "total_execution_events": total_events,
                "total_delegations": total_delgs,
                "total_interactions": total_ixs,
                "total_workflow_runs": total_wfs,
                "recent_sessions": recent
            }
        except Exception:
            return {
                "mongodb_connected": False,
                "storage_mode": "local_persistent_json",
                "database": self.db_name,
                "collections": ["conversations", "execution_events", "delegations", "interactions", "workflow_runs"],
                "total_chats": len(self._in_memory_chats),
                "total_messages": mem_total_msgs,
                "total_execution_events": mem_total_evs,
                "total_delegations": mem_total_delgs,
                "total_interactions": mem_total_ixs,
                "recent_sessions": []
            }

    def backfill_telemetry_from_sqlite(
        self,
        event_store=None,
        tracker=None,
        three_graphs=None
    ) -> Dict[str, Any]:
        """
        Scans existing chats and backfills execution_events, delegations, interactions,
        three_graphs, and provenance for any chat that executed a workflow but has missing telemetry.
        """
        if event_store is None:
            return {"backfilled_count": 0, "status": "skipped_no_store"}

        backfilled_count = 0

        for chat_id, chat in list(self._in_memory_chats.items()):
            msgs = chat.get("messages", [])
            chat_updated = False
            for m in msgs:
                if m.get("role") != "assistant":
                    continue
                wf_id = m.get("workflow_id") or m.get("metadata", {}).get("workflow_id")
                if not wf_id and isinstance(m.get("workflow_run"), dict):
                    wf_id = m["workflow_run"].get("workflow_id")
                if not wf_id:
                    continue

                m_meta = m.setdefault("metadata", {})

                # 1. Backfill execution_events
                evs = m.get("execution_events") or m_meta.get("execution_events")
                if not evs:
                    db_evs = event_store.list_execution_events(workflow_id=wf_id)
                    if db_evs:
                        evs = [e.model_dump() if hasattr(e, "model_dump") else (e.dict() if hasattr(e, "dict") else dict(e)) for e in db_evs]
                        m["execution_events"] = evs
                        m_meta["execution_events"] = evs
                        chat_updated = True

                # 2. Backfill delegations
                delgs = m.get("delegations") or m_meta.get("delegations")
                if not delgs:
                    root_del = m.get("workflow_run", {}).get("root_delegation_id") if isinstance(m.get("workflow_run"), dict) else None
                    db_delgs = event_store.get_delegation_closure(root_del) if root_del else event_store.list_delegations(limit=50)
                    if db_delgs:
                        delgs = [d.model_dump() if hasattr(d, "model_dump") else (d.dict() if hasattr(d, "dict") else dict(d)) for d in db_delgs]
                        m["delegations"] = delgs
                        m_meta["delegations"] = delgs
                        chat_updated = True

                # 3. Backfill interactions
                ixs = m.get("interactions") or m_meta.get("interactions")
                if not ixs:
                    db_ixs = event_store.list_interactions(workflow_id=wf_id)
                    if db_ixs:
                        ixs = [i.model_dump() if hasattr(i, "model_dump") else (i.dict() if hasattr(i, "dict") else dict(i)) for i in db_ixs]
                        m["interactions"] = ixs
                        m_meta["interactions"] = ixs
                        chat_updated = True

                # 4. Backfill graphs
                eg = m.get("execution_graph") or m_meta.get("execution_graph")
                ag = m.get("authority_graph") or m_meta.get("authority_graph")
                ig = m.get("interaction_graph") or m_meta.get("interaction_graph")
                if (not eg or not ag) and three_graphs:
                    try:
                        g_bundle = three_graphs.get_graphs_for_workflow(wf_id, conversation_id=f"conv_{wf_id}")
                        if not eg and "execution_graph" in g_bundle:
                            eg = _serialize_nx_graph(g_bundle["execution_graph"])
                            m["execution_graph"] = eg
                            m_meta["execution_graph"] = eg
                            chat_updated = True
                        if not ag and "authority_graph" in g_bundle:
                            ag = _serialize_nx_graph(g_bundle["authority_graph"])
                            m["authority_graph"] = ag
                            m_meta["authority_graph"] = ag
                            chat_updated = True
                        if not ig and "interaction_graph" in g_bundle:
                            ig = _serialize_nx_graph(g_bundle["interaction_graph"])
                            m["interaction_graph"] = ig
                            m_meta["interaction_graph"] = ig
                            chat_updated = True
                    except Exception:
                        pass

                # 5. Backfill provenance
                prov = m.get("provenance") or m_meta.get("provenance")
                if not prov and tracker:
                    try:
                        prov = tracker.export_prov_json(wf_id)
                        if prov:
                            m["provenance"] = prov
                            m_meta["provenance"] = prov
                            chat_updated = True
                    except Exception:
                        pass

                if chat_updated:
                    self.store_workflow_telemetry(
                        chat_id=chat_id,
                        workflow_id=wf_id,
                        events=evs,
                        delegations=delgs,
                        interactions=ixs,
                        workflow_run=m.get("workflow_run") or m_meta.get("workflow_run"),
                        graphs={
                            "execution_graph": eg,
                            "authority_graph": ag,
                            "interaction_graph": ig
                        },
                        provenance=prov,
                        goal_matrix=m.get("goal_traceability") or m_meta.get("goal_traceability")
                    )

            if chat_updated:
                backfilled_count += 1

        if backfilled_count > 0:
            self._save_local_chats()

        return {"backfilled_count": backfilled_count, "total_chats": len(self._in_memory_chats)}


def _serialize_nx_graph(g: Any) -> Dict[str, Any]:
    """Helper to serialize NetworkX graphs safely."""
    if g is None:
        return {"nodes": [], "edges": []}
    if isinstance(g, dict) and "nodes" in g and "edges" in g:
        return g
    nodes = []
    if hasattr(g, "nodes"):
        for n in g.nodes:
            d = dict(g.nodes[n])
            d["id"] = str(n)
            if "label" not in d:
                d["label"] = str(n)
            nodes.append(d)
    edges = []
    if hasattr(g, "edges"):
        for u, v, data in g.edges(data=True):
            ed = dict(data)
            ed["source"] = str(u)
            ed["target"] = str(v)
            edges.append(ed)
    return {"nodes": nodes, "edges": edges}
