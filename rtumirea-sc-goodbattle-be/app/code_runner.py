from __future__ import annotations

import io
import json
import os
import tarfile
import threading
import time
from dataclasses import dataclass
from typing import Any

import docker
from docker.errors import DockerException

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'code-runner', 'languages.json')
WORKDIR = '/workspace'
STDIN_FILENAME = '.stdin'


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
    timed_out: bool


class DockerCodeRunner:
    _pull_lock = threading.Lock()
    _images_ready = False

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH) -> None:
        self.client = docker.from_env()
        self.languages = self._load_config(config_path)

    def ensure_ready(self) -> None:
        if DockerCodeRunner._images_ready:
            return

        with DockerCodeRunner._pull_lock:
            if DockerCodeRunner._images_ready:
                return
            images = sorted({config.image for config in self.languages.values()})
            for image in images:
                self.client.images.pull(image)
            DockerCodeRunner._images_ready = True

    def run_once(
        self,
        language: str,
        source_code: str,
        stdin: str,
        timeout_ms: int,
        memory_limit_mb: int,
    ) -> ExecutionResult:
        config = self.languages.get(language)
        if config is None:
            supported = ', '.join(sorted(self.languages.keys()))
            raise ValueError(f'Unsupported language: {language}. Supported: {supported}')

        command = config.command.format(file=config.filename)
        container = self.client.containers.create(
            image=config.image,
            command=['sh', '-lc', f'{command} < {STDIN_FILENAME}'],
            working_dir=WORKDIR,
            network_disabled=True,
            mem_limit=f'{max(memory_limit_mb, 8)}m',
            stdin_open=False,
            tty=False,
            detach=True,
        )

        try:
            archive = self._build_archive(
                {
                    config.filename: source_code,
                    STDIN_FILENAME: stdin,
                }
            )
            container.put_archive(WORKDIR, archive)
            container.start()

            timeout_seconds = max(timeout_ms / 1000.0, 0.05)
            deadline = time.monotonic() + timeout_seconds

            while True:
                container.reload()
                if container.status in {'exited', 'dead'}:
                    break

                if time.monotonic() >= deadline:
                    container.remove(force=True)
                    return ExecutionResult(
                        stdout='',
                        stderr='Time limit exceeded',
                        exit_code=124,
                        timed_out=True,
                    )

                time.sleep(0.01)

            wait_result = container.wait()
            exit_code = int(wait_result.get('StatusCode', 1))
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')
            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                timed_out=False,
            )
        finally:
            try:
                container.remove(force=True)
            except DockerException:
                pass

    @staticmethod
    def _load_config(config_path: str) -> dict[str, LanguageConfig]:
        with open(config_path, 'r', encoding='utf-8') as config_file:
            raw_config: dict[str, Any] = json.load(config_file)

        parsed: dict[str, LanguageConfig] = {}
        for language, payload in raw_config.items():
            parsed[language] = LanguageConfig(
                image=str(payload['image']),
                filename=str(payload['filename']),
                command=str(payload['command']),
            )
        return parsed

    @staticmethod
    def _build_archive(files: dict[str, str]) -> bytes:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w') as tar:
            for name, content in files.items():
                encoded = content.encode('utf-8')
                info = tarfile.TarInfo(name=name)
                info.size = len(encoded)
                tar.addfile(tarinfo=info, fileobj=io.BytesIO(encoded))
        return buffer.getvalue()


runner = DockerCodeRunner()
