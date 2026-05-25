from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..models import SessionFlowNode, SessionLogEntry, SessionLogSection, SessionPreview, SessionSummary


def load_session_previews(session_root: Path) -> list[SessionPreview]:
    session_rows: list[tuple[str, SessionPreview]] = []
    if not session_root.exists():
        return []

    for session_dir in session_root.iterdir():
        if not session_dir.is_dir():
            continue

        metadata = read_workspace_metadata(session_dir / "workspace.yaml")
        title = session_title_from_metadata(metadata)
        if not title:
            continue

        updated_at = metadata.get("updated_at") or metadata.get("created_at") or ""
        session_rows.append(
            (
                updated_at,
                SessionPreview(session_id=session_dir.name, title=title),
            )
        )

    session_rows.sort(key=lambda item: item[0], reverse=True)
    previews = [session for _, session in session_rows]
    if previews:
        active = previews[0]
        previews[0] = SessionPreview(session_id=active.session_id, title=active.title, is_active=True)
    return previews


def load_session_summary(session_root: Path, session_id: str) -> SessionSummary | None:
    session_dir = session_root / session_id
    if not session_dir.is_dir():
        return None

    metadata = read_workspace_metadata(session_dir / "workspace.yaml")
    title = session_title_from_metadata(metadata)
    if not title:
        return None

    events = read_jsonl_events(session_dir / "events.jsonl")
    shutdown_event = next((event for event in reversed(events) if event.get("type") == "session.shutdown"), None)
    model_name = find_current_model(events, shutdown_event)
    usage = extract_usage(shutdown_event, model_name)
    created_value = metadata.get("created_at") or first_event_timestamp(events)
    updated_value = metadata.get("updated_at") or last_event_timestamp(events) or created_value

    return SessionSummary(
        session_id=session_id,
        title=title,
        created_label=format_timestamp(created_value),
        updated_label=format_timestamp(updated_value),
        session_type="Local",
        location="CLI",
        status="Idle" if shutdown_event else "Active",
        model_name=model_name or "Unknown",
        repository=repository_name(metadata.get("repository", "")),
        branch=metadata.get("branch", ""),
        model_turns=count_events(events, "assistant.turn_start"),
        tool_calls=count_events(events, "tool.execution_start"),
        total_input_tokens=usage.get("inputTokens", 0),
        total_output_tokens=usage.get("outputTokens", 0),
        total_cached_input_tokens=usage.get("cacheReadTokens", 0),
        total_tokens=usage.get("inputTokens", 0) + usage.get("outputTokens", 0),
        error_count=count_errors(events),
    )


def load_session_logs(session_root: Path, session_id: str) -> list[SessionLogEntry] | None:
    session_dir = session_root / session_id
    if not session_dir.is_dir():
        return None

    events = read_jsonl_events(session_dir / "events.jsonl")
    return [build_log_entry(index, event) for index, event in enumerate(events)]


def load_session_flow(session_root: Path, session_id: str) -> list[SessionFlowNode] | None:
    session_dir = session_root / session_id
    if not session_dir.is_dir():
        return None

    events = read_jsonl_events(session_dir / "events.jsonl")
    shutdown_event = next((event for event in reversed(events) if event.get("type") == "session.shutdown"), None)
    model_name = find_current_model(events, shutdown_event) or "Unknown"
    return build_flow_nodes(events, model_name)


def read_workspace_metadata(workspace_file: Path) -> dict[str, str]:
    if not workspace_file.exists():
        return {}

    metadata: dict[str, str] = {}
    for raw_line in workspace_file.read_text(encoding="utf-8").splitlines():
        key, separator, value = raw_line.partition(":")
        if not separator:
            continue
        metadata[key.strip()] = value.strip()
    return metadata


def session_title_from_metadata(metadata: dict[str, str]) -> str | None:
    title = metadata.get("name", "").strip()
    return title or None


def read_jsonl_events(events_file: Path) -> list[dict]:
    if not events_file.exists():
        return []

    events: list[dict] = []
    for raw_line in events_file.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            events.append(json.loads(raw_line))
        except json.JSONDecodeError:
            continue
    return events


def find_current_model(events: list[dict], shutdown_event: dict | None) -> str:
    if shutdown_event:
        model_name = shutdown_event.get("data", {}).get("currentModel")
        if isinstance(model_name, str) and model_name:
            return model_name

    for event in reversed(events):
        if event.get("type") != "session.model_change":
            continue
        model_name = event.get("data", {}).get("newModel")
        if isinstance(model_name, str) and model_name:
            return model_name
    return ""


def extract_usage(shutdown_event: dict | None, current_model: str) -> dict[str, int]:
    if not shutdown_event:
        return {}

    model_metrics = shutdown_event.get("data", {}).get("modelMetrics", {})
    if not isinstance(model_metrics, dict) or not model_metrics:
        return {}

    if current_model and current_model in model_metrics:
        usage = model_metrics[current_model].get("usage", {})
    else:
        first_metrics = next(iter(model_metrics.values()))
        usage = first_metrics.get("usage", {}) if isinstance(first_metrics, dict) else {}

    if not isinstance(usage, dict):
        return {}

    return {
        "inputTokens": int(usage.get("inputTokens", 0) or 0),
        "outputTokens": int(usage.get("outputTokens", 0) or 0),
        "cacheReadTokens": int(usage.get("cacheReadTokens", 0) or 0),
    }


def count_events(events: list[dict], event_type: str) -> int:
    return sum(1 for event in events if event.get("type") == event_type)


def count_errors(events: list[dict]) -> int:
    return sum(1 for event in events if is_error_event(event))


def first_event_timestamp(events: list[dict]) -> str:
    for event in events:
        timestamp = event.get("timestamp")
        if isinstance(timestamp, str) and timestamp:
            return timestamp
    return ""


def last_event_timestamp(events: list[dict]) -> str:
    for event in reversed(events):
        timestamp = event.get("timestamp")
        if isinstance(timestamp, str) and timestamp:
            return timestamp
    return ""


def format_timestamp(raw_value: str) -> str:
    if not raw_value:
        return "-"
    try:
        dt = datetime.fromisoformat(raw_value.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return raw_value

    hour = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{dt.month}/{dt.day}/{dt.year}, {hour}:{dt.minute:02d}:{dt.second:02d} {ampm}"


def repository_name(repository: str) -> str:
    return repository.rsplit("/", 1)[-1] if repository else ""


def build_log_entry(index: int, event: dict) -> SessionLogEntry:
    event_type = str(event.get("type") or "event")
    data = event.get("data", {})
    return SessionLogEntry(
        index=index,
        created_label=format_log_timestamp(str(event.get("timestamp") or "")),
        name=display_event_name(event_type, data),
        event_type=event_type,
        details=display_event_details(event_type, data),
        is_error=is_error_event(event),
        sections=build_log_sections(event_type, event),
    )


def is_error_event(event: dict) -> bool:
    if event.get("type") == "abort":
        return True

    data = event.get("data", {})
    return isinstance(data, dict) and data.get("success") is False


def format_log_timestamp(raw_value: str) -> str:
    if not raw_value:
        return "-"
    try:
        dt = datetime.fromisoformat(raw_value.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return raw_value

    hour = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{dt.strftime('%b')} {dt.day}, {hour}:{dt.minute:02d}:{dt.second:02d} {ampm}"


def display_event_name(event_type: str, data: object) -> str:
    if isinstance(data, dict):
        tool_name = data.get("toolName")
        if event_type.startswith("tool.execution") and isinstance(tool_name, str) and tool_name:
            return tool_name

        if event_type.endswith(".message"):
            role = data.get("role")
            if isinstance(role, str) and role:
                return f"{role.title()} Message"

    return humanize_identifier(event_type)


def display_event_details(event_type: str, data: object) -> str:
    if not isinstance(data, dict):
        return compact_text(pretty_value(data), 140)

    if event_type == "session.start":
        context = data.get("context") if isinstance(data.get("context"), dict) else {}
        producer = compact_text(str(data.get("producer") or ""), 36)
        cwd = compact_text(str(context.get("cwd") or ""), 72)
        return join_non_empty([producer, cwd]) or "Session started"

    if event_type == "session.model_change":
        return f"Switched to {data.get('newModel') or 'unknown model'}"

    if event_type.endswith(".message"):
        content = data.get("content") or data.get("transformedContent") or ""
        return compact_text(str(content), 140) or "Message payload"

    if event_type == "assistant.turn_start":
        return join_non_empty([f"turn {data.get('turnId')}" if data.get("turnId") is not None else "", str(data.get("interactionId") or "")]) or "Assistant turn started"

    if event_type.startswith("tool.execution"):
        tool_name = str(data.get("toolName") or "tool")
        turn_id = f"turn {data.get('turnId')}" if data.get("turnId") is not None else ""
        if event_type.endswith("complete"):
            success = data.get("success")
            state = "success" if success is True else "failed" if success is False else "completed"
            return join_non_empty([tool_name, turn_id, state])
        return join_non_empty([tool_name, turn_id, "started"])

    fragments: list[str] = []
    for key, value in data.items():
        if key in {"arguments", "output", "content", "transformedContent"}:
            continue
        if isinstance(value, (dict, list)):
            continue
        fragments.append(f"{key}: {compact_text(str(value), 48)}")
        if len(fragments) == 3:
            break
    return join_non_empty(fragments) or compact_text(pretty_value(data), 140) or "Event payload"


def build_log_sections(event_type: str, event: dict) -> list[SessionLogSection]:
    data = event.get("data", {})
    sections = [
        SessionLogSection(
            title="Metadata",
            content=pretty_value(
                {
                    "type": event_type,
                    "timestamp": event.get("timestamp"),
                }
            ),
        )
    ]

    if isinstance(data, dict):
        if "arguments" in data:
            sections.append(SessionLogSection(title="Arguments", content=pretty_value(data.get("arguments"))))
        if "output" in data:
            sections.append(SessionLogSection(title="Output", content=pretty_value(data.get("output"))))
        if "content" in data:
            sections.append(SessionLogSection(title="Content", content=pretty_value(data.get("content"))))
        if "transformedContent" in data:
            sections.append(SessionLogSection(title="Transformed Content", content=pretty_value(data.get("transformedContent"))))
        if "toolRequests" in data:
            sections.append(SessionLogSection(title="Tool Requests", content=pretty_value(data.get("toolRequests"))))

        remaining = {
            key: value
            for key, value in data.items()
            if key not in {"arguments", "output", "content", "transformedContent", "toolRequests"}
        }
        if remaining:
            sections.append(SessionLogSection(title="Data", content=pretty_value(remaining)))
    elif data not in ({}, None, ""):
        sections.append(SessionLogSection(title="Data", content=pretty_value(data)))

    sections.append(SessionLogSection(title="Raw Event", content=pretty_value(event)))
    return sections


def pretty_value(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def compact_text(value: str, limit: int) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 1]}..."


def humanize_identifier(value: str) -> str:
    parts = [part for part in value.replace("_", ".").replace("-", ".").split(".") if part]
    return " ".join(part.capitalize() for part in parts) or "Event"


def join_non_empty(parts: list[str]) -> str:
    return " | ".join(part for part in parts if part)


def build_flow_nodes(events: list[dict], model_name: str) -> list[SessionFlowNode]:
    nodes: list[SessionFlowNode] = []
    pending_tools: dict[str, dict] = {}

    discovery_events, start_index = split_discovery_events(events)
    if discovery_events:
        nodes.append(build_discovery_node(0, discovery_events))

    next_index = len(nodes)
    for event_index, event in enumerate(events[start_index:], start=start_index):
        event_type = str(event.get("type") or "event")
        data = event.get("data") if isinstance(event.get("data"), dict) else {}

        if event_type == "tool.execution_start":
            tool_call_id = str(data.get("toolCallId") or "")
            if tool_call_id:
                pending_tools[tool_call_id] = data
            continue

        if event_type in {"hook.start", "hook.end", "assistant.turn_start", "assistant.turn_end", "session.start", "session.model_change", "system.message", "session.shutdown"}:
            continue

        if event_type == "user.message":
            if is_internal_user_message(data):
                continue
            nodes.append(build_user_flow_node(next_index, event, event_index))
            next_index += 1
            continue

        if event_type == "assistant.message":
            assistant_nodes = build_assistant_flow_nodes(next_index, event, event_index, model_name)
            nodes.extend(assistant_nodes)
            next_index += len(assistant_nodes)
            continue

        if event_type == "tool.execution_complete":
            tool_call_id = str(data.get("toolCallId") or "")
            started = pending_tools.pop(tool_call_id, None)
            nodes.append(build_tool_flow_node(next_index, event, event_index, started))
            next_index += 1
            continue

        if event_type == "skill.invoked":
            nodes.append(build_skill_flow_node(next_index, event, event_index))
            next_index += 1
            continue

        if event_type == "subagent.selected":
            nodes.append(build_subagent_flow_node(next_index, event, event_index))
            next_index += 1
            continue

        if event_type.startswith("permission."):
            nodes.append(build_permission_flow_node(next_index, event, event_index))
            next_index += 1
            continue

        if event_type == "abort":
            nodes.append(build_abort_flow_node(next_index, event, event_index))
            next_index += 1

    return nodes


def split_discovery_events(events: list[dict]) -> tuple[list[tuple[int, dict]], int]:
    discovery_events: list[tuple[int, dict]] = []
    index = 0
    while index < len(events):
        event = events[index]
        event_type = str(event.get("type") or "event")
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if event_type in {"session.start", "session.model_change", "subagent.selected", "system.message"}:
            discovery_events.append((index, event))
            index += 1
            continue
        if event_type == "user.message" and is_internal_user_message(data):
            discovery_events.append((index, event))
            index += 1
            continue
        break
    return discovery_events, index


def build_discovery_node(index: int, events: list[tuple[int, dict]]) -> SessionFlowNode:
    agent_name = next(
        (
            str((event.get("data") or {}).get("agentDisplayName") or (event.get("data") or {}).get("agentName") or "")
            for _, event in events
            if event.get("type") == "subagent.selected" and isinstance(event.get("data"), dict)
        ),
        "",
    )
    labels = [flow_event_label(event) for _, event in events]
    detail = " · ".join(label for label in ([agent_name] if agent_name else []) + [label for label in labels if label][:3])
    subtitle = f"{len(events)} discovery steps"
    return SessionFlowNode(
        index=index,
        kind="group",
        title="Agent Discovery",
        subtitle=subtitle,
        detail=detail,
        meta=format_log_timestamp(str(events[0][1].get("timestamp") or "")),
        log_index=events[0][0],
        status="muted",
        count=len(events),
    )


def build_user_flow_node(index: int, event: dict, event_index: int) -> SessionFlowNode:
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    content = compact_text(str(data.get("content") or data.get("transformedContent") or "User input"), 220)
    return SessionFlowNode(
        index=index,
        kind="user",
        title="User Message",
        subtitle=format_log_timestamp(str(event.get("timestamp") or "")),
        detail=content,
        meta="",
        log_index=event_index,
        status="accent",
    )


def build_assistant_flow_nodes(index: int, event: dict, event_index: int, model_name: str) -> list[SessionFlowNode]:
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    output_tokens = int(data.get("outputTokens", 0) or 0)
    tool_requests = data.get("toolRequests") if isinstance(data.get("toolRequests"), list) else []
    content = str(data.get("content") or "").strip()
    if not content:
        content = f"Requested {len(tool_requests)} tool calls" if tool_requests else "Assistant emitted a structured response"
    turn_id = data.get("turnId")
    model_subtitle = ["assistant.message"]
    if output_tokens:
        model_subtitle.append(f"{output_tokens} output tokens")
    model_subtitle.append(format_log_timestamp(str(event.get("timestamp") or "")))
    model_detail = join_non_empty(
        [
            f"turn {turn_id}" if turn_id is not None else "",
            f"{len(tool_requests)} tool requests" if tool_requests else "",
        ]
    ) or "Model turn completed"

    return [
        SessionFlowNode(
            index=index,
            kind="model",
            title=model_name,
            subtitle=join_non_empty(model_subtitle),
            detail=model_detail,
            meta="",
            log_index=event_index,
            status="accent",
        ),
        SessionFlowNode(
            index=index + 1,
            kind="response",
            title="Agent Response",
            subtitle=format_log_timestamp(str(event.get("timestamp") or "")),
            detail=compact_text(content, 260),
            meta="",
            log_index=event_index,
            status="neutral",
        ),
    ]


def build_tool_flow_node(index: int, event: dict, event_index: int, started: dict | None) -> SessionFlowNode:
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    started = started or {}
    tool_name = str(started.get("toolName") or (data.get("toolTelemetry") or {}).get("displayTitle") or "Tool")
    arguments = pretty_value(started.get("arguments")) if "arguments" in started else ""
    result = data.get("result")
    detail = compact_text(arguments or pretty_value(result), 220)
    success = data.get("success") is not False
    turn_id = started.get("turnId") or data.get("turnId")
    subtitle_parts = ["success" if success else "failed"]
    if turn_id is not None:
        subtitle_parts.append(f"turn {turn_id}")
    return SessionFlowNode(
        index=index,
        kind="tool",
        title=tool_name,
        subtitle=join_non_empty(subtitle_parts),
        detail=detail or "Tool execution completed",
        meta=format_log_timestamp(str(event.get("timestamp") or "")),
        log_index=event_index,
        status="success" if success else "error",
    )


def build_skill_flow_node(index: int, event: dict, event_index: int) -> SessionFlowNode:
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    name = str(data.get("name") or "Skill")
    description = compact_text(str(data.get("description") or "Skill invoked"), 220)
    return SessionFlowNode(
        index=index,
        kind="skill",
        title=name,
        subtitle="skill.invoked",
        detail=description,
        meta=format_log_timestamp(str(event.get("timestamp") or "")),
        log_index=event_index,
        status="success",
    )


def build_subagent_flow_node(index: int, event: dict, event_index: int) -> SessionFlowNode:
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    tools = data.get("tools") if isinstance(data.get("tools"), list) else []
    tool_summary = f"{len(tools)} tools available" if tools else "Subagent selected"
    return SessionFlowNode(
        index=index,
        kind="agent",
        title=str(data.get("agentDisplayName") or data.get("agentName") or "Subagent"),
        subtitle="subagent.selected",
        detail=tool_summary,
        meta=format_log_timestamp(str(event.get("timestamp") or "")),
        log_index=event_index,
        status="muted",
    )


def build_permission_flow_node(index: int, event: dict, event_index: int) -> SessionFlowNode:
    event_type = str(event.get("type") or "permission")
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    return SessionFlowNode(
        index=index,
        kind="state",
        title=humanize_identifier(event_type),
        subtitle=str(data.get("toolName") or event_type),
        detail=compact_text(pretty_value(data), 180),
        meta=format_log_timestamp(str(event.get("timestamp") or "")),
        log_index=event_index,
        status="muted",
    )


def build_abort_flow_node(index: int, event: dict, event_index: int) -> SessionFlowNode:
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    return SessionFlowNode(
        index=index,
        kind="state",
        title="Abort",
        subtitle=str(data.get("reason") or "Session aborted"),
        detail=compact_text(pretty_value(data), 180),
        meta=format_log_timestamp(str(event.get("timestamp") or "")),
        log_index=event_index,
        status="error",
    )


def flow_event_label(event: dict) -> str:
    event_type = str(event.get("type") or "event")
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    if event_type == "subagent.selected":
        return str(data.get("agentDisplayName") or data.get("agentName") or "Subagent")
    if event_type == "session.model_change":
        return str(data.get("newModel") or "Model selected")
    if event_type == "user.message" and is_internal_user_message(data):
        return "Skill Context"
    return humanize_identifier(event_type)


def is_internal_user_message(data: dict) -> bool:
    content = str(data.get("content") or "")
    return content.lstrip().startswith("<skill-context")
