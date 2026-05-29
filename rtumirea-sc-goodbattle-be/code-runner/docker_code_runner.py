from __future__ import annotations

import io
import json
import logging
import tarfile
import threading
import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

import docker

DEFAULT_CONFIG_PATH = "languages.json"
DEFAULT_WORKDIR = "/workspace"
DEFAULT_STDIN_FILE = ".stdin"


@dataclass(frozen=True)
class LanguageConfig:
    image: str
    filename: str
    command: str


@dataclass(frozen=True)
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    stdin: str | None


class DockerCodeRunner:
    _pull_lock = threading.Lock()
    _images_pulled = False

    def __init__(
        self,
        config_path: str = DEFAULT_CONFIG_PATH,
        workdir: str = DEFAULT_WORKDIR,
        auto_pull: bool = True,
        logger: logging.Logger | None = None,
    ) -> None:
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.client = docker.from_env()
        self.config_path = config_path
        self.workdir = workdir
        self.auto_pull = auto_pull
        self.languages = self._load_config(config_path)

        self.logger.info(
            "Runner initialized: config=%s workdir=%s auto_pull=%s languages=%s",
            self.config_path,
            self.workdir,
            self.auto_pull,
            ",".join(sorted(self.languages.keys())),
        )

        if self.auto_pull:
            self._ensure_images_pulled_once()

    def pull_all_images(self) -> None:
        images = sorted({cfg.image for cfg in self.languages.values()})
        for image in images:
            self.logger.info("Pull image: %s", image)
            self._pull_image_with_progress(image)
        self.logger.info("All language images are ready")

    def _pull_image_with_progress(self, image: str) -> None:
        last_status_by_layer: dict[str, str] = {}
        last_report_at = 0.0

        for event in self.client.api.pull(image, stream=True, decode=True):
            status = str(event.get("status", "")).strip()
            layer_id = str(event.get("id", "")).strip()
            progress = str(event.get("progress", "")).strip()
            detail = event.get("progressDetail") or {}

            total = int(detail.get("total") or 0)
            current = int(detail.get("current") or 0)
            percent = int((current / total) * 100) if total > 0 else None

            if layer_id:
                status_key = f"{status}|{percent if percent is not None else progress}"
                if last_status_by_layer.get(layer_id) == status_key:
                    continue
                last_status_by_layer[layer_id] = status_key

            now = time.monotonic()
            should_log = (
                "Downloading" in status
                or "Extracting" in status
                or "Pull complete" in status
                or "Already exists" in status
                or (now - last_report_at) >= 1.0
            )
            if not should_log:
                continue

            last_report_at = now

            if layer_id and percent is not None:
                self.logger.info("  %s: %s (%d%%)", layer_id, status, percent)
            elif layer_id and progress:
                self.logger.info("  %s: %s %s", layer_id, status, progress)
            elif layer_id:
                self.logger.info("  %s: %s", layer_id, status)
            elif status:
                self.logger.info("  %s", status)

    def run_once(
        self,
        language: str,
        source_code: str,
        input_files: dict[str, str] | None = None,
        stdin: str | None = None,
        timeout: int | None = None,
    ) -> ExecutionResult:
        if self.auto_pull:
            self._ensure_images_pulled_once()

        cfg = self._get_language(language)
        files = dict(input_files or {})
        files[cfg.filename] = source_code

        command = cfg.command.format(file=cfg.filename)
        if stdin is not None:
            files[DEFAULT_STDIN_FILE] = stdin
            command = f"{command} < {DEFAULT_STDIN_FILE}"

        self.logger.info(
            "Run start: lang=%s image=%s files=%d stdin=%s",
            language,
            cfg.image,
            len(files),
            "yes" if stdin is not None else "no",
        )

        container = self.client.containers.create(
            image=cfg.image,
            command=["sh", "-lc", command],
            working_dir=self.workdir,
            network_disabled=True,
            stdin_open=False,
            tty=False,
            detach=True,
        )

        try:
            archive = self._build_archive(files)
            container.put_archive(self.workdir, archive)
            container.start()

            wait_result = container.wait(timeout=timeout)
            exit_code = int(wait_result.get("StatusCode", 1))
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            self.logger.info(
                "Run finish: lang=%s exit_code=%d stdout=%dB stderr=%dB",
                language,
                exit_code,
                len(stdout.encode("utf-8")),
                len(stderr.encode("utf-8")),
            )

            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                stdin=stdin,
            )
        finally:
            container.remove(force=True)
            self.logger.debug("Container removed")

    def run_many(
        self,
        language: str,
        source_code: str,
        stdins: list[str | None],
        input_files: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> list[ExecutionResult]:
        results: list[ExecutionResult] = []
        for idx, stdin in enumerate(stdins, start=1):
            self.logger.info("Batch run %d/%d for language=%s", idx, len(stdins), language)
            result = self.run_once(
                language=language,
                source_code=source_code,
                input_files=input_files,
                stdin=stdin,
                timeout=timeout,
            )
            results.append(result)
        return results

    def _ensure_images_pulled_once(self) -> None:
        if DockerCodeRunner._images_pulled:
            return

        with DockerCodeRunner._pull_lock:
            if DockerCodeRunner._images_pulled:
                return
            self.pull_all_images()
            DockerCodeRunner._images_pulled = True

    def _get_language(self, language: str) -> LanguageConfig:
        if language not in self.languages:
            available = ", ".join(sorted(self.languages))
            raise ValueError(f"Unsupported language '{language}'. Available: {available}")
        return self.languages[language]

    @staticmethod
    def _load_config(path: str) -> dict[str, LanguageConfig]:
        with open(path, "r", encoding="utf-8") as f:
            raw: dict[str, Any] = json.load(f)

        parsed: dict[str, LanguageConfig] = {}
        for language, cfg in raw.items():
            parsed[language] = LanguageConfig(
                image=cfg["image"],
                filename=cfg["filename"],
                command=cfg["command"],
            )
        return parsed

    @staticmethod
    def _build_archive(files: dict[str, str]) -> bytes:
        buffer = io.BytesIO()

        with tarfile.open(fileobj=buffer, mode="w") as tar:
            for name, content in files.items():
                safe_name = DockerCodeRunner._safe_rel_path(name)
                data = content.encode("utf-8")
                info = tarfile.TarInfo(name=safe_name)
                info.size = len(data)
                tar.addfile(tarinfo=info, fileobj=io.BytesIO(data))

        return buffer.getvalue()

    @staticmethod
    def _safe_rel_path(path: str) -> str:
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts:
            raise ValueError(f"Invalid file path: {path}")
        normalized = str(pure)
        if normalized in {"", "."}:
            raise ValueError(f"Invalid file path: {path}")
        return normalized
