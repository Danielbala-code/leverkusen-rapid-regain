# Methods and mathematical specification

## Unit of analysis

One row is one **resolved eligible own loss**. An action is eligible when: (1) action type is PASS or DRIBBLE, (2) result is FAIL, (3) action owner equals current attacking team, and (4) phase is IN_POSSESSION or ATTACKING_TRANSITION.

Let Y_i = 1 when the original team becomes the attacking team again before the opponent first records an IN_POSSESSION event in the same period; Y_i = 0 when the opponent enters IN_POSSESSION first. Interruptions, period endings and unclassifiable chains are censored rather than forced into either class.

## Context model

For loss i by team j:

    Y_i ~ Bernoulli(p_i)
    logit(p_i) = alpha + beta_phase[phase_i] + beta_action[action_i]
                 + beta_position[position_i] + beta_lane[lane_i]
                 + beta_pressure[pressure_i] + u_j

The context terms are all known at the instant of the loss. Team effect u_j represents residual team tendency after those contexts have been aligned.

## Partial pooling

    u_j ~ Normal(0, tau^2)
    beta_k ~ Normal(0, 1)
    alpha ~ Normal(0, 2.5^2)

Partial pooling matters because teams have different numbers and types of eligible losses. It pulls a noisy team estimate toward the league mean by an amount justified by its information, rather than presenting raw ranking as certainty.

The public result uses a conditional Laplace approximation at three team-effect prior scales: tau = 0.2, 0.5 and 1.0. The Leverkusen contrast remains positive across the checks: OR 1.099–1.106 and P(u_Leverkusen > mean) 0.966–0.970.

## Standardisation

Raw rate answers “what happened in the observed mix of losses?”. Context-standardisation answers “what would be expected if Leverkusen and an equal-team reference had the same distribution of observed pre-loss contexts?”.

The standardised estimate is:

    mean_i p_hat(team = Leverkusen, x_i)

computed over a common context distribution. It is not a causal counterfactual: unmeasured tactical structure and opponent context remain.

## Leakage/circularity controls

pxT, packing, bypass values, subsequent actions and post-loss phases are not predictors. They either describe the aftermath, encode related game-state information, or risk using the provider’s own model to explain the target. They can be used later only as separately labelled descriptive outcomes.

## Interpretation

The model estimates association with a defined event outcome, not a causal effect of counterpressing. The 95% interval for the primary OR narrowly includes 1.0, so the disciplined conclusion is **modest positive evidence**, not a claim of dominance.
