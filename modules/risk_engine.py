from dataclasses import dataclass

from models import RiskAssessment


@dataclass(frozen=True)
class RiskResult:
    score: int
    level: str


def classify_score(score):
    if type(score) is not int or not 1 <= score <= 25:
        raise ValueError("Risk score must be an integer from 1 to 25.")
    for upper_bound, level in ((4, "Low"), (9, "Medium"), (16, "High"), (25, "Critical")):
        if score <= upper_bound:
            return level


def calculate_risk(likelihood, impact):
    for label, value in (("Likelihood", likelihood), ("Impact", impact)):
        if type(value) is not int or not 1 <= value <= 5:
            raise ValueError(f"{label} must be an integer from 1 to 5.")
    score = likelihood * impact
    return RiskResult(score, classify_score(score))


def build_assessment(kind, likelihood, impact, **mitigation):
    result = calculate_risk(likelihood, impact)
    return RiskAssessment(kind=kind, likelihood=likelihood, impact=impact,
                          score=result.score, level=result.level, **mitigation)
