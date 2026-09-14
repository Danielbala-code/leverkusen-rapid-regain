"""Build the reproducible rapid-regain label table from Impect event files.

This script writes only a user-local aggregate/label table. Do not commit its output
when it contains event identifiers: the Impect data licence prohibits redistribution.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ELIGIBLE_PHASES = {"IN_POSSESSION", "ATTACKING_TRANSITION"}
ELIGIBLE_ACTIONS = {"PASS", "DRIBBLE"}
STOP_ACTIONS = {"SET_PIECE", "FOUL", "OFFSIDE", "OUT"}

def records(path: Path):
    with path.open(encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return data
    for key in ("events", "data", "items"):
        if isinstance(data, dict) and isinstance(data.get(key), list):
            return data[key]
    return [data] if isinstance(data, dict) else []

def sort_key(event):
    return (int(event.get("periodId") or 0), int(event.get("sequenceIndex") or event.get("index") or 0))

def classify(events, i, team_id, max_steps):
    """Return regain=1, stabilised=0, or None for a censored chain."""
    for event in events[i + 1 : i + 1 + max_steps]:
        action = str(event.get("actionType") or "")
        if action in STOP_ACTIONS or event.get("phase") == "SET_PIECE":
            return None
        owner = str(event.get("currentAttackingSquadId") or "")
        if owner == team_id:
            return 1
        if owner and owner != team_id and event.get("phase") == "IN_POSSESSION":
            return 0
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-steps", type=int, default=80)
    args = parser.parse_args()

    rows = []
    for path in sorted((args.data_root / "data" / "events").glob("events_*.json")):
        events = sorted(records(path), key=sort_key)
        match_id = path.stem.rsplit("_", 1)[-1]
        for i, event in enumerate(events):
            team_id = str(event.get("squadId") or "")
            possession_team = str(event.get("currentAttackingSquadId") or "")
            if not team_id or team_id != possession_team:
                continue
            if event.get("phase") not in ELIGIBLE_PHASES:
                continue
            if event.get("actionType") not in ELIGIBLE_ACTIONS or event.get("result") != "FAIL":
                continue
            outcome = classify(events, i, team_id, args.max_steps)
            if outcome is None:
                continue
            start = event.get("start") or {}
            pressure = event.get("pressure")
            pressure_band = "missing" if pressure is None else ("low" if pressure < 40 else "medium" if pressure < 80 else "high")
            rows.append({
                "match_id": match_id, "team_id": team_id, "rapid_regain": outcome,
                "loss_phase": event.get("phase"), "loss_action_type": event.get("actionType"),
                "start_pitch_position": start.get("pitchPosition"), "start_lane": start.get("lane"),
                "pressure_band": pressure_band,
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["match_id", "team_id", "rapid_regain", "loss_phase", "loss_action_type", "start_pitch_position", "start_lane", "pressure_band"]
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Resolved rapid-regain rows: {len(rows):,}")

if __name__ == "__main__":
    main()
