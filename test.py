from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from textwrap import indent

ROOT = Path(__file__).resolve().parent
QUESTIONS_PATH = ROOT / "questions.md"
ANSWERS_DIR = ROOT / "answers"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
MAIN_PATH = ROOT / "main.py"
TIMEOUT_SECONDS = 900

if not PYTHON.exists():
    PYTHON = Path(sys.executable)


def load_questions() -> list[str]:
    questions: list[str] = []
    for line in QUESTIONS_PATH.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*\d+\.\s+(.*\S)\s*$", line)
        if match:
            questions.append(match.group(1))
    if len(questions) != 10:
        raise RuntimeError(f"Expected 10 questions, found {len(questions)}")
    return questions


def prepare_output_dir() -> None:
    if ANSWERS_DIR.exists():
        shutil.rmtree(ANSWERS_DIR)
    ANSWERS_DIR.mkdir(parents=True, exist_ok=True)


def _drain_stdout(pipe: object, chunks: list[str]) -> None:
    while True:
        chunk = pipe.read(1)
        if chunk == "":
            break
        chunks.append(chunk)
        sys.stdout.write(chunk)
        sys.stdout.flush()


def _drain_stderr(pipe: object, chunks: list[str]) -> None:
    while True:
        chunk = pipe.read(1)
        if chunk == "":
            break
        chunks.append(chunk)


def run_main(question: str) -> tuple[int, str, str, str, str, float]:
    started_at = datetime.now(timezone.utc)
    proc = subprocess.Popen(
        [str(PYTHON), str(MAIN_PATH), question],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    assert proc.stdout is not None
    assert proc.stderr is not None

    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    timed_out = False

    stdout_thread = threading.Thread(target=_drain_stdout, args=(proc.stdout, stdout_chunks), daemon=True)
    stderr_thread = threading.Thread(target=_drain_stderr, args=(proc.stderr, stderr_chunks), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    try:
        returncode = proc.wait(timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        returncode = proc.wait()
    finally:
        stdout_thread.join()
        stderr_thread.join()

    finished_at = datetime.now(timezone.utc)
    stdout = "".join(stdout_chunks)
    stderr = "".join(stderr_chunks)

    if timed_out:
        timeout_note = f"TIMEOUT after {TIMEOUT_SECONDS} seconds"
        stderr = f"{stderr.rstrip()}\n{timeout_note}".strip() if stderr else timeout_note

    return (
        returncode,
        stdout,
        stderr,
        started_at.isoformat(),
        finished_at.isoformat(),
        (finished_at - started_at).total_seconds(),
    )


def render_section(title: str, content: str) -> str:
    body = content.rstrip("\n") or "(empty)"
    return "\n".join([f"## {title}", "", indent(body, "    ")])


def render_answer_file(index: int, question: str, result: tuple[int, str, str, str, str, float]) -> str:
    returncode, stdout, stderr, started_at, finished_at, duration_seconds = result
    status = "success" if returncode == 0 else "failed"
    command = json.dumps(
        {
            "cwd": str(ROOT),
            "argv": [str(PYTHON), str(MAIN_PATH), question],
        },
        ensure_ascii=False,
        indent=2,
    )

    sections = [
        f"# Question {index:02d}",
        "",
        render_section("Question", question),
        "",
        "## Run metadata",
        "",
        f"- Status: {status}",
        f"- Return code: {returncode}",
        f"- Started at: {started_at}",
        f"- Finished at: {finished_at}",
        f"- Duration seconds: {duration_seconds:.2f}",
        "",
        render_section("Command", command),
        "",
        render_section("Stdout", stdout),
        "",
        render_section("Stderr", stderr),
    ]
    return "\n".join(sections) + "\n"


def main() -> None:
    questions = load_questions()
    prepare_output_dir()

    for index, question in enumerate(questions, start=1):
        answer_path = ANSWERS_DIR / f"question_{index:02d}.md"
        print(f"\n[{index}/{len(questions)}] running main.py -> {answer_path.relative_to(ROOT)}")
        result = run_main(question)
        answer_path.write_text(render_answer_file(index, question, result), encoding="utf-8")

        returncode, stdout, stderr, _, _, _ = result
        if stdout and not stdout.endswith("\n"):
            print()
        if stderr.strip():
            print("\n[stderr]", file=sys.stderr)
            sys.stderr.write(stderr)
            if not stderr.endswith("\n"):
                sys.stderr.write("\n")
            sys.stderr.flush()
        print(f"[{index}/{len(questions)}] finished rc={returncode} -> {answer_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
