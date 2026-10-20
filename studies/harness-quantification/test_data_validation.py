"""MIT. Contracts for the pilot-coding data format, validator and comparison script.

Positive and negative cases use the synthetic fixtures in data/fixtures/synthetic only.
"""
import copy
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import compare_codings
import validate_data as vd

STUDY = Path(__file__).resolve().parent
FIX = vd.FIXTURES
CFG_A = "Z90__synthetic-a__local-default"
CFG_B = "Z91__synthetic-b__local-default"
ADAPTER = "Z90__synthetic-a__local-default__synthetic-model-1__official-compatible"


def load(rel):
    return json.loads((FIX / rel).read_text())


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real = vd.Context()
        cls.syn = vd.Context(cls.real.schema, synthetic=True)

    def coding(self, coder="coder-a", cfg=CFG_A):
        return load(f"codings/{coder}/{cfg}.json")

    def assertError(self, errors, pattern):
        self.assertTrue(any(re.search(pattern, e) for e in errors), f"no error matching {pattern!r} in {errors}")


class SchemaMatchesReport(Base):
    def test_fields_copy_report_tables_verbatim(self):
        body = (STUDY / "report.md").read_text().split("<!-- REFERENCES:GENERATED -->")[0]
        rows = re.findall(r"^\| (F\d{2}) \| (.+?) \| (.+?) \| (.+?) \|$", body, re.M)
        self.assertEqual([r[0] for r in rows], [f"F{i:02}" for i in range(1, 37)])
        for (fid, q, t, hint), f in zip(rows, self.real.schema["fields"]):
            self.assertEqual((fid, q, t, hint), (f["id"], f["question"], f["answer_type_label"], f["coding_hint"]))

    def test_types_vocab_and_conditions(self):
        types = {"类别（无顺序）": "nominal", "集合（可多选）": "set", "条件集合": "conditional_set"}
        groups = {g["id"]: g["fields"] for g in self.real.schema["groups"]}
        self.assertEqual(sorted(groups), list("ABCDEFGHI"))
        for f in self.real.schema["fields"]:
            self.assertEqual(f["type"], types[f["answer_type_label"]])
            self.assertIn(f["id"], groups[f["group"]])
            ids = [v["id"] for v in f["vocabulary"]]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual("condition" in f, f["type"] == "conditional_set")
            if "absent_value" in f and f["type"] == "nominal":
                self.assertIn(f["absent_value"], ids)
            if f.get("needs_definition"):
                self.assertTrue(f.get("definition_gap"))
        self.assertEqual([f["id"] for f in self.real.schema["fields"] if "condition" in f], ["F26", "F27", "F28"])

    def test_private_bench_tables_match_renderer(self):
        source = (vd.REPO / "research/private_bench.py").read_text()
        rendered = set(re.findall(r"if table == '([a-z-]+)'", source))
        self.assertEqual(set(self.real.enums["private_bench_tables"]), rendered)

    def test_evidence_kinds_cover_card(self):
        self.assertTrue({"source_path", "official_doc", "default_release", "account_check", "observed_run",
                         "private_bench_aggregate"} <= set(self.real.enums["evidence_kind"]))


DRAFT_FIELDS = ["F01", "F12", "F21", "F22", "F23"]


class DraftDefinitions(Base):
    """Draft definitions are read and shape-checked, never applied to codings."""

    def schema_with(self, mutate):
        schema = copy.deepcopy(self.real.schema)
        mutate({f["id"]: f for f in schema["fields"]})
        return vd.check_proposals(schema)

    def entry(self, fid="F12", **changes):
        e = copy.deepcopy(self.coding()["fields"][fid])
        e.update(changes)
        return e

    def test_real_drafts_are_well_formed(self):
        self.assertEqual(vd.check_proposals(self.real.schema), [])

    def test_drafts_cover_the_five_open_fields_and_stay_drafts(self):
        drafted = [f["id"] for f in self.real.schema["fields"] if "proposed" in f]
        self.assertEqual(drafted, DRAFT_FIELDS)
        self.assertEqual(drafted, [f["id"] for f in self.real.schema["fields"] if f.get("needs_definition")])
        for fid in DRAFT_FIELDS:
            f = self.real.fields[fid]
            self.assertIs(f["proposed"]["draft"], True)
            self.assertTrue(f["needs_definition"])
            self.assertEqual(f["proposed"]["type"], f["type"])
            self.assertTrue((vd.REPO / f["proposed"]["draft_source"]).exists())

    def test_codebook_still_uses_the_report_vocabulary(self):
        # The F23 draft adds runtime_sandbox; until adopted, codings must not use it in value.
        self.assertNotIn("runtime_sandbox", [v["id"] for v in self.real.fields["F23"]["vocabulary"]])
        rec = self.coding()
        rec["fields"]["F23"].update(status="known", value=["runtime_sandbox"])
        self.assertError(vd.validate_coding(rec, "x", self.syn), r"vocabulary_proposals")
        rec = self.coding()
        rec["fields"]["F12"]["facets"] = {"hard_stop": ["output_limit"]}
        self.assertError(vd.validate_coding(rec, "x", self.syn), r"unexpected keys \['facets'\]")

    def test_malformed_drafts_rejected(self):
        self.assertError(self.schema_with(lambda f: f["F12"]["proposed"].update(draft=False)), r"draft must be true")
        self.assertError(self.schema_with(lambda f: f["F03"].update(proposed=f["F12"]["proposed"])),
                         r"only to fields marked needs_definition")
        self.assertError(self.schema_with(lambda f: f["F22"]["proposed"].update(type="ordinal")),
                         r"keeps the field's answer type")
        self.assertError(self.schema_with(lambda f: f["F21"]["proposed"]["vocabulary"].pop()),
                         r"must keep the report's values \['network_target'\]")
        self.assertError(self.schema_with(lambda f: f["F12"]["proposed"]["facets"][0].update(type="graph")),
                         r"no new answer types")
        self.assertError(self.schema_with(lambda f: f["F23"]["proposed"]["facets"][0].update(vocabulary_from="value")),
                         r"exactly one of")
        self.assertError(self.schema_with(lambda f: f["F01"]["proposed"].pop("alternative")), r"missing keys")

    def test_entries_against_drafts(self):
        ctx, f12 = self.syn, self.real.fields["F12"]
        ok = self.entry(value=["output_limit", "call_count"],
                        facets={"hard_stop": ["output_limit"], "soft_notice": ["call_count"]})
        self.assertEqual(vd.check_proposed_entry(f12, ok, "x", ctx), [])
        self.assertEqual(vd.check_proposed_entry(f12, self.entry(facets={"hard_stop": None}), "x", ctx), [])
        self.assertError(vd.check_proposed_entry(f12, self.entry(facets={"hard_stop": ["money"]}), "x", ctx),
                         r"subset of value")
        self.assertError(vd.check_proposed_entry(f12, self.entry(facets={"ui_layers": []}), "x", ctx),
                         r"not a facet of F12")
        f23 = self.real.fields["F23"]
        sandbox = self.entry("F23", status="known", value=["runtime_sandbox"], confidence="medium",
                             evidence=self.entry()["evidence"], unknown_reason=None,
                             facets={"prompt_instruction": "present"})
        self.assertEqual(vd.check_proposed_entry(f23, sandbox, "x", ctx), [])
        sandbox["facets"] = {"prompt_instruction": "maybe"}
        self.assertError(vd.check_proposed_entry(f23, sandbox, "x", ctx), r"not in the facet vocabulary")
        f01 = self.real.fields["F01"]
        loop = self.entry("F01", value="model_loop", facets={"secondary_modes": ["model_loop"]})
        self.assertError(vd.check_proposed_entry(f01, loop, "x", ctx), r"must not repeat the main value")
        absent = self.entry(status="known_absent", value=[], facets={"hard_stop": []})
        self.assertError(vd.check_proposed_entry(f12, absent, "x", ctx), r"only status known carries facets")


class RealDataAndTemplates(Base):
    def test_real_tree_is_valid(self):
        self.assertEqual(vd.validate_tree(vd.DATA, self.real), [])

    def test_templates_are_in_sync(self):
        self.assertEqual(vd.check_templates(self.real.schema), [])
        tpl = json.loads((vd.DATA / "templates/coding.template.json").read_text())
        self.assertEqual(list(tpl["fields"]), [f["id"] for f in self.real.schema["fields"]])
        self.assertTrue(all(e["status"] is None and e["value"] is None for e in tpl["fields"].values()))

    def test_no_synthetic_records_in_real_dirs(self):
        for sub in ("rounds", "configs", "codings", "adapters"):
            for p in (vd.DATA / sub).rglob("*.json"):
                self.assertFalse(json.loads(p.read_text()).get("synthetic"), p)

    def test_pilot_round_scope(self):
        rnd = json.loads((vd.DATA / "rounds/pilot-1.json").read_text())
        self.assertEqual({t["tool_id"] for t in rnd["tools"]},
                         {"A01", "A02", "A05", "A06", "A07", "A08", "A09", "A17", "A10", "C02"})
        self.assertEqual([c["id"] for c in rnd["coders"]], ["opus", "gpt"])


class FixturesPositive(Base):
    def test_fixture_tree_is_valid(self):
        self.assertEqual(vd.validate_tree(FIX, self.syn), [])

    def test_all_fixture_files_are_marked_synthetic(self):
        files = list(FIX.rglob("*.json"))
        self.assertTrue(files)
        for p in files:
            self.assertIs(json.loads(p.read_text())["synthetic"], True, p)

    def test_fixtures_rejected_as_real_data(self):
        errors = vd.validate_tree(FIX, self.real)
        self.assertError(errors, r"synthetic data is not allowed")
        self.assertError(errors, r"not in research/catalog.json")
        self.assertError(errors, r"synthetic campaign")


class CodingNegative(Base):
    def check(self, mutate, pattern, coder="coder-a", cfg=CFG_A):
        rec = self.coding(coder, cfg)
        mutate(rec["fields"])
        self.assertError(vd.validate_coding(rec, "x", self.syn), pattern)

    def test_unknown_and_missing_field_ids(self):
        self.check(lambda f: f.update(F99=f.pop("F01")), r"unknown field ids \['F99'\]")
        self.check(lambda f: f.pop("F36"), r"missing field ids \['F36'\]")

    def test_illegal_values_and_types(self):
        self.check(lambda f: f["F01"].update(value="smart"), r"not in the nominal vocabulary")
        self.check(lambda f: f["F03"].update(value="budget"), r"must be a list")
        self.check(lambda f: f["F03"].update(value=["budget", "budget"]), r"duplicate")
        self.check(lambda f: f["F23"].update(value=["application_check", "new_thing"]), r"vocabulary_proposals")
        self.check(lambda f: f["F01"].update(status="maybe"), r"status 'maybe'")

    def test_known_needs_evidence_and_confidence(self):
        self.check(lambda f: f["F01"].update(evidence=[]), r"known needs at least one evidence card")
        self.check(lambda f: f["F01"].update(confidence=None), r"needs confidence")

    def test_unknown_rules(self):
        self.check(lambda f: f["F20"].update(value=["session_branch"]), r"unknown must not carry a value")
        self.check(lambda f: f["F20"].update(unknown_reason=None), r"unknown needs unknown_reason")
        self.check(lambda f: f["F20"].update(unknown_reason="conflicting_sources"), r"at least two")
        self.check(lambda f: f["F01"].update(unknown_reason="not_found"), r"only for status unknown")

    def test_absent_semantics(self):
        self.check(lambda f: f["F16"].update(status="known"), r"use status known_absent")
        self.check(lambda f: f["F01"].update(status="known_absent"), r"has no absent value")
        self.check(lambda f: f["F35"].update(status="known_absent", value="persistent"), r"known_absent value must be")

    def test_not_applicable_only_for_conditional(self):
        self.check(lambda f: f["F05"].update(status="not_applicable", value=None, evidence=[], confidence=None),
                   r"cannot be not_applicable")

    def test_conditional_dependencies(self):
        none = {"status": "known_absent", "value": "absent"}
        self.check(lambda f: f["F25"].update(none), r"F26: F25 is not 'present', so F26 must be not_applicable")
        na = {"status": "not_applicable", "value": None, "evidence": [], "confidence": None}
        self.check(lambda f: f["F27"].update(na), r"F27: F25=present, so F27 must be coded")
        unk = {"status": "unknown", "value": None, "unknown_reason": "closed_source", "evidence": [], "confidence": None}
        self.check(lambda f: f["F25"].update(unk), r"F25 is unknown, so F26 must also be unknown")
        # F25 absent with all dependents not_applicable is valid (config B)
        self.assertEqual(vd.validate_coding(self.coding(cfg=CFG_B), "x", self.syn), [])

    def test_evidence_cards(self):
        def card(**kw):
            return lambda f: f["F01"]["evidence"][0].update(kw)
        self.check(card(evidence_kind="blog"), r"unknown evidence_kind 'blog'")
        self.check(card(source_url="https://example.invalid/synthetic-harness/blob/main/src/core.ts"),
                   r"pin a full 40-character commit SHA")
        self.check(card(lines="12-40"), r"lines must look like")
        self.check(lambda f: f["F01"]["evidence"][0].pop("lines"), r"source_path needs lines")
        self.check(card(retrieved_at="yesterday"), r"retrieved_at must be an ISO date")
        self.check(card(retrieved_at="2026-12-01"), r"after the record's evidence_cutoff")
        self.check(card(content_sha256="abc"), r"content_sha256")
        self.check(card(source_url="http://example.invalid/x"), r"https URL")
        self.check(lambda f: f["F01"]["evidence"].append(
            {"evidence_kind": "observed_run", "retrieved_at": "2026-10-01"}), r"observed_run needs run_id")

    def test_private_bench_is_not_mechanism_evidence(self):
        bench = {"evidence_kind": "private_bench_aggregate", "bench_ref": "synthetic-example.totals",
                 "retrieved_at": "2026-10-01"}
        self.check(lambda f: f["F01"]["evidence"].append(bench), r"not mechanism evidence")

    def test_local_paths_rejected(self):
        self.check(lambda f: f["F01"].update(coder_note="see /Users/someone/notes.txt"), r"absolute path")


class AdapterNegative(Base):
    def check(self, mutate, pattern, ctx=None):
        rec = load(f"adapters/coder-a/{ADAPTER}.json")
        mutate(rec)
        self.assertError(vd.validate_adapter(rec, "x", ctx or self.syn, "Z90"), pattern)

    def ref(self, **kw):
        return lambda r: r["private_bench_refs"][0].update(kw)

    def test_valid_adapter(self):
        rec = load(f"adapters/coder-a/{ADAPTER}.json")
        self.assertEqual(vd.validate_adapter(rec, "x", self.syn, "Z90"), [])

    def test_bench_reference_rules(self):
        self.check(self.ref(bench_ref="synthetic-example.task-list"), r"unknown private-bench table")
        self.check(self.ref(bench_ref="no-such-round.totals"), r"does not exist")
        self.check(self.ref(bench_ref="configs.totals"), r"does not exist")
        self.check(self.ref(bench_ref="synthetic-example"), r"<campaign>.<table>")
        self.check(self.ref(note="见题目 7 的日志"), r"must not mention single tasks")
        self.check(self.ref(note="bench_task=xyz"), r"must not mention single tasks")
        self.check(self.ref(bench_config="no-such-config"), r"not in research/private-bench/configs.json")
        self.check(self.ref(source_url="https://example.invalid/x"), r"cites only bench_ref")
        self.check(self.ref(evidence_kind="official_doc", locator="x", source_url="https://example.invalid/x"),
                   r"not allowed here")

    def test_bench_reference_real_mode(self):
        rec = load(f"adapters/coder-a/{ADAPTER}.json")
        errors = vd.validate_adapter(rec, "x", self.real, "A01")  # astra is a Codex (A02) configuration
        self.assertError(errors, r"synthetic campaign")
        self.assertError(errors, r"belongs to another tool")
        errors = vd.validate_adapter(rec, "x", self.real, "A02")
        self.assertFalse(any("belongs to another tool" in e for e in errors))

    def test_chain_check_states(self):
        def state(cid, **kw):
            return lambda r: r["capability_checks"][cid].update(kw)
        self.check(state("streaming_merge", state="multistep_verified",
                         evidence=[{"evidence_kind": "official_doc", "source_url": "https://example.invalid/d",
                                    "locator": "s", "retrieved_at": "2026-10-01"}]), r"needs observed_run")
        self.check(state("multimodal_input", failure_reason=None), r"needs failure_reason")
        self.check(state("tool_definition_request", evidence=[]), r"doc_declared needs")
        self.check(state("cancel_interrupt", failure_reason="x"), r"failure_reason only for")
        self.check(state("cancel_interrupt", state="works"), r"state must be one of")
        self.check(lambda r: r["capability_checks"].pop("subagent_model_selection"), r"must list exactly")

    def test_no_performance_and_access_path(self):
        self.check(lambda r: r.update(success_rate=0.8), r"unexpected keys \['success_rate'\]")
        self.check(lambda r: r.update(access_path="works_fine"), r"access_path must be one of")
        self.check(lambda r: r.update(access_path_evidence=[]), r"needs official evidence")
        self.check(lambda r: r.update(access_path="author_suggested_trial", note=""), r"needs a note")
        self.check(lambda r: r["model_endpoint"].update(model_id=""), r"model_id: required")


class TreeLinks(Base):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(FIX, self.tmp, dirs_exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, rel, fn):
        p = self.tmp / rel
        rec = json.loads(p.read_text())
        fn(rec)
        p.write_text(json.dumps(rec, ensure_ascii=False))

    def errors(self):
        return vd.validate_tree(self.tmp, self.syn)

    def test_coding_without_config(self):
        (self.tmp / f"configs/{CFG_B}.json").unlink()
        self.edit("rounds/synthetic-1.json", lambda r: r["tools"][1].update(config_id=None))
        self.assertError(self.errors(), rf"config '{CFG_B}' has no configs/ record")

    def test_coder_directory_must_match(self):
        shutil.move(self.tmp / "codings/coder-b", self.tmp / "codings/coder-c")
        self.assertError(self.errors(), r"sits under coder-c/ but coder.id is 'coder-b'")

    def test_coder_must_be_in_round(self):
        self.edit("rounds/synthetic-1.json", lambda r: r["coders"].pop())
        errors = self.errors()
        self.assertError(errors, r"coder 'coder-b' is not listed")
        self.assertError(errors, r"at least two independent coders")

    def test_file_name_and_round_link(self):
        shutil.copy(self.tmp / f"configs/{CFG_A}.json", self.tmp / "configs/Z90__synthetic-a__other.json")
        self.assertError(self.errors(), r"file name must equal config_id")
        self.edit(f"configs/{CFG_A}.json", lambda r: r.update(round="synthetic-9"))
        self.assertError(self.errors(), r"round 'synthetic-9' has no rounds")

    def test_disabled_subagents_conflict(self):
        self.edit(f"configs/{CFG_A}.json", lambda r: r.update(subagents_enabled=False))
        self.assertError(self.errors(), r"config disables subagents")

    def test_non_synthetic_fixture_rejected(self):
        self.edit(f"configs/{CFG_A}.json", lambda r: r.update(synthetic=False))
        self.assertError(self.errors(), r"fixture records must be marked synthetic")

    def test_round_tool_must_exist_in_round(self):
        self.edit("rounds/synthetic-1.json", lambda r: r["tools"].pop(0))
        self.assertError(self.errors(), r"tool Z90 is not listed in round")


class Comparison(Base):
    def test_fixture_agreement(self):
        result, errors = compare_codings.compare_tree(FIX, self.syn)
        self.assertEqual(errors, [])
        pairs = {p["config_id"]: p for p in result["pairs"]}
        a = pairs[CFG_A]
        self.assertEqual(a["outcomes"], {"agree_unknown": 1, "agree_value": 31, "status_differs": 1, "value_differs": 3})
        self.assertAlmostEqual(a["agreement_rate"], round(32 / 36, 4))
        self.assertAlmostEqual(a["known_agreement_rate"], round(31 / 34, 4))
        self.assertAlmostEqual(pairs[CFG_B]["agreement_rate"], round(35 / 36, 4))
        fields = {f["field"]: f for f in result["fields"]}
        self.assertEqual(fields["F06"]["cases"][0]["jaccard_distance"], 0.5)
        self.assertEqual(fields["F18"]["status_differs"], 1)
        self.assertEqual(fields["F20"]["reason_differs"], 1)
        self.assertEqual(fields["F23"]["proposals"][0]["coder"], "coder-b")
        self.assertTrue(fields["F01"]["needs_definition"])
        self.assertIn("F06", compare_codings.render_text(result))

    def test_set_order_does_not_matter(self):
        f = self.syn.fields["F03"]
        out = compare_codings.compare_entry(f, {"status": "known", "value": ["budget", "user_interrupt"]},
                                            {"status": "known", "value": ["user_interrupt", "budget"]})
        self.assertEqual(out["outcome"], "agree_value")

    def test_invalid_data_stops_comparison(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copytree(FIX, tmp, dirs_exist_ok=True)
            p = tmp / f"codings/coder-a/{CFG_A}.json"
            rec = json.loads(p.read_text())
            rec["fields"]["F01"]["value"] = "smart"
            p.write_text(json.dumps(rec))
            result, errors = compare_codings.compare_tree(tmp, self.syn)
            self.assertIsNone(result)
            self.assertTrue(errors)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
