"""
SQLite Database schema initialization and connection management.
Ensures durable, concurrent-safe persistence that survives application restarts.
"""

import sqlite3
import json
import threading
from pathlib import Path
from typing import Optional
from backend.config import settings

_local = threading.local()

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS workflow_runs (
    workflow_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    task_description TEXT NOT NULL,
    dataset_name TEXT,
    mode TEXT NOT NULL,
    capture_level INTEGER NOT NULL,
    status TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    root_delegation_id TEXT,
    final_output TEXT,
    error_message TEXT,
    stats TEXT
);

CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    description TEXT,
    system_prompt TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    parent_task_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    assigned_agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    result_summary TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflow_runs(workflow_id)
);

CREATE TABLE IF NOT EXISTS delegations (
    delegation_id TEXT PRIMARY KEY,
    delegation_parent_id TEXT,
    principal_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    completed_at TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS interactions (
    interaction_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    sender_agent_id TEXT NOT NULL,
    receiver_agent_id TEXT NOT NULL,
    interaction_type TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    workflow_id TEXT,
    delegation_id TEXT NOT NULL,
    delegation_parent_id TEXT,
    trace_id TEXT,
    span_id TEXT,
    message_id TEXT NOT NULL,
    reply_to_message_id TEXT,
    semantic_summary TEXT,
    content TEXT,
    resource_refs TEXT,
    sensitivity_label TEXT NOT NULL,
    status TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    downstream_action_ids TEXT,
    provenance_refs TEXT,
    capture_level INTEGER NOT NULL,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS execution_events (
    event_id TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    delegation_id TEXT NOT NULL,
    delegation_parent_id TEXT,
    principal_user_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    agent_instance_id TEXT,
    tool_name TEXT NOT NULL,
    tool_operation TEXT,
    action_semantic TEXT NOT NULL,
    action_outcome TEXT NOT NULL,
    direction TEXT,
    principal_scope TEXT,
    resource_type TEXT,
    resource_id TEXT,
    resource_uri TEXT,
    sensitivity_label TEXT,
    target_principal_id TEXT,
    trace_id TEXT,
    span_id TEXT,
    parent_span_id TEXT,
    workflow_id TEXT,
    task_id TEXT,
    parameters TEXT,
    output_summary TEXT,
    labels TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    title TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    format TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    created_by_agent_id TEXT NOT NULL,
    delegation_id TEXT NOT NULL,
    sensitivity_label TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source_resource_refs TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflow_runs(workflow_id)
);

CREATE TABLE IF NOT EXISTS provenance_edges (
    edge_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    relation TEXT NOT NULL,
    confidence REAL NOT NULL,
    timestamp TEXT NOT NULL,
    metadata TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflow_runs(workflow_id)
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    eval_id TEXT PRIMARY KEY,
    scenario_name TEXT NOT NULL,
    baseline_name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    workload_size INTEGER NOT NULL,
    raw_results_json TEXT
);

-- Performance indices for fast querying and graph reconstruction
CREATE INDEX IF NOT EXISTS idx_exec_delegation ON execution_events(delegation_id);
CREATE INDEX IF NOT EXISTS idx_exec_trace ON execution_events(trace_id);
CREATE INDEX IF NOT EXISTS idx_exec_workflow ON execution_events(workflow_id);
CREATE INDEX IF NOT EXISTS idx_exec_agent ON execution_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_exec_time ON execution_events(time);

CREATE INDEX IF NOT EXISTS idx_interact_delegation ON interactions(delegation_id);
CREATE INDEX IF NOT EXISTS idx_interact_conv ON interactions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_interact_trace ON interactions(trace_id);
CREATE INDEX IF NOT EXISTS idx_interact_sender ON interactions(sender_agent_id);
CREATE INDEX IF NOT EXISTS idx_interact_receiver ON interactions(receiver_agent_id);
CREATE INDEX IF NOT EXISTS idx_interact_time ON interactions(timestamp);

CREATE INDEX IF NOT EXISTS idx_del_parent ON delegations(delegation_parent_id);
CREATE INDEX IF NOT EXISTS idx_del_agent ON delegations(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_workflow ON tasks(workflow_id);
CREATE INDEX IF NOT EXISTS idx_prov_wf ON provenance_edges(workflow_id);
CREATE INDEX IF NOT EXISTS idx_prov_src ON provenance_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_prov_tgt ON provenance_edges(target_id);
"""

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns a thread-local SQLite connection with dictionary-like row factory."""
    path = db_path or settings.DATABASE_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = getattr(_local, "conn", None)
    current_path = getattr(_local, "db_path", None)
    
    if conn is None or current_path != path:
        conn = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode and foreign keys
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        _local.conn = conn
        _local.db_path = path
    return conn

def close_connection():
    """Closes thread-local SQLite connection if open."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _local.conn = None
        _local.db_path = None

def init_db(db_path: Optional[str] = None):
    """Initializes SQLite database tables and default agent records."""
    conn = get_connection(db_path)
    with conn:
        # Pre-migration: If interactions table exists without workflow_id, add it before schema execution
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='interactions'")
        if cur.fetchone():
            col_cur = conn.execute("PRAGMA table_info(interactions)")
            existing_cols = {row[1] for row in col_cur.fetchall()}
            if "workflow_id" not in existing_cols:
                conn.execute("ALTER TABLE interactions ADD COLUMN workflow_id TEXT")

        conn.executescript(SCHEMA_SQL)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_interact_workflow ON interactions(workflow_id)")
        
        # Backfill workflow_id for existing records if null
        conn.execute("""
            UPDATE interactions
            SET workflow_id = CASE
                WHEN task_id LIKE '%task_%' THEN SUBSTR(task_id, INSTR(task_id, 'task_') + 5)
                WHEN conversation_id LIKE 'wf_%' THEN conversation_id
                ELSE conversation_id
            END
            WHERE workflow_id IS NULL AND (task_id IS NOT NULL OR conversation_id IS NOT NULL)
        """)
        
        # Populate default agent identities if not present
        default_agents = [
            ("agent_coordinator", "Coordinator", "Primary Coordinator Agent", 
             "Orchestrates sub-tasks, delegates authority, aggregates multi-agent findings and handles clarification."),
            ("agent_researcher", "Research Agent", "Data & Information Collector", 
             "Collects information from allowlisted local datasets, extracts records, and sends findings to peers."),
            ("agent_analyst", "Analysis Agent", "Statistical & Quantitative Analyst", 
             "Performs statistical, sentiment, and metric calculations through permitted tools and generates structured findings."),
            ("agent_reporter", "Report Agent", "Markdown Report Synthesizer", 
             "Synthesizes received findings into an actionable, transparent Markdown report with verified source references.")
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO agents (agent_id, name, role, description) VALUES (?, ?, ?, ?)",
            default_agents
        )

if __name__ == "__main__":
    init_db()
    print("Database schema initialized at:", settings.DATABASE_PATH)
