"""Real H-MEM reference storage/retrieval; deterministic mock embeddings, no LLM.

This is a local human review interface, not multi-user authentication. Only
trusted CLI/server code may choose the actor, scope and storage root.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


class MemoryError(ValueError):
    """Sanitized memory validation/worker error."""


def _dict(value):
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class HMemMemory:
    """Source-linked interpretation pointers. They never replace financial facts."""

    def __init__(self, root=None, *, scope_id="local-cli", actor="local-human", timeout=3):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", scope_id) or not re.fullmatch(r"[A-Za-z0-9_. -]{1,80}", actor):
            raise MemoryError("Invalid trusted local scope or actor")
        self.root = Path(root) if root else Path(__file__).resolve().parents[2] / ".local" / "hmem"
        self.scope_id, self.actor = scope_id, actor
        self.timeout = min(max(float(timeout), .01), 3)

    def _scope(self, request):
        r = _dict(request)
        company = _dict(r["company"])
        return {"scope_id": self.scope_id, "cik": str(company["cik"]).zfill(10),
                "fiscal_year": r["fiscal_year"], "period": r["period"], "accounting_basis": "GAAP"}

    def _sources(self, request, evidence):
        cutoff = date.fromisoformat(_dict(request)["as_of"])
        sources = []
        for item in evidence:
            e = _dict(item)
            url = e.get("url", "")
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.hostname not in {"sec.gov", "www.sec.gov", "data.sec.gov"} or parsed.username or parsed.password:
                raise MemoryError("Memory requires primary SEC source citations")
            publication = str(e["published_at"])
            source_cik = re.search(r"/Archives/edgar/data/(\d+)/", parsed.path)
            if not source_cik or source_cik[1].zfill(10) != self._scope(request)["cik"]:
                raise MemoryError("Memory source issuer does not match investigation scope")
            if not (date.fromisoformat(str(e["period_start"])) <= date.fromisoformat(str(e["period_end"])) <= date.fromisoformat(publication) <= cutoff) or not e.get("locator"):
                raise MemoryError("Memory source is ineligible for this as-of date")
            # Always bind the exact financial snapshot, even if the document hash
            # is unchanged. Null document hashes do not become invented hashes.
            stable = {k:e.get(k) for k in ("id", "url", "published_at", "period_start", "period_end", "unit", "value", "concept", "locator", "source_sha256")}
            if e.get('value_decimal') is not None:
                stable['value_decimal'] = e['value_decimal']
            sources.append({"id":e["id"], "url":url, "published_at":publication,
                            "fingerprint":_digest(stable), "fingerprint_kind":"evidence_snapshot_sha256"})
        if not sources:
            raise MemoryError("A correction requires freshly retrieved source evidence")
        if len(sources) > 25 or len({s["id"] for s in sources}) != len(sources):
            raise MemoryError("Invalid source evidence set")
        return sorted(sources, key=lambda s:s["id"])

    def propose(self, request, text, evidence, correction_id, supersedes=None):
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            raise MemoryError("Correction text must contain 1–4000 characters")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", correction_id):
            raise MemoryError("Invalid correction id")
        if supersedes is not None and not re.fullmatch(r"mem-[1-9][0-9]*", supersedes):
            raise MemoryError("Invalid superseded memory id")
        scope = self._scope(request)
        payload = {"version":1,"correction_id":correction_id,"text":text,"scope":scope,
                   "scope_key":_digest(scope),"sources":self._sources(request,evidence),
                   "as_of":_dict(request)["as_of"],"supersedes":supersedes,"reviewer":self.actor,
                   "proposed_at":datetime.now(timezone.utc).isoformat()}
        return {**payload,"digest":_digest(payload)}

    def _validate(self, proposal):
        p = dict(proposal)
        digest = p.pop("digest", None)
        if digest != _digest(p) or p.get("reviewer") != self.actor or p.get("scope",{}).get("scope_id") != self.scope_id or p.get("scope_key") != _digest(p["scope"]):
            raise MemoryError("Review must approve this exact local actor/scope payload")
        return proposal

    def review(self, proposal, *, approved_digest, approve):
        self._validate(proposal)
        if type(approve) is not bool or approved_digest != proposal["digest"]:
            raise MemoryError("Explicit review decision and exact proposal digest required")
        if not approve:
            return {"status":"rejected", "digest":proposal["digest"]}
        return self._worker("approve",proposal["scope_key"],proposal=proposal)

    def _worker(self, op, scope_key, **args):
        node = shutil.which("node")
        if not node:
            raise MemoryError("H-MEM requires the existing Node 24 runtime")
        worker = Path(__file__).with_name("memory_worker.mjs")
        message = {"op":op,"directory":str((self.root / scope_key).resolve()),"actor":self.actor,"scope_key":scope_key,**args}
        try:
            result = subprocess.run([node,"--disable-warning=ExperimentalWarning","--experimental-transform-types",str(worker)],
                                    input=json.dumps(message),text=True,capture_output=True,timeout=self.timeout,check=False)
            if len(result.stdout) > 2_000_000:
                raise MemoryError("H-MEM response limit exceeded")
            envelope = json.loads(result.stdout)
            if result.returncode or not envelope.get("ok"):
                raise MemoryError("H-MEM operation failed; inspect local state before retrying")
            return envelope["result"]
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            raise MemoryError("H-MEM worker unavailable or deadline exceeded") from exc

    def recall(self, request, evidence):
        scope = self._scope(request)
        sources = {s["id"]:s for s in self._sources(request,evidence)}
        result = self._worker("recall",_digest(scope),query="quarterly financial evidence interpretation correction")
        cutoff = _dict(request)["as_of"]
        approved = []
        for item in result["memories"]:
            p = item.get("proposal")
            if not p or p.get("scope") != scope or p.get("as_of", "9999") > cutoff:
                continue
            # Approval time and evidence publication are distinct. A correction
            # reviewed later can be reused only when its original as-of <= run.
            if all(s == sources.get(s["id"]) and s["published_at"] <= cutoff for s in p["sources"]):
                approved.append({"memory_id":item["memory_id"],"text":item["content"],
                                 "sources":p["sources"],"reviewer":p["reviewer"],"digest":p["digest"],
                                 "reviewed_at":item.get("reviewed_at"),
                                 "supersedes":item["supersedes"],"retrieval":"hmem_reference_deterministic_hash_embeddings",
                                 "role":"reviewed_context_only_not_financial_fact"})
        return approved

    def feedback(self, request, memory_id, kind):
        if kind not in {"helpful", "not_helpful", "wrong"}:
            raise MemoryError("Unknown H-MEM feedback kind")
        return self._worker("feedback",_digest(self._scope(request)),memory_id=memory_id,kind=kind)
