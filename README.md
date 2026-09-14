# Transition Security After Ball Loss

**Human-led, AI-assisted research note** using Impect Bundesliga 2023/24 open data.

## Executive result

For Bayer Leverkusen, **76.16%** of resolved eligible open-play failed pass/dribble losses ended in a regain before the opponent established an IN_POSSESSION phase (1,434 of 1,883). After standardising for pre-loss context, the estimated rate was **74.52%** versus an equal-team Bundesliga reference of **72.54%**: a modest difference of about **2 percentage points**.

A hierarchical Bayesian logistic approximation estimated Leverkusen’s team effect at **OR 1.105** versus the equal-team mean, with a 95% interval of **0.996–1.226** and posterior probability **0.970** of being above that reference. This supports an above-average tendency to regain quickly in this defined sample; it is **not** proof of league dominance, a causal explanation of the title, or direct measurement of counterpress intent.

## Research question

> Did Bayer Leverkusen regain possession rapidly after eligible open-play ball losses more often than Bundesliga opponents would be expected to, after accounting for where and how the ball was lost?

This is a team-level, game-model-informed question. It tests an observable consequence that event data can support; it does **not** reconstruct local support, rest defence, player spacing, or a tactical instruction.

## Event-flow diagram

~~~mermaid
flowchart LR
    A[Bundesliga 2023/24<br/>306 matches · 939,200 events] --> B[Eligible own loss<br/>failed PASS or DRIBBLE<br/>open-play phase]
    B -->|38,602 actions| C{What happens next<br/>in the same period?}
    C -->|Original team returns first| D[Rapid regain = 1]
    C -->|Opponent begins IN_POSSESSION first| E[Opponent stabilised = 0]
    C -->|set piece / interruption / timeout / unclear| F[Censored]
    D --> G[31,933 resolved samples<br/>team + pre-loss context model]
    E --> G
~~~

**Eligible loss:** the team in possession failed a pass or dribble during IN_POSSESSION or ATTACKING_TRANSITION.

**Rapid regain:** that same team became the attacking team again before the opponent had an event labelled IN_POSSESSION.

**Censored:** cases ending in a set piece, foul/offside/out, period end, a 30-second timeout, or an unclassifiable chain. Of 38,602 eligible losses, 31,933 resolved into the binary study outcome and 6,669 were censored.

## Results

| Measure | Leverkusen | Bundesliga reference | Meaning |
|---|---:|---:|---|
| Raw rapid-regain rate | 76.16% (1,434/1,883) | 72.55% across all resolved cases | Unadjusted descriptive rate |
| Context-standardised rate | 74.52% | 72.54% equal-team reference | Expected rate after aligning pre-loss context |
| Hierarchical team effect | OR 1.105 | OR 1.000 | Conditional team contrast |
| Posterior uncertainty | 95% OR interval 0.996–1.226 | — | Interval narrowly includes no difference |

The context model used only information available **at the loss**: team, phase, action type, pitch position, lane, and pressure band. No post-loss event, opponent outcome, pxT value, or post-loss phase entered the model.

### Bayesian-prior sensitivity

| Team-effect prior scale | Leverkusen OR | Posterior P(above equal-team mean) |
|---:|---:|---:|
| 0.2 | 1.099 | 0.966 |
| 0.5 (primary) | 1.105 | 0.970 |
| 1.0 | 1.106 | 0.970 |

The conclusion is directionally stable but modest. It does not support a claim that Leverkusen were uniquely elite or that rapid regain caused their results.

## Why pxT is not a model input

pxT is deliberately held back as a **downstream descriptive annotation**, not a predictor of rapid regain. Impect pxT incorporates game-state information including pressure and opponent positioning. Using pxT, packing, or post-loss opponent actions to predict the outcome would be circular: it would allow later information or a related provider model to help explain the regain being studied.

## Method and validity

- **Population:** Bundesliga 2023/24; 306 matches, 18 teams.
- **Grain:** one eligible failed pass/dribble loss; chains remain within their period.
- **Primary model:** context-adjusted logistic baseline plus a conditional Laplace approximation to a Bayesian hierarchical logistic model with partially pooled team effects.
- **Priors:** team effects centre at zero; context coefficients use weak regularisation. Pooling scale checked at 0.2, 0.5, and 1.0.
- **Validation status:** explanatory/descriptive, single-season analysis. Posterior predictive agreement is in-sample, not held-out validation. No calibration or future-season generalisation claim is made.

## What this study can and cannot say

**It can say:** within this explicit event-data definition, Leverkusen were estimated to regain before opponent stabilisation slightly more often than an equal-team Bundesliga reference after pre-loss context adjustment.

**It cannot say:** that every regain was an intentional counterpress; which player created local support; whether team shape caused the regain; whether the mechanism transfers to England; or that this behaviour caused the 2023/24 title.

Limitations:

- Event data cannot observe spacing, cover shadows, exact time on ball, or tactical instructions without tracking/video.
- Only failed passes and dribbles were eligible; duels, aerial contests and loose-ball mechanisms are outside the definition.
- Impect phase labels are algorithmic provider labels, not manual tactical tags.
- One season limits generalisation.
- The Bayesian result is a conditional Laplace approximation, not a full MCMC fit with chain diagnostics.

## Human-led, AI-assisted development

This was not a prompt-to-dashboard exercise. The analyst set the football problem, brought the Leverkusen game-model lens, challenged possession and transition definitions, rejected circular pxT use, and selected the final estimand: **rapid regain after ball loss**.

AI assistance supported repeatable data inspection, code scaffolding, method checks, documentation, and a partly automated workflow. The tactical interpretation, scope decisions, and responsibility for the published research remain human-led.

The exploratory route/packing work was intentionally demoted to supporting material: frequent centre-back/defensive-midfield circulation may be meaningful for retention but does not, by itself, test the counterpress hypothesis. This is why the repository leads with the regain study rather than a weak route ranking.

## Data, attribution and licence boundary

This repository does **not** redistribute Impect data, event files, derived event-level tables, provider documentation, or provider models. Obtain the source independently from the [Impect Open Data repository](https://github.com/ImpectAPI/open-data) and comply with its terms before reproducing the analysis.

Impect is credited as the data provider. The included MIT licence applies **only to original code in this repository**; it does not grant rights to Impect data or documentation.

## Reproduction status

The public research note and methods are published here now. Source scripts will be added from the D: working directory only after local repository permissions allow a clean export; no raw or event-level Impect data will be committed.

## Next responsible extension

Use a full MCMC hierarchical model with a match-level intercept, convergence diagnostics, and out-of-season replication before making stronger comparative claims. Keep pxT as an outcome annotation, not a regain-model input.


## Evidence map

- [Game-model decision record](docs/PROJECT_DECISIONS.md): why the Leverkusen/Tuchel lens led to rapid regain, and why other routes were rejected as headlines.
- [Methods and mathematics](docs/METHODS_AND_MATH.md): target, partial-pooling model, standardisation and circularity controls.
- [Reproduction guide](REPRODUCTION.md): public inputs, expected audits and local command.
- [Aggregate result artifact](results/aggregate_results.json): machine-readable headline result only.
- [Label-construction code](src/stage4_rapid_regain_labels.py): executable event-to-outcome step.

The prior Stage 0–3 audits are documented in the decision record. They are retained as methodological evidence, not presented as equal-status results.
