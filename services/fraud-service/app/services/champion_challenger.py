from app.services.model_loader import challenger_model_loader
from app.services.model_loader import model_loader


def evaluate_model_candidates(
    features
):
    champion_probability = model_loader.predict_probability(
        features
    )
    challenger_probability = None
    probability_delta = None

    if challenger_model_loader.is_enabled:
        challenger_probability = challenger_model_loader.predict_probability(
            features
        )
        probability_delta = abs(
            champion_probability - challenger_probability
        )

    return {
        "champion_probability": champion_probability,
        "challenger_probability": challenger_probability,
        "probability_delta": probability_delta
    }
