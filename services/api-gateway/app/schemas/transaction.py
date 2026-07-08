from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


class TransactionCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True
    )

    user_id: int
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    country: str = Field(min_length=2, max_length=2)
    device_type: str = Field(min_length=2, max_length=50)

    @field_validator("currency")
    @classmethod
    def normalize_currency(
        cls,
        value: str
    ) -> str:
        return value.upper()

    @field_validator("country")
    @classmethod
    def normalize_country(
        cls,
        value: str
    ) -> str:
        return value.upper()


class TransactionResponse(TransactionCreate):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    status: str
