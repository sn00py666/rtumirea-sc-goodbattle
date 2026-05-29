import logging

from docker.errors import DockerException

from docker_code_runner import DockerCodeRunner


def print_result(result_title: str, result) -> None:
    print(f"\n=== {result_title} ===")
    print(f"stdin: {result.stdin!r}")
    print(f"exit_code: {result.exit_code}")
    print(f"stdout: {result.stdout.strip()!r}")
    print(f"stderr: {result.stderr.strip()!r}")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    runner = DockerCodeRunner(config_path="languages.json", auto_pull=False)

    print("Подготовка Python-образа... (это единственная загрузка)")
    runner.client.images.pull("python:3.12-alpine")

    python_code = """
a, b = map(int, input().split())
print(a + b)
""".strip()

    result = runner.run_once(
        language="python",
        source_code=python_code,
        stdin="2 3\n",
    )
    print_result("Python: сложение двух чисел", result)


if __name__ == "__main__":
    try:
        main()
    except DockerException as exc:
        print("Docker error:", exc)
