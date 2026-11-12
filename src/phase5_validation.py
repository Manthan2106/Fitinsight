"""Run and record the complete repository test suite for Phase 5 evidence."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from .phase5_common import EVIDENCE_ROOT, ROOT, proof, sha256_file, write_json
except ImportError:  # Running as ``python src/phase5_validation.py``.
    from phase5_common import (  # type: ignore
        EVIDENCE_ROOT,
        ROOT,
        proof,
        sha256_file,
        write_json,
    )


def run_and_record() -> dict[str, Any]:
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    combined = result.stdout + result.stderr
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    run_match = re.search(r"Ran (\d+) tests? in ([0-9.]+)s", combined)
    failure_match = re.search(r"failures=(\d+)", combined)
    error_match = re.search(r"errors=(\d+)", combined)
    skipped_match = re.search(r"skipped=(\d+)", combined)
    tests_run = int(run_match.group(1)) if run_match else 0
    failures = int(failure_match.group(1)) if failure_match else 0
    errors = int(error_match.group(1)) if error_match else 0
    skipped = int(skipped_match.group(1)) if skipped_match else 0
    success = result.returncode == 0 and run_match is not None
    test_path = EVIDENCE_ROOT / "test_results.json"
    test_results = {
        "command": "python -m unittest discover -s tests -v",
        "status": "PASS" if success else "FAIL",
        "tests_run": tests_run,
        "passed": max(0, tests_run - failures - errors - skipped),
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "exit_code": result.returncode,
        "stdout_summary": (
            "OK" if success and not skipped
            else "OK with skipped tests" if success
            else "See test command output for failure details"
        ),
    }
    write_json(test_path, test_results)

    manifest_path = EVIDENCE_ROOT / "run_manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["test_suite"] = {
            **test_results,
            "evidence": "reports/evidence/P5/test_results.json",
        }
        file_entry = {
            "path": "reports/evidence/P5/test_results.json",
            "sha256": sha256_file(test_path),
            "bytes": test_path.stat().st_size,
        }
        prior = [
            row for row in manifest.get("generated_files", [])
            if row.get("path") != file_entry["path"]
        ]
        prior.append(file_entry)
        prior.sort(key=lambda row: row["path"])
        manifest["generated_files"] = prior
        write_json(manifest_path, manifest)
    proof(
        "P5-FULL-TESTS",
        status=test_results["status"],
        tests_run=tests_run,
        passed=test_results["passed"],
        failures=failures,
        errors=errors,
        skipped=skipped,
        evidence="reports/evidence/P5/test_results.json",
    )
    if not success:
        raise SystemExit(result.returncode or 1)
    return test_results


if __name__ == "__main__":
    run_and_record()
