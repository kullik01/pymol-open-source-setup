#!/usr/bin/env python3
"""Validate and score observable behavior for the human-AI workflow."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CATALOG_RELATIVE = Path("evals/development-workflow/scenarios.json")
ALLOWED_OBSERVERS = {"human", "harness", "independent-ai"}


@dataclass(frozen=True)
class Evaluation:
    """Store the score and diagnostics for one workflow evaluation."""

    passed: bool
    earned: int
    possible: int
    messages: list[str]


def read_json(path: Path) -> Any:
    """Read and decode a JSON document.

    Args:
        path: JSON file to read.

    Returns:
        The decoded JSON value.

    Raises:
        ValueError: If the file is missing or contains invalid JSON.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"missing file: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}: {error}") from error


def validate_catalog(catalog: Any) -> list[str]:
    """Validate the workflow scenario catalog structure.

    Args:
        catalog: Decoded catalog value.

    Returns:
        Validation error messages, or an empty list when valid.
    """
    errors: list[str] = []
    if not isinstance(catalog, dict):
        return ["catalog root must be an object"]
    if catalog.get("schema_version") != 1:
        errors.append("catalog schema_version must be 1")

    criteria = catalog.get("criteria")
    if not isinstance(criteria, dict) or not criteria:
        errors.append("catalog criteria must be a non-empty object")
        criteria = {}
    else:
        for name, description in criteria.items():
            if not isinstance(name, str) or not name.replace("_", "").isalnum():
                errors.append(f"invalid criterion name: {name!r}")
            if not isinstance(description, str) or len(description.strip()) < 20:
                errors.append(f"criterion {name!r} needs a useful description")

    scenarios = catalog.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        errors.append("catalog scenarios must be a non-empty array")
        return errors

    seen_ids: set[str] = set()
    used_criteria: set[str] = set()
    for index, scenario in enumerate(scenarios):
        location = f"scenario[{index}]"
        if not isinstance(scenario, dict):
            errors.append(f"{location} must be an object")
            continue
        scenario_id = scenario.get("id")
        if not isinstance(scenario_id, str) or not scenario_id:
            errors.append(f"{location} needs a non-empty id")
        elif scenario_id in seen_ids:
            errors.append(f"duplicate scenario id: {scenario_id}")
        else:
            seen_ids.add(scenario_id)
            location = scenario_id

        for field in ("title", "prompt", "fixture"):
            if not isinstance(scenario.get(field), str) or not scenario[field].strip():
                errors.append(f"{location}: {field} must be non-empty text")

        routes = scenario.get("accepted_routes")
        if (
            not isinstance(routes, list)
            or not routes
            or any(
                not isinstance(route, list)
                or not route
                or any(not isinstance(skill, str) or not skill for skill in route)
                for route in routes
            )
        ):
            errors.append(f"{location}: accepted_routes must contain skill arrays")

        required = scenario.get("required_criteria")
        if not isinstance(required, list) or not required:
            errors.append(f"{location}: required_criteria must be a non-empty array")
            continue
        if len(required) != len(set(required)):
            errors.append(f"{location}: required_criteria contains duplicates")
        for criterion in required:
            if criterion not in criteria:
                errors.append(f"{location}: unknown criterion {criterion!r}")
            else:
                used_criteria.add(criterion)

    unused = set(criteria) - used_criteria
    if unused:
        errors.append("unused criteria: " + ", ".join(sorted(unused)))
    return errors


def result_template(catalog: dict[str, Any]) -> dict[str, Any]:
    """Create a blank observation result document for a catalog.

    Args:
        catalog: Validated workflow catalog.

    Returns:
        A result document ready for an observer to complete.
    """
    return {
        "catalog_schema_version": catalog["schema_version"],
        "run_id": "replace-with-run-id",
        "observer": {
            "kind": "human",
            "name": "replace-with-observer",
            "independent_of_agent": True,
        },
        "results": [
            {
                "scenario_id": scenario["id"],
                "skills": scenario["accepted_routes"][0],
                "criteria": {
                    criterion: {
                        "passed": False,
                        "evidence": "replace with an observable tool call, artifact, stop, or output",
                    }
                    for criterion in scenario["required_criteria"]
                },
                "notes": "",
            }
            for scenario in catalog["scenarios"]
        ],
    }


def evaluate_results(
    catalog: dict[str, Any], results: Any, *, allow_partial: bool = False
) -> Evaluation:
    """Score observed workflow results against the catalog.

    Args:
        catalog: Validated workflow catalog.
        results: Decoded observation result document.
        allow_partial: Whether missing scenarios should be permitted.

    Returns:
        Evaluation score and any validation diagnostics.
    """
    messages: list[str] = []
    earned = 0
    possible = 0
    if not isinstance(results, dict):
        return Evaluation(False, 0, 0, ["results root must be an object"])
    if results.get("catalog_schema_version") != catalog["schema_version"]:
        messages.append("results catalog_schema_version does not match the catalog")

    observer = results.get("observer")
    if not isinstance(observer, dict):
        messages.append("observer must be an object")
    else:
        if observer.get("kind") not in ALLOWED_OBSERVERS:
            messages.append(
                "observer.kind must be human, harness, or independent-ai"
            )
        if not isinstance(observer.get("name"), str) or not observer["name"].strip():
            messages.append("observer.name must be non-empty")
        if observer.get("independent_of_agent") is not True:
            messages.append("the observer must be independent of the agent under test")

    raw_results = results.get("results")
    if not isinstance(raw_results, list):
        return Evaluation(False, 0, 0, messages + ["results must be an array"])
    if not raw_results:
        messages.append("results must contain at least one observed scenario")

    by_id: dict[str, dict[str, Any]] = {}
    for item in raw_results:
        if not isinstance(item, dict) or not isinstance(item.get("scenario_id"), str):
            messages.append("every result needs a string scenario_id")
            continue
        scenario_id = item["scenario_id"]
        if scenario_id in by_id:
            messages.append(f"duplicate result for {scenario_id}")
        by_id[scenario_id] = item

    scenarios = {scenario["id"]: scenario for scenario in catalog["scenarios"]}
    unknown = set(by_id) - set(scenarios)
    if unknown:
        messages.append("unknown scenario results: " + ", ".join(sorted(unknown)))
    missing = set(scenarios) - set(by_id)
    if missing and not allow_partial:
        messages.append("missing scenario results: " + ", ".join(sorted(missing)))

    for scenario_id, scenario in scenarios.items():
        item = by_id.get(scenario_id)
        if item is None:
            continue
        possible += 1
        route = item.get("skills")
        if route in scenario["accepted_routes"]:
            earned += 1
        else:
            messages.append(
                f"{scenario_id}: route {route!r} is not accepted; expected one of "
                f"{scenario['accepted_routes']!r}"
            )

        observations = item.get("criteria")
        if not isinstance(observations, dict):
            messages.append(f"{scenario_id}: criteria must be an object")
            observations = {}
        extras = set(observations) - set(scenario["required_criteria"])
        if extras:
            messages.append(
                f"{scenario_id}: unexpected criteria: {', '.join(sorted(extras))}"
            )
        for criterion in scenario["required_criteria"]:
            possible += 1
            observation = observations.get(criterion)
            if not isinstance(observation, dict):
                messages.append(f"{scenario_id}/{criterion}: observation is missing")
                continue
            evidence = observation.get("evidence")
            if not isinstance(evidence, str) or not evidence.strip():
                messages.append(f"{scenario_id}/{criterion}: evidence is required")
                continue
            if observation.get("passed") is True:
                earned += 1
            elif observation.get("passed") is False:
                messages.append(
                    f"{scenario_id}/{criterion}: failed — {evidence.strip()}"
                )
            else:
                messages.append(f"{scenario_id}/{criterion}: passed must be boolean")

    return Evaluation(not messages and earned == possible, earned, possible, messages)


def self_test(catalog: dict[str, Any]) -> list[str]:
    """Verify that the evaluator accepts and rejects known fixtures.

    Args:
        catalog: Validated workflow catalog.

    Returns:
        Error messages produced by failed self-test cases.
    """
    passing = result_template(catalog)
    passing["run_id"] = "evaluator-self-test"
    passing["observer"]["name"] = "deterministic-fixture"
    for result in passing["results"]:
        for observation in result["criteria"].values():
            observation["passed"] = True
            observation["evidence"] = "synthetic observable evidence for scorer self-test"
    pass_evaluation = evaluate_results(catalog, passing)
    errors: list[str] = []
    if not pass_evaluation.passed:
        errors.append("known-passing fixture did not pass")
        errors.extend(pass_evaluation.messages)

    failing = json.loads(json.dumps(passing))
    first = failing["results"][0]
    first_criterion = next(iter(first["criteria"]))
    first["criteria"][first_criterion] = {
        "passed": False,
        "evidence": "synthetic failure for scorer self-test",
    }
    fail_evaluation = evaluate_results(catalog, failing)
    if fail_evaluation.passed or not fail_evaluation.messages:
        errors.append("known-failing fixture was not rejected")

    unauthorized_observer = json.loads(json.dumps(passing))
    unauthorized_observer["observer"]["independent_of_agent"] = False
    observer_evaluation = evaluate_results(catalog, unauthorized_observer)
    if observer_evaluation.passed:
        errors.append("self-evaluation fixture was not rejected")

    invalid_route = json.loads(json.dumps(passing))
    invalid_route["results"][0]["skills"] = ["launch-product"]
    route_evaluation = evaluate_results(catalog, invalid_route)
    if route_evaluation.passed:
        errors.append("invalid routing fixture was not rejected")
    return errors


def main() -> int:
    """Run catalog validation, self-tests, or result scoring.

    Returns:
        Process exit status.
    """
    parser = argparse.ArgumentParser(
        description="Validate workflow scenarios or score externally observed runs."
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--results", type=Path, help="JSON results to score")
    action.add_argument(
        "--write-template", type=Path, help="write an observation template"
    )
    action.add_argument(
        "--self-test", action="store_true", help="test the deterministic scorer"
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="allow results for only a subset of scenarios",
    )
    args = parser.parse_args()

    repo = args.repo.resolve()
    catalog_path = repo / CATALOG_RELATIVE
    try:
        catalog = read_json(catalog_path)
    except ValueError as error:
        print(f"Workflow evaluation catalog failed: {error}")
        return 1

    catalog_errors = validate_catalog(catalog)
    if catalog_errors:
        print("Workflow evaluation catalog failed:")
        for error in catalog_errors:
            print(f"- {error}")
        return 1

    if args.write_template:
        target = args.write_template.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(result_template(catalog), indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote observation template: {target}")
        return 0

    if args.self_test:
        errors = self_test(catalog)
        if errors:
            print("Workflow evaluator self-test failed:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("Workflow evaluator self-test passed")
        return 0

    if args.results:
        try:
            results = read_json(args.results.resolve())
        except ValueError as error:
            print(f"Workflow evaluation failed: {error}")
            return 1
        evaluation = evaluate_results(
            catalog, results, allow_partial=args.allow_partial
        )
        print(
            f"Workflow behavioral score: {evaluation.earned}/{evaluation.possible} "
            f"checks ({len(catalog['scenarios'])} catalog scenarios)"
        )
        for message in evaluation.messages:
            print(f"- {message}")
        return 0 if evaluation.passed else 1

    print(
        "Workflow evaluation catalog passed: "
        f"{len(catalog['scenarios'])} scenarios and {len(catalog['criteria'])} criteria"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
