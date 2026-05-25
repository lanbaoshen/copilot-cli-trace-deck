from __future__ import annotations

import argparse
import json
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from ..data.sessions import load_session_flow, load_session_logs, load_session_previews, load_session_summary
from .pages import PAGE_TITLE, build_flow_feed_payload, build_flow_page, build_index_feed_payload, build_index_page, build_logs_feed_payload, build_logs_page, build_missing_session_page, build_session_page, build_session_snapshot_payload


DEFAULT_SESSION_ROOT = Path.home() / ".copilot" / "session-state"
RELEVANT_SESSION_FILES = {"events.jsonl", "workspace.yaml"}
SSE_HEARTBEAT_INTERVAL = 15.0


def build_server_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def serialize_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def is_relevant_session_path(raw_path: str, session_root: Path) -> bool:
    if not raw_path:
        return False

    path = Path(raw_path).expanduser().resolve(strict=False)
    normalized_root = session_root.expanduser().resolve(strict=False)
    if path.name not in RELEVANT_SESSION_FILES:
        return False

    try:
        path.relative_to(normalized_root)
    except ValueError:
        return False
    return True


class SessionStateChangeHandler(FileSystemEventHandler):
    def __init__(self, broadcaster: "SessionStateChangeBroadcaster") -> None:
        self.broadcaster = broadcaster

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        src_path = getattr(event, "src_path", "")
        dest_path = getattr(event, "dest_path", "")
        if is_relevant_session_path(src_path, self.broadcaster.session_root) or is_relevant_session_path(dest_path, self.broadcaster.session_root):
            self.broadcaster.notify_change()


class SessionStateChangeBroadcaster:
    def __init__(self, session_root: Path) -> None:
        self.session_root = session_root.expanduser()
        self._condition = threading.Condition()
        self._version = 0
        self._observer: Observer | None = None

    def start(self) -> None:
        watch_root = self.session_root if self.session_root.exists() else self.session_root.parent
        observer = Observer()
        observer.schedule(SessionStateChangeHandler(self), str(watch_root), recursive=True)
        observer.start()
        self._observer = observer

    def stop(self) -> None:
        observer = self._observer
        if observer is None:
            return

        observer.stop()
        observer.join(timeout=5)
        self._observer = None

    def current_version(self) -> int:
        with self._condition:
            return self._version

    def notify_change(self) -> None:
        with self._condition:
            self._version += 1
            self._condition.notify_all()

    def wait_for_change(self, version: int, timeout: float) -> int:
        with self._condition:
            if self._version != version:
                return self._version

            self._condition.wait(timeout=timeout)
            return self._version


class TraceDeckHandler(BaseHTTPRequestHandler):
    session_root = DEFAULT_SESSION_ROOT
    change_broadcaster: SessionStateChangeBroadcaster | None = None

    def handle(self) -> None:
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            self.close_connection = True

    def do_GET(self) -> None:  # noqa: N802
        parsed_url = urlsplit(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)
        if path == "/index.events":
            self.respond_event_stream(lambda: serialize_payload(build_index_feed_payload(load_session_previews(self.session_root))))
            return

        if path == "/index.json":
            self.respond_json(build_index_feed_payload(load_session_previews(self.session_root)), HTTPStatus.OK)
            return

        if path in {"/", "/index.html"}:
            self.respond_html(build_index_page(load_session_previews(self.session_root)), HTTPStatus.OK)
            return

        path_parts = [part for part in path.split("/") if part]
        if path_parts[:1] == ["sessions"]:
            if len(path_parts) < 2:
                self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                return

            session_id = path_parts[1]
            summary = load_session_summary(self.session_root, session_id)
            if summary is None:
                self.respond_html(build_missing_session_page(session_id), HTTPStatus.NOT_FOUND)
                return

            if len(path_parts) == 3 and path_parts[2] == "logs":
                log_entries = load_session_logs(self.session_root, session_id)
                self.respond_html(build_logs_page(summary, log_entries or []), HTTPStatus.OK)
                return

            if len(path_parts) == 3 and path_parts[2] == "summary.events":
                self.respond_event_stream(
                    lambda: serialize_payload(build_session_snapshot_payload(load_session_summary(self.session_root, session_id) or summary))
                )
                return

            if len(path_parts) == 3 and path_parts[2] == "summary.json":
                self.respond_json(build_session_snapshot_payload(summary), HTTPStatus.OK)
                return

            if len(path_parts) == 3 and path_parts[2] == "logs.events":
                self.respond_event_stream(
                    lambda: serialize_payload(build_logs_feed_payload(load_session_logs(self.session_root, session_id) or [], -1))
                )
                return

            if len(path_parts) == 3 and path_parts[2] == "logs.json":
                after_value = query.get("after", ["-1"])[0]
                try:
                    after_index = int(after_value)
                except ValueError:
                    after_index = -1

                log_entries = load_session_logs(self.session_root, session_id) or []
                payload = build_logs_feed_payload(log_entries, after_index)
                self.respond_json(payload, HTTPStatus.OK)
                return

            if len(path_parts) == 3 and path_parts[2] == "flow":
                flow_nodes = load_session_flow(self.session_root, session_id)
                self.respond_html(build_flow_page(summary, flow_nodes or []), HTTPStatus.OK)
                return

            if len(path_parts) == 3 and path_parts[2] == "flow.events":
                self.respond_event_stream(
                    lambda: serialize_payload(
                        build_flow_feed_payload(
                            session_id,
                            load_session_summary(self.session_root, session_id) or summary,
                            load_session_flow(self.session_root, session_id) or [],
                            -1,
                        )
                    )
                )
                return

            if len(path_parts) == 3 and path_parts[2] == "flow.json":
                after_value = query.get("after", ["-1"])[0]
                try:
                    after_index = int(after_value)
                except ValueError:
                    after_index = -1

                flow_nodes = load_session_flow(self.session_root, session_id) or []
                payload = build_flow_feed_payload(session_id, summary, flow_nodes, after_index)
                self.respond_json(payload, HTTPStatus.OK)
                return

            if len(path_parts) == 2:
                self.respond_html(build_session_page(summary), HTTPStatus.OK)
                return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def respond_html(self, page: str, status: HTTPStatus) -> None:
        body = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_json(self, payload: dict[str, object], status: HTTPStatus) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_event_stream(self, snapshot_loader) -> None:
        self.close_connection = True
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        broadcaster = self.change_broadcaster
        version = broadcaster.current_version() if broadcaster else 0
        previous_snapshot = snapshot_loader()
        last_heartbeat = time.monotonic()

        try:
            self.write_event_stream_message("update")
            while True:
                if broadcaster is None:
                    time.sleep(SSE_HEARTBEAT_INTERVAL)
                    self.write_event_stream_comment("keepalive")
                    last_heartbeat = time.monotonic()
                    continue

                remaining = max(0.0, SSE_HEARTBEAT_INTERVAL - (time.monotonic() - last_heartbeat))
                next_version = broadcaster.wait_for_change(version, remaining)
                now = time.monotonic()
                if next_version != version:
                    version = next_version
                    snapshot = snapshot_loader()
                    if snapshot != previous_snapshot:
                        self.write_event_stream_message("update")
                        previous_snapshot = snapshot
                        last_heartbeat = now
                        continue

                if now - last_heartbeat >= SSE_HEARTBEAT_INTERVAL:
                    self.write_event_stream_comment("keepalive")
                    last_heartbeat = now
        except (BrokenPipeError, ConnectionResetError, TimeoutError, ValueError):
            return

    def write_event_stream_comment(self, comment: str) -> None:
        self.wfile.write(f": {comment}\n\n".encode("utf-8"))
        self.wfile.flush()

    def write_event_stream_message(self, data: str) -> None:
        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
        self.wfile.flush()

    def log_message(self, format: str, *args: object) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=PAGE_TITLE)
    parser.add_argument("source", nargs="?", default=str(DEFAULT_SESSION_ROOT), help="Session-state root to read")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=9887, help="Port to listen on")
    parser.add_argument(
        "--quiet",
        "--quite",
        action="store_true",
        dest="quiet",
        help="Suppress the startup banner and do not open a browser automatically",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    TraceDeckHandler.session_root = Path(args.source).expanduser()
    TraceDeckHandler.change_broadcaster = SessionStateChangeBroadcaster(TraceDeckHandler.session_root)
    TraceDeckHandler.change_broadcaster.start()
    server = ThreadingHTTPServer((args.host, args.port), TraceDeckHandler)
    url = build_server_url(args.host, args.port)
    if not args.quiet:
        print(f"Serving {PAGE_TITLE} on {url}")
        webbrowser.open(url)
    else:
        print(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if TraceDeckHandler.change_broadcaster is not None:
            TraceDeckHandler.change_broadcaster.stop()
            TraceDeckHandler.change_broadcaster = None
    return 0
