"""Conditional Laplace approximation for the rapid-regain team effect.

Input is the local-only CSV made by stage4_rapid_regain_labels.py.
The script fits a logistic model with context fixed effects and partially pooled
team effects, then uses the inverse Hessian as a Laplace covariance approximation.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

CONTEXT = ["loss_phase", "loss_action_type", "start_pitch_position", "start_lane", "pressure_band"]

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--team", default="Bayer Leverkusen")
    parser.add_argument("--team-map", type=Path, help="CSV with team_id,team_name")
    parser.add_argument("--tau", type=float, default=0.5)
    parser.add_argument("--max-iter", type=int, default=100)
    args = parser.parse_args()

    df = pd.read_csv(args.labels)
    if args.team_map:
        names = pd.read_csv(args.team_map)[["team_id", "team_name"]]
        df = df.merge(names, on="team_id", how="left")
        team_col = "team_name"
    else:
        team_col = "team_id"
    if args.team not in set(df[team_col].astype(str)):
        raise ValueError("Requested team not present; supply --team-map or use team_id")

    context = pd.get_dummies(df[CONTEXT].fillna("MISSING"), drop_first=True, dtype=float)
    teams = pd.get_dummies(df[team_col].astype(str), dtype=float)
    X = np.column_stack([np.ones(len(df)), context.to_numpy(), teams.to_numpy()])
    y = df["rapid_regain"].to_numpy(float)
    n_context = 1 + context.shape[1]
    n_team = teams.shape[1]

    # Priors: intercept N(0, 2.5^2), context coefficients N(0,1), team effects N(0,tau^2).
    penalty = np.r_[1 / 2.5**2, np.ones(n_context - 1), np.repeat(1 / args.tau**2, n_team)]
    theta = np.zeros(X.shape[1])
    for _ in range(args.max_iter):
        p = sigmoid(X @ theta)
        w = np.clip(p * (1 - p), 1e-8, None)
        gradient = X.T @ (y - p) - penalty * theta
        hessian = X.T @ (w[:, None] * X) + np.diag(penalty)
        step = np.linalg.solve(hessian, gradient)
        theta_next = theta + step
        if np.max(np.abs(step)) < 1e-8:
            theta = theta_next
            break
        theta = theta_next

    covariance = np.linalg.inv(hessian)
    team_names = list(teams.columns)
    target = team_names.index(str(args.team))
    team_slice = slice(n_context, n_context + n_team)
    effects = theta[team_slice]
    contrast = effects[target] - effects.mean()
    c = np.zeros_like(theta)
    c[n_context + target] = 1
    c[team_slice] -= 1 / n_team
    se = math.sqrt(float(c @ covariance @ c))
    z = contrast / se
    prob_above = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    print({
        "team": str(args.team), "tau": args.tau, "n": int(len(df)),
        "log_odds_contrast": float(contrast), "odds_ratio": float(math.exp(contrast)),
        "or_95_interval": [float(math.exp(contrast - 1.96 * se)), float(math.exp(contrast + 1.96 * se))],
        "posterior_probability_above_equal_team_mean": float(prob_above),
    })

if __name__ == "__main__":
    main()
