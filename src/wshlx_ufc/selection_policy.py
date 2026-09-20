from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GateDecision:
    eligible: bool
    reasons: tuple[str, ...] = ()


def evidence_adjusted_confidence(
    confidence_10: float,
    fighter_a_prior_ufc_bouts: int,
    fighter_b_prior_ufc_bouts: int,
) -> float:
    """Cap presentation confidence when UFC evidence is unusually sparse.

    This does not alter the underlying model probability. It prevents a tiny
    UFC sample from being presented as a lock-level selection before the model
    has observed enough promotion-level evidence.
    """
    minimum = min(int(fighter_a_prior_ufc_bouts), int(fighter_b_prior_ufc_bouts))
    cap = 10.0
    if minimum < 2:
        cap = 7.5
    elif minimum < 4:
        cap = 8.0
    return float(min(float(confidence_10), cap))


def research_override_gate(
    *,
    flips_raw_model_side: bool,
    raw_favorite_probability: float,
    material_data_omission: bool = False,
    near_coinflip_ceiling: float = 0.525,
) -> GateDecision:
    """Govern manual/research winner overrides.

    UFC 331 showed that narrative/style rechecks can harm a correct model side.
    Research may always downgrade confidence or turn a pick into a pass. A
    directional flip is reserved for (a) a verified material data omission or
    (b) a genuinely near-coinflip raw model.
    """
    if not flips_raw_model_side:
        return GateDecision(True)
    if material_data_omission:
        return GateDecision(True, ("verified_material_data_omission",))
    if float(raw_favorite_probability) <= float(near_coinflip_ceiling):
        return GateDecision(True, ("raw_model_near_coinflip",))
    return GateDecision(
        False,
        (
            "research_may_downgrade_or_pass_but_not_flip",
            "raw_model_not_near_coinflip",
        ),
    )


def method_bet_gate(
    *,
    winner_probability: float,
    exact_joint_method_probability: float,
    conditional_method_probability: float,
    baseline_top_method: str,
    shadow_top_method: str,
    fighter_a_prior_ufc_bouts: int,
    fighter_b_prior_ufc_bouts: int,
    min_winner_probability: float = 0.60,
    min_joint_probability: float = 0.35,
    min_conditional_probability: float = 0.55,
) -> GateDecision:
    """Eligibility gate for an official winner+method wager.

    The gate is deliberately stricter than merely choosing the largest method
    bucket. It requires side confidence, meaningful exact-outcome mass,
    baseline/shadow agreement, and an additional sparse-sample safeguard.
    """
    reasons: list[str] = []
    if float(winner_probability) < min_winner_probability:
        reasons.append("winner_probability_below_gate")
    if float(exact_joint_method_probability) < min_joint_probability:
        reasons.append("exact_joint_method_probability_below_gate")
    if float(conditional_method_probability) < min_conditional_probability:
        reasons.append("conditional_method_probability_below_gate")
    if str(baseline_top_method).upper() != str(shadow_top_method).upper():
        reasons.append("baseline_shadow_method_disagreement")

    minimum = min(int(fighter_a_prior_ufc_bouts), int(fighter_b_prior_ufc_bouts))
    if minimum < 2 and float(exact_joint_method_probability) < 0.65:
        reasons.append("sparse_ufc_sample_requires_exceptional_exact_method_mass")

    return GateDecision(not reasons, tuple(reasons))


def timing_bet_gate(
    *,
    model_probability: float,
    market_break_even_probability: float,
    research_conflict: bool = False,
    minimum_probability_edge: float = 0.12,
) -> GateDecision:
    """Promotion gate for O/U, GTD and round-start wagers.

    UFC 331 timing leans went 5-7 and the promoted timing wagers were too
    permissive. Small theoretical edges are no longer enough to promote a
    timing bet, especially when current-form research conflicts with the
    survival model.
    """
    reasons: list[str] = []
    edge = float(model_probability) - float(market_break_even_probability)
    if edge < minimum_probability_edge:
        reasons.append("timing_probability_edge_below_gate")
    if research_conflict:
        reasons.append("research_conflicts_with_timing_model")
    return GateDecision(not reasons, tuple(reasons))
