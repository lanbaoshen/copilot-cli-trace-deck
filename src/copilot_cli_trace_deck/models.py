from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionPreview:
    session_id: str
    title: str
    is_active: bool = False


@dataclass(frozen=True)
class SessionSummary:
    session_id: str
    title: str
    created_label: str
    updated_label: str
    session_type: str
    location: str
    status: str
    model_name: str
    repository: str
    branch: str
    model_turns: int
    tool_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_cached_input_tokens: int
    total_tokens: int
    error_count: int


@dataclass(frozen=True)
class SessionLogSection:
    title: str
    content: str


@dataclass(frozen=True)
class SessionLogEntry:
    index: int
    created_label: str
    name: str
    event_type: str
    details: str
    is_error: bool
    sections: list[SessionLogSection]


@dataclass(frozen=True)
class SessionFlowNode:
    index: int
    kind: str
    title: str
    subtitle: str
    detail: str
    meta: str
    log_index: int | None = None
    status: str = "neutral"
    count: int = 1
