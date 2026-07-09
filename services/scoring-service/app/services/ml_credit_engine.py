import pandas as pd

from app.services.model_loader import model_loader


def build_features(
    *,
    age,
    monthly_income,
    existing_debt,
    credit_history_months,
    delinquency_count,
    utilization_ratio,
    active_loans
):
    debt_to_income_ratio = (
        existing_debt / monthly_income
        if monthly_income > 0
        else 1.0
    )

    return pd.DataFrame([
        {
            "age": age,
            "monthly_income": monthly_income,
            "existing_debt": existing_debt,
            "credit_history_months": credit_history_months,
            "delinquency_count": delinquency_count,
            "utilization_ratio": utilization_ratio,
            "active_loans": active_loans,
            "debt_to_income_ratio": debt_to_income_ratio
        }
    ])


def probability_to_credit_score(
    repayment_probability: float
) -> float:
    return round(
        300.0 + (550.0 * repayment_probability),
        2
    )


def get_score_band(
    credit_score: float
) -> str:
    if credit_score >= 750:
        return "EXCELLENT"

    if credit_score >= 680:
        return "GOOD"

    if credit_score >= 600:
        return "FAIR"

    return "HIGH_RISK"


def score_credit(
    *,
    age,
    monthly_income,
    existing_debt,
    credit_history_months,
    delinquency_count,
    utilization_ratio,
    active_loans
):
    features = build_features(
        age=age,
        monthly_income=monthly_income,
        existing_debt=existing_debt,
        credit_history_months=credit_history_months,
        delinquency_count=delinquency_count,
        utilization_ratio=utilization_ratio,
        active_loans=active_loans
    )
    repayment_probability = model_loader.predict_probability(
        features
    )
    credit_score = probability_to_credit_score(
        repayment_probability
    )

    return (
        features,
        repayment_probability,
        credit_score,
        get_score_band(credit_score)
    )
