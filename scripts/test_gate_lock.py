from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ID = "gate_test_project"
ROOT = Path.cwd()
DOCS_DIR = ROOT / "docs"
PROJECT_STATE_DIR = ROOT / "project_state" / PROJECT_ID
CHANGE_REQUESTS_DIR = PROJECT_STATE_DIR / "change_requests"

GATE_STATE_FILE = PROJECT_STATE_DIR / "gate_state.json"
ARTIFACT_LOCKS_FILE = PROJECT_STATE_DIR / "artifact_locks.json"


@dataclass
class ArtifactLock:
    path: str
    gate: str
    state: str
    locked_at: str


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def reset_test_project() -> None:
    if PROJECT_STATE_DIR.exists():
        shutil.rmtree(PROJECT_STATE_DIR)

    test_docs = [
        DOCS_DIR / "brief.md",
        DOCS_DIR / "market_research.md",
        DOCS_DIR / "domain_research.md",
        DOCS_DIR / "prd.md",
        DOCS_DIR / "architecture.md",
    ]
    for p in test_docs:
        if p.exists():
            p.unlink()

    ensure_dir(DOCS_DIR)
    ensure_dir(PROJECT_STATE_DIR)
    ensure_dir(CHANGE_REQUESTS_DIR)

    write_json(GATE_STATE_FILE, {"project_id": PROJECT_ID, "gates": []})
    write_json(ARTIFACT_LOCKS_FILE, {"project_id": PROJECT_ID, "artifacts": []})


def seed_artifacts() -> None:
    artifacts: dict[Path, str] = {
        DOCS_DIR / "brief.md": "# Brief draft\n\nInitial brief content.\n",
        DOCS_DIR / "market_research.md": "# Market research\n\nInitial market research.\n",
        DOCS_DIR / "domain_research.md": "# Domain research\n\nInitial domain research.\n",
        DOCS_DIR / "prd.md": "# PRD\n\nInitial PRD draft.\n",
        DOCS_DIR / "architecture.md": "# Architecture\n\nInitial architecture draft.\n",
        PROJECT_STATE_DIR / "epic_context.json": json.dumps(
            {"epic_id": "TEST-EPIC-1", "stories": []}, indent=2
        ),
        PROJECT_STATE_DIR / "story_map.json": json.dumps(
            {"stories": []}, indent=2
        ),
        PROJECT_STATE_DIR / "acceptance_criteria.json": json.dumps(
            {"criteria": []}, indent=2
        ),
        PROJECT_STATE_DIR / "ownership_map.json": json.dumps(
            {
                "teams": {
                    "frontend": {"owned_paths": ["src/", "frontend/"]},
                    "backend": {"owned_paths": ["backend/", "api/", "db/"]},
                },
                "shared_paths": ["docs/", "shared/"],
            },
            indent=2,
        ),
        PROJECT_STATE_DIR / "work_breakdown.json": json.dumps(
            {"items": []}, indent=2
        ),
        PROJECT_STATE_DIR / "readiness_report.json": json.dumps(
            {"ready": True}, indent=2
        ),
    }

    for path, content in artifacts.items():
        ensure_dir(path.parent)
        path.write_text(content, encoding="utf-8")


def set_gate_status(gate_name: str, status: str) -> None:
    data = read_json(GATE_STATE_FILE)
    gates = data.get("gates", [])

    replaced = False
    for gate in gates:
        if gate.get("gate") == gate_name:
            gate["status"] = status
            gate["updated_at"] = now_iso()
            replaced = True
            break

    if not replaced:
        gates.append(
            {
                "gate": gate_name,
                "status": status,
                "updated_at": now_iso(),
            }
        )

    data["project_id"] = PROJECT_ID
    data["gates"] = gates
    write_json(GATE_STATE_FILE, data)


def lock_artifacts(gate_name: str, artifact_paths: list[Path]) -> None:
    data = read_json(ARTIFACT_LOCKS_FILE)
    artifacts = data.get("artifacts", [])
    existing_keys = {(a["path"], a["gate"]) for a in artifacts if "path" in a and "gate" in a}

    for path in artifact_paths:
        key = (str(path), gate_name)
        if key in existing_keys:
            continue

        lock = ArtifactLock(
            path=str(path),
            gate=gate_name,
            state="locked",
            locked_at=now_iso(),
        )
        artifacts.append(lock.__dict__)

    data["project_id"] = PROJECT_ID
    data["artifacts"] = artifacts
    write_json(ARTIFACT_LOCKS_FILE, data)


def is_locked(path: Path) -> bool:
    data = read_json(ARTIFACT_LOCKS_FILE)
    for artifact in data.get("artifacts", []):
        if artifact.get("path") == str(path) and artifact.get("state") == "locked":
            return True
    return False


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_not_locked(path: Path) -> None:
    assert_true(not is_locked(path), f"{path} should NOT be locked")


def assert_locked(path: Path) -> None:
    assert_true(is_locked(path), f"{path} should be locked")


def create_change_request(artifact_path: Path, reason: str, gate: str) -> Path:
    ensure_dir(CHANGE_REQUESTS_DIR)
    cr_path = CHANGE_REQUESTS_DIR / f"cr_{gate}_{artifact_path.name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    payload = {
        "project_id": PROJECT_ID,
        "target_artifact": str(artifact_path),
        "reason": reason,
        "gate": gate,
        "status": "open",
        "created_at": now_iso(),
    }
    write_json(cr_path, payload)
    return cr_path


def mutate_artifact(path: Path, new_content: str) -> tuple[bool, str]:
    if is_locked(path):
        locks = read_json(ARTIFACT_LOCKS_FILE).get("artifacts", [])
        matched_gate = "UNKNOWN_GATE"
        for item in locks:
            if item.get("path") == str(path) and item.get("state") == "locked":
                matched_gate = item.get("gate", "UNKNOWN_GATE")
                break

        cr_path = create_change_request(
            artifact_path=path,
            reason="Attempted mutation after artifact lock during test.",
            gate=matched_gate,
        )
        return False, f"Artifact locked. Change request created: {cr_path}"

    path.write_text(new_content, encoding="utf-8")
    return True, "Artifact updated"


def test_gate_1_research() -> None:
    print("\n[TEST] Gate 1 - Research lock")

    brief = DOCS_DIR / "brief.md"
    market = DOCS_DIR / "market_research.md"
    domain = DOCS_DIR / "domain_research.md"

    assert_not_locked(brief)
    assert_not_locked(market)
    assert_not_locked(domain)

    set_gate_status("GATE_1_RESEARCH", "passed")
    lock_artifacts("GATE_1_RESEARCH", [brief, market, domain])

    assert_locked(brief)
    assert_locked(market)
    assert_locked(domain)

    ok, msg = mutate_artifact(brief, "# Brief edited after lock\n")
    assert_true(not ok, "Mutation should be blocked for locked brief.md")
    assert_true("Change request created" in msg, "Expected change request creation for locked artifact")

    print("[PASS] Gate 1 lock behavior is correct")


def test_gate_2_specification() -> None:
    print("\n[TEST] Gate 2 - Specification lock")

    prd = DOCS_DIR / "prd.md"
    epic_context = PROJECT_STATE_DIR / "epic_context.json"
    story_map = PROJECT_STATE_DIR / "story_map.json"
    acceptance = PROJECT_STATE_DIR / "acceptance_criteria.json"

    assert_not_locked(prd)
    assert_not_locked(epic_context)
    assert_not_locked(story_map)
    assert_not_locked(acceptance)

    set_gate_status("GATE_2_SPECIFICATION", "passed")
    lock_artifacts("GATE_2_SPECIFICATION", [prd, epic_context, story_map, acceptance])

    assert_locked(prd)
    assert_locked(epic_context)
    assert_locked(story_map)
    assert_locked(acceptance)

    ok, msg = mutate_artifact(epic_context, json.dumps({"epic_id": "CHANGED"}, indent=2))
    assert_true(not ok, "Mutation should be blocked for locked epic_context.json")
    assert_true("Change request created" in msg, "Expected change request creation for locked spec artifact")

    print("[PASS] Gate 2 lock behavior is correct")


def test_gate_3_design() -> None:
    print("\n[TEST] Gate 3 - Design lock")

    architecture = DOCS_DIR / "architecture.md"
    ownership_map = PROJECT_STATE_DIR / "ownership_map.json"
    work_breakdown = PROJECT_STATE_DIR / "work_breakdown.json"
    readiness = PROJECT_STATE_DIR / "readiness_report.json"

    assert_not_locked(architecture)
    assert_not_locked(ownership_map)
    assert_not_locked(work_breakdown)
    assert_not_locked(readiness)

    set_gate_status("GATE_3_DESIGN", "passed")
    lock_artifacts(
        "GATE_3_DESIGN",
        [architecture, ownership_map, work_breakdown, readiness],
    )

    assert_locked(architecture)
    assert_locked(ownership_map)
    assert_locked(work_breakdown)
    assert_locked(readiness)

    ok, msg = mutate_artifact(ownership_map, json.dumps({"teams": {}}, indent=2))
    assert_true(not ok, "Mutation should be blocked for locked ownership_map.json")
    assert_true("Change request created" in msg, "Expected change request creation for locked design artifact")

    print("[PASS] Gate 3 lock behavior is correct")


def test_resume_locked_state() -> None:
    print("\n[TEST] Resume mode - locked state persists")

    expected_locked = [
        DOCS_DIR / "brief.md",
        DOCS_DIR / "market_research.md",
        DOCS_DIR / "domain_research.md",
        DOCS_DIR / "prd.md",
        DOCS_DIR / "architecture.md",
        PROJECT_STATE_DIR / "epic_context.json",
        PROJECT_STATE_DIR / "story_map.json",
        PROJECT_STATE_DIR / "acceptance_criteria.json",
        PROJECT_STATE_DIR / "ownership_map.json",
        PROJECT_STATE_DIR / "work_breakdown.json",
        PROJECT_STATE_DIR / "readiness_report.json",
    ]

    for path in expected_locked:
        assert_locked(path)

    before = len(list(CHANGE_REQUESTS_DIR.glob("*.json")))
    ok, msg = mutate_artifact(DOCS_DIR / "brief.md", "# resume edit attempt\n")
    after = len(list(CHANGE_REQUESTS_DIR.glob("*.json")))

    assert_true(not ok, "Resume mode mutation should still be blocked")
    assert_true("Change request created" in msg, "Expected change request creation in resume mode")
    assert_true(after == before + 1, "Resume mode should create exactly one additional CR")

    print("[PASS] Resume mode confirms persisted lock behavior")


def print_summary() -> None:
    print("\n========== SUMMARY ==========")
    print(f"Gate state file: {GATE_STATE_FILE}")
    print(f"Artifact locks file: {ARTIFACT_LOCKS_FILE}")
    print(f"Change requests dir: {CHANGE_REQUESTS_DIR}")

    print("\nGate state:")
    print(json.dumps(read_json(GATE_STATE_FILE), indent=2, ensure_ascii=False))

    print("\nArtifact locks:")
    print(json.dumps(read_json(ARTIFACT_LOCKS_FILE), indent=2, ensure_ascii=False))

    cr_files = sorted(CHANGE_REQUESTS_DIR.glob("*.json"))
    print(f"\nChange requests created: {len(cr_files)}")
    for f in cr_files:
        print(f"- {f}")


def run_fresh() -> None:
    reset_test_project()
    seed_artifacts()

    test_gate_1_research()
    test_gate_2_specification()
    test_gate_3_design()

    print_summary()
    print("\nFRESH TESTS PASSED")


def run_resume() -> None:
    assert_true(PROJECT_STATE_DIR.exists(), "Resume mode requires an existing test state")
    assert_true(GATE_STATE_FILE.exists(), "Resume mode requires gate_state.json")
    assert_true(ARTIFACT_LOCKS_FILE.exists(), "Resume mode requires artifact_locks.json")

    test_resume_locked_state()
    print_summary()
    print("\nRESUME TEST PASSED")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test gate lock workflow for the first 3 phases.")
    parser.add_argument(
        "--mode",
        choices=["fresh", "resume"],
        default="fresh",
        help="fresh = reset and run from scratch, resume = reuse existing locked state",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.mode == "fresh":
        run_fresh()
    else:
        run_resume()


if __name__ == "__main__":
    main()