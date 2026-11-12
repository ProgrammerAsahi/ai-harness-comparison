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
        self.assertEqual([f["id"] for f in self.real.schema["fields"] if "condition" in f], ["F26", "F27", "F28"])

    def test_private_bench_tables_match_renderer(self):
        source = (vd.REPO / "research/private_bench.py").read_text()
        rendered = set(re.findall(r"if table == '([a-z-]+)'", source))
        self.assertEqual(set(self.real.enums["private_bench_tables"]), rendered)

    def test_evidence_kinds_cover_card(self):
        self.assertTrue({"source_path", "official_doc", "default_release", "account_check", "observed_run",
                         "private_bench_aggregate"} <= set(self.real.enums["evidence_kind"]))


FACETED_FIELDS = ["F01", "F11", "F12", "F13", "F21", "F22", "F23", "F27", "F28", "F29", "F30", "F31", "F32", "F33",
                  "F34", "F35", "F36"]  # fields with facets a coder always fills (besides the optional unresolved)


class DefinitionsAndFacets(Base):
    """fields-0.7: every field carries an adopted definition; general rules and facets are shape-checked."""

    def schema_with(self, mutate):
        schema = copy.deepcopy(self.real.schema)
        mutate({f["id"]: f for f in schema["fields"]})
        return vd.check_definitions(schema)

    def errors(self, fid="F12", **changes):
        rec = self.coding()
        rec["fields"][fid].update(changes)
        return [e for e in vd.validate_coding(rec, "x", self.syn) if f".{fid}" in e or f"{fid}:" in e]

    def facets(self, fid, **changes):
        return {**self.coding()["fields"][fid]["facets"], **changes}

    def test_real_definitions_are_well_formed(self):
        self.assertEqual(self.real.schema["schema_version"], "fields-0.7")
        self.assertEqual(vd.check_definitions(self.real.schema), [])

    def test_every_field_is_defined_and_no_draft_remains(self):
        fields = self.real.schema["fields"]
        self.assertTrue(all("definition" in f for f in fields))
        required = lambda f: [fc["id"] for fc in f.get("facets", []) if not fc.get("optional")]
        self.assertEqual([f["id"] for f in fields if required(f)], FACETED_FIELDS)
        # every set field, and only those, offers the optional "unresolved" facet (general rule R7)
        self.assertEqual([f["id"] for f in fields if [fc["id"] for fc in f.get("facets", []) if fc.get("optional")]
                          == ["unresolved"]], [f["id"] for f in fields if f["type"] in ("set", "conditional_set")])
        self.assertEqual([r["id"] for r in self.real.schema["general_rules"]], [f"R{i}" for i in range(1, 11)])
        self.assertIn("vocabulary_gap", self.real.enums["unknown_reason"])
        self.assertFalse([f["id"] for f in fields if "proposed" in f or "needs_definition" in f])
        self.assertIn("runtime_sandbox", [v["id"] for v in self.real.fields["F23"]["vocabulary"]])
        self.assertEqual({fc["id"]: fc["in_distance"] for fc in self.real.fields["F12"]["facets"]},
                         {"hard_stop": True, "soft_notice": False, "mode_unknown": False, "unresolved": False})

    def test_general_rules_and_missing_definitions_rejected(self):
        schema = copy.deepcopy(self.real.schema)
        schema["general_rules"][1]["id"] = "R9"
        self.assertError(vd.check_definitions(schema), r"general_rules ids must run")
        del schema["general_rules"]
        self.assertError(vd.check_definitions(schema), r"general_rules must list rules")
        self.assertError(self.schema_with(lambda f: f["F02"].pop("definition")), r"every field carries a definition")
        self.assertError(self.schema_with(lambda f: f["F03"]["facets"][-1].update(optional=False)), r"optional is either true")

    def test_rules_r6_r7_in_codings(self):
        self.assertEqual(self.errors("F03", value=["budget"], confidence="medium", facets={"unresolved": ["user_interrupt"]}), [])
        self.assertEqual(self.errors("F03", value=["budget"], facets={}), [])  # the optional facet may be left out
        self.assertError(self.errors("F03", value=["budget"], facets={"unresolved": ["budget"]}), r"must not repeat members")
        self.assertError(self.errors("F03", value=["budget"], confidence="high", facets={"unresolved": ["user_interrupt"]}),
                         r"confidence is medium at most")
        self.assertError(self.errors("F03", value_note="推断：官方文档只写了预算上限。", confidence="medium"),
                         r"has confidence low")
        gap = dict(status="unknown", value=None, unknown_reason="vocabulary_gap", evidence=[], confidence=None, facets={})
        self.assertError(self.errors("F03", **gap), r"vocabulary_gap needs a vocabulary proposal")

    def test_malformed_definitions_rejected(self):
        self.assertError(self.schema_with(lambda f: f["F12"].update(proposed={})), r"drafts are not kept")
        self.assertError(self.schema_with(lambda f: f["F01"]["definition"].pop("absent_rule")), r"definition must give")
        self.assertError(self.schema_with(lambda f: f["F21"]["vocabulary"][0].pop("example")),
                         r"criterion and example must be text")
        self.assertError(self.schema_with(lambda f: f["F12"]["facets"][0].update(type="graph")), r"no new answer types")
        self.assertError(self.schema_with(lambda f: f["F23"]["facets"][0].update(vocabulary_from="value")),
                         r"exactly one of")
        self.assertError(self.schema_with(lambda f: f["F12"]["facets"][2].update(complement_of=["nope"])),
                         r"complement_of lists earlier facets")
        self.assertError(self.schema_with(lambda f: f["F21"]["facets"][0].update(subset_of_value=True)),
                         r"subset_of_value needs vocabulary_from")
        self.assertError(self.schema_with(lambda f: f["F22"]["facets"].append(dict(f["F22"]["facets"][0]))),
                         r"duplicate facet id")

    def test_examples_do_not_name_tools_under_coding(self):
        # Both coders read the same codebook: an example naming a pilot tool would hand them the answer.
        self.assertIn("A01", vd.pilot_tool_ids())
        self.assertError(self.schema_with(
            lambda f: f["F22"]["vocabulary"][1].update(example="A01 Claude Code 手动模式（03A）")),
            r"example names tools under coding \['A01'\]")

    def test_facets_only_on_fields_that_declare_them(self):
        self.assertError(self.errors("F02", facets={"hard_stop": []}), r"F02 has no facets")
        self.assertError(self.errors(facets=self.facets("F12", ui_layers=[])), r"are not facets of F12")
        self.assertError(self.errors(facets={"hard_stop": ["output_limit"]}), r"soft_notice: missing; write null")

    def test_budget_facets(self):
        value = ["output_limit", "call_count"]
        split = {"hard_stop": ["output_limit"], "soft_notice": ["call_count"], "mode_unknown": []}
        self.assertEqual(self.errors(value=value, facets=split), [])
        self.assertEqual(self.errors(value=value, facets={**split, "soft_notice": [], "mode_unknown": ["call_count"]}), [])
        self.assertError(self.errors(value=value, facets={**split, "soft_notice": []}), r"exactly the values in none of")
        self.assertError(self.errors(value=value, facets={**split, "soft_notice": [], "mode_unknown": None}),
                         r"must list the values in none of")
        self.assertEqual(self.errors(value=value, facets={"hard_stop": None, "soft_notice": None, "mode_unknown": None}), [])
        self.assertError(self.errors(facets=self.facets("F12", hard_stop=["money"])), r"subset of value")
        self.assertError(self.errors(facets=self.facets("F12", hard_stop="output_limit")), r"list of unique ids")

    def test_other_facets(self):
        self.assertEqual(self.errors("F23", value=["runtime_sandbox"], facets={"prompt_only": "present"}), [])
        self.assertError(self.errors("F23", facets={"prompt_only": "maybe"}), r"not in the facet vocabulary")
        self.assertError(self.errors("F01", value="model_loop", facets={"secondary_modes": ["model_loop"]}),
                         r"must not repeat the main value")
        self.assertEqual(self.errors("F01", value="model_loop", facets={"secondary_modes": ["explicit_workflow"]}), [])
        self.assertError(self.errors("F21", facets=self.facets("F21", default_edit="ask")), r"not in the facet vocabulary")
        self.assertError(self.errors("F22", facets=self.facets("F22", approver=["model"])), r"not in the facet vocabulary")
        # the approval UI may sit on a layer the gate does not: ui_layers is not a subset of value
        self.assertEqual(self.errors("F22", value=["tool_call"], facets={"ui_layers": ["whole_task"], "approver": ["user"]}), [])

    def test_facets_by_status(self):
        # tied to value (subsets, exclusions): only when the value is known and non-empty
        absent = dict(status="known_absent", value=[])
        self.assertError(self.errors(**absent, facets=self.facets("F12", hard_stop=[])), r"stays null when status is known_absent")
        self.assertEqual(self.errors(**absent, facets={"hard_stop": None, "soft_notice": None, "mode_unknown": None}), [])
        self.assertEqual(self.errors(**absent, facets={}), [])
        # own-vocabulary facets still say something when the main value is empty
        self.assertEqual(self.errors("F23", **absent, facets={"prompt_only": "present"}), [])
        open_all = {"default_edit": "allow", "default_command": "allow", "default_outside_write": "allow",
                    "default_network": None}
        self.assertEqual(self.errors("F21", **absent, facets=open_all), [])
        self.assertError(self.errors("F21", **absent, facets={"default_edit": "allow"}), r"default_command: missing")
        unknown = dict(status="unknown", value=None, unknown_reason="closed_source", evidence=[], confidence=None)
        self.assertError(self.errors("F21", **unknown, facets=open_all), r"stays null when status is unknown")
        self.assertEqual(self.errors("F21", **unknown, facets=dict.fromkeys(open_all)), [])


class RealDataAndTemplates(Base):
    def test_real_tree_is_valid(self):
        self.assertEqual(vd.validate_tree(vd.DATA, self.real), [])

    def test_templates_are_in_sync(self):
        self.assertEqual(vd.check_templates(self.real.schema), [])
        tpl = json.loads((vd.DATA / "templates/coding.template.json").read_text())
        self.assertEqual(list(tpl["fields"]), [f["id"] for f in self.real.schema["fields"]])
        self.assertTrue(all(e["status"] is None and e["value"] is None for e in tpl["fields"].values()))
        self.assertEqual({fid: list(e["facets"]) for fid, e in tpl["fields"].items() if "facets" in e},
                         {fid: [fc["id"] for fc in self.real.fields[fid]["facets"] if not fc.get("optional")]
                          for fid in FACETED_FIELDS})
        self.assertEqual(list(tpl["fields"]["F12"])[:3], ["status", "value", "facets"])

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
        self.assertNotIn("needs_definition", fields["F01"])
        # facets are compared where both coders know the value, and never change the field agreement
        self.assertEqual((fields["F22"]["agreement_rate"], fields["F22"]["facet_compared"], fields["F22"]["facet_differs"]),
                         (1.0, 4, 1))
        self.assertEqual(fields["F22"]["cases"][0]["outcome"], "facet_differs")
        self.assertEqual(fields["F21"]["cases"][0]["outcome"], "facet_one_unknown")
        self.assertEqual((fields["F01"]["facet_compared"], fields["F01"]["facet_differs"]), (2, 0))
        self.assertEqual(fields["F03"]["facet_compared"], 0)
        text = compare_codings.render_text(result)
        self.assertIn("F06", text)
        self.assertIn("facets differ 1 of 4", text)

    def test_set_order_does_not_matter(self):
        f = self.syn.fields["F03"]
        out = compare_codings.compare_entry(f, {"status": "known", "value": ["budget", "user_interrupt"]},
                                            {"status": "known", "value": ["user_interrupt", "budget"]})
        self.assertEqual(out["outcome"], "agree_value")

    def test_facets_compared_only_when_both_know_the_value(self):
        f = self.syn.fields["F22"]
        known = {"status": "known", "value": ["tool_call"], "facets": {"ui_layers": ["tool_call"], "approver": ["user"]}}
        other = {"status": "known", "value": ["tool_call", "whole_task"], "facets": {"ui_layers": None, "approver": ["user"]}}
        out = compare_codings.compare_entry(f, known, other)
        self.assertEqual((out["outcome"], out["facets"]), ("value_differs", {"ui_layers": "one_unknown", "approver": "agree"}))
        unknown = {"status": "unknown", "value": None, "unknown_reason": "closed_source"}
        self.assertNotIn("facets", compare_codings.compare_entry(f, known, unknown))
        self.assertNotIn("facets", compare_codings.compare_entry(f, unknown, unknown))

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
