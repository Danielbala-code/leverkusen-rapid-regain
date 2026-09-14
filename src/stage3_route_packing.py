from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd


PXT_PASS = 1404
PXT_DRIBBLE = 1405
BYPASSED_OPPONENTS = 0
BYPASSED_DEFENDERS = 2

PRIMARY_PHASE = "ATTACKING_TRANSITION"


def load_records(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["events", "eventKpis", "eventKPIs", "data", "items"]:
            if isinstance(data.get(key), list):
                return data[key]
        return [data]

    return []


def collapse_bypass_values(values: list[float]):
    """
    Identical duplicate values are collapsed.
    Conflicting duplicates are excluded from bypass averages.
    """
    if not values:
        return None, "missing"

    rounded_values = {round(value, 12) for value in values}

    if len(rounded_values) == 1:
        return values[0], "available"

    return None, "conflict"


def main():
    parser = argparse.ArgumentParser(
        description="Build Impect route × dynamic-packing-zone outputs."
    )
    parser.add_argument(
        "--data-root",
        default=r"D:\Impect\impect-open-data",
    )
    parser.add_argument(
        "--output-dir",
        default=r"D:\Impect\england-game-model\outputs",
    )
    parser.add_argument(
        "--min-actions",
        type=int,
        default=30,
        help="Minimum actions before a route is eligible for ranking.",
    )
    args = parser.parse_args()

    data_root = Path(args.data_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    events_dir = data_root / "data" / "events"
    event_kpis_dir = data_root / "data" / "events_kpis"
    squads_dir = data_root / "data" / "squads"

    event_files = sorted(events_dir.glob("events_*.json"))
    kpi_files = sorted(event_kpis_dir.glob("events_kpis_*.json"))
    squad_files = sorted(squads_dir.glob("squads_*.json"))

    if not event_files or not kpi_files:
        raise FileNotFoundError(
            "Expected events and events_kpis folders were not found."
        )

    # Squad ID -> readable team name
    squad_names = {}

    for path in squad_files:
        for squad in load_records(path):
            if squad.get("id") is not None and squad.get("name") is not None:
                squad_names[str(squad["id"])] = squad["name"]

    # Candidate grain: one successful PASS or DRIBBLE action
    # with valid start/end dynamic packing zones.
    candidates = {}
    total_events = 0
    excluded_no_end_zone = 0
    excluded_not_successful = 0
    excluded_action_type = 0

    for path in event_files:
        match_id = path.stem.rsplit("_", 1)[-1]

        for event in load_records(path):
            total_events += 1

            event_id = event.get("id")
            action_type = event.get("actionType")
            result = event.get("result")
            start = event.get("start") or {}
            end = event.get("end") or {}

            if action_type not in {"PASS", "DRIBBLE"}:
                excluded_action_type += 1
                continue

            if result != "SUCCESS":
                excluded_not_successful += 1
                continue

            start_zone = start.get("packingZone")
            end_zone = end.get("packingZone")

            if not start_zone or not end_zone:
                excluded_no_end_zone += 1
                continue

            expected_pxt_kpi = (
                PXT_PASS
                if action_type == "PASS"
                else PXT_DRIBBLE
            )

            event_id = str(event_id)

            candidates[event_id] = {
                "event_id": event_id,
                "match_id": match_id,
                "team_id": str(event.get("squadId")),
                "team_name": squad_names.get(
                    str(event.get("squadId")),
                    f"Unknown team {event.get('squadId')}",
                ),
                "phase": event.get("phase"),
                "action_type": action_type,
                "action_label": event.get("action"),
                "start_packing_zone": start_zone,
                "end_packing_zone": end_zone,
                "start_pitch_position": start.get("pitchPosition"),
                "end_pitch_position": end.get("pitchPosition"),
                "start_lane": start.get("lane"),
                "end_lane": end.get("lane"),
                "expected_pxt_kpi": expected_pxt_kpi,
            }

    print(f"Raw events scanned: {total_events:,}")
    print(f"Eligible successful actions: {len(candidates):,}")

    # Join action-level pxT and packing KPIs by event ID.
    pxt_values = {}
    bypass_opponents = defaultdict(list)
    bypass_defenders = defaultdict(list)
    pxt_duplicates = 0

    for path in kpi_files:
        for row in load_records(path):
            event_id = row.get("eventId")

            if event_id is None:
                continue

            event_id = str(event_id)

            if event_id not in candidates:
                continue

            try:
                kpi_id = int(row.get("kpiId"))
                value = float(row.get("value"))
            except (TypeError, ValueError):
                continue

            candidate = candidates[event_id]

            if kpi_id == candidate["expected_pxt_kpi"]:
                if event_id in pxt_values:
                    pxt_duplicates += 1
                else:
                    pxt_values[event_id] = value

            elif kpi_id == BYPASSED_OPPONENTS:
                bypass_opponents[event_id].append(value)

            elif kpi_id == BYPASSED_DEFENDERS:
                bypass_defenders[event_id].append(value)

    route_rows = []
    bypass_conflicts = 0

    for event_id, candidate in candidates.items():
        pxt_action_delta = pxt_values.get(event_id)

        # A route is only valued when its action-specific pxT KPI exists.
        if pxt_action_delta is None:
            continue

        opponents_value, opponents_status = collapse_bypass_values(
            bypass_opponents[event_id]
        )
        defenders_value, defenders_status = collapse_bypass_values(
            bypass_defenders[event_id]
        )

        if (
            opponents_status == "conflict"
            or defenders_status == "conflict"
        ):
            bypass_conflicts += 1

        route_rows.append(
            {
                **candidate,
                "pxt_action_delta": pxt_action_delta,
                "positive_pxt": int(pxt_action_delta > 0),
                "bypassed_opponents": opponents_value,
                "bypassed_opponents_status": opponents_status,
                "bypassed_defenders": defenders_value,
                "bypassed_defenders_status": defenders_status,
            }
        )

    if not route_rows:
        raise RuntimeError(
            "No action routes received a matching action-level pxT KPI."
        )

    routes = pd.DataFrame(route_rows)

    event_output = output_dir / "route_packing_events.csv"
    routes.to_csv(event_output, index=False)

    group_columns = [
        "team_id",
        "team_name",
        "phase",
        "action_type",
        "action_label",
        "start_packing_zone",
        "end_packing_zone",
    ]

    route_summary = (
        routes.groupby(group_columns, dropna=False)
        .agg(
            action_count=("event_id", "size"),
            total_pxt_action_delta=("pxt_action_delta", "sum"),
            mean_pxt_action_delta=("pxt_action_delta", "mean"),
            median_pxt_action_delta=("pxt_action_delta", "median"),
            positive_pxt_share=("positive_pxt", "mean"),
            mean_bypassed_opponents=("bypassed_opponents", "mean"),
            mean_bypassed_defenders=("bypassed_defenders", "mean"),
            bypassed_opponents_coverage=(
                "bypassed_opponents",
                lambda series: series.notna().mean(),
            ),
            bypassed_defenders_coverage=(
                "bypassed_defenders",
                lambda series: series.notna().mean(),
            ),
        )
        .reset_index()
        .sort_values(
            ["total_pxt_action_delta", "action_count"],
            ascending=[False, False],
        )
    )

    route_summary_output = output_dir / "route_packing_summary_all.csv"
    route_summary.to_csv(route_summary_output, index=False)

    route_summary_minimum = route_summary.loc[
        route_summary["action_count"] >= args.min_actions
    ].copy()

    route_summary_minimum_output = (
        output_dir / "route_packing_summary_min30.csv"
    )
    route_summary_minimum.to_csv(
        route_summary_minimum_output,
        index=False,
    )

    transition_routes_minimum = route_summary_minimum.loc[
        route_summary_minimum["phase"] == PRIMARY_PHASE
    ].copy()

    transition_routes_output = (
        output_dir / "route_packing_transition_min30.csv"
    )
    transition_routes_minimum.to_csv(
        transition_routes_output,
        index=False,
    )

    team_phase_summary = (
        routes.groupby(["team_id", "team_name", "phase"], dropna=False)
        .agg(
            action_count=("event_id", "size"),
            total_pxt_action_delta=("pxt_action_delta", "sum"),
            mean_pxt_action_delta=("pxt_action_delta", "mean"),
            median_pxt_action_delta=("pxt_action_delta", "median"),
            positive_pxt_share=("positive_pxt", "mean"),
        )
        .reset_index()
        .sort_values(
            ["phase", "total_pxt_action_delta"],
            ascending=[True, False],
        )
    )

    team_phase_output = output_dir / "team_phase_route_value.csv"
    team_phase_summary.to_csv(team_phase_output, index=False)

    audit = {
        "grain": (
            "One successful PASS or DRIBBLE event with valid dynamic "
            "start/end packing zones and a matching action-level pxT KPI."
        ),
        "raw_events_scanned": total_events,
        "eligible_successful_actions": len(candidates),
        "valued_route_events": len(routes),
        "unvalued_eligible_actions": len(candidates) - len(routes),
        "excluded_not_pass_or_dribble": excluded_action_type,
        "excluded_not_successful": excluded_not_successful,
        "excluded_missing_end_packing_zone": excluded_no_end_zone,
        "pxt_duplicate_rows_ignored": pxt_duplicates,
        "bypass_conflicting_events_excluded_from_bypass_averages": (
            bypass_conflicts
        ),
        "minimum_route_volume": args.min_actions,
    }

    audit_output = output_dir / "stage3_route_packing_audit.json"

    with audit_output.open("w", encoding="utf-8") as file:
        json.dump(audit, file, indent=2)

    print("\nStage 3 completed.")
    print(f"Valued action routes: {len(routes):,}")
    print(
        "Transition routes with at least "
        f"{args.min_actions} actions: {len(transition_routes_minimum):,}"
    )
    print(f"\nPrimary file to inspect:\n{transition_routes_output}")


if __name__ == "__main__":
    main()