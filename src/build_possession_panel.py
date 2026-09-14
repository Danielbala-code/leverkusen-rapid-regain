"""Build a possession-aware team-match exposure panel from Impect event files."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


SECOND_HALF_OFFSET = 10_000.0


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def corrected_time(event: dict, first_half_end: float) -> float:
    raw_time = event["gameTime"]["gameTimeInSec"]
    if event["periodId"] == 1:
        return raw_time
    if event["periodId"] == 2:
        return first_half_end + raw_time - SECOND_HALF_OFFSET
    raise ValueError(f"Unsupported period: {event['periodId']}")


def event_exposures(events: list[dict]) -> tuple[list[float], int]:
    """Return corrected next-event exposures and count any clock defects."""
    first_half_times = [
        event["gameTime"]["gameTimeInSec"]
        for event in events
        if event["periodId"] == 1
    ]
    if not first_half_times:
        raise ValueError("No first-half events")
    first_half_end = max(first_half_times)
    times = [corrected_time(event, first_half_end) for event in events]
    durations = []
    negative_gaps = 0
    for index, current_time in enumerate(times):
        next_time = times[index + 1] if index + 1 < len(times) else current_time
        gap = next_time - current_time
        if gap < 0:
            negative_gaps += 1
            gap = 0.0
        durations.append(gap)
    return durations, negative_gaps


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    data_root = args.data_root
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    matches = load_json(next((data_root / "data" / "matches").glob("*.json")))
    squads = {
        squad["id"]: squad["name"]
        for squad in load_json(next((data_root / "data" / "squads").glob("*.json")))
    }
    match_meta = {match["id"]: match for match in matches}
    panel = defaultdict(lambda: defaultdict(float))
    audit = defaultdict(int)

    for event_path in sorted((data_root / "data" / "events").glob("*.json")):
        match_id = int(event_path.stem.split("_")[-1])
        events = sorted(load_json(event_path), key=lambda event: event["index"])
        durations, negative_gaps = event_exposures(events)
        audit["negative_clock_gaps"] += negative_gaps

        possessors = [event.get("currentAttackingSquadId") for event in events]
        previous_known = []
        latest_known = None
        for possessor in possessors:
            previous_known.append(latest_known)
            if possessor in squads:
                latest_known = possessor
        next_known = [None] * len(events)
        latest_known = None
        for index in range(len(events) - 1, -1, -1):
            possessor = possessors[index]
            if possessor in squads:
                latest_known = possessor
            next_known[index] = latest_known

        teams = {
            match_meta[match_id]["homeSquadId"],
            match_meta[match_id]["awaySquadId"],
        }
        for team_id in teams:
            panel[(match_id, team_id)]["event_count"] = 0
            panel[(match_id, team_id)]["observed_with_ball_seconds"] = 0.0
            panel[(match_id, team_id)]["imputed_with_ball_seconds"] = 0.0
            panel[(match_id, team_id)]["observed_without_ball_seconds"] = 0.0
            panel[(match_id, team_id)]["imputed_without_ball_seconds"] = 0.0
            panel[(match_id, team_id)]["unknown_possession_seconds"] = 0.0

        for index, (event, duration) in enumerate(zip(events, durations)):
            possessor = event.get("currentAttackingSquadId")
            action_team = event.get("squadId")
            phase = event.get("phase") or "NULL_PHASE"

            if possessor in teams:
                panel[(match_id, possessor)]["observed_with_ball_seconds"] += duration
                panel[(match_id, possessor)][f"observed_with_ball_{phase}_seconds"] += duration
                for other_team in teams - {possessor}:
                    panel[(match_id, other_team)]["observed_without_ball_seconds"] += duration
            elif previous_known[index] == next_known[index] and previous_known[index] in teams:
                imputed_possessor = previous_known[index]
                audit["bracket_imputed_possession_events"] += 1
                panel[(match_id, imputed_possessor)]["imputed_with_ball_seconds"] += duration
                for other_team in teams - {imputed_possessor}:
                    panel[(match_id, other_team)]["imputed_without_ball_seconds"] += duration
            else:
                audit["unknown_possession_events"] += 1
                for team_id in teams:
                    panel[(match_id, team_id)]["unknown_possession_seconds"] += duration

            if action_team in teams:
                panel[(match_id, action_team)]["event_count"] += 1
                panel[(match_id, action_team)][f"action_{event['actionType']}_count"] += 1
            else:
                audit["unknown_action_team_events"] += 1

    rows = []
    for (match_id, team_id), values in sorted(panel.items()):
        observed_seconds = (
            values["observed_with_ball_seconds"]
            + values["observed_without_ball_seconds"]
        )
        assigned_seconds = observed_seconds + (
            values["imputed_with_ball_seconds"]
            + values["imputed_without_ball_seconds"]
        )
        rows.append(
            {
                "match_id": match_id,
                "date": match_meta[match_id]["scheduledDate"],
                "team_id": team_id,
                "team": squads[team_id],
                "observed_with_ball_seconds": round(values["observed_with_ball_seconds"], 3),
                "imputed_with_ball_seconds": round(values["imputed_with_ball_seconds"], 3),
                "observed_without_ball_seconds": round(values["observed_without_ball_seconds"], 3),
                "imputed_without_ball_seconds": round(values["imputed_without_ball_seconds"], 3),
                "unknown_possession_seconds": round(values["unknown_possession_seconds"], 3),
                "possession_pct_observed": round(
                    100 * values["observed_with_ball_seconds"] / observed_seconds, 3
                ) if observed_seconds else None,
                "possession_pct_assigned": round(
                    100 * (values["observed_with_ball_seconds"] + values["imputed_with_ball_seconds"])
                    / assigned_seconds,
                    3,
                ) if assigned_seconds else None,
                "event_count": int(values["event_count"]),
            }
        )

    panel_path = output_dir / "team_match_possession.csv"
    with panel_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    with (output_dir / "clock_and_possession_audit.json").open("w", encoding="utf-8") as handle:
        json.dump(dict(audit), handle, indent=2)

    print(f"Wrote {len(rows)} team-match rows to {panel_path}")
    print(json.dumps(dict(audit), indent=2))


if __name__ == "__main__":
    main()
