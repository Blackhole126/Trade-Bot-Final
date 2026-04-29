from dataclasses import dataclass
from typing import Dict, Optional
from backend.hft.models.trade_event import TradeType


@dataclass
class TaxClassification:
    """
    Tax classification for a trade.
    For explanation and compliance purposes ONLY - not tax advice.
    """
    category: str                   # Income category
    description: str                # Human-readable explanation
    subcategory: str = ""           # Subcategory (optional)
    # Indicative rate (None if slab-dependent)
    tax_rate: Optional[float] = None
    notes: str = ""                 # Additional notes

    @property
    def summary(self) -> str:
        """Concise summary for UI display."""
        return f"{self.category}: {self.description}"


class TaxModel:
    """
    Tax Awareness Layer (Explainable, Not Advisory).

    Maps trade types to income categories for compliance and reporting.
    DOES NOT provide tax advice - only informational.

    Indian Tax Treatment (as of FY 2024-25):
    - Equity Intraday: Speculative Business Income (slab rates)
    - Equity Delivery: Capital Gains (STCG 20% / LTCG 12.5%)
    - F&O: Non-speculative Business Income (slab rates)
    - Crypto: VDA Flat Tax (30% + cess)

    Usage:
        tax_model = TaxModel()
        classification = tax_model.classify_trade(TradeType.EQUITY_INTRADAY)
        print(f"Category: {classification.category}")
    """

    # Tax classifications by trade type
    CLASSIFICATIONS: Dict[TradeType, TaxClassification] = {
        TradeType.EQUITY_INTRADAY: TaxClassification(
            category="BUSINESS_INCOME",
            subcategory="SPECULATIVE_BUSINESS",
            description="Intraday equity trading profits taxed as speculative business income at slab rates",
            notes="Losses can be carried forward for 4 years against speculative gains only",
            tax_rate=None  # Slab-dependent
        ),

        TradeType.EQUITY_DELIVERY: TaxClassification(
            category="CAPITAL_GAINS",
            subcategory="STCG_OR_LTCG",
            description="Delivery trades attract Capital Gains tax based on holding period",
            notes="STCG (20%) if held < 1 year, LTCG (12.5% above ₹1L exemption) if held > 1 year",
            tax_rate=0.20  # STCG rate (LTCG has exemption)
        ),

        TradeType.FUTURES: TaxClassification(
            category="BUSINESS_INCOME",
            subcategory="NON_SPECULATIVE_BUSINESS",
            description="F&O trading profits taxed as non-speculative business income at slab rates",
            notes="Losses can be carried forward for 8 years against any business income",
            tax_rate=None  # Slab-dependent
        ),

        TradeType.OPTIONS: TaxClassification(
            category="BUSINESS_INCOME",
            subcategory="NON_SPECULATIVE_BUSINESS",
            description="Options trading profits taxed as non-speculative business income at slab rates",
            notes="Turnover calculation important for audit limits",
            tax_rate=None  # Slab-dependent
        ),

        TradeType.CRYPTO_SPOT: TaxClassification(
            category="VDA_INCOME",
            subcategory="VIRTUAL_DIGITAL_ASSET",
            description="Crypto/VDA transfers taxed at flat 30% + applicable cess",
            notes="No deduction for expenses (except acquisition cost). Losses cannot be set off.",
            tax_rate=0.30
        ),

        TradeType.CURRENCY_DERIVATIVES: TaxClassification(
            category="BUSINESS_INCOME",
            subcategory="NON_SPECULATIVE_BUSINESS",
            description="Currency derivatives taxed as non-speculative business income",
            notes="Similar treatment to F&O",
            tax_rate=None  # Slab-dependent
        )
    }

    def classify_trade(self, trade_type: TradeType) -> TaxClassification:
        """
        Get tax classification for a trade type.

        Args:
            trade_type: Type of trade

        Returns:
            TaxClassification with category and explanation

        Raises:
            ValueError: If trade type is unknown
        """
        if trade_type not in self.CLASSIFICATIONS:
            return TaxClassification(
                category="UNKNOWN",
                description=f"Unknown trade type: {trade_type.value}",
                notes="Cannot determine tax treatment"
            )

        return self.CLASSIFICATIONS[trade_type]

    def get_tax_summary(self, trade_type: TradeType) -> str:
        """
        Get concise tax summary for a trade type.

        Args:
            trade_type: Trade type

        Returns:
            Human-readable tax summary
        """
        classification = self.classify_trade(trade_type)
        return (
            f"{classification.category} ({classification.subcategory}): "
            f"{classification.description}"
        )

    def explain_tax_treatment(self, trade_type: TradeType) -> str:
        """
        Get detailed tax treatment explanation.

        Args:
            trade_type: Trade type

        Returns:
            Detailed explanation with notes
        """
        classification = self.classify_trade(trade_type)

        explanation = (
            f"Tax Category: {classification.category}\n"
            f"Subcategory: {classification.subcategory}\n"
            f"Treatment: {classification.description}\n"
        )

        if classification.tax_rate is not None:
            explanation += f"Indicative Rate: {classification.tax_rate * 100:.0f}%\n"
        else:
            explanation += "Rate: As per income slab\n"

        if classification.notes:
            explanation += f"Important: {classification.notes}"

        return explanation

    @classmethod
    def get_all_classifications(cls) -> Dict[str, str]:
        """
        Get all trade type classifications as dictionary.
        Useful for documentation/UI.

        Returns:
            Dict mapping trade type names to descriptions
        """
        return {
            tt.value: cls.CLASSIFICATIONS[tt].description
            for tt in TradeType
        }
