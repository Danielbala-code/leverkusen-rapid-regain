# Reproduction guide

## Inputs

Obtain the Bundesliga 2023/24 Impect Open Data release yourself from https://github.com/ImpectAPI/open-data and accept its terms. The label script needs only:

- data/events/events_*.json
- Event fields: id, periodId, sequenceIndex or index, squadId, currentAttackingSquadId, phase, actionType, result, start, pressure.

No data file is supplied in this repository. This is deliberate: the upstream licence forbids redistribution.

## Environment

Python 3.10+; the label script uses only the standard library.

## Rebuild labels

Run:

    python src/stage4_rapid_regain_labels.py --data-root D:/Impect/impect-open-data --output D:/Impect/england-game-model/outputs/rapid_regain_labels.csv

The output is a local-only resolved-loss table. Do not publish it. Expected overall audit totals are 38,602 eligible losses, 31,933 resolved outcomes and 6,669 censored outcomes.

## Model specification

Outcome: regain before the opponent first enters IN_POSSESSION after an eligible loss. Eligible losses are failed PASS or DRIBBLE actions made by the team in possession in IN_POSSESSION or ATTACKING_TRANSITION.

Predictors are all pre-loss: team, loss phase, action type, start pitch position, start lane and pressure band. A partially pooled team-effect logistic model is then fit with zero-centred team effects. pxT, packing and post-loss actions are excluded from the model inputs to prevent target leakage/circularity.

The reported Bayesian result is a conditional Laplace approximation, not MCMC. The aggregate evidence artifact is results/aggregate_results.json.

## Verification checks

- Confirm 306 match event files and 18 teams.
- Check the three overall audit totals above before interpreting a team result.
- Compare Bayer Leverkusen: 1,434 regains from 1,883 resolved losses; raw rate 0.7615507.
- Confirm that no event-level labels, raw data, or derived event tables are pushed to a public remote.


## Fit the partially pooled team effect

Install numpy and pandas, then provide a local team lookup CSV with team_id and team_name:

    python src/fit_hierarchical_team_effect.py --labels D:/Impect/england-game-model/outputs/rapid_regain_labels.csv --team-map D:/Impect/impect-open-data/data/squads/squads_743.csv --team "Bayer Leverkusen" --tau 0.5

If your Impect squad file is JSON rather than a CSV lookup, create a local two-column team_id/team_name lookup first. Run tau values 0.2, 0.5 and 1.0 as the documented sensitivity check. The fit is a conditional Laplace approximation; it is not an MCMC run.
