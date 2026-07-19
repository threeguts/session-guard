import json
import os
import subprocess
from pathlib import Path
from threading import Event, Thread
from time import sleep
from typing import Any, Callable

from config_helpers import (
    PROJECT_ROOT,
    get_browser_roots,
    get_sensitive_paths,
    get_traceevent_helper_path,
)

from .event_handling import handle_external_file_event

FileEventCallback = Callable[[dict[str, Any]], None]


class TraceEventFileSource:
    def __init__(
        self,
        callback: FileEventCallback = handle_external_file_event,
    ) -> None:
        self.callback = callback
        self.process: subprocess.Popen[str] | None = None
        self.threads: list[Thread] = []
        self.stop_requested = Event()

    def start(self) -> None:
        if self.process is not None and self.process.poll() is None:
            return

        command = self.build_command()
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.stop_requested.clear()
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creationflags,
        )

        self.threads = [
            Thread(target=self.read_stdout, daemon=True),
            Thread(target=self.read_stderr, daemon=True),
        ]
        for thread in self.threads:
            thread.start()

        sleep(0.25)
        if self.process.poll() is not None:
            raise RuntimeError(
                f"TraceEvent file helper exited early with code {self.process.returncode}."
            )

    def stop(self) -> None:
        self.stop_requested.set()
        process = self.process
        if process is not None and process.poll() is None:
            if process.stdin is not None:
                try:
                    process.stdin.write("stop\n")
                    process.stdin.flush()
                    process.stdin.close()
                except OSError:
                    pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            except OSError:
                process.kill()
                process.wait(timeout=5)

        for thread in self.threads:
            thread.join(timeout=1)

        self.process = None
        self.threads = []

    def build_command(self) -> list[str]:
        helper_path = Path(get_traceevent_helper_path())
        if helper_path.exists():
            command = [str(helper_path)]
        else:
            project_path = PROJECT_ROOT / "tools" / "SessionGuard.FileEtw"
            command = ["dotnet", "run", "--project", str(project_path), "--"]

        command.extend(["--session-name", "SessionGuardFileEtw"])
        command.extend(["--ttl-seconds", "120"])

        for browser_root in get_browser_roots() or []:
            expanded_root = os.path.expandvars(str(browser_root))
            if expanded_root:
                command.extend(["--browser-root", expanded_root])

        for sensitive_path in get_sensitive_paths():
            command.extend(["--sensitive-path", sensitive_path])

        return command

    def read_stdout(self) -> None:
        process = self.process
        if process is None or process.stdout is None:
            return

        for line in process.stdout:
            if self.stop_requested.is_set():
                break
            line = line.strip()
            if not line:
                continue
            try:
                file_row = json.loads(line)
            except json.JSONDecodeError as error:
                print(f"TraceEvent file helper emitted invalid JSON: {error}: {line}")
                continue
            if not isinstance(file_row, dict):
                print(f"TraceEvent file helper emitted non-object JSON: {line}")
                continue
            try:
                self.callback(file_row)
            except Exception as error:
                print(f"TraceEvent file helper row failed: {error}")

    def read_stderr(self) -> None:
        process = self.process
        if process is None or process.stderr is None:
            return

        for line in process.stderr:
            if self.stop_requested.is_set():
                break
            line = line.strip()
            if line:
                print(f"TraceEvent file helper: {line}")
