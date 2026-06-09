def build_features(
    amount: float,
    tx_count: int,
    country: str,
    previous_country: str | None,
    previous_amount: float | None
):

    country_risk = int(
        country in ["IR", "KP", "NG"]
    )

    country_changed = int(
        previous_country is not None
        and previous_country != country
    )

    amount_spike = 0

    if (
        previous_amount is not None
        and amount > previous_amount * 10
    ):
        amount_spike = 1

    return [
        amount,
        tx_count,
        country_risk,
        country_changed,
        amount_spike
    ]