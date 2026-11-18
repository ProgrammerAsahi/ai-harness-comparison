#!/usr/bin/env python3
"""MIT. Reproduce synthetic examples; not a production Harness rating engine."""
from __future__ import annotations

import json
import math
from fractions import Fraction
from pathlib import Path


def field_difference(a, b, kind, span=None):
    """None is unknown. Structural inapplicability must be resolved upstream."""
    if a is None or b is None:
        return None
    if kind == "nominal":
        return float(a != b)
    if kind == "set":
        left, right = set(a), set(b)
        return 1 - len(left & right) / len(left | right) if left | right else 0.0
    if kind in {"numeric", "ordinal"}:
        if span is None or not math.isfinite(span) or span <= 0:
            raise ValueError("Numeric and ordinal fields require a positive fixed span")
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (a, b)):
            raise ValueError("Values must be finite numbers")
        return min(abs(a - b) / span, 1.0)
    raise ValueError(f"Unsupported field kind: {kind}")


def compare(left, right, schema):
    """Fixed eligible field set, weights > 0, no conditional branches or imputation.

    Normalization uses fixed total weight. Missing weight remains unknown and
    contributes to logical bounds, not to an estimated confidence interval.

    Accumulate the supplied numbers exactly before converting ratios to float.
    Output coverage (and field weights) may round to zero for positive mass;
    point existence depends on raw known mass, never on rounded coverage.
    Float outputs and sums of rounded field details need not be exact identities.
    """
    if not schema:
        raise ValueError("At least one field is required")
    identifiers = [field["id"] for field in schema]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate field ids")
    if any(isinstance(f["weight"], bool) or not math.isfinite(f["weight"])
           or f["weight"] <= 0 for f in schema):
        raise ValueError("Weights must be finite and positive")
    # Binary float inputs are preserved, not reinterpreted as decimal strings.
    # Exact raw masses avoid both overflow and loss of tiny common evidence.
    weights = [Fraction(f["weight"]) for f in schema]
    total = sum(weights, Fraction())
    known, contribution, details = Fraction(), Fraction(), []
    for field, raw_weight in zip(schema, weights):
        key, weight = field["id"], raw_weight / total
        delta = field_difference(left.get(key), right.get(key), field["kind"], field.get("span"))
        cost = None if delta is None else raw_weight * Fraction(delta)
        if delta is not None:
            known += raw_weight
            contribution += cost
        details.append({"id": key, "weight": float(weight), "difference": delta,
                        "contribution": None if cost is None else float(cost / total)})
    unknown = total - known
    lower, upper = float(contribution / total), float((contribution + unknown) / total)
    distance = float(contribution / known) if known else None
    return {"observed_distance": distance, "coverage": float(known / total),
            "distance_bounds": [lower, upper],
            "observed_similarity": None if distance is None else 1 - distance,
            "similarity_bounds": [1 - upper, 1 - lower], "fields": details}


def examples():
    schema = [
        {"id": "control", "kind": "nominal", "weight": 0.25},
        {"id": "context", "kind": "set", "weight": 0.25},
        {"id": "recovery", "kind": "ordinal", "span": 2, "weight": 0.25},
        {"id": "trigger", "kind": "set", "weight": 0.25},
    ]
    left = {"control": "loop", "context": ["summary", "file"], "recovery": 2, "trigger": ["manual"]}
    right = {"control": "loop", "context": ["summary"], "recovery": 1, "trigger": None}
    binary = [{"id": key, "kind": "nominal", "weight": 1} for key in ("x", "y", "z")]
    points = {"A": {"x": 0, "y": 0}, "B": {"x": 0, "z": 0}, "C": {"y": 1, "z": 0}}
    return {
        "notice": "全部为虚构教学数据；未测量任何真实 Harness 或模型",
        "four_fields": {"schema": schema, "left": left, "right": right, "result": compare(left, right, schema)},
        "missing_triangle": {pair: compare(points[pair[0]], points[pair[1]], binary) for pair in ("AB", "BC", "AC")},
        "interaction_percentages": {"A": {"model_A": 80, "model_B": 50}, "B": {"model_A": 60, "model_B": 75}},
        "swing_weights": {"success": 100 / 200, "review": 60 / 200, "latency": 40 / 200},
        "pilot_runs": 3 * 2 * 4 * 5 * 3,
    }


if __name__ == "__main__":
    output = Path(__file__).with_name("examples.json")
    output.write_text(json.dumps(examples(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Wrote synthetic examples.json")
