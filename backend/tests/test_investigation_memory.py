"""Product memory tests invoke the actual vendored TS engine, never a mock."""
import json
import shutil
import subprocess

import pytest

from backend.investigation.memory import HMemMemory, MemoryError


def request():
    return {"company":{"name":"Example","ticker":"EX","cik":"1035267"},
            "fiscal_year":2026,"period":"Q2","as_of":"2026-10-23"}


def evidence():
    return [{"id":"eps","url":"https://www.sec.gov/Archives/edgar/data/1035267/000103526726000058/isrg-20260630.htm",
             "published_at":"2026-07-21","period_start":"2026-04-01","period_end":"2026-06-30",
             "unit":"USD/shares","value":2.29,"concept":"EarningsPerShareDiluted","locator":"eps table",
             "source_sha256":None}]


def proposal(memory, correction_id="first", supersedes=None):
    return memory.propose(request(),"Interpret diluted EPS as GAAP quarter, not six months.",evidence(),correction_id,supersedes)


def approve(memory,p):
    return memory.review(p,approved_digest=p["digest"],approve=True)


def test_real_hmem_reject_writes_nothing_then_approve_restart_recall_feedback(tmp_path):
    memory = HMemMemory(tmp_path)
    p = proposal(memory)
    assert memory.review(p,approved_digest=p["digest"],approve=False)["status"] == "rejected"
    assert list(tmp_path.iterdir()) == []
    receipt = approve(memory,p)
    recalled = HMemMemory(tmp_path).recall(request(),evidence())
    assert len(recalled) == 1
    assert recalled[0]["memory_id"] == receipt["memory_id"]
    assert recalled[0]["sources"][0]["fingerprint_kind"] == "evidence_snapshot_sha256"
    assert recalled[0]["reviewed_at"]
    memory.feedback(request(),receipt["memory_id"],"helpful")
    ledger = next(tmp_path.glob("*/ledger.jsonl")).read_text()
    actions = [json.loads(line)["action"] for line in ledger.splitlines()]
    assert {"create","read","feedback"} <= set(actions)
    state = json.loads(next(tmp_path.glob("*/state.json")).read_text())
    assert state["records"][0]["confidence"] == pytest.approx(.9)
    memory.feedback(request(),receipt["memory_id"],"wrong")
    assert memory.recall(request(),evidence()) == []


def test_exact_approval_and_actor_required(tmp_path):
    memory = HMemMemory(tmp_path)
    p = proposal(memory)
    altered = {**p,"text":"Replace financial fact with invented EPS"}
    with pytest.raises(MemoryError):
        memory.review(altered,approved_digest=p["digest"],approve=True)
    with pytest.raises(MemoryError):
        memory.review(p,approved_digest="wrong",approve=True)
    with pytest.raises(MemoryError):
        HMemMemory(tmp_path,actor="different").review(p,approved_digest=p["digest"],approve=True)
    assert list(tmp_path.iterdir()) == []


def test_idempotent_approval_and_conflicting_key(tmp_path):
    memory = HMemMemory(tmp_path)
    p = proposal(memory)
    assert approve(memory,p) == approve(memory,p)
    assert len(memory.recall(request(),evidence())) == 1
    changed = memory.propose(request(),"Different approved interpretation",evidence(),"first")
    with pytest.raises(MemoryError):
        approve(memory,changed)


def test_recall_revalidates_snapshot_cutoff_and_scope(tmp_path):
    memory = HMemMemory(tmp_path)
    approve(memory,proposal(memory))
    changed = evidence(); changed[0]["value"] = 9
    assert memory.recall(request(),changed) == []
    cutoff = {**request(),"as_of":"2026-07-20"}
    with pytest.raises(MemoryError):
        memory.recall(cutoff,evidence())
    other = request(); other["company"]["cik"] = "320193"
    other_evidence = evidence(); other_evidence[0]["url"] = other_evidence[0]["url"].replace("/1035267/", "/320193/")
    assert memory.recall(other,other_evidence) == []
    assert HMemMemory(tmp_path,scope_id="other-session").recall(request(),evidence()) == []
    other_period = {**request(),"period":"Q1"}
    assert memory.recall(other_period,evidence()) == []


def test_source_required_and_future_source_denied(tmp_path):
    memory = HMemMemory(tmp_path)
    with pytest.raises(MemoryError):
        memory.propose(request(),"correction",[],"empty")
    future = evidence(); future[0]["published_at"] = "2027-01-01"
    with pytest.raises(MemoryError):
        memory.propose(request(),"correction",future,"future")
    malicious = evidence(); malicious[0]["url"] = "https://evil.invalid/fake"
    with pytest.raises(MemoryError):
        memory.propose(request(),"correction",malicious,"fake")


def test_supersession_both_links_and_replay_recovery(tmp_path):
    memory = HMemMemory(tmp_path)
    old = approve(memory,proposal(memory))
    new_p = memory.propose(request(),"Correction: EPS is a quarterly GAAP per-share measure.",evidence(),"second",old["memory_id"])
    new = approve(memory,new_p)
    state_path = next(tmp_path.glob("*/state.json"))
    state = json.loads(state_path.read_text())
    by_id = {r["id"]:r for r in state["records"]}
    assert by_id[old["memory_id"]]["supersededBy"] == new["memory_id"]
    assert by_id[new["memory_id"]]["supersedes"] == old["memory_id"]
    # Reproduce the durable state of a crash after add and before the backlink.
    by_id[old["memory_id"]].pop("supersededBy")
    state_path.write_text(json.dumps(state))
    journal_path = next(tmp_path.glob("*/operations.json"))
    journal = json.loads(journal_path.read_text()); journal["second"]["done"] = False
    journal_path.write_text(json.dumps(journal))
    recalled = HMemMemory(tmp_path).recall(request(),evidence())
    assert [r["memory_id"] for r in recalled] == [new["memory_id"]]
    recovered = json.loads(state_path.read_text())
    assert len(recovered["records"]) == 2
    assert next(r for r in recovered["records"] if r["id"] == old["memory_id"])["supersededBy"] == new["memory_id"]


def test_reference_auto_supersession_does_not_bypass_review(tmp_path):
    memory = HMemMemory(tmp_path)
    first = memory.propose(request(),"Correction quarterly GAAP EPS interpretation.",evidence(),"one")
    second = memory.propose(request(),"Correction quarterly GAAP EPS interpretation.",evidence(),"two")
    approve(memory,first); approve(memory,second)
    # Both independently approved pointers remain active unless supersedes was
    # explicitly part of a reviewed payload; engine similarity cannot choose.
    recalled = memory.recall(request(),evidence())
    assert len(recalled) == 2
    assert all(r["supersedes"] is None for r in recalled)


def test_worker_active_lock_is_not_removed_and_dead_owner_is_recovered(tmp_path):
    memory = HMemMemory(tmp_path)
    p = proposal(memory); approve(memory,p)
    directory = next(tmp_path.iterdir())
    lock = directory / ".worker-lock"; lock.mkdir()
    owner = subprocess.Popen([shutil.which("node"),"-e","setInterval(()=>{},1000)"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        (lock / "pid").write_text(str(owner.pid))
        with pytest.raises(MemoryError):
            memory.recall(request(),evidence())
        assert lock.exists() and (lock / "pid").read_text() == str(owner.pid)
    finally:
        owner.kill(); owner.wait(timeout=3)
    # Real terminated owner process, not a mocked liveness check.
    assert len(memory.recall(request(),evidence())) == 1
    assert not lock.exists()
