from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zakat_calculator import CalculationInput, ZakatCalculator, NisabThresholds


def test_cash_only_above_nisab_returns_2_5_percent():
    calculator = ZakatCalculator(
        nisab=NisabThresholds(base_currency="USD", gold_price_per_gram=75.0, silver_price_per_gram=1.0)
    )
    payload = CalculationInput(cash_savings={"USD": 100000}, preferred_currency="USD")

    result = calculator.calculate(payload)

    assert result.zakat_due == 2500.0
    assert result.qualifying_assets == 100000.0
    assert result.above_nisab is True


def test_gold_below_nisab_returns_zero():
    calculator = ZakatCalculator(
        nisab=NisabThresholds(base_currency="USD", gold_price_per_gram=75.0, silver_price_per_gram=1.0)
    )
    payload = CalculationInput(gold_grams=50, gold_karat=24, preferred_currency="USD")

    result = calculator.calculate(payload)

    assert result.zakat_due == 0.0
    assert result.above_nisab is False
