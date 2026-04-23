from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable


@dataclass(slots=True)
class NisabThresholds:
    base_currency: str = "USD"
    gold_price_per_gram: float = 75.0
    silver_price_per_gram: float = 1.0
    gold_nisab_grams: float = 87.48
    silver_nisab_grams: float = 612.36
    manual_override: bool = False

    @property
    def gold_nisab_value(self) -> float:
        return round(self.gold_nisab_grams * self.gold_price_per_gram, 2)

    @property
    def silver_nisab_value(self) -> float:
        return round(self.silver_nisab_grams * self.silver_price_per_gram, 2)

    @property
    def effective_threshold(self) -> float:
        return min(self.gold_nisab_value, self.silver_nisab_value)


@dataclass(slots=True)
class CalculationInput:
    cash_savings: dict[str, float] = field(default_factory=dict)
    gold_grams: float = 0.0
    gold_karat: int = 24
    silver_grams: float = 0.0
    silver_karat: int = 24
    equities_value: float = 0.0
    business_equity: float = 0.0
    crypto_totals: dict[str, float] = field(default_factory=dict)
    debts_owed_to_you: float = 0.0
    liabilities: float = 0.0
    preferred_currency: str = "USD"
    exchange_rates: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class CalculationResult:
    preferred_currency: str
    nisab_threshold: float
    qualifying_assets: float
    deductible_liabilities: float
    net_assets: float
    zakat_due: float
    above_nisab: bool
    breakdown: dict[str, float]

    def to_dict(self) -> dict:
        return asdict(self)


class ZakatCalculator:
    def __init__(self, nisab: NisabThresholds | None = None, rate_provider: Callable[[str], float] | None = None):
        self.nisab = nisab or NisabThresholds()
        self.rate_provider = rate_provider

    def calculate(self, payload: CalculationInput) -> CalculationResult:
        preferred = payload.preferred_currency.upper()
        cash_total = sum(self._convert(amount, currency, preferred, payload.exchange_rates) for currency, amount in payload.cash_savings.items())
        crypto_total = sum(self._convert(amount, currency, preferred, payload.exchange_rates) for currency, amount in payload.crypto_totals.items())
        gold_value = self._metal_value(payload.gold_grams, payload.gold_karat, self.nisab.gold_price_per_gram)
        silver_value = self._metal_value(payload.silver_grams, payload.silver_karat, self.nisab.silver_price_per_gram)

        qualifying_assets = round(
            cash_total + gold_value + silver_value + payload.equities_value + payload.business_equity + crypto_total + payload.debts_owed_to_you,
            2,
        )
        liabilities = round(payload.liabilities, 2)
        net_assets = round(qualifying_assets - liabilities, 2)

        non_metal_assets = round(
            cash_total + payload.equities_value + payload.business_equity + crypto_total + payload.debts_owed_to_you,
            2,
        )
        gold_meets_weight_nisab = payload.gold_grams >= self.nisab.gold_nisab_grams
        silver_meets_weight_nisab = payload.silver_grams >= self.nisab.silver_nisab_grams

        if non_metal_assets == 0 and gold_value > 0 and silver_value == 0:
            nisab_threshold = round(self.nisab.gold_nisab_value, 2)
            above_nisab = gold_meets_weight_nisab
        elif non_metal_assets == 0 and silver_value > 0 and gold_value == 0:
            nisab_threshold = round(self.nisab.silver_nisab_value, 2)
            above_nisab = silver_meets_weight_nisab
        else:
            nisab_threshold = round(self.nisab.effective_threshold, 2)
            above_nisab = net_assets >= nisab_threshold

        zakat_due = round(net_assets * 0.025, 2) if above_nisab else 0.0

        return CalculationResult(
            preferred_currency=preferred,
            nisab_threshold=nisab_threshold,
            qualifying_assets=qualifying_assets,
            deductible_liabilities=liabilities,
            net_assets=net_assets,
            zakat_due=zakat_due,
            above_nisab=above_nisab,
            breakdown={
                "cash_total": round(cash_total, 2),
                "gold_value": round(gold_value, 2),
                "silver_value": round(silver_value, 2),
                "equities_value": round(payload.equities_value, 2),
                "business_equity": round(payload.business_equity, 2),
                "crypto_total": round(crypto_total, 2),
                "debts_owed_to_you": round(payload.debts_owed_to_you, 2),
            },
        )

    def _convert(self, amount: float, currency: str, preferred: str, exchange_rates: dict[str, float]) -> float:
        currency = currency.upper()
        if currency == preferred:
            return amount
        rate = exchange_rates.get(currency)
        if rate is None and self.rate_provider:
            rate = self.rate_provider(currency)
        if rate is None:
            raise ValueError(f"Missing exchange rate for {currency}")
        return round(amount * rate, 2)

    @staticmethod
    def _metal_value(weight_grams: float, karat: int, price_per_gram: float) -> float:
        purity = max(0.0, min(karat / 24.0, 1.0))
        return round(weight_grams * purity * price_per_gram, 2)
