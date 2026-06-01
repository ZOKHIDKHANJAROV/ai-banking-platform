from pydantic import BaseModel


class TransactionCreate(BaseModel):
    user_id: int
    amount: float
    currency: str
    country: str
    device_type: str


class TransactionResponse(TransactionCreate):
    id: int
    status: str

    class Config:
        from_attributes = True