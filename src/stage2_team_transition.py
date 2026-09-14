from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd


# Impect event-KPI definitions
KPI = {
    20: "loss_added_opponents",
    21: "loss_removed_teammates",
    24: "win_removed_opponents",
    25: "win_removed_defenders",
    27: "ball_win_number",
    69: "loss_removed_defenders",
    1409: "pxt_ball_win",
    1421: "opp_pxt_ball_loss",
    1536: "press",
}

PHASES = [
    "ATTACKING_TRANSITION",
    "SECOND_BALL",
    "IN_POSSESSION",
    "SET_PIECE",
]


def load_records(path: Path) -> list[dict]:
    """Load a JSON list or a JSON object containing a list."""
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


def as_string(value):
    if value is None:
        return None
    return str(value)


def main():
    parser = argparse.ArgumentParser(
        description="Build an Impect team transition-value component table."
    )
    parser.add_argument(
        "--data-root",
        default=r"D:\Impect\impect-open-data",
        help="Impect Open Data root folder",
    )
    parser.add_argument(
        "--output-dir",
        default=r"D:\Impect\england-game-model\outputs",
        help="Folder for generated CSV files",
    )
    args = parser.parse_args()

    data_root = Path(args.data_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    events_dir = data_root / "data" / "events"
    event_kpis_dir = data_root / "data" / "events_kpis"
    matches_dir = data_root / "data" / "matches"
    squads_dir = data_root / "data" / "squads"

    if not events_dir.exists():
        raise FileNotFoundError(f"Events folder not found: {events_dir}")

    if not event_kpis_dir.exists():
        raise FileNotFoundError(f"Event-KPI folder not found: {event_kpis_dir}")

    event_files = sorted(events_dir.glob("events_*.json"))
    event_kpi_files = sorted(event_kpis_dir.glob("events_kpis_*.json"))
    match_files = sorted(matches_dir.glob("matches_*.json"))
    squad_files = sorted(squads_dir.glob("squads_*.json"))

    print(f"Event files: {len(event_files)}")
    print(f"Event-KPI files: {len(event_kpi_files)}")
    print(f"Match files: {len(match_files)}")

    # Team-name lookup
    squad_names = {}

    for path in squad_files:
        for squad in load_records(path):
            squad_id = squad.get("id")
            squad_name = squad.get("name")

            if squad_id is not None and squad_name is not None:
                squad_names[str(squad_id)] = squad_name

    # Match ID -> the two competing teams
    match_teams = {}

    for path in match_files:
        for match in load_records(path):
            match_id = match.get("id")

            home_team = match.get("homeSquadId")
            away_team = match.get("awaySquadId")

            if (
                match_id is not None
                and home_team is not None
                and away_team is not None
            ):
                match_teams[str(match_id)] = {
                    str(home_team),
                    str(away_team),
                }

    # Event ID -> event properties needed for attribution
    event_team = {}
    event_match = {}
    event_phase = {}
    event_presser = {}

    for path in event_files:
        # Example: events_122838.json -> match ID 122838.
        # This is necessary because matchId is not inside each event object.
        match_id = path.stem.rsplit("_", 1)[-1]

        for event in load_records(path):
            event_id = event.get("id")

            if event_id is None:
                continue

            event_id = str(event_id)
            event_team[event_id] = as_string(event.get("squadId"))
            event_match[event_id] = match_id
            event_phase[event_id] = event.get("phase")
            event_presser[event_id] = as_string(event.get("pressingPlayerId"))

    # Totals and unique event denominators, by team and metric.
    metric_values = defaultdict(float)
    metric_events = defaultdict(set)

    phase_values = defaultdict(float)
    phase_events = defaultdict(set)

    teams_seen = set()

    for path in event_kpi_files:
        for row in load_records(path):
            event_id = row.get("eventId")
            kpi_id = row.get("kpiId")

            if event_id is None or kpi_id is None:
                continue

            event_id = str(event_id)

            try:
                kpi_id = int(kpi_id)
            except (TypeError, ValueError):
                continue

            if kpi_id not in KPI:
                continue

            actor_team = event_team.get(event_id)

            if actor_team is None:
                continue

            metric = KPI[kpi_id]
            attributed_team = actor_team

            try:
                value = float(row.get("value", 0))
            except (TypeError, ValueError):
                continue

            # For press KPI 1536, row.playerId is the pressing player,
            # while event.squadId is the team on the ball.
            if metric == "press":
                kpi_player = as_string(row.get("playerId"))
                pressing_player = event_presser.get(event_id)

                # Only retain confirmed press attribution.
                if (
                    pressing_player is None
                    or kpi_player != pressing_player
                ):
                    continue

                match_id = event_match.get(event_id)
                teams_in_match = match_teams.get(match_id, set())

                opponent_teams = [
                    team for team in teams_in_match
                    if team != actor_team
                ]

                if len(opponent_teams) != 1:
                    continue

                attributed_team = opponent_teams[0]

            teams_seen.add(attributed_team)

            metric_key = (attributed_team, metric)
            metric_values[metric_key] += value
            metric_events[metric_key].add(event_id)

            phase = event_phase.get(event_id)

            if phase in PHASES:
                phase_key = (attributed_team, metric, phase)
                phase_values[phase_key] += value
                phase_events[phase_key].add(event_id)

    rows = []

    for team_id in sorted(teams_seen, key=int):
        row = {
            "team_id": team_id,
            "team_name": squad_names.get(team_id, f"Unknown team {team_id}"),
        }

        for metric in KPI.values():
            key = (team_id, metric)
            row[f"{metric}_events"] = len(metric_events[key])
            row[metric] = metric_values[key]

        for phase in PHASES:
            phase_suffix = phase.lower()

            for metric in ["pxt_ball_win", "opp_pxt_ball_loss", "press"]:
                key = (team_id, metric, phase)
                row[f"{metric}_{phase_suffix}"] = phase_values[key]
                row[f"{metric}_events_{phase_suffix}"] = len(phase_events[key])

        pxt_win_events = row["pxt_ball_win_events"]
        pxt_loss_events = row["opp_pxt_ball_loss_events"]

        row["transition_net_value"] = (
            row["pxt_ball_win"] - row["opp_pxt_ball_loss"]
        )

        row["pxt_ball_win_per_100_pxt_win_events"] = (
            100 * row["pxt_ball_win"] / pxt_win_events
            if pxt_win_events else None
        )

        row["opp_pxt_ball_loss_per_100_pxt_loss_events"] = (
            100 * row["opp_pxt_ball_loss"] / pxt_loss_events
            if pxt_loss_events else None
        )

        row["win_removed_opponents_per_pxt_win_event"] = (
            row["win_removed_opponents"] / pxt_win_events
            if pxt_win_events else None
        )

        row["win_removed_defenders_per_pxt_win_event"] = (
            row["win_removed_defenders"] / pxt_win_events
            if pxt_win_events else None
        )

        row["loss_added_opponents_per_pxt_loss_event"] = (
            row["loss_added_opponents"] / pxt_loss_events
            if pxt_loss_events else None
        )

        row["loss_removed_teammates_per_pxt_loss_event"] = (
            row["loss_removed_teammates"] / pxt_loss_events
            if pxt_loss_events else None
        )

        rows.append(row)

    output = pd.DataFrame(rows).sort_values(
        "transition_net_value",
        ascending=False,
    )

    output_path = output_dir / "team_transition_value.csv"
    output.to_csv(output_path, index=False)

    print("\nOutput written to:")
    print(output_path)

    print("\nTop-level audit:")
    print(f"Teams: {len(output)}")
    print(f"pxT ball-win events: {int(output['pxt_ball_win_events'].sum())}")
    print(
        "Opponent pxT-loss events: "
        f"{int(output['opp_pxt_ball_loss_events'].sum())}"
    )
    print(f"Confirmed press events: {int(output['press_events'].sum())}")

    print("\nTeam transition-value table:")
    print(
        output[
            [
                "team_name",
                "pxt_ball_win",
                "opp_pxt_ball_loss",
                "transition_net_value",
                "pxt_ball_win_per_100_pxt_win_events",
                "opp_pxt_ball_loss_per_100_pxt_loss_events",
                "press_events",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()