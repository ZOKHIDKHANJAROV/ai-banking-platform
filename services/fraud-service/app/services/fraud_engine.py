def calculate_fraud_score(
    amount: float,
    country: str,
    tx_count: int,
    previous_country: str | None
) -> float:

    score = 0.0

    # Большая сумма
    if amount > 5000:
        score += 0.3

    if amount > 10000:
        score += 0.3

    # Рискованные страны
    risky_countries = [
        "NG",  # Nigeria
        "KP",  # North Korea
        "IR"   # Iran
    ]

    if country in risky_countries:
        score += 0.2

    # Частые транзакции
    if tx_count > 10:
        score += 0.3

    if tx_count > 20:
        score += 0.5

    # Смена страны
    if (
        previous_country is not None
        and previous_country != country
    ):
        score += 0.3

    return min(score, 1.0)


def get_risk_level(score: float) -> str:

    if score >= 0.8:
        return "HIGH"

    if score >= 0.5:
        return "MEDIUM"

    return "LOW"