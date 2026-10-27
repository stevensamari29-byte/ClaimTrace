from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from urllib.parse import urlsplit


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Company(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    ticker: str = Field(pattern=r'^[A-Za-z0-9.\-]{1,12}$')
    cik: str = Field(pattern=r'^\d{1,10}$')

    @field_validator('name')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Company name is required')
        return value.strip()


class InvestigationRequest(StrictModel):
    company: Company
    fiscal_year: int = Field(ge=1990, le=2100, strict=True)
    period: Literal['Q1', 'Q2', 'Q3', 'Q4', 'FY']
    as_of: date
    evidence_backend: Literal['sec', 'zetaris'] = 'sec'

    @field_validator('as_of', mode='before')
    @classmethod
    def iso_date(cls, value):
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError('Use YYYY-MM-DD')
        date.fromisoformat(value)
        return value


class Evidence(StrictModel):
    id: str
    document: str
    url: str
    published_at: date
    period_start: date
    period_end: date
    unit: str
    value: float = Field(allow_inf_nan=False)
    value_decimal: str | None = Field(default=None, max_length=80, pattern=r'^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$', description='Exact received numeric representation when retained; does not establish original filing rounding precision.')
    concept: str
    locator: str
    source_mode: Literal['live_sec', 'cached_sec', 'live_zetaris']
    source_sha256: str | None = None

    @field_validator('value_decimal')
    @classmethod
    def bounded_exact_value(cls, value):
        if value is None:
            return value
        try:
            number = Decimal(value)
        except InvalidOperation:
            raise ValueError('Exact evidence value must be a finite decimal') from None
        if (not number.is_finite() or len(number.as_tuple().digits) > 34 or
                (number != 0 and abs(number.adjusted()) > 30)):
            raise ValueError('Exact evidence value requires <=34 digits and adjusted exponent within +/-30')
        return str(number)

    @field_validator('url')
    @classmethod
    def primary_url(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or parsed.hostname not in ('www.sec.gov', 'sec.gov', 'data.sec.gov') or parsed.username or parsed.password:
            raise ValueError('Evidence must link to a primary SEC HTTPS document')
        return value

    @model_validator(mode='after')
    def chronology(self):
        if self.value_decimal is not None and float(Decimal(self.value_decimal)) != self.value:
            raise ValueError('Exact evidence value conflicts with the compatible numeric value')
        if not self.period_start <= self.period_end <= self.published_at:
            raise ValueError('Evidence reporting/publication chronology is invalid')
        return self


class Calculation(StrictModel):
    id: str
    label: str
    formula: str
    value: float = Field(allow_inf_nan=False)
    unit: str
    evidence_ids: list[str]


class Claim(StrictModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_url: str | None = None


class Finding(StrictModel):
    id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    classification: Literal['supported', 'contradicted', 'incomplete', 'unresolved']
    evidence_ids: list[str]
    explanation: str = Field(min_length=1)


class InvestigationResponse(StrictModel):
    company: Company
    fiscal_year: int
    period: str
    as_of: date
    evidence_backend: str
    status: Literal['complete', 'partial', 'blocked']
    evidence: list[Evidence]
    claims: list[Claim]
    calculations: list[Calculation]
    findings: list[Finding]
    limitations: list[str]
    unresolved_questions: list[str]
    human_review_status: Literal['required'] = 'required'
    integration_status: dict[str, str]
