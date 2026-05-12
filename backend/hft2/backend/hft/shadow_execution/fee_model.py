from dataclasses import dataclass
from enum import Enum
from typing import Tuple
from hft2.backend.hft.models.trade_event import FeeBreakdown, TradeType
from .tax_model import TaxModel, TaxClassification


class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class CompleteFeeBreakdown:
    """
    Comprehensive fee breakdown for Indian equity trades.
    All values in absolute Rupees.
    """
    brokerage: float
    stt: float                      # Securities Transaction Tax
    exchange_txn_charge: float      # NSE/BSE transaction charge
    sebi_turnover_fee: float        # SEBI turnover fee
    stamp_duty: float               # State stamp duty
    gst: float                      # GST on brokerage + transaction charges
    total_fees: float               # Sum of all fees
    fees_as_bps: float              # Fees as basis points of turnover

    @property
    def summary(self) -> str:
        """Human-readable summary."""
        return (
            f"Total fees: ₹{self.total_fees:.2f} ({self.fees_as_bps:.1f}bps) | "
            f"Brokerage: ₹{self.brokerage:.2f} | "
            f"STT: ₹{self.stt:.2f} | "
            f"GST: ₹{self.gst:.2f}"
        )


class FeeImpactCalculator:
    """
    Calculate total fee impact for intraday and delivery trades.
    Indian market specifics: STT, GST, Stamp Duty, Exchange charges, SEBI fees.

    Rate Card (Zerodha/FYERS standard as of 2024):
    - Brokerage: ₹20 per order or 0.03% (whichever is lower)
    - STT: 0.025% on sell (intraday), 0.1% both sides (delivery)
    - Exchange Txn: 0.00325% (NSE)
    - SEBI: ₹10 per crore (0.0001%)
    - Stamp Duty: 0.003% buy (intraday), 0.015% buy (delivery)
    - GST: 18% on (brokerage + exchange txn + SEBI)
    """

    def __init__(self):
        """Initialize fee calculator with tax model."""
        self.tax_model = TaxModel()

    # Brokerage rates
    BROKERAGE_PCT = 0.0003         # 0.03%
    BROKERAGE_MAX = 20.0           # ₹20 max per order
    BROKERAGE_MIN = 0.01           # Minimum brokerage

    # STT rates - Equity only
    STT_INTRADAY_SELL_PCT = 0.00025   # 0.025% on sell side only
    STT_DELIVERY_BOTH_PCT = 0.001     # 0.1% on both sides
    STT_FUTURES_SELL_PCT = 0.0001     # 0.01% on sell side (F&O)
    STT_OPTIONS_PREMIUM_PCT = 0.0005  # 0.05% on option premium (sell side)

    # Exchange transaction charges
    EXCHANGE_TXN_NSE_PCT = 0.0000325  # 0.00325% (NSE equity)
    EXCHANGE_TXN_FNO_PCT = 0.0000345  # 0.00345% (F&O - NSE)
    EXCHANGE_TXN_CRYPTO_PCT = 0.001   # 0.1% (Crypto exchanges)

    # SEBI turnover fees
    SEBI_TURNOVER_PCT = 0.000001      # ₹10 per crore = 0.0001%

    # Stamp duty (varies by state, using Maharashtra as default)
    STAMP_DUTY_INTRADAY_PCT = 0.00003   # 0.003% on buy side
    STAMP_DUTY_DELIVERY_PCT = 0.00015   # 0.015% on buy side
    STAMP_DUTY_FUTURES_PCT = 0.00003    # 0.003% on buy side
    STAMP_DUTY_OPTIONS_PCT = 0.00003    # 0.003% on premium
    STAMP_DUTY_CRYPTO_PCT = 0.0         # Crypto - varies by jurisdiction

    # GST rate
    GST_PCT = 0.18                    # 18%

    def calculate_complete_breakdown(
        self,
        buy_price: float,
        sell_price: float,
        qty: int,
        trade_type: TradeType
    ) -> CompleteFeeBreakdown:
        """
        Calculate complete fee breakdown for a round-trip trade.

        Args:
            buy_price: Buy execution price
            sell_price: Sell execution price
            qty: Quantity
            trade_type: Trade type (INTRADAY/DELIVERY)

        Returns:
            CompleteFeeBreakdown with all components
        """
        is_intraday = (trade_type == TradeType.EQUITY_INTRADAY)

        # Calculate turnover
        buy_turnover = buy_price * qty
        sell_turnover = sell_price * qty
        total_turnover = buy_turnover + sell_turnover

        # 1. Brokerage (both sides)
        brokerage_buy = min(
            buy_turnover * self.BROKERAGE_PCT, self.BROKERAGE_MAX)
        brokerage_sell = min(
            sell_turnover * self.BROKERAGE_PCT, self.BROKERAGE_MAX)
        brokerage = max(brokerage_buy + brokerage_sell, self.BROKERAGE_MIN * 2)

        # 2. STT
        if is_intraday:
            # Intraday: STT only on sell side
            stt = sell_turnover * self.STT_INTRADAY_SELL_PCT
        else:
            # Delivery: STT on both sides
            stt = (buy_turnover + sell_turnover) * self.STT_DELIVERY_BOTH_PCT

        # 3. Exchange transaction charge
        exchange_txn_charge = total_turnover * self.EXCHANGE_TXN_NSE_PCT

        # 4. SEBI turnover fee
        sebi_turnover_fee = total_turnover * self.SEBI_TURNOVER_PCT

        # 5. Stamp duty (buy side only)
        if is_intraday:
            stamp_duty = buy_turnover * self.STAMP_DUTY_INTRADAY_PCT
        else:
            stamp_duty = buy_turnover * self.STAMP_DUTY_DELIVERY_PCT

        # 6. GST (on brokerage + exchange txn + SEBI)
        gst_base = brokerage + exchange_txn_charge + sebi_turnover_fee
        gst = gst_base * self.GST_PCT

        # Total fees
        total_fees = brokerage + stt + exchange_txn_charge + \
            sebi_turnover_fee + stamp_duty + gst

        # Express as basis points of turnover
        fees_as_bps = (total_fees / total_turnover) * \
            10000 if total_turnover > 0 else 0.0

        return CompleteFeeBreakdown(
            brokerage=brokerage,
            stt=stt,
            exchange_txn_charge=exchange_txn_charge,
            sebi_turnover_fee=sebi_turnover_fee,
            stamp_duty=stamp_duty,
            gst=gst,
            total_fees=total_fees,
            fees_as_bps=fees_as_bps
        )

    def fees_as_bps(self, turnover: float, fees: float) -> float:
        """
        Express fees as basis points of turnover.

        Args:
            turnover: Total turnover
            fees: Total fees

        Returns:
            Fees in basis points
        """
        if turnover == 0:
            return 0.0
        return (fees / turnover) * 10000

    def estimate_fee_impact_for_feature_vector(
        self,
        avg_price: float,
        qty: int,
        trade_type: TradeType = TradeType.EQUITY_INTRADAY
    ) -> float:
        """
        Estimate fee impact in bps for feature vector calculation.
        Uses typical intraday assumptions (2-3 bps typical).

        Args:
            avg_price: Average trade price
            qty: Quantity
            trade_type: Trade type

        Returns:
            Estimated fee impact in basis points
        """
        # Simplified estimation for feature vectors
        # Assumes round-trip trade with typical spread
        estimated_sell_price = avg_price * 1.001  # Assume 10 bps profit target

        breakdown = self.calculate_complete_breakdown(
            buy_price=avg_price,
            sell_price=estimated_sell_price,
            qty=qty,
            trade_type=trade_type
        )

        return breakdown.fees_as_bps

    def calculate_fees_with_tax(
        self,
        buy_price: float,
        sell_price: float,
        qty: int,
        trade_type: TradeType
    ) -> Tuple[CompleteFeeBreakdown, TaxClassification]:
        """
        Calculate complete fees and get tax classification.

        Args:
            buy_price: Buy execution price
            sell_price: Sell execution price
            qty: Quantity
            trade_type: Trade type

        Returns:
            Tuple of (fee_breakdown, tax_classification)
        """
        fee_breakdown = self.calculate_complete_breakdown(
            buy_price=buy_price,
            sell_price=sell_price,
            qty=qty,
            trade_type=trade_type
        )

        tax_class = self.tax_model.classify_trade(trade_type)

        return fee_breakdown, tax_class

    def calculate_fno_fees(
        self,
        buy_premium: float,
        sell_premium: float,
        lot_size: int,
        is_futures: bool = False
    ) -> CompleteFeeBreakdown:
        """
        Calculate fees for F&O trades.

        Args:
            buy_premium: Option premium paid (or futures price)
            sell_premium: Option premium received (or futures sell price)
            lot_size: Lot size (quantity)
            is_futures: True for futures, False for options

        Returns:
            CompleteFeeBreakdown with all components
        """
        # Calculate turnover
        if is_futures:
            # Futures: turnover = (buy_price + sell_price) * lot_size
            buy_turnover = buy_premium * lot_size
            sell_turnover = sell_premium * lot_size
        else:
            # Options: turnover = premium * lot_size (only sell side taxed)
            buy_turnover = 0.0  # No STT on option buy
            sell_turnover = sell_premium * lot_size

        total_turnover = buy_turnover + sell_turnover

        # 1. Brokerage (same as equity)
        brokerage_buy = min(
            buy_turnover * self.BROKERAGE_PCT, self.BROKERAGE_MAX)
        brokerage_sell = min(
            sell_turnover * self.BROKERAGE_PCT, self.BROKERAGE_MAX)
        brokerage = max(brokerage_buy + brokerage_sell, self.BROKERAGE_MIN * 2)

        # 2. STT (different for futures vs options)
        if is_futures:
            # Futures: STT only on sell side at 0.01%
            stt = sell_turnover * self.STT_FUTURES_SELL_PCT
        else:
            # Options: STT on sell side premium at 0.05%
            stt = sell_turnover * self.STT_OPTIONS_PREMIUM_PCT

        # 3. Exchange transaction charge (F&O rate)
        exchange_txn_charge = total_turnover * self.EXCHANGE_TXN_FNO_PCT

        # 4. SEBI turnover fee
        sebi_turnover_fee = total_turnover * self.SEBI_TURNOVER_PCT

        # 5. Stamp duty (on buy side)
        if is_futures:
            stamp_duty = buy_turnover * self.STAMP_DUTY_FUTURES_PCT
        else:
            stamp_duty = buy_turnover * self.STAMP_DUTY_OPTIONS_PCT

        # 6. GST (on brokerage + exchange txn + SEBI)
        gst_base = brokerage + exchange_txn_charge + sebi_turnover_fee
        gst = gst_base * self.GST_PCT

        # Total fees
        total_fees = brokerage + stt + exchange_txn_charge + \
            sebi_turnover_fee + stamp_duty + gst

        # Express as basis points
        fees_as_bps = (total_fees / total_turnover) * \
            10000 if total_turnover > 0 else 0.0

        return CompleteFeeBreakdown(
            brokerage=brokerage,
            stt=stt,
            exchange_txn_charge=exchange_txn_charge,
            sebi_turnover_fee=sebi_turnover_fee,
            stamp_duty=stamp_duty,
            gst=gst,
            total_fees=total_fees,
            fees_as_bps=fees_as_bps
        )

    def calculate_crypto_fees(
        self,
        buy_price: float,
        sell_price: float,
        quantity: float,
        exchange_fee_pct: float = 0.001  # 0.1% typical for crypto
    ) -> CompleteFeeBreakdown:
        """
        Calculate fees for crypto spot trades.

        Args:
            buy_price: Buy price in INR/USD
            sell_price: Sell price in INR/USD
            quantity: Crypto quantity
            exchange_fee_pct: Exchange trading fee (default 0.1%)

        Returns:
            CompleteFeeBreakdown
        """
        buy_turnover = buy_price * quantity
        sell_turnover = sell_price * quantity
        total_turnover = buy_turnover + sell_turnover

        # 1. Trading fee (exchange-specific)
        brokerage = (buy_turnover + sell_turnover) * exchange_fee_pct

        # 2. NO STT for crypto
        stt = 0.0

        # 3. Exchange/network fees
        exchange_txn_charge = total_turnover * self.EXCHANGE_TXN_CRYPTO_PCT

        # 4. Network/gas fees (simplified - would be actual gas cost in production)
        sebi_turnover_fee = 0.0  # No SEBI for crypto

        # 5. NO stamp duty (varies by jurisdiction)
        stamp_duty = 0.0

        # 6. GST on brokerage
        gst = brokerage * self.GST_PCT

        # Total fees
        total_fees = brokerage + stt + exchange_txn_charge + \
            sebi_turnover_fee + stamp_duty + gst

        # Express as basis points
        fees_as_bps = (total_fees / total_turnover) * \
            10000 if total_turnover > 0 else 0.0

        return CompleteFeeBreakdown(
            brokerage=brokerage,
            stt=stt,
            exchange_txn_charge=exchange_txn_charge,
            sebi_turnover_fee=sebi_turnover_fee,
            stamp_duty=stamp_duty,
            gst=gst,
            total_fees=total_fees,
            fees_as_bps=fees_as_bps
        )
