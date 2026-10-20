#!/usr/bin/env python3
"""MIT. Validate the pilot-coding data under data/ against data/schema/fields.json.

Checks field IDs and types, legal values, conditional fields (report §5.5), how status and
evidence fit together (§4.2, §8.1), evidence kinds, private-bench references, and that
rounds, configs, codings and adapters refer to each other. Prints errors only; exit 1 on any.

  python3 studies/harness-quantification/validate_data.py              real data + templates
  python3 studies/harness-quantification/validate_data.py --fixtures   also the synthetic fixtures
  python3 studies/harness-quantification/validate_data.py --write-templates
"""
import argparse
import copy
import datetime as dt
import json
import re
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent
REPO = STUDY.parent.parent
DATA = STUDY / "data"
SCHEMA_PATH = DATA / "schema/fields.json"
FIXTURES = DATA / "fixtures/synthetic"
BENCH_DIR = REPO / "research/private-bench"
CATALOG_PATH = REPO / "research/catalog.json"

CONFIG_SCHEMA, CODING_SCHEMA, ADAPTER_SCHEMA = "config-0.1", "coding-0.1", "adapter-0.1"
ROLES = {
    "core": "第一轮核心样本",
    "control_same_origin_pair": "同源一对（Pi 与 Step Code）",
    "control_editor_host": "编辑器宿主对照",
    "control_resident_gateway": "常驻网关对照",
}
# Words that would point at single private-bench tasks; never allowed near a bench reference.
BENCH_FORBIDDEN = ("题目", "题号", "单题", "题面", "评分细则", "task_id", "bench_task", "task id", "rubric")
ABS_PATH = re.compile(r"(^|[\s\"'(=])(/Users/|/home/|/private/|[A-Za-z]:\\)")
SHA40 = re.compile(r"/[0-9a-f]{40}(/|$)")
LINES = re.compile(r"^L\d+(-L\d+)?$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})?)?$")
CODER_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CONFIG_ID = re.compile(r"^[A-Z]\d{2}__[a-z0-9-]+__[a-z0-9-]+$")
ADAPTER_ID = re.compile(r"^[A-Z]\d{2}__[a-z0-9-]+__[a-z0-9-]+__[a-z0-9.-]+__[a-z0-9-]+$")
BENCH_REF = re.compile(r"^([a-z0-9][a-z0-9-]*)\.([a-z-]+)$")

CARD_KEYS = {"evidence_kind", "source_url", "locator", "lines", "retrieved_at", "content_sha256", "version",
             "configuration_scope", "environment", "run_id", "bench_ref", "bench_config", "note"}
CODER_KEYS = {"id", "model", "prompt_version", "coded_at"}
CONFIG_KEYS = {"schema_version", "synthetic", "config_id", "round", "tool_id", "product", "view", "version_or_commit",
               "mode", "representative_rationale", "entrypoint", "install_method", "permission_mode",
               "subagents_enabled", "enabled_extensions", "operating_system", "model_policy", "evidence_cutoff",
               "evidence", "note"}
CODING_KEYS = {"schema_version", "codebook_version", "synthetic", "round", "config_id", "coder", "independent",
               "evidence_cutoff", "fields"}
ENTRY_KEYS = {"status", "value", "unknown_reason", "value_note", "evidence", "confidence", "coder_note",
              "review_status", "vocabulary_proposals"}
ADAPTER_KEYS = {"schema_version", "synthetic", "adapter_id", "round", "config_id", "coder", "model_endpoint",
                "access_path", "access_path_evidence", "adapter_configuration", "capability_checks",
                "private_bench_refs", "evidence_cutoff", "note"}
ENDPOINT_KEYS = {"model_id", "provider", "channel", "endpoint_version", "parameters"}
CHECK_KEYS = {"state", "failure_reason", "evidence", "note"}
ROUND_KEYS = {"round", "synthetic", "codebook_version", "coders", "independence", "tools", "note"}
ROUND_CODER_KEYS = {"id", "model_family", "dispatch"}
ROUND_TOOL_KEYS = {"tool_id", "product", "role", "config_id", "evidence_entry"}

DOC_STATES = {"doc_declared"}
RUN_STATES = {"minimal_request_verified", "multistep_verified", "target_task_verified"}
FAIL_STATES = {"incompatible", "partially_degraded", "environment_limited"}


class Context:
    def __init__(self, schema=None, synthetic=False, bench_dir=BENCH_DIR, catalog_path=CATALOG_PATH, repo=REPO):
        self.schema = schema or json.loads(SCHEMA_PATH.read_text())
        self.fields = {f["id"]: f for f in self.schema["fields"]}
        self.enums = self.schema["enums"]
        self.synthetic = synthetic
        self.bench_dir = bench_dir
        self.repo = repo
        self.catalog = {t["id"]: t["name"] for t in json.loads(catalog_path.read_text())}
        configs = bench_dir / "configs.json"
        self.bench_configs = json.loads(configs.read_text())["configs"] if configs.exists() else {}


def _is_str(x, allow_empty=False):
    return isinstance(x, str) and (allow_empty or x.strip() != "")


def _date(x):
    if not isinstance(x, str) or not DATE.match(x):
        return None
    try:
        return dt.date.fromisoformat(x[:10])
    except ValueError:
        return None


def _keys(obj, allowed, required, where, errors):
    if not isinstance(obj, dict):
        errors.append(f"{where}: expected an object")
        return False
    extra, missing = set(obj) - allowed, set(required) - set(obj)
    if extra:
        errors.append(f"{where}: unexpected keys {sorted(extra)}")
    if missing:
        errors.append(f"{where}: missing keys {sorted(missing)}")
    return not missing


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def check_no_local_paths(obj, where, errors):
    for s in _strings(obj):
        if ABS_PATH.search(s):
            errors.append(f"{where}: contains a machine-specific absolute path: {s[:60]!r}")
            return


def check_synthetic_flag(rec, where, ctx, errors):
    flag = rec.get("synthetic")
    if not isinstance(flag, bool):
        errors.append(f"{where}: 'synthetic' must be true or false")
    elif ctx.synthetic and not flag:
        errors.append(f"{where}: fixture records must be marked synthetic: true")
    elif not ctx.synthetic and flag:
        errors.append(f"{where}: synthetic data is not allowed in the real data directories")


def check_tool(tool_id, product, where, ctx, errors):
    if ctx.synthetic:
        if not (isinstance(tool_id, str) and re.fullmatch(r"Z\d{2}", tool_id)):
            errors.append(f"{where}: synthetic tool_id must be Z00–Z99 (reserved range)")
        if not (isinstance(product, str) and "合成" in product):
            errors.append(f"{where}: synthetic product name must contain 合成")
        return
    if tool_id not in ctx.catalog:
        errors.append(f"{where}: tool_id {tool_id!r} is not in research/catalog.json")
    elif product != ctx.catalog[tool_id]:
        errors.append(f"{where}: product {product!r} differs from catalog name {ctx.catalog[tool_id]!r}")


def check_coder(coder, where, errors):
    if not _keys(coder, CODER_KEYS, CODER_KEYS, f"{where}.coder", errors):
        return
    if not (isinstance(coder["id"], str) and CODER_ID.match(coder["id"])):
        errors.append(f"{where}.coder.id: use lowercase letters, digits and hyphens")
    for k in ("model", "prompt_version"):
        if not _is_str(coder[k]):
            errors.append(f"{where}.coder.{k}: required (report §14.1 keeps model and prompt versions)")
    if not _date(coder["coded_at"]):
        errors.append(f"{where}.coder.coded_at: ISO date required")


def check_bench_ref(card, where, ctx, errors, tool_id=None):
    ref = card.get("bench_ref")
    m = BENCH_REF.match(ref) if isinstance(ref, str) else None
    if not m:
        errors.append(f"{where}: bench_ref must be '<campaign>.<table>'")
        return
    campaign, table = m.groups()
    if table not in ctx.enums["private_bench_tables"]:
        errors.append(f"{where}: unknown private-bench table {table!r}")
    path = ctx.bench_dir / f"{campaign}.json"
    if campaign == "configs" or not path.exists():
        errors.append(f"{where}: research/private-bench/{campaign}.json does not exist")
        return
    data = json.loads(path.read_text())
    if data.get("synthetic") and not ctx.synthetic:
        errors.append(f"{where}: {campaign} is a synthetic campaign; real records cannot cite it")
    bench_config = card.get("bench_config")
    if bench_config is not None:
        if bench_config not in ctx.bench_configs:
            errors.append(f"{where}: bench_config {bench_config!r} is not in research/private-bench/configs.json")
        elif bench_config not in [c.get("id") for c in data.get("configs", [])]:
            errors.append(f"{where}: campaign {campaign} has no configuration {bench_config!r}")
        elif tool_id and not ctx.synthetic and ctx.bench_configs[bench_config].get("tool") != tool_id:
            errors.append(f"{where}: bench_config {bench_config!r} belongs to another tool")


def check_bench_wording(obj, where, errors):
    for s in _strings(obj):
        low = s.lower()
        hit = next((w for w in BENCH_FORBIDDEN if w in low), None)
        if hit:
            errors.append(f"{where}: private-bench material must not mention single tasks ({hit!r})")
            return


def check_evidence(card, where, ctx, errors, cutoff=None, allowed=None, tool_id=None):
    if not _keys(card, CARD_KEYS, {"evidence_kind", "retrieved_at"}, where, errors):
        return None
    kind = card["evidence_kind"]
    if kind not in ctx.enums["evidence_kind"]:
        errors.append(f"{where}: unknown evidence_kind {kind!r}")
        return None
    if allowed is not None and kind not in allowed:
        errors.append(f"{where}: evidence_kind {kind!r} is not allowed here")
    when = _date(card["retrieved_at"])
    if not when:
        errors.append(f"{where}: retrieved_at must be an ISO date or datetime")
    elif cutoff and when > cutoff:
        errors.append(f"{where}: retrieved_at is after the record's evidence_cutoff")
    if "content_sha256" in card and not re.fullmatch(r"[0-9a-f]{64}", str(card["content_sha256"])):
        errors.append(f"{where}: content_sha256 must be 64 lowercase hex characters")
    url = card.get("source_url")
    if kind != "private_bench_aggregate" and url is not None and not str(url).startswith("https://"):
        errors.append(f"{where}: source_url must be an https URL")
    need = {
        "source_path": ("source_url", "locator", "lines"),
        "official_doc": ("source_url", "locator"),
        "default_release": ("source_url", "version"),
        "account_check": ("locator", "environment"),
        "observed_run": ("run_id", "environment"),
        "private_bench_aggregate": ("bench_ref",),
    }[kind]
    for k in need:
        if not _is_str(card.get(k)):
            errors.append(f"{where}: {kind} needs {k}")
    if kind == "source_path":
        if _is_str(url) and not SHA40.search(url):
            errors.append(f"{where}: source_path URL must pin a full 40-character commit SHA")
        if _is_str(card.get("lines")) and not LINES.match(card["lines"]):
            errors.append(f"{where}: lines must look like L12 or L12-L40")
    if kind == "private_bench_aggregate":
        for k in ("source_url", "locator", "lines", "run_id"):
            if k in card:
                errors.append(f"{where}: private_bench_aggregate cites only bench_ref (and bench_config), not {k}")
        check_bench_ref(card, where, ctx, errors, tool_id)
        check_bench_wording(card, where, errors)
    elif "bench_ref" in card or "bench_config" in card:
        errors.append(f"{where}: bench_ref/bench_config belong only to private_bench_aggregate")
    return kind


def check_value(field, value, where, errors):
    vocab = {v["id"] for v in field.get("vocabulary", [])}
    t = field["type"]
    if t in ("nominal", "ordinal"):
        allowed = vocab if t == "nominal" else set(field.get("levels", []))
        if not isinstance(value, str) or value not in allowed:
            errors.append(f"{where}: value {value!r} is not in the {t} vocabulary")
    elif t in ("set", "conditional_set"):
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            errors.append(f"{where}: {t} value must be a list of vocabulary ids")
            return
        if len(set(value)) != len(value):
            errors.append(f"{where}: duplicate values in set")
        bad = [v for v in value if v not in vocab]
        if bad:
            errors.append(f"{where}: values {bad} are not in the vocabulary (propose them in vocabulary_proposals)")
    elif t == "numeric":
        lo, hi = field["range"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not lo <= value <= hi:
            errors.append(f"{where}: numeric value must lie in {field['range']}")
    else:
        errors.append(f"{where}: schema type {t!r} is not supported")


def _same(field, a, b):
    if field["type"] in ("set", "conditional_set") and isinstance(a, list) and isinstance(b, list):
        return set(a) == set(b)
    return a == b


def check_entry(field, entry, where, ctx, errors, cutoff):
    if not _keys(entry, ENTRY_KEYS, {"status", "value", "evidence"}, where, errors):
        return
    status, value, evidence = entry["status"], entry["value"], entry["evidence"]
    if status not in ctx.enums["status"]:
        errors.append(f"{where}: status {status!r} is not one of {sorted(ctx.enums['status'])}")
        return
    if not isinstance(evidence, list):
        errors.append(f"{where}: evidence must be a list")
        evidence = []
    allowed = set(ctx.enums["evidence_kind"]) - {"private_bench_aggregate"}
    kinds = []
    for i, card in enumerate(evidence):
        kind = check_evidence(card, f"{where}.evidence[{i}]", ctx, errors, cutoff)
        if kind == "private_bench_aggregate":
            errors.append(f"{where}.evidence[{i}]: private-bench aggregates are not mechanism evidence (report §4.2)")
        elif kind in allowed:
            kinds.append(kind)
    reason = entry.get("unknown_reason")
    if status != "unknown" and reason is not None:
        errors.append(f"{where}: unknown_reason is only for status unknown")
    if status in ("known", "known_absent"):
        if not kinds:
            errors.append(f"{where}: {status} needs at least one evidence card")
        if entry.get("confidence") not in ctx.enums["confidence"]:
            errors.append(f"{where}: {status} needs confidence {sorted(ctx.enums['confidence'])}")
        if value is None:
            errors.append(f"{where}: {status} needs a value")
            return
        check_value(field, value, where, errors)
        has_absent = "absent_value" in field
        is_absent = has_absent and _same(field, value, field["absent_value"])
        if status == "known" and is_absent:
            errors.append(f"{where}: value means the mechanism is absent; use status known_absent")
        if status == "known_absent" and not has_absent:
            errors.append(f"{where}: {field['id']} has no absent value; record the category with status known")
        elif status == "known_absent" and not is_absent:
            errors.append(f"{where}: known_absent value must be {field['absent_value']!r}")
    elif status == "unknown":
        if value is not None:
            errors.append(f"{where}: unknown must not carry a value")
        if reason not in ctx.enums["unknown_reason"]:
            errors.append(f"{where}: unknown needs unknown_reason {sorted(ctx.enums['unknown_reason'])}")
        if reason == "conflicting_sources" and len(kinds) < 2:
            errors.append(f"{where}: conflicting_sources needs the conflicting evidence cards (at least two)")
    elif status == "not_applicable":
        if value is not None:
            errors.append(f"{where}: not_applicable must not carry a value")
        if "condition" not in field:
            errors.append(f"{where}: {field['id']} has no precondition, so it cannot be not_applicable")
    if "confidence" in entry and entry["confidence"] is not None and entry["confidence"] not in ctx.enums["confidence"]:
        errors.append(f"{where}: confidence must be one of {sorted(ctx.enums['confidence'])}")
    if "review_status" in entry and entry["review_status"] not in ctx.enums["review_status"]:
        errors.append(f"{where}: review_status must be one of {sorted(ctx.enums['review_status'])}")
    for k in ("value_note", "coder_note"):
        if k in entry and entry[k] is not None and not isinstance(entry[k], str):
            errors.append(f"{where}: {k} must be text")
    proposals = entry.get("vocabulary_proposals", [])
    if not isinstance(proposals, list) or not all(
            isinstance(p, dict) and set(p) == {"value", "definition"} and _is_str(p["value"]) and _is_str(p["definition"])
            for p in proposals):
        errors.append(f"{where}: vocabulary_proposals must be a list of {{value, definition}}")


def check_conditions(fields_rec, where, ctx, errors):
    for fid, field in ctx.fields.items():
        cond = field.get("condition")
        if not cond or fid not in fields_rec or cond["field"] not in fields_rec:
            continue
        gate, dep = fields_rec[cond["field"]], fields_rec[fid]
        if not isinstance(gate, dict) or not isinstance(dep, dict):
            continue
        g_status, d_status = gate.get("status"), dep.get("status")
        if g_status in ("known", "known_absent"):
            holds = gate.get("value") == cond["equals"]
            if holds and d_status == "not_applicable":
                errors.append(f"{where}.{fid}: {cond['field']}={cond['equals']}, so {fid} must be coded, not not_applicable")
            if not holds and d_status != "not_applicable":
                errors.append(f"{where}.{fid}: {cond['field']} is not {cond['equals']!r}, so {fid} must be not_applicable")
        elif g_status == "unknown" and d_status != "unknown":
            errors.append(f"{where}.{fid}: {cond['field']} is unknown, so {fid} must also be unknown")


def validate_config(rec, where, ctx):
    errors = []
    if not _keys(rec, CONFIG_KEYS, CONFIG_KEYS - {"note"}, where, errors):
        return errors
    check_synthetic_flag(rec, where, ctx, errors)
    if rec["schema_version"] != CONFIG_SCHEMA:
        errors.append(f"{where}: schema_version must be {CONFIG_SCHEMA}")
    if not (isinstance(rec["config_id"], str) and CONFIG_ID.match(rec["config_id"])):
        errors.append(f"{where}: config_id must look like A01__product-slug__variant")
    elif not rec["config_id"].startswith(f"{rec['tool_id']}__"):
        errors.append(f"{where}: config_id must start with the tool_id")
    check_tool(rec["tool_id"], rec["product"], where, ctx, errors)
    if rec["view"] not in ctx.enums["config_view"]:
        errors.append(f"{where}: view must be one of {sorted(ctx.enums['config_view'])}")
    if rec["mode"] != "local":
        errors.append(f"{where}: the pilot only codes local configurations (mode: local)")
    for k in ("round", "version_or_commit", "representative_rationale", "entrypoint", "install_method",
              "permission_mode", "operating_system", "model_policy"):
        if not _is_str(rec[k]):
            errors.append(f"{where}: {k} is required")
    if rec["subagents_enabled"] not in (True, False, None):
        errors.append(f"{where}: subagents_enabled must be true, false or null (unknown)")
    if not isinstance(rec["enabled_extensions"], list) or not all(_is_str(x) for x in rec["enabled_extensions"]):
        errors.append(f"{where}: enabled_extensions must be a list of names ([] when none)")
    cutoff = _date(rec["evidence_cutoff"])
    if not cutoff:
        errors.append(f"{where}: evidence_cutoff must be an ISO date")
    evidence = rec["evidence"] if isinstance(rec["evidence"], list) else []
    if not evidence:
        errors.append(f"{where}: evidence must list the cards behind version, entrypoint and install method")
    allowed = set(ctx.enums["evidence_kind"]) - {"private_bench_aggregate"}
    for i, card in enumerate(evidence):
        check_evidence(card, f"{where}.evidence[{i}]", ctx, errors, cutoff, allowed)
    check_no_local_paths(rec, where, errors)
    return errors


def validate_coding(rec, where, ctx):
    errors = []
    if not _keys(rec, CODING_KEYS, CODING_KEYS, where, errors):
        return errors
    check_synthetic_flag(rec, where, ctx, errors)
    if rec["schema_version"] != CODING_SCHEMA:
        errors.append(f"{where}: schema_version must be {CODING_SCHEMA}")
    if rec["codebook_version"] != ctx.schema["schema_version"]:
        errors.append(f"{where}: codebook_version must be {ctx.schema['schema_version']}")
    if rec["independent"] is not True:
        errors.append(f"{where}: pilot codings must be independent (independent: true)")
    check_coder(rec["coder"], where, errors)
    cutoff = _date(rec["evidence_cutoff"])
    if not cutoff:
        errors.append(f"{where}: evidence_cutoff must be an ISO date")
    fields_rec = rec["fields"]
    if not isinstance(fields_rec, dict):
        errors.append(f"{where}: fields must be an object keyed by field id")
        return errors
    unknown_ids = sorted(set(fields_rec) - set(ctx.fields))
    missing = sorted(set(ctx.fields) - set(fields_rec))
    if unknown_ids:
        errors.append(f"{where}: unknown field ids {unknown_ids}")
    if missing:
        errors.append(f"{where}: missing field ids {missing}")
    for fid in sorted(set(fields_rec) & set(ctx.fields)):
        check_entry(ctx.fields[fid], fields_rec[fid], f"{where}.{fid}", ctx, errors, cutoff)
    check_conditions(fields_rec, where, ctx, errors)
    check_no_local_paths(rec, where, errors)
    return errors


def validate_adapter(rec, where, ctx, tool_id=None):
    errors = []
    if not _keys(rec, ADAPTER_KEYS, ADAPTER_KEYS - {"note"}, where, errors):
        return errors
    check_synthetic_flag(rec, where, ctx, errors)
    if rec["schema_version"] != ADAPTER_SCHEMA:
        errors.append(f"{where}: schema_version must be {ADAPTER_SCHEMA}")
    if not (isinstance(rec["adapter_id"], str) and ADAPTER_ID.match(rec["adapter_id"])):
        errors.append(f"{where}: adapter_id must look like <config_id>__<model-slug>__<access-path>")
    elif isinstance(rec["config_id"], str) and not rec["adapter_id"].startswith(rec["config_id"] + "__"):
        errors.append(f"{where}: adapter_id must start with its config_id")
    check_coder(rec["coder"], where, errors)
    cutoff = _date(rec["evidence_cutoff"])
    if not cutoff:
        errors.append(f"{where}: evidence_cutoff must be an ISO date")
    ep = rec["model_endpoint"]
    if _keys(ep, ENDPOINT_KEYS, ENDPOINT_KEYS, f"{where}.model_endpoint", errors):
        for k in ("model_id", "provider", "channel"):
            if not _is_str(ep[k]):
                errors.append(f"{where}.model_endpoint.{k}: required (exact model id, provider, channel)")
        if not isinstance(ep["endpoint_version"], str):
            errors.append(f"{where}.model_endpoint.endpoint_version: text ('' when the channel has none)")
        if not isinstance(ep["parameters"], dict):
            errors.append(f"{where}.model_endpoint.parameters: object")
    mechanism = set(ctx.enums["evidence_kind"]) - {"private_bench_aggregate"}
    if rec["access_path"] not in ctx.enums["access_path"]:
        errors.append(f"{where}: access_path must be one of {sorted(ctx.enums['access_path'])}")
    path_cards = rec["access_path_evidence"] if isinstance(rec["access_path_evidence"], list) else []
    for i, card in enumerate(path_cards):
        check_evidence(card, f"{where}.access_path_evidence[{i}]", ctx, errors, cutoff, mechanism - {"observed_run"})
    if rec["access_path"] in ("native", "official_compatible") and not path_cards:
        errors.append(f"{where}: {rec['access_path']} needs official evidence in access_path_evidence")
    if rec["access_path"] == "author_suggested_trial" and not _is_str(rec.get("note")):
        errors.append(f"{where}: author_suggested_trial needs a note saying who suggested it and why")
    checks = rec["capability_checks"]
    if not isinstance(checks, dict):
        errors.append(f"{where}: capability_checks must be an object keyed by check id")
        checks = {}
    expected = set(ctx.enums["capability_check"])
    if set(checks) != expected:
        errors.append(f"{where}: capability_checks must list exactly {sorted(expected)}")
    for cid in sorted(set(checks) & expected):
        c, w = checks[cid], f"{where}.capability_checks.{cid}"
        if not _keys(c, CHECK_KEYS, CHECK_KEYS - {"note"}, w, errors):
            continue
        state = c["state"]
        if state not in ctx.enums["check_state"]:
            errors.append(f"{w}: state must be one of {sorted(ctx.enums['check_state'])}")
            continue
        cards = c["evidence"] if isinstance(c["evidence"], list) else []
        kinds = [check_evidence(card, f"{w}.evidence[{i}]", ctx, errors, cutoff, mechanism)
                 for i, card in enumerate(cards)]
        if state in DOC_STATES and not any(k in ("official_doc", "source_path", "default_release") for k in kinds):
            errors.append(f"{w}: doc_declared needs official_doc, source_path or default_release evidence")
        if state in RUN_STATES and "observed_run" not in kinds:
            errors.append(f"{w}: {state} needs observed_run evidence; this round runs nothing")
        if state in FAIL_STATES:
            if not _is_str(c["failure_reason"]):
                errors.append(f"{w}: {state} needs failure_reason")
            if not cards:
                errors.append(f"{w}: {state} needs evidence")
        elif c["failure_reason"] is not None:
            errors.append(f"{w}: failure_reason only for incompatible / partially_degraded / environment_limited")
        if state == "unverified" and cards:
            errors.append(f"{w}: unverified must not carry evidence; use doc_declared or a failure state")
    refs = rec["private_bench_refs"] if isinstance(rec["private_bench_refs"], list) else None
    if refs is None:
        errors.append(f"{where}: private_bench_refs must be a list ([] when none)")
    for i, card in enumerate(refs or []):
        check_evidence(card, f"{where}.private_bench_refs[{i}]", ctx, errors, cutoff,
                       {"private_bench_aggregate"}, tool_id)
    check_bench_wording(rec, where, errors)
    check_no_local_paths(rec, where, errors)
    return errors


def validate_round(rec, where, ctx):
    errors = []
    if not _keys(rec, ROUND_KEYS, ROUND_KEYS - {"note"}, where, errors):
        return errors
    check_synthetic_flag(rec, where, ctx, errors)
    if rec["codebook_version"] != ctx.schema["schema_version"]:
        errors.append(f"{where}: codebook_version must be {ctx.schema['schema_version']}")
    if not _is_str(rec["independence"]):
        errors.append(f"{where}: independence rule is required")
    coders = rec["coders"] if isinstance(rec["coders"], list) else []
    if len(coders) < 2:
        errors.append(f"{where}: the pilot needs at least two independent coders")
    for i, c in enumerate(coders):
        if _keys(c, ROUND_CODER_KEYS, ROUND_CODER_KEYS, f"{where}.coders[{i}]", errors) and not (
                isinstance(c["id"], str) and CODER_ID.match(c["id"])):
            errors.append(f"{where}.coders[{i}].id: lowercase letters, digits and hyphens")
    seen = set()
    for i, t in enumerate(rec["tools"] if isinstance(rec["tools"], list) else []):
        w = f"{where}.tools[{i}]"
        if not _keys(t, ROUND_TOOL_KEYS, ROUND_TOOL_KEYS, w, errors):
            continue
        if t["tool_id"] in seen:
            errors.append(f"{w}: duplicate tool {t['tool_id']}")
        seen.add(t["tool_id"])
        check_tool(t["tool_id"], t["product"], w, ctx, errors)
        if t["role"] not in ROLES:
            errors.append(f"{w}: role must be one of {sorted(ROLES)}")
        if t["config_id"] is not None and not (isinstance(t["config_id"], str) and CONFIG_ID.match(t["config_id"])):
            errors.append(f"{w}: config_id must be null (not chosen yet) or a config id")
        for entry in t["evidence_entry"] if isinstance(t["evidence_entry"], list) else []:
            path, _, key = str(entry).partition("#")
            target = ctx.repo / path
            if ctx.synthetic:
                continue
            if not target.exists():
                errors.append(f"{w}: evidence entry {entry} does not exist")
            elif key and target.suffix == ".json" and key not in json.loads(target.read_text()):
                errors.append(f"{w}: evidence entry {entry} has no key {key}")
    check_no_local_paths(rec, where, errors)
    return errors


def _load(path, errors):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name}: cannot read JSON ({exc})")
        return None


def validate_tree(root, ctx):
    """Validate rounds/, configs/, codings/<coder>/ and adapters/<coder>/ under root and their links."""
    errors, rel = [], (lambda p: str(p.relative_to(root)))
    rounds, configs = {}, {}
    for p in sorted((root / "rounds").glob("*.json")):
        rec = _load(p, errors)
        if rec is None:
            continue
        errors += validate_round(rec, rel(p), ctx)
        if rec.get("round") != p.stem:
            errors.append(f"{rel(p)}: file name must equal round")
        rounds[p.stem] = rec
    for p in sorted((root / "configs").glob("*.json")):
        rec = _load(p, errors)
        if rec is None:
            continue
        errors += validate_config(rec, rel(p), ctx)
        if rec.get("config_id") != p.stem:
            errors.append(f"{rel(p)}: file name must equal config_id")
        configs[p.stem] = rec
        rnd = rounds.get(rec.get("round"))
        if rnd is None:
            errors.append(f"{rel(p)}: round {rec.get('round')!r} has no rounds/<round>.json")
        else:
            tool = next((t for t in rnd.get("tools", []) if t.get("tool_id") == rec.get("tool_id")), None)
            if tool is None:
                errors.append(f"{rel(p)}: tool {rec.get('tool_id')} is not listed in round {rec.get('round')}")
            elif tool.get("config_id") not in (None, p.stem):
                errors.append(f"{rel(p)}: round {rec.get('round')} names {tool.get('config_id')} for this tool")
    for name, rnd in rounds.items():
        for t in rnd.get("tools", []):
            if isinstance(t, dict) and t.get("config_id") and t["config_id"] not in configs:
                errors.append(f"rounds/{name}.json: config {t['config_id']} has no configs/ record")

    def owner(p, rec, kind):
        coder = (rec.get("coder") or {}).get("id") if isinstance(rec.get("coder"), dict) else None
        if coder != p.parent.name:
            errors.append(f"{rel(p)}: {kind} sits under {p.parent.name}/ but coder.id is {coder!r}")
        cfg = configs.get(rec.get("config_id"))
        if cfg is None:
            errors.append(f"{rel(p)}: config {rec.get('config_id')!r} has no configs/ record")
            return None
        if rec.get("round") != cfg.get("round"):
            errors.append(f"{rel(p)}: round differs from its config's round")
        rnd = rounds.get(rec.get("round"), {})
        if coder not in [c.get("id") for c in rnd.get("coders", []) if isinstance(c, dict)]:
            errors.append(f"{rel(p)}: coder {coder!r} is not listed in round {rec.get('round')}")
        return cfg

    for p in sorted((root / "codings").glob("*/*.json")):
        rec = _load(p, errors)
        if rec is None:
            continue
        errors += validate_coding(rec, rel(p), ctx)
        if rec.get("config_id") != p.stem:
            errors.append(f"{rel(p)}: file name must equal config_id")
        cfg = owner(p, rec, "coding")
        f25 = (rec.get("fields") or {}).get("F25") if isinstance(rec.get("fields"), dict) else None
        if cfg and cfg.get("subagents_enabled") is False and isinstance(f25, dict) and f25.get("value") == "present":
            errors.append(f"{rel(p)}: F25=present, but the config disables subagents; code the configured view")
    for p in sorted((root / "adapters").glob("*/*.json")):
        rec = _load(p, errors)
        if rec is None:
            continue
        cfg = configs.get(rec.get("config_id")) or {}
        errors += validate_adapter(rec, rel(p), ctx, cfg.get("tool_id"))
        if rec.get("adapter_id") != p.stem:
            errors.append(f"{rel(p)}: file name must equal adapter_id")
        owner(p, rec, "adapter")
    for sub in ("configs", "rounds"):
        for p in (root / sub).glob("*/**/*.json") if (root / sub).exists() else []:
            errors.append(f"{rel(p)}: nested files are not read; keep {sub}/ flat")
    return errors


# ---------- templates ----------

def _blank_card():
    return {"evidence_kind": "", "source_url": "", "locator": "", "lines": "", "retrieved_at": "",
            "configuration_scope": "", "note": ""}


def make_templates(schema):
    blank_coder = {"id": "", "model": "", "prompt_version": "", "coded_at": ""}
    config = {k: "" for k in ("schema_version", "config_id", "round", "tool_id", "product", "view",
                              "version_or_commit", "mode", "representative_rationale", "entrypoint",
                              "install_method", "permission_mode", "operating_system", "model_policy",
                              "evidence_cutoff", "note")}
    config.update({"schema_version": CONFIG_SCHEMA, "synthetic": False, "view": "configured", "mode": "local",
                   "subagents_enabled": None, "enabled_extensions": [], "evidence": [_blank_card()]})
    entry = {"status": None, "value": None, "unknown_reason": None, "value_note": "", "evidence": [],
             "confidence": None, "coder_note": "", "review_status": "single_review", "vocabulary_proposals": []}
    coding = {"schema_version": CODING_SCHEMA, "codebook_version": schema["schema_version"], "synthetic": False,
              "round": "", "config_id": "", "coder": dict(blank_coder), "independent": True,
              "evidence_cutoff": "", "fields": {f["id"]: copy.deepcopy(entry) for f in schema["fields"]}}
    check = {"state": "unverified", "failure_reason": None, "evidence": [], "note": ""}
    adapter = {"schema_version": ADAPTER_SCHEMA, "synthetic": False, "adapter_id": "", "round": "", "config_id": "",
               "coder": dict(blank_coder),
               "model_endpoint": {"model_id": "", "provider": "", "channel": "", "endpoint_version": "",
                                  "parameters": {}},
               "access_path": "", "access_path_evidence": [_blank_card()], "adapter_configuration": "",
               "capability_checks": {c: dict(check) for c in schema["enums"]["capability_check"]},
               "private_bench_refs": [], "evidence_cutoff": "", "note": ""}
    return {"config.template.json": config, "coding.template.json": coding, "adapter.template.json": adapter}


def check_templates(schema, folder=DATA / "templates"):
    errors = []
    for name, expected in make_templates(schema).items():
        path = folder / name
        if not path.exists() or json.loads(path.read_text()) != expected:
            errors.append(f"templates/{name}: out of date; run validate_data.py --write-templates")
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixtures", action="store_true", help="also validate data/fixtures/synthetic")
    ap.add_argument("--write-templates", action="store_true", help="regenerate data/templates from the schema")
    args = ap.parse_args(argv)
    ctx = Context()
    if args.write_templates:
        (DATA / "templates").mkdir(exist_ok=True)
        for name, body in make_templates(ctx.schema).items():
            (DATA / "templates" / name).write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n")
    errors = check_templates(ctx.schema) + validate_tree(DATA, ctx)
    if args.fixtures:
        errors += [f"fixtures/synthetic/{e}" for e in validate_tree(FIXTURES, Context(ctx.schema, synthetic=True))]
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
