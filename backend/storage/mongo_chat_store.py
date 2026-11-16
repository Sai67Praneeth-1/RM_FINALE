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
        self._collection: Optional[Collection] = None
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
            try:
                self._collection.create_index("id", unique=True)
                self._collection.create_index([("updated_at", -1)])
            except Exception:
                pass
            logger.info(f"[MongoChatStore] Connected to MongoDB database: {self.db_name}")
            self._offline_mode = False
            return True
        except Exception:
            # Silent fallback: do not dump lengthy SSL exception traces to terminal
            self._offline_mode = True
            self._client = None
            self._db = None
            self._collection = None
            logger.info("[MongoChatStore] Operating in local persistence mode (local_chats.json + SQLite).")
            return False

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
                    if k in ("execution_graph", "authority_graph"):
                        continue
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
        """Deletes a conversation by ID."""
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
            except Exception:
                pass
        return deleted

    def get_chat_telemetry_summary(self) -> Dict[str, Any]:
        """
        Returns aggregated telemetry metrics about saved chats and sessions.
        """
        if not self.is_connected() or self._collection is None:
            mem_chats = list(self._in_memory_chats.values())
            mem_total_msgs = sum(len(c.get("messages", [])) for c in mem_chats)
            recent_mem = [
                {"id": c["id"], "title": c.get("title", ""), "message_count": len(c.get("messages", [])), "updated_at": c.get("updated_at", "")}
                for c in sorted(mem_chats, key=lambda x: x.get("updated_at", ""), reverse=True)[:6]
            ]
            return {
                "mongodb_connected": False,
                "storage_mode": "local_persistent_json",
                "database": self.db_name,
                "total_chats": len(mem_chats),
                "total_messages": mem_total_msgs,
                "recent_sessions": recent_mem
            }
        try:
            total_chats = self._collection.count_documents({})
            docs = list(self._collection.find({}, {"_id": 0, "message_count": 1}))
            total_messages = sum(d.get("message_count", 0) for d in docs)
            
            recent = list(self._collection.find(
                {},
                {"_id": 0, "id": 1, "title": 1, "message_count": 1, "updated_at": 1}
            ).sort("updated_at", -1).limit(6))
            
            return {
                "mongodb_connected": True,
                "storage_mode": "mongodb_atlas",
                "database": self.db_name,
                "total_chats": total_chats,
                "total_messages": total_messages,
                "recent_sessions": recent
            }
        except Exception:
            return {
                "mongodb_connected": False,
                "storage_mode": "local_persistent_json",
                "database": self.db_name,
                "total_chats": len(self._in_memory_chats),
                "total_messages": sum(len(c.get("messages", [])) for c in self._in_memory_chats.values()),
                "recent_sessions": []
            }
