"""Versioned standalone contracts. No model extraction is implied by typed input."""
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator
from backend.models import InvestigationRequest, StrictModel


class ClaimInput(StrictModel):
    id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=4000)
    metric: Literal['revenue', 'diluted_eps', 'net_income', 'net_margin', 'unsupported']
    expected_value_decimal: Decimal | None = Field(default=None, allow_inf_nan=False)
    unit: str = Field(default='USD', max_length=40)
    accounting_basis: Literal['GAAP', 'non-GAAP', 'unknown'] = 'GAAP'
    period_start: date
    period_end: date
    input_kind: Literal['human_assertion'] = 'human_assertion'
    tolerance_decimal: Decimal = Field(default=Decimal('0'), ge=0, allow_inf_nan=False)

    @field_validator('expected_value_decimal', 'tolerance_decimal', mode='before')
    @classmethod
    def decimal_strings(cls, value):
        if value is not None and not isinstance(value, (str, Decimal)):
            raise ValueError('Supply decimal strings, not floating point JSON numbers')
        if value is not None and len(str(value)) > 80:
            raise ValueError('Decimal input exceeds the 80-character bound')
        return value

    @field_validator('expected_value_decimal', 'tolerance_decimal')
    @classmethod
    def bounded_decimals(cls, value):
        if value is not None and (not value.is_finite() or len(value.as_tuple().digits) > 34 or
                                  (value != 0 and abs(value.adjusted()) > 30)):
            raise ValueError('Decimal input requires <=34 digits and adjusted exponent within +/-30')
        return value

    @model_validator(mode='after')
    def valid_claim(self):
        if not self.id.strip() or not self.text.strip() or self.period_start > self.period_end:
            raise ValueError('Claim identity/text and ordered period are required')
        if self.metric != 'unsupported' and self.expected_value_decimal is None:
            raise ValueError('Financial assertions require an expected decimal value')
        if self.expected_value_decimal is not None and self.tolerance_decimal > max(abs(self.expected_value_decimal), Decimal(1)) * Decimal('0.01'):
            raise ValueError('Declared tolerance cannot exceed 1% of expected magnitude (minimum reference magnitude 1)')
        return self


class InvestigationInput(StrictModel):
    request: InvestigationRequest
    claim_inputs: list[ClaimInput] = Field(min_length=1, max_length=3)

    @model_validator(mode='after')
    def unique(self):
        if len({c.id for c in self.claim_inputs}) != len(self.claim_inputs):
            raise ValueError('Claim IDs must be unique')
        if sum(len(c.text) for c in self.claim_inputs) > 12000:
            raise ValueError('Claim text exceeds the shared 12000-character bound')
        return self
