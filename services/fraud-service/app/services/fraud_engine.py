def calculate_fraud_score(
    amount: float,
    country: str,
    tx_count: int,
    previous_country: str | None,
    previous_amount: float | None
):
    score = 0.0

    if (
        previous_amount is not None
        and amount > previous_amount * 10
    ):
        score += 0.3
        
    if amount > 5000:
        score += 0.3

    if amount > 10000:
        score += 0.3

    risky_countries = [
        "NG",
        "KP",
        "IR"
    ]

    if country in risky_countries:
        score += 0.2

    if tx_count > 10:
        score += 0.3

    if tx_count > 20:
        score += 0.5

    if (
        previous_country
        and previous_country != country
    ):
        score += 0.3

    return min(score, 1.0)