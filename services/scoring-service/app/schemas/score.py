from pydantic import BaseModel


class CreditScoreRequest(BaseModel):
    user_id: int
    age: int
    monthly_income: float
    existing_debt: float
    credit_history_months: int
    delinquency_count: int
    utilization_ratio: float
    active_loans: int


class CreditScoreResponse(BaseModel):
    user_id: int
    credit_score: float
    repayment_probability: float
    score_band: str
