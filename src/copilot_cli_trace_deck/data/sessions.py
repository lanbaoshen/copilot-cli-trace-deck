from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from ..models import SessionFlowNode, SessionLogEntry, SessionLogSection, SessionModelUsage, SessionPreview, SessionSummary


@dataclass(frozen=True)
class ModelPricing:
    input_usd_per_million: Decimal
    cached_input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    cache_write_usd_per_million: Decimal = Decimal("0")


AI_CREDIT_USD = Decimal("0.01")
TOKENS_PER_MILLION = Decimal("1000000")
MODEL_PRICING: dict[str, ModelPricing] = {
    "gpt-4.1": ModelPricing(Decimal("2.00"), Decimal("0.50"), Decimal("8.00")),
    "gpt-5-mini": ModelPricing(Decimal("0.25"), Decimal("0.025"), Decimal("2.00")),
    "gpt-5.2": ModelPricing(Decimal("1.75"), Decimal("0.175"), Decimal("14.00")),
    "gpt-5.2-codex": ModelPricing(Decimal("1.75"), Decimal("0.175"), Decimal("14.00")),
    "gpt-5.3-codex": ModelPricing(Decimal("1.75"), Decimal("0.175"), Decimal("14.00")),
    "gpt-5.4": ModelPricing(Decimal("2.50"), Decimal("0.25"), Decimal("15.00")),
    "gpt-5.4-mini": ModelPricing(Decimal("0.75"), Decimal("0.075"), Decimal("4.50")),
    "gpt-5.4-nano": ModelPricing(Decimal("0.20"), Decimal("0.02"), Decimal("1.25")),
    "gpt-5.5": ModelPricing(Decimal("5.00"), Decimal("0.50"), Decimal("30.00")),
    "claude-haiku-4.5": ModelPricing(Decimal("1.00"), Decimal("0.10"), Decimal("5.00"), Decimal("1.25")),
    "claude-sonnet-4": ModelPricing(Decimal("3.00"), Decimal("0.30"), Decimal("15.00"), Decimal("3.75")),
    "claude-sonnet-4.5": ModelPricing(Decimal("3.00"), Decimal("0.30"), Decimal("15.00"), Decimal("3.75")),
    "claude-sonnet-4.6": ModelPricing(Decimal("3.00"), Decimal("0.30"), Decimal("15.00"), Decimal("3.75")),
    "claude-opus-4.5": ModelPricing(Decimal("5.00"), Decimal("0.50"), Decimal("25.00"), Decimal("6.25")),
    "claude-opus-4.6": ModelPricing(Decimal("5.00"), Decimal("0.50"), Decimal("25.00"), Decimal("6.25")),
    "claude-opus-4.7": ModelPricing(Decimal("5.00"), Decimal("0.50"), Decimal("25.00"), Decimal("6.25")),
    "gemini-2.5-pro": ModelPricing(Decimal("1.25"), Decimal("0.125"), Decimal("10.00")),
    "gemini-3-flash": ModelPricing(Decimal("0.50"), Decimal("0.05"), Decimal("3.00")),
    "gemini-3.1-pro": ModelPricing(Decimal("2.00"), Decimal("0.20"), Decimal("12.00")),
    "gemini-3.5-flash": ModelPricing(Decimal("1.50"), Decimal("0.15"), Decimal("9.00")),
    "raptor-mini": ModelPricing(Decimal("0.25"), Decimal("0.025"), Decimal("2.00")),
    "goldeneye": ModelPricing(Decimal("1.25"), Decimal("0.125"), Decimal("10.00")),
}


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

        events = read_jsonl_events(session_dir / "events.jsonl")
        shutdown_event = find_current_shutdown_event(events)
        model_name = find_current_model(events, shutdown_event)
        updated_at = last_event_timestamp(events) or metadata.get("updated_at") or metadata.get("created_at") or first_event_timestamp(events)
        session_rows.append(
            (
                updated_at,
                SessionPreview(
                    session_id=session_dir.name,
                    title=title,
                    status="Idle" if shutdown_event else "Active",
                    model_name=model_name,
                    repository=repository_name(metadata.get("repository", "")),
                    branch=metadata.get("branch", ""),
                    updated_label=format_timestamp(updated_at) if updated_at else "",
                    is_active=shutdown_event is None,
                ),
            )
        )

    session_rows.sort(key=lambda item: item[0], reverse=True)
    return [session for _, session in session_rows]


def load_session_summary(session_root: Path, session_id: str) -> SessionSummary | None:
    session_dir = session_root / session_id
    if not session_dir.is_dir():
        return None

    metadata = read_workspace_metadata(session_dir / "workspace.yaml")
    title = session_title_from_metadata(metadata)
    if not title:
        return None

    events = read_jsonl_events(session_dir / "events.jsonl")
    shutdown_event = find_current_shutdown_event(events)
    model_name = find_current_model(events, shutdown_event)
    model_usages, billing_stage = extract_model_usages(events, shutdown_event)
    usage = aggregate_usage(model_usages)
    estimated_cost_usd, estimated_ai_credits, billing_note = build_billing_estimate(model_usages, billing_stage)
    created_value = metadata.get("created_at") or first_event_timestamp(events)
    updated_value = last_event_timestamp(events) or metadata.get("updated_at") or created_value

    return SessionSummary(
        session_id=session_id,
        title=title,
        created_label=format_timestamp(created_value),
        updated_label=format_timestamp(updated_value),
        session_type="Local",
        location="CLI",
        status="Idle" if shutdown_event else "Active",
        model_name=model_name or "Unknown",
        models_used_label=build_models_used_label(model_usages, model_name),
        repository=repository_name(metadata.get("repository", "")),
        branch=metadata.get("branch", ""),
        model_turns=count_events(events, "assistant.turn_start"),
        tool_calls=count_events(events, "tool.execution_start"),
        total_input_tokens=usage.get("inputTokens", 0),
        total_output_tokens=usage.get("outputTokens", 0),
        total_cached_input_tokens=usage.get("cacheReadTokens", 0),
        total_cache_write_tokens=usage.get("cacheWriteTokens", 0),
        total_tokens=usage.get("inputTokens", 0) + usage.get("outputTokens", 0),
        estimated_cost_usd=estimated_cost_usd,
        estimated_ai_credits=estimated_ai_credits,
        billing_note=billing_note,
        model_usages=model_usages,
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
    shutdown_event = find_current_shutdown_event(events)
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


def find_current_shutdown_event(events: list[dict]) -> dict | None:
    latest_shutdown: dict | None = None
    latest_shutdown_index = -1
    latest_lifecycle_resume_index = -1

    for index, event in enumerate(events):
        event_type = event.get("type")
        if event_type == "session.shutdown":
            latest_shutdown = event
            latest_shutdown_index = index
            continue
        if event_type in {"session.start", "session.resume"}:
            latest_lifecycle_resume_index = index

    if latest_shutdown_index == -1:
        return None
    if latest_lifecycle_resume_index > latest_shutdown_index:
        return None
    return latest_shutdown


def extract_model_usages(events: list[dict], shutdown_event: dict | None) -> tuple[list[SessionModelUsage], str]:
    shutdown_model_usages = extract_all_shutdown_model_usages(events)
    if shutdown_event:
        return shutdown_model_usages, "shutdown"

    live_model_usages = extract_live_model_usages_since_last_shutdown(events)
    merged_model_usages = merge_model_usages(shutdown_model_usages, live_model_usages)
    if merged_model_usages:
        return merged_model_usages, "live"
    return [], "pending"


def extract_all_shutdown_model_usages(events: list[dict]) -> list[SessionModelUsage]:
    merged_model_usages: list[SessionModelUsage] = []
    for event in events:
        if event.get("type") != "session.shutdown":
            continue
        merged_model_usages = merge_model_usages(merged_model_usages, extract_shutdown_model_usages(event))
    return merged_model_usages


def extract_shutdown_model_usages(shutdown_event: dict | None) -> list[SessionModelUsage]:
    if not shutdown_event:
        return []

    model_metrics = shutdown_event.get("data", {}).get("modelMetrics", {})
    if not isinstance(model_metrics, dict):
        return []

    model_usages: list[SessionModelUsage] = []
    for model_name, metrics in model_metrics.items():
        if not isinstance(model_name, str) or not isinstance(metrics, dict):
            continue
        usage = metrics.get("usage", {})
        if not isinstance(usage, dict):
            continue

        model_usage = build_model_usage(model_name, usage)
        if model_usage is None:
            continue
        model_usages.append(model_usage)

    model_usages.sort(key=model_usage_sort_key, reverse=True)
    return model_usages


def extract_live_model_usages(events: list[dict]) -> list[SessionModelUsage]:
    usage_by_model: dict[str, dict[str, int]] = {}
    current_model = ""
    for event in events:
        event_type = str(event.get("type") or "")
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if event_type == "session.model_change":
            model_name = data.get("newModel")
            if isinstance(model_name, str) and model_name:
                current_model = model_name
            continue

        if event_type != "assistant.message":
            continue

        model_name = data.get("model")
        if not isinstance(model_name, str) or not model_name:
            model_name = current_model
        if not model_name:
            continue

        usage = usage_by_model.setdefault(
            model_name,
            {
                "inputTokens": 0,
                "outputTokens": 0,
                "cacheReadTokens": 0,
                "cacheWriteTokens": 0,
            },
        )
        usage["inputTokens"] += parse_token_count(data.get("inputTokens"))
        usage["outputTokens"] += parse_token_count(data.get("outputTokens"))
        usage["cacheReadTokens"] += parse_token_count(data.get("cacheReadTokens"))
        usage["cacheWriteTokens"] += parse_token_count(data.get("cacheWriteTokens"))

    model_usages = [
        model_usage
        for model_name, usage in usage_by_model.items()
        if (model_usage := build_model_usage(model_name, usage)) is not None
    ]
    model_usages.sort(key=model_usage_sort_key, reverse=True)
    return model_usages


def extract_live_model_usages_since_last_shutdown(events: list[dict]) -> list[SessionModelUsage]:
    last_shutdown_index = -1
    for index, event in enumerate(events):
        if event.get("type") == "session.shutdown":
            last_shutdown_index = index
    return extract_live_model_usages(events[last_shutdown_index + 1 :])


def build_model_usage(model_name: str, usage: dict[str, object]) -> SessionModelUsage | None:
    if not model_name:
        return None

    input_tokens = parse_token_count(usage.get("inputTokens"))
    output_tokens = parse_token_count(usage.get("outputTokens"))
    cached_input_tokens = parse_token_count(usage.get("cacheReadTokens"))
    cache_write_tokens = parse_token_count(usage.get("cacheWriteTokens"))
    total_tokens = input_tokens + output_tokens + cached_input_tokens + cache_write_tokens
    estimated_cost_usd = estimate_model_cost(
        model_name,
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        cache_write_tokens=cache_write_tokens,
        output_tokens=output_tokens,
    )

    return SessionModelUsage(
        model_name=model_name,
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        cache_write_tokens=cache_write_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost_usd,
    )


def merge_model_usages(*usage_lists: list[SessionModelUsage]) -> list[SessionModelUsage]:
    merged_usage: dict[str, dict[str, int]] = {}
    for usage_list in usage_lists:
        for item in usage_list:
            usage = merged_usage.setdefault(
                item.model_name,
                {
                    "inputTokens": 0,
                    "outputTokens": 0,
                    "cacheReadTokens": 0,
                    "cacheWriteTokens": 0,
                },
            )
            usage["inputTokens"] += item.input_tokens
            usage["outputTokens"] += item.output_tokens
            usage["cacheReadTokens"] += item.cached_input_tokens
            usage["cacheWriteTokens"] += item.cache_write_tokens

    model_usages = [
        model_usage
        for model_name, usage in merged_usage.items()
        if (model_usage := build_model_usage(model_name, usage)) is not None
    ]
    model_usages.sort(key=model_usage_sort_key, reverse=True)
    return model_usages


def aggregate_usage(model_usages: list[SessionModelUsage]) -> dict[str, int]:
    return {
        "inputTokens": sum(item.input_tokens for item in model_usages),
        "outputTokens": sum(item.output_tokens for item in model_usages),
        "cacheReadTokens": sum(item.cached_input_tokens for item in model_usages),
        "cacheWriteTokens": sum(item.cache_write_tokens for item in model_usages),
    }


def parse_token_count(raw_value: object) -> int:
    try:
        return int(raw_value or 0)
    except (TypeError, ValueError):
        return 0


def estimate_model_cost(
    model_name: str,
    *,
    input_tokens: int,
    cached_input_tokens: int,
    cache_write_tokens: int,
    output_tokens: int,
) -> Decimal | None:
    pricing = lookup_model_pricing(model_name)
    if not pricing:
        return Decimal("0") if not any((input_tokens, cached_input_tokens, cache_write_tokens, output_tokens)) else None

    return (
        Decimal(input_tokens) * pricing.input_usd_per_million
        + Decimal(cached_input_tokens) * pricing.cached_input_usd_per_million
        + Decimal(cache_write_tokens) * pricing.cache_write_usd_per_million
        + Decimal(output_tokens) * pricing.output_usd_per_million
    ) / TOKENS_PER_MILLION


def build_billing_estimate(model_usages: list[SessionModelUsage], billing_stage: str) -> tuple[Decimal | None, Decimal | None, str]:
    if not model_usages:
        if billing_stage == "live":
            return None, None, "Live billing estimate will appear after the first assistant response. Copilot only publishes live output tokens; input and cache token counters refresh on session shutdown."
        return None, None, "Billing estimate appears after session shutdown publishes model metrics."

    missing_pricing = [item.model_name for item in model_usages if item.total_tokens and item.estimated_cost_usd is None]
    known_costs = [item.estimated_cost_usd for item in model_usages if item.estimated_cost_usd is not None]
    if not known_costs and missing_pricing:
        missing_models = ", ".join(missing_pricing)
        return None, None, f"Billing estimate unavailable because pricing is missing for: {missing_models}."

    estimated_cost_usd = sum(known_costs, Decimal("0"))
    estimated_ai_credits = estimated_cost_usd / AI_CREDIT_USD
    if missing_pricing:
        missing_models = ", ".join(missing_pricing)
        if billing_stage == "live":
            note = f"Live partial estimate. Completed shutdown metrics are included when available; the active segment contributes output tokens only because Copilot does not publish live input or cache token counts. Unpriced models excluded: {missing_models}. Final shutdown metrics may increase totals."
        else:
            note = f"Partial estimate. Unpriced models excluded: {missing_models}."
    elif billing_stage == "live":
        note = "Live estimate includes completed shutdown metrics plus live output tokens from the active event log tail. Input and cache token totals refresh on the next session shutdown."
    else:
        note = "Estimate aggregates all models recorded in session shutdown metrics."
    return estimated_cost_usd, estimated_ai_credits, note


def build_models_used_label(model_usages: list[SessionModelUsage], current_model: str) -> str:
    model_names = [item.model_name for item in model_usages if item.model_name]
    if not model_names:
        return current_model or "Unknown"
    if len(model_names) == 1:
        return model_names[0]

    primary_model = current_model if current_model in model_names else model_names[0]
    remaining_models = len(model_names) - 1
    return f"{primary_model} + {remaining_models} more"


def model_usage_sort_key(item: SessionModelUsage) -> tuple[int, Decimal, int, str]:
    estimated_cost = item.estimated_cost_usd if item.estimated_cost_usd is not None else Decimal("-1")
    has_pricing = 1 if item.estimated_cost_usd is not None else 0
    return has_pricing, estimated_cost, item.total_tokens, item.model_name.lower()


def lookup_model_pricing(model_name: str) -> ModelPricing | None:
    for candidate in model_key_candidates(model_name):
        pricing = MODEL_PRICING.get(candidate)
        if pricing:
            return pricing
    return None


def model_key_candidates(model_name: str) -> list[str]:
    raw_candidates = {model_name}
    for separator in ("/", ":", "@"):
        if separator in model_name:
            raw_candidates.add(model_name.rsplit(separator, 1)[-1])

    normalized_candidates: list[str] = []
    seen: set[str] = set()
    for raw_candidate in raw_candidates:
        candidate = normalize_model_key(raw_candidate)
        for variant in candidate_variants(candidate):
            if variant and variant not in seen:
                seen.add(variant)
                normalized_candidates.append(variant)
    return normalized_candidates


def candidate_variants(candidate: str) -> list[str]:
    variants = [candidate]
    for suffix in ("-public-preview", "-preview", "-ga"):
        if candidate.endswith(suffix):
            variants.append(candidate[: -len(suffix)])
    return variants


def normalize_model_key(value: str) -> str:
    normalized_chars: list[str] = []
    previous_is_separator = False
    for char in value.strip().lower():
        if char.isalnum() or char == ".":
            normalized_chars.append(char)
            previous_is_separator = False
            continue
        if not previous_is_separator:
            normalized_chars.append("-")
            previous_is_separator = True
    return "".join(normalized_chars).strip("-")


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

        if event_type == "session.resume":
            nodes.append(build_resume_flow_node(next_index, event, event_index))
            next_index += 1
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


def build_resume_flow_node(index: int, event: dict, event_index: int) -> SessionFlowNode:
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    return SessionFlowNode(
        index=index,
        kind="state",
        title="Session Resumed",
        subtitle=format_log_timestamp(str(event.get("timestamp") or "")),
        detail=compact_text(pretty_value(data), 180) if data else "Resumed previous Copilot CLI session",
        meta="",
        log_index=event_index,
        status="muted",
    )


def flow_event_label(event: dict) -> str:
    event_type = str(event.get("type") or "event")
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    if event_type == "subagent.selected":
        return str(data.get("agentDisplayName") or data.get("agentName") or "Subagent")
    if event_type == "session.resume":
        return "Session Resumed"
    if event_type == "session.model_change":
        return str(data.get("newModel") or "Model selected")
    if event_type == "user.message" and is_internal_user_message(data):
        return "Skill Context"
    return humanize_identifier(event_type)


def is_internal_user_message(data: dict) -> bool:
    content = str(data.get("content") or "")
    return content.lstrip().startswith("<skill-context")
