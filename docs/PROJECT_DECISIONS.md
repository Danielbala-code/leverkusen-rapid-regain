# Project decision record: from game model to measurable question

## The football starting point

The project began with Bayer Leverkusen 2023/24 as a reference case, not because league-table success proves a tactical mechanism, but because the season provides a concrete game-model hypothesis to interrogate. The tactical reading was: create stable attacking occupation, preserve local support around the ball, and react aggressively after a loss so the opponent cannot establish control.

Thomas Tuchel is relevant as an England-role lens: his teams have repeatedly treated transition control, rest defence, pressure cues and the relationship between possession structure and defensive protection as linked problems. That is a tactical vocabulary for asking better questions; this study makes **no claim** that club behaviour transfers directly to England or represents a Tuchel team.

## What the data can see

Impect event data can locate actions, action type/result, team in possession, algorithmic phase, pressure band, action-level pxT and dynamic packing zones. It cannot directly observe player spacing, cover shadows, individual counterpress assignments, exact time on ball, local numerical support or rest-defence shape.

Therefore the project does not try to prove “Leverkusen counterpressed well”. It tests an observable consequence: after a defined own loss, did the team regain before the opponent established controlled possession?

## Decision path

### Stage 0 — data contract and possession audit

We first tested whether the source could support possession-time rankings. It could not: unknown-possession exposure was too high for whole-match possession-time claims. This is a useful negative result. It stopped the project from building a polished analysis on an invalid denominator.

### Stage 1 — provider semantics

We separated: action owner versus team in possession; attacking transition versus a manually coded counterattack; pxT state versus action-level pxT components; and dynamic packing zones versus literal player positions. This prevented invalid interpretations such as treating all attacking-transition threat as defensive-transition concession.

### Stage 2 — transition-component audit

We audited ball-win, opponent-ball-loss and press attributions. The result is a descriptive component table, not the main answer. In particular, opponent pxT from a team’s own ATTACKING_TRANSITION ball loss is turnover risk during its attack — it is not total threat conceded in opponent transitions.

### Stage 3 — route and packing exploration

We tested whether packing-zone routes could answer the game-model question. A high-volume centre-back/defensive-midfield route mostly represented recycling. A smaller high-value route sample was too sparse to become the headline. This stage was kept as supporting evidence because it established what routes can and cannot tell us.

### Stage 4 — rapid regain after ball loss

We locked the final estimand. This is the point where tactical theory became a measurable event-data question. The target is simple enough to audit and sufficiently close to the game-model consequence to be football-relevant.

## Why this is senior-level work

The value is not a complicated model for its own sake. It is the decision discipline: reject invalid possession claims; distinguish provider constructs; identify circular pxT usage; keep exploratory route work in its correct supporting role; and use partial pooling only after the football question, observation unit and legal pre-loss inputs are fixed.

## Future work

1. Add tracking/video to test local support, distances and rest-defence shape directly.
2. Fit a full MCMC hierarchical model with match-level effects, convergence diagnostics and posterior predictive checks.
3. Repeat in further seasons and competitions before treating the contrast as stable.
4. Add a separate, non-circular pxT annotation of what follows non-regains.
5. Use the framework with England-specific data only after defining an England game-model hypothesis and a comparable event taxonomy.
