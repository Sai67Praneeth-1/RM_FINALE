"""
MongoDB Persistence Layer for Agentic AI Chat History and Multi-Turn Conversations.
Stores conversational sessions, generated agent reasoning, interaction graphs, and workflow results.
"""

import os
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
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
        self._last_attempt_time: float = 0.0
        self._connect()

    def _connect(self) -> bool:
        if not self.uri:
            logger.warning("[MongoChatStore] No MONGODB_URI provided in configuration.")
            return False
        import time
        now = time.time()
        # Cooldown: don't attempt reconnection more than once every 10 seconds if offline
        if self._collection is None and (now - self._last_attempt_time) < 10.0:
            return False
        self._last_attempt_time = now
        try:
            self._client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000,
                socketTimeoutMS=4000,
                retryWrites=True,
                maxPoolSize=20
            )
            # Ping database to verify connection
            self._client.admin.command("ping")
            self._db = self._client.get_database(self.db_name)
            self._collection = self._db.get_collection("conversations")
            try:
                # Create indexes for fast lookup and chronological sorting
                self._collection.create_index("id", unique=True)
                self._collection.create_index([("updated_at", -1)])
            except Exception:
                pass
            logger.info(f"[MongoChatStore] Successfully connected to MongoDB database: {self.db_name}")
            return True
        except Exception as e:
            logger.error(f"[MongoChatStore] Connection error: {e}")
            self._client = None
            self._db = None
            self._collection = None
            return False

    @classmethod
    def get_instance(cls) -> "MongoChatStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_connected(self) -> bool:
        if self._collection is not None and self._client is not None:
            try:
                self._client.admin.command("ping")
                return True
            except Exception:
                self._client = None
                self._collection = None
                self._db = None

        import time
        now = time.time()
        if hasattr(self, "_last_attempt_time") and (now - self._last_attempt_time < 10.0):
            return False
        return self._connect()

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
        if not self.is_connected():
            return []
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
            return list(cursor)
        except Exception as e:
            logger.error(f"[MongoChatStore] list_chats error: {e}")
            return []

    def get_chat(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Returns the full conversation document including all messages and graphs."""
        if not self.is_connected():
            return None
        try:
            doc = self._collection.find_one({"id": chat_id}, {"_id": 0})
            return doc
        except Exception as e:
            logger.error(f"[MongoChatStore] get_chat error for {chat_id}: {e}")
            return None

    def create_chat(
        self,
        title: Optional[str] = None,
        initial_messages: Optional[List[Dict[str, Any]]] = None,
        chat_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a new conversation record in MongoDB."""
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
        if self.is_connected():
            try:
                self._collection.update_one({"id": cid}, {"$set": doc}, upsert=True)
            except Exception as e:
                logger.error(f"[MongoChatStore] create_chat error: {e}")
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
            for k, v in metadata.items():
                if v is not None:
                    # Exclude heavyweight full graph structures (these are retrieved via /api/graphs/{wf_id})
                    if k in ("execution_graph", "authority_graph"):
                        continue
                    msg_obj[k] = v

        if not self.is_connected():
            return {
                "id": chat_id,
                "title": "Local Chat",
                "messages": [msg_obj],
                "updated_at": now_iso
            }

        try:
            existing = self._collection.find_one({"id": chat_id})
            if not existing:
                # First message in this chat
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
                self._collection.insert_one(doc)
                doc.pop("_id", None)
                return doc
            else:
                update_fields = {
                    "updated_at": now_iso,
                    "last_message": content[:120]
                }
                # If existing title is generic and this is a user message, update title
                if role == "user" and (existing.get("title") in ("New Investigation", "New Conversation", "Untitled Chat", "") or existing.get("message_count", 0) <= 1):
                    update_fields["title"] = self.generate_smart_title(content)

                self._collection.update_one(
                    {"id": chat_id},
                    {
                        "$push": {"messages": msg_obj},
                        "$inc": {"message_count": 1},
                        "$set": update_fields
                    }
                )
                updated = self._collection.find_one({"id": chat_id}, {"_id": 0})
                return updated or {}
        except Exception as e:
            logger.error(f"[MongoChatStore] append_message error for {chat_id}: {e}")
            return {"id": chat_id, "messages": [msg_obj], "updated_at": now_iso}

    def update_chat_title(self, chat_id: str, new_title: str) -> bool:
        """Renames a chat title."""
        if not self.is_connected() or not new_title:
            return False
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            res = self._collection.update_one(
                {"id": chat_id},
                {"$set": {"title": new_title.strip(), "updated_at": now_iso}}
            )
            return res.matched_count > 0
        except Exception as e:
            logger.error(f"[MongoChatStore] update_chat_title error: {e}")
            return False

    def delete_chat(self, chat_id: str) -> bool:
        """Deletes a conversation by ID."""
        if not self.is_connected():
            return False
        try:
            res = self._collection.delete_one({"id": chat_id})
            return res.deleted_count > 0
        except Exception as e:
            logger.error(f"[MongoChatStore] delete_chat error: {e}")
            return False

    def get_chat_telemetry_summary(self) -> Dict[str, Any]:
        """
        Returns aggregated telemetry metrics about saved chats and sessions in MongoDB.
        Uses safe projections and avoids restricted Atlas free-tier pipeline commands.
        """
        if not self.is_connected() or self._collection is None:
            return {
                "mongodb_connected": False,
                "database": self.db_name,
                "total_chats": 0,
                "total_messages": 0,
                "recent_sessions": []
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
                "database": self.db_name,
                "total_chats": total_chats,
                "total_messages": total_messages,
                "recent_sessions": recent
            }
        except Exception as e:
            logger.error(f"[MongoChatStore] get_chat_telemetry_summary error: {e}")
            return {
                "mongodb_connected": False,
                "database": self.db_name,
                "total_chats": 0,
                "total_messages": 0,
                "recent_sessions": []
            }
