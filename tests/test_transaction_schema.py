import pytest
from pydantic import ValidationError

from tests.helpers import load_module


transaction_schema_module = load_module(
    "api_gateway_transaction_schema",
    "services/api-gateway/app/schemas/transaction.py"
)

TransactionCreate = transaction_schema_module.TransactionCreate


def test_transaction_schema_normalizes_codes():
    payload = TransactionCreate(
        user_id=7,
        amount=10.5,
        currency="usd",
        country="uz",
        device_type="ios"
    )

    assert payload.currency == "USD"
    assert payload.country == "UZ"


def test_transaction_schema_rejects_invalid_amount():
    with pytest.raises(ValidationError):
        TransactionCreate(
            user_id=7,
            amount=0,
            currency="USD",
            country="US",
            device_type="ios"
        )
