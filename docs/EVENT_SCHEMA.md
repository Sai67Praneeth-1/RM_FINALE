# Event Schema Specification

This document details the exact JSON and database schemas for all telemetry events captured by the Observability Gateway.

---

## 1. Common Information Model (CIM) Event Schema

Standardized autonomous multi-agent execution event schema specification.

| Field | Required | Type | Semantics |
|---|---|---|---|
| `event_id` | **Yes** | String (UUID) | Unique identifier for this execution event. |
| `time` | **Yes** | String (ISO 8601) | Timestamp at capture point (UTC). |
| `delegation_id` | **Yes** | String | Durable authorization context identifier. |
| `delegation_parent_id` | No | String / null | Parent delegation identifier for lineage closure. |
| `principal_user_id` | **Yes** | String | Authenticated principal who originated authority. |
| `agent_id` | **Yes** | String | Logical agent identity (`agent_coordinator`, etc.). |
| `agent_instance_id` | No | String / null | Concrete session or process instance. |
| `tool_name` | **Yes** | String | Tool family name (`file_system`, `analytics_engine`). |
| `tool_operation` | No | String | Native operation name (`read_sample_dataset`). |
| `action_semantic` | **Yes** | Enum | Tier-1 verb: `read`, `write`, `search`, `share`, `invoke`, `delegate`, `spawn`. |
| `action_outcome` | No | Enum | `success`, `failure`, `unknown`. |
| `direction` | No | Enum | `internal`, `external`, `unknown`. |
| `principal_scope` | No | Enum | `self`, `org`, `external`, `unknown`. |
| `resource_type` | No | Enum | `document`, `dataset`, `message`, `ticket`, `artifact`. |
| `resource_id` | No | String | Tool-scoped resource identifier. |
| `resource_uri` | No | String | Canonical URI (e.g., `file://customer_complaints.csv`). |
| `sensitivity_label` | No | Enum | `public`, `internal`, `confidential`, `restricted`. |
| `trace_id` | No | String | Distributed tracing identifier. |
| `span_id` | No | String | Current execution span identifier. |
| `parent_span_id` | No | String / null | Causal parent span identifier. |
| `workflow_id` | No | String | Workflow correlation identifier. |
| `task_id` | No | String | Subtask identifier. |
| `parameters` | No | Dict | Sanitized tool input parameters. |
| `output_summary` | No | String | Output description and elapsed execution latency. |

### Example CIM Event:
```json
{
  "event_id": "evt_7f8a9b1c2d3e",
  "time": "2026-10-15T09:30:00.120Z",
  "delegation_id": "del_5ca7578404ab",
  "delegation_parent_id": "del_root_99a8b7",
  "principal_user_id": "principal_alice",
  "agent_id": "agent_researcher",
  "tool_name": "file_system",
  "tool_operation": "read_sample_dataset",
  "action_semantic": "read",
  "action_outcome": "success",
  "direction": "internal",
  "principal_scope": "org",
  "resource_type": "dataset",
  "resource_id": "customer_complaints.csv",
  "resource_uri": "file://customer_complaints.csv",
  "sensitivity_label": "internal",
  "trace_id": "trc_84920aef",
  "span_id": "spn_9901bc34",
  "workflow_id": "wf_756dcd433d",
  "parameters": {"file_name": "customer_complaints.csv"},
  "output_summary": "Completed read on customer_complaints.csv in 1.45ms",
  "labels": {"elapsed_ms": "1.45"}
}
```

---

## 2. Inter-Agent Interaction Record Schema (Our Proposed Extension)

Based on *RM_MID.pdf*, Slide 12.

| Field | Required | Type | Semantics |
|---|---|---|---|
| `interaction_id` | **Yes** | String (UUID) | Unique interaction identifier. |
| `timestamp` | **Yes** | String (ISO 8601) | Timestamp of message exchange. |
| `sender_agent_id` | **Yes** | String | Verified sender agent identity. |
| `receiver_agent_id` | **Yes** | String | Verified recipient agent identity. |
| `interaction_type` | **Yes** | Enum | `request`, `response`, `delegation`, `result`, `information_transfer`, `escalation`, `handoff`, `clarification`, `warning`. |
| `conversation_id` | **Yes** | String | Conversation or session identifier. |
| `task_id` | **Yes** | String | Subtask identifier. |
| `delegation_id` | **Yes** | String | Bound delegation context. |
| `delegation_parent_id`| No | String / null | Parent delegation for authority closure. |
| `trace_id` | No | String | Causal trace identifier. |
| `span_id` | No | String | Execution span identifier. |
| `message_id` | **Yes** | String | Unique envelope message identifier. |
| `reply_to_message_id` | No | String / null | Explicit reply link for request-response pairs. |
| `semantic_summary` | No | String / null | Permitted semantic summary (Levels 2 & 3). |
| `content` | No | String / null | Observable payload (Level 3 only, PII redacted). |
| `resource_refs` | No | List[String] | Resource identifiers referenced in message. |
| `sensitivity_label` | **Yes** | Enum | `public`, `internal`, `confidential`, `restricted`. |
| `status` | **Yes** | String | `delivered`, `sent`, `failed`, `retried`. |
| `downstream_action_ids`| No | List[String] | Tool/execution event IDs triggered by this message. |
| `provenance_refs` | No | List[String] | Origin resource or artifact links. |
| `capture_level` | **Yes** | Integer (1, 2, 3) | Active capture level when persisted. |

### Example Interaction Record:
```json
{
  "interaction_id": "itr_91109b43fc4e",
  "timestamp": "2026-10-15T09:30:02.450Z",
  "sender_agent_id": "agent_researcher",
  "receiver_agent_id": "agent_analyst",
  "interaction_type": "information_transfer",
  "conversation_id": "conv_99a8b1c2",
  "task_id": "research_task_wf_756d",
  "delegation_id": "del_5ca7578404ab",
  "delegation_parent_id": "del_root_99a8b7",
  "trace_id": "trc_84920aef",
  "message_id": "msg_00192a83",
  "semantic_summary": "Transferred 8 extracted records from customer_complaints.csv to Analysis Agent.",
  "content": null,
  "resource_refs": ["file://customer_complaints.csv"],
  "sensitivity_label": "internal",
  "status": "delivered",
  "retry_count": 0,
  "downstream_action_ids": ["evt_7f8a9b1c2d3e"],
  "provenance_refs": ["file://customer_complaints.csv"],
  "capture_level": 2
}
```

