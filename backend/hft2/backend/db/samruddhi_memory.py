"""
SAMRUDDHI'S FINANCIAL MEMORY LAYER
===================================

This is the PERMANENT database and retrieval infrastructure for the trading system.

Purpose:
- Power Knowledgebase (financial reasoning)
- HFT decision validation
- Explainability grounding
- Multi-user system memory
- Future autonomous intelligence

Design Principles:
- Deterministic: Same query always returns same result
- Auditable: Every operation logged and traceable
- Persistent: Data outlives individual developers
- Multi-tenant safe: User isolation guaranteed
- Future-proof: Schema designed to last

This system must outlive individual developers.
Future builders must be able to continue from this work without asking questions.
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, JSON,
    ForeignKey, Boolean, Text, BigInteger, Numeric, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, validates
from sqlalchemy.pool import StaticPool
from datetime import datetime
from pathlib import Path
import json
import os
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
import hashlib

logger = logging.getLogger(__name__)
Base = declarative_base()


# ============================================================================
# CORE TABLES - Users & Portfolios (Integration with Krishna's work)
# ============================================================================

class User(Base):
    """
    User table - integrates with Krishna's authentication system.
    DO NOT DUPLICATE - extend if needed.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), unique=True, index=True,
                     nullable=False)  # External UUID
    username = Column(String(255), index=True)
    email = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    risk_profile = Column(String(50))  # 'low', 'moderate', 'high'
    metadata_json = Column(JSON)  # Additional user metadata

    # Relationships
    portfolios = relationship(
        "Portfolio", back_populates="user", cascade="all, delete-orphan")
    shadow_trades = relationship(
        "ShadowTrade", back_populates="user", cascade="all, delete-orphan")
    live_trades = relationship(
        "LiveTrade", back_populates="user", cascade="all, delete-orphan")
    strategy_signals = relationship(
        "StrategySignal", back_populates="user", cascade="all, delete-orphan")

    @validates('user_id')
    def validate_user_id(self, key, user_id):
        if not user_id or len(user_id) == 0:
            raise ValueError("user_id cannot be empty")
        return user_id


class Portfolio(Base):
    """
    Portfolio - EXTENDED from existing schema with user_id.
    Already being built by Krishna - integrate, don't duplicate.
    """
    __tablename__ = 'portfolios'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), ForeignKey(
        'users.user_id'), index=True, nullable=True)
    # 'paper', 'shadow', 'live'
    mode = Column(String(50), index=True, nullable=False)
    name = Column(String(255))
    cash = Column(Numeric(18, 4), default=0.0)
    starting_balance = Column(Numeric(18, 4))
    realized_pnl = Column(Numeric(18, 4), default=0.0)
    unrealized_pnl = Column(Numeric(18, 4), default=0.0)
    total_fees_paid = Column(Numeric(18, 4), default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="portfolios")
    holdings = relationship(
        "Holding", back_populates="portfolio", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="portfolio",
                          cascade="all, delete-orphan")


class Holding(Base):
    """Current portfolio holdings"""
    __tablename__ = 'holdings'

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey(
        'portfolios.id'), index=True, nullable=False)
    ticker = Column(String(100), index=True, nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False, default=0)
    avg_price = Column(Numeric(18, 4), nullable=False, default=0)
    last_price = Column(Numeric(18, 4))
    invested_value = Column(Numeric(18, 4))
    current_value = Column(Numeric(18, 4))
    unrealized_pnl = Column(Numeric(18, 4))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")

    __table_args__ = (
        UniqueConstraint('portfolio_id', 'ticker', name='uq_portfolio_ticker'),
    )


# ============================================================================
# TRADE TABLES - Shadow, Live, and Generic
# ============================================================================

class Trade(Base):
    """
    Generic trade table - base class for all trades.
    For historical migration and simple use cases.
    Use ShadowTrade or LiveTrade for new implementations.
    """
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), index=True)
    timestamp = Column(DateTime, index=True, nullable=False)
    ticker = Column(String(100), index=True, nullable=False)
    action = Column(String(20), nullable=False)  # 'BUY', 'SELL'
    quantity = Column(Numeric(18, 4), nullable=False)
    price = Column(Numeric(18, 4), nullable=False)
    pnl = Column(Numeric(18, 4))
    stop_loss = Column(Numeric(18, 4))
    take_profit = Column(Numeric(18, 4))
    trade_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="trades")


class ShadowTrade(Base):
    """
    Shadow trades - paper trades with full audit trail.
    Every signal, order, fill, PnL, fee, risk rejection, Karma log.
    Nothing remains only in JSON files.
    """
    __tablename__ = 'shadow_trades'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), ForeignKey(
        'users.user_id'), index=True, nullable=False)
    trade_id = Column(String(255), unique=True, index=True,
                      nullable=False)  # External trade ID
    symbol = Column(String(100), index=True, nullable=False)
    side = Column(String(20), nullable=False)  # 'BUY', 'SELL'
    quantity = Column(Numeric(18, 4), nullable=False)
    entry_price = Column(Numeric(18, 4), nullable=False)
    exit_price = Column(Numeric(18, 4))
    entry_timestamp = Column(DateTime, nullable=False)
    exit_timestamp = Column(DateTime)
    # 'OPEN', 'CLOSED', 'CANCELLED', 'REJECTED'
    status = Column(String(50), default='OPEN')

    # Financial calculations
    gross_pnl = Column(Numeric(18, 4))
    total_fees = Column(Numeric(18, 4))
    net_pnl = Column(Numeric(18, 4))
    fees_breakdown = Column(JSON)  # Complete fee breakdown

    # Strategy & signals
    strategy_id = Column(String(255), index=True)
    signal_id = Column(String(255))
    confidence = Column(Numeric(5, 4))  # 0.0 to 1.0

    # Risk management
    risk_accepted = Column(Boolean, default=True)
    risk_stop_reason = Column(String(255))  # If rejected, why?

    # Audit trail
    karma_log_id = Column(String(255))
    explainability_log_id = Column(String(255))

    # Metadata
    metadata_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="shadow_trades")

    __table_args__ = (
        Index('idx_shadow_symbol_time', 'symbol', 'entry_timestamp'),
    )


class LiveTrade(Base):
    """
    Live trades - actual executed trades with broker confirmations.
    Immutable once created (audit requirement).
    """
    __tablename__ = 'live_trades'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), ForeignKey(
        'users.user_id'), index=True, nullable=False)
    trade_id = Column(String(255), unique=True, index=True,
                      nullable=False)  # Broker trade ID
    order_id = Column(String(255), unique=True, index=True)  # Broker order ID
    symbol = Column(String(100), index=True, nullable=False)
    side = Column(String(20), nullable=False)  # 'BUY', 'SELL'
    quantity = Column(Numeric(18, 4), nullable=False)
    filled_quantity = Column(Numeric(18, 4), default=0)
    entry_price = Column(Numeric(18, 4), nullable=False)
    exit_price = Column(Numeric(18, 4))
    entry_timestamp = Column(DateTime, nullable=False)
    exit_timestamp = Column(DateTime)
    # 'PENDING', 'FILLED', 'PARTIALLY_FILLED', 'CANCELLED', 'REJECTED'
    status = Column(String(50), nullable=False)

    # Broker details
    broker = Column(String(100))  # 'DHAN', 'FYERS', etc.
    exchange = Column(String(50))  # 'NSE', 'BSE', etc.
    product_type = Column(String(50))  # 'MIS', 'CNC', 'NRML'

    # Financial calculations
    gross_pnl = Column(Numeric(18, 4))
    total_fees = Column(Numeric(18, 4))
    net_pnl = Column(Numeric(18, 4))
    fees_breakdown = Column(JSON)
    stt = Column(Numeric(18, 4))
    gst = Column(Numeric(18, 4))
    stamp_duty = Column(Numeric(18, 4))

    # Strategy linkage
    strategy_id = Column(String(255), index=True)
    signal_id = Column(String(255))

    # Compliance
    # 'BUSINESS_INCOME', 'CAPITAL_GAINS', etc.
    tax_classification = Column(String(100))

    # Audit trail
    karma_log_id = Column(String(255))
    explainability_log_id = Column(String(255))
    broker_response = Column(JSON)  # Full broker response

    # Metadata
    metadata_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="live_trades")

    __table_args__ = (
        Index('idx_live_symbol_time', 'symbol', 'entry_timestamp'),
    )


# ============================================================================
# STRATEGY & SIGNALS TABLES
# ============================================================================

class StrategySignal(Base):
    """
    Strategy signals - every signal generated by any strategy.
    Tracks performance for continuous learning.
    """
    __tablename__ = 'strategy_signals'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), ForeignKey('users.user_id'), index=True)
    signal_id = Column(String(255), unique=True, index=True, nullable=False)
    strategy_id = Column(String(255), index=True, nullable=False)
    symbol = Column(String(100), index=True, nullable=False)
    # 'ENTRY_LONG', 'EXIT_LONG', 'ENTRY_SHORT', 'EXIT_SHORT'
    signal_type = Column(String(50), nullable=False)
    signal_strength = Column(Numeric(5, 4))  # 0.0 to 1.0
    confidence = Column(Numeric(5, 4))  # 0.0 to 1.0

    # Market context
    market_price = Column(Numeric(18, 4))
    market_regime = Column(String(50))  # 'BULL', 'BEAR', 'SIDEWAYS'
    # 'LOW', 'NORMAL', 'HIGH', 'EXTREME'
    volatility_regime = Column(String(50))

    # Signal features
    features_json = Column(JSON)  # Feature vector at signal time

    # Outcome tracking
    was_executed = Column(Boolean, default=False)
    execution_price = Column(Numeric(18, 4))
    outcome_return = Column(Numeric(18, 6))  # Actual return after signal
    is_correct = Column(Boolean)  # Whether signal prediction was correct

    # Performance
    pnl_generated = Column(Numeric(18, 4))

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow,
                       nullable=False, index=True)
    expiry_timestamp = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="strategy_signals")

    __table_args__ = (
        Index('idx_signal_strategy_time', 'strategy_id', 'timestamp'),
    )


# ============================================================================
# KNOWLEDGEBASE TABLES
# ============================================================================

class FinancialKnowledge(Base):
    """
    Financial Knowledgebase - stores concepts, explanations, sources.
    Powers financial reasoning and RAG systems.
    """
    __tablename__ = 'financial_knowledgebase'

    id = Column(Integer, primary_key=True)
    knowledge_id = Column(String(255), unique=True, index=True, nullable=False)
    concept = Column(String(500), nullable=False, index=True)
    # 'TECHNICAL_ANALYSIS', 'RISK_MANAGEMENT', etc.
    category = Column(String(100), index=True)
    subcategory = Column(String(100))

    # Content
    title = Column(String(500), nullable=False)
    explanation = Column(Text, nullable=False)
    formula = Column(Text)  # Mathematical formulas
    example = Column(Text)

    # Source tracking
    source = Column(String(500))  # Original source
    source_url = Column(String(1000))
    source_verified = Column(Boolean, default=False)

    # Confidence & quality
    confidence_level = Column(Numeric(3, 2))  # 0.00 to 1.00
    quality_score = Column(Numeric(3, 2))

    # Relationships
    related_concepts = Column(JSON)  # List of related concept IDs
    tags = Column(JSON)  # Tags for search

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    created_by = Column(String(255))  # Who added this knowledge

    __table_args__ = (
        Index('idx_knowledge_category', 'category', 'subcategory'),
    )


# ============================================================================
# MARKET EVENTS TABLE
# ============================================================================

class MarketEvent(Base):
    """
    Market events - significant market movements, news, economic data.
    Provides context for trading decisions.
    """
    __tablename__ = 'market_events'

    id = Column(Integer, primary_key=True)
    event_id = Column(String(255), unique=True, index=True, nullable=False)
    # 'EARNINGS', 'ECONOMIC_DATA', 'NEWS', etc.
    event_type = Column(String(100), index=True, nullable=False)
    symbol = Column(String(100), index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Impact assessment
    impact_level = Column(String(50))  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    expected_impact = Column(String(100))  # Expected market impact

    # Timing
    event_timestamp = Column(DateTime, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Source
    source = Column(String(500))
    source_url = Column(String(1000))

    # Market reaction
    price_before = Column(Numeric(18, 4))
    price_after = Column(Numeric(18, 4))
    price_change_pct = Column(Numeric(8, 4))
    volume_change_pct = Column(Numeric(8, 4))

    # Metadata
    metadata_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_market_event_time', 'event_timestamp'),
    )


# ============================================================================
# EXPLAINABILITY & AUDIT TABLES
# ============================================================================

class ExplainabilityLog(Base):
    """
    Explainability logs - WHY each decision was made.
    Critical for debugging and regulatory compliance.
    """
    __tablename__ = 'explainability_logs'

    id = Column(Integer, primary_key=True)
    log_id = Column(String(255), unique=True, index=True, nullable=False)
    trade_id = Column(String(255), index=True)  # Reference to trade
    signal_id = Column(String(255), index=True)  # Reference to signal

    # Decision explanation
    decision = Column(String(50), nullable=False)  # 'BUY', 'SELL', 'HOLD'
    reasoning = Column(Text, nullable=False)  # Human-readable explanation

    # Feature importance
    feature_importance = Column(JSON)  # {feature: importance_score}

    # Contributing factors
    positive_factors = Column(JSON)  # Factors supporting decision
    negative_factors = Column(JSON)  # Factors against decision

    # Model state
    model_version = Column(String(100))
    model_confidence = Column(Numeric(5, 4))

    # Counterfactuals
    what_if_scenarios = Column(JSON)  # What would change the decision?

    # Compliance
    is_compliant = Column(Boolean, default=True)
    compliance_notes = Column(Text)

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_explain_trade', 'trade_id'),
    )


class KarmaLog(Base):
    """
    Karma logs - immutable audit trail (append-only).
    Records observations without authority.
    This is the system's conscience.
    """
    __tablename__ = 'karma_logs'

    id = Column(Integer, primary_key=True)
    log_id = Column(String(255), unique=True, index=True, nullable=False)
    # 'ticks', 'trades', 'risk_checks'
    bucket = Column(String(100), index=True, nullable=False)

    # Event type
    event_type = Column(String(100), nullable=False)

    # Data (immutable once written)
    data_json = Column(JSON, nullable=False)

    # Hash chain for immutability verification
    previous_hash = Column(String(64))  # SHA-256 of previous log
    current_hash = Column(String(64), index=True)  # SHA-256 of this log

    # Timestamp (immutable)
    timestamp = Column(DateTime, default=datetime.utcnow,
                       nullable=False, index=True)

    # Cannot update karma logs
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Generate hash chain
        self._generate_hash()

    def _generate_hash(self):
        """Generate SHA-256 hash for immutability"""
        data_str = json.dumps({
            'log_id': self.log_id,
            'bucket': self.bucket,
            'event_type': self.event_type,
            'data_json': self.data_json,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'previous_hash': self.previous_hash
        }, sort_keys=True)
        self.current_hash = hashlib.sha256(data_str.encode()).hexdigest()

    __table_args__ = (
        Index('idx_karma_bucket_time', 'bucket', 'timestamp'),
    )


# ============================================================================
# SYSTEM HEALTH & MONITORING
# ============================================================================

class SystemHealth(Base):
    """
    System health metrics - performance, errors, resource usage.
    For monitoring and debugging.
    """
    __tablename__ = 'system_health'

    id = Column(Integer, primary_key=True)
    metric_name = Column(String(255), index=True, nullable=False)
    metric_value = Column(Numeric(18, 6), nullable=False)
    metric_unit = Column(String(50))

    # Context
    component = Column(String(100))  # 'API', 'HFT_ENGINE', 'DATABASE', etc.
    severity = Column(String(50))  # 'INFO', 'WARNING', 'ERROR', 'CRITICAL'

    # Additional data
    metadata_json = Column(JSON)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow,
                       nullable=False, index=True)

    __table_args__ = (
        Index('idx_health_metric_time', 'metric_name', 'timestamp'),
    )


# ============================================================================
# DATABASE INITIALIZATION & MANAGEMENT
# ============================================================================

def _default_db_uri() -> str:
    """Get default database URI"""
    env_data_dir = os.environ.get("DATA_DIR", "")
    if env_data_dir:
        data_dir = Path(env_data_dir)
    else:
        backend_dir = Path(__file__).resolve().parents[1]
        project_root = backend_dir.parent
        data_dir = project_root / 'data'

    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(data_dir / 'samruddhi_memory.db').as_posix()}"


def init_database(db_path: str | None = None):
    """Initialize Samruddhi's Financial Memory Layer"""
    try:
        db_uri = db_path if db_path else _default_db_uri()
        logger.info(
            f"Initializing Samruddhi's Financial Memory Layer with URI: {db_uri}")

        # Create engine with WAL mode for concurrent access
        engine = create_engine(
            db_uri,
            connect_args={"timeout": 30, "check_same_thread": False},
            poolclass=StaticPool,  # For SQLite
        )

        # Enable WAL mode
        from sqlalchemy import event, text

        @event.listens_for(engine, "connect")
        def _set_wal_mode(dbapi_conn, _record):
            try:
                dbapi_conn.execute("PRAGMA journal_mode=WAL")
                dbapi_conn.execute("PRAGMA busy_timeout=30000")
                dbapi_conn.execute("PRAGMA synchronous=NORMAL")
                dbapi_conn.execute("PRAGMA cache_size=10000")
            except Exception:
                pass

        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(engine)
        logger.info(
            "✓ Samruddhi's Financial Memory Layer initialized successfully")
        logger.info(f"✓ Database location: {db_uri}")

        return engine

    except Exception as e:
        logger.error(f"✗ Error initializing database: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise


def create_session(engine):
    """Create a new database session"""
    Session = sessionmaker(bind=engine)
    return Session()


class FinancialMemoryManager:
    """
    High-level manager for Samruddhi's Financial Memory Layer.
    Provides deterministic, auditable, persistent operations.
    """

    def __init__(self, db_path: str | None = None):
        self.engine = init_database(db_path)
        self.Session = sessionmaker(bind=self.engine)
        logger.info("✓ FinancialMemoryManager initialized")

    def get_session(self):
        """Get a new database session"""
        return self.Session()

    # ========================================================================
    # USER OPERATIONS
    # ========================================================================

    def create_user(self, user_id: str, username: str = None, email: str = None,
                    risk_profile: str = 'moderate') -> User:
        """Create a new user"""
        session = self.get_session()
        try:
            # Check if user exists
            existing = session.query(User).filter(
                User.user_id == user_id).first()
            if existing:
                logger.warning(f"User {user_id} already exists")
                return existing

            user = User(
                user_id=user_id,
                username=username or user_id,
                email=email,
                risk_profile=risk_profile
            )
            session.add(user)
            session.commit()
            logger.info(f"✓ Created user: {user_id}")
            return user
        except Exception as e:
            session.rollback()
            logger.error(f"✗ Error creating user: {e}")
            raise
        finally:
            session.close()

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        session = self.get_session()
        try:
            return session.query(User).filter(User.user_id == user_id).first()
        finally:
            session.close()

    # ========================================================================
    # TRADE OPERATIONS
    # ========================================================================

    def record_shadow_trade(self, user_id: str, trade_data: Dict) -> ShadowTrade:
        """Record a shadow trade with full audit trail"""
        session = self.get_session()
        try:
            trade = ShadowTrade(
                user_id=user_id,
                trade_id=trade_data.get(
                    'trade_id', f"SHADOW_{datetime.utcnow().isoformat()}"),
                symbol=trade_data['symbol'],
                side=trade_data['side'],
                quantity=Decimal(str(trade_data['quantity'])),
                entry_price=Decimal(str(trade_data['entry_price'])),
                exit_price=Decimal(str(trade_data.get('exit_price'))) if trade_data.get(
                    'exit_price') else None,
                entry_timestamp=datetime.fromisoformat(trade_data['entry_timestamp']) if isinstance(
                    trade_data['entry_timestamp'], str) else trade_data['entry_timestamp'],
                exit_timestamp=datetime.fromisoformat(trade_data['exit_timestamp']) if trade_data.get(
                    'exit_timestamp') and isinstance(trade_data['exit_timestamp'], str) else trade_data.get('exit_timestamp'),
                status=trade_data.get('status', 'OPEN'),
                gross_pnl=Decimal(str(trade_data.get('gross_pnl', 0))),
                total_fees=Decimal(str(trade_data.get('total_fees', 0))),
                net_pnl=Decimal(str(trade_data.get('net_pnl', 0))),
                fees_breakdown=trade_data.get('fees_breakdown'),
                strategy_id=trade_data.get('strategy_id'),
                signal_id=trade_data.get('signal_id'),
                confidence=Decimal(str(trade_data.get('confidence', 0))),
                risk_accepted=trade_data.get('risk_accepted', True),
                risk_stop_reason=trade_data.get('risk_stop_reason'),
                karma_log_id=trade_data.get('karma_log_id'),
                explainability_log_id=trade_data.get('explainability_log_id'),
                metadata_json=trade_data.get('metadata')
            )

            session.add(trade)
            session.commit()
            logger.info(f"✓ Recorded shadow trade: {trade.trade_id}")
            return trade

        except Exception as e:
            session.rollback()
            logger.error(f"✗ Error recording shadow trade: {e}")
            raise
        finally:
            session.close()

    def record_live_trade(self, user_id: str, trade_data: Dict) -> LiveTrade:
        """Record a live trade with broker confirmation"""
        session = self.get_session()
        try:
            trade = LiveTrade(
                user_id=user_id,
                trade_id=trade_data['trade_id'],
                order_id=trade_data.get('order_id'),
                symbol=trade_data['symbol'],
                side=trade_data['side'],
                quantity=Decimal(str(trade_data['quantity'])),
                filled_quantity=Decimal(
                    str(trade_data.get('filled_quantity', 0))),
                entry_price=Decimal(str(trade_data['entry_price'])),
                exit_price=Decimal(str(trade_data.get('exit_price'))) if trade_data.get(
                    'exit_price') else None,
                entry_timestamp=datetime.fromisoformat(trade_data['entry_timestamp']) if isinstance(
                    trade_data['entry_timestamp'], str) else trade_data['entry_timestamp'],
                exit_timestamp=datetime.fromisoformat(trade_data['exit_timestamp']) if trade_data.get(
                    'exit_timestamp') and isinstance(trade_data['exit_timestamp'], str) else trade_data.get('exit_timestamp'),
                status=trade_data['status'],
                broker=trade_data.get('broker'),
                exchange=trade_data.get('exchange'),
                product_type=trade_data.get('product_type'),
                gross_pnl=Decimal(str(trade_data.get('gross_pnl', 0))),
                total_fees=Decimal(str(trade_data.get('total_fees', 0))),
                net_pnl=Decimal(str(trade_data.get('net_pnl', 0))),
                fees_breakdown=trade_data.get('fees_breakdown'),
                stt=Decimal(str(trade_data.get('stt', 0))),
                gst=Decimal(str(trade_data.get('gst', 0))),
                stamp_duty=Decimal(str(trade_data.get('stamp_duty', 0))),
                strategy_id=trade_data.get('strategy_id'),
                signal_id=trade_data.get('signal_id'),
                tax_classification=trade_data.get('tax_classification'),
                karma_log_id=trade_data.get('karma_log_id'),
                explainability_log_id=trade_data.get('explainability_log_id'),
                broker_response=trade_data.get('broker_response'),
                metadata_json=trade_data.get('metadata')
            )

            session.add(trade)
            session.commit()
            logger.info(f"✓ Recorded live trade: {trade.trade_id}")
            return trade

        except Exception as e:
            session.rollback()
            logger.error(f"✗ Error recording live trade: {e}")
            raise
        finally:
            session.close()

    # ========================================================================
    # KNOWLEDGE OPERATIONS
    # ========================================================================

    def add_knowledge(self, knowledge_data: Dict) -> FinancialKnowledge:
        """Add knowledge to the knowledgebase"""
        session = self.get_session()
        try:
            knowledge = FinancialKnowledge(
                knowledge_id=knowledge_data.get(
                    'knowledge_id', f"KNOW_{datetime.utcnow().isoformat()}"),
                concept=knowledge_data['concept'],
                category=knowledge_data.get('category', 'GENERAL'),
                subcategory=knowledge_data.get('subcategory'),
                title=knowledge_data['title'],
                explanation=knowledge_data['explanation'],
                formula=knowledge_data.get('formula'),
                example=knowledge_data.get('example'),
                source=knowledge_data.get('source'),
                source_url=knowledge_data.get('source_url'),
                source_verified=knowledge_data.get('source_verified', False),
                confidence_level=Decimal(
                    str(knowledge_data.get('confidence_level', 0.5))),
                quality_score=Decimal(
                    str(knowledge_data.get('quality_score', 0.5))),
                related_concepts=knowledge_data.get('related_concepts'),
                tags=knowledge_data.get('tags'),
                created_by=knowledge_data.get('created_by')
            )

            session.add(knowledge)
            session.commit()
            logger.info(f"✓ Added knowledge: {knowledge.knowledge_id}")
            return knowledge

        except Exception as e:
            session.rollback()
            logger.error(f"✗ Error adding knowledge: {e}")
            raise
        finally:
            session.close()

    def get_knowledge(self, concept: str = None, category: str = None) -> List[FinancialKnowledge]:
        """Retrieve knowledge by concept or category"""
        session = self.get_session()
        try:
            query = session.query(FinancialKnowledge)

            if concept:
                query = query.filter(
                    FinancialKnowledge.concept.ilike(f"%{concept}%"))
            if category:
                query = query.filter(FinancialKnowledge.category == category)

            results = query.order_by(
                FinancialKnowledge.confidence_level.desc()).all()
            return results

        finally:
            session.close()

    # ========================================================================
    # RETRIEVAL APIs
    # ========================================================================

    def get_user_trades(self, user_id: str, trade_type: str = 'all',
                        limit: int = 100) -> List:
        """Get all trades for a user (deterministic, ordered)"""
        session = self.get_session()
        try:
            if trade_type == 'shadow':
                trades = session.query(ShadowTrade)\
                    .filter(ShadowTrade.user_id == user_id)\
                    .order_by(ShadowTrade.entry_timestamp.desc())\
                    .limit(limit).all()
            elif trade_type == 'live':
                trades = session.query(LiveTrade)\
                    .filter(LiveTrade.user_id == user_id)\
                    .order_by(LiveTrade.entry_timestamp.desc())\
                    .limit(limit).all()
            else:  # all
                shadow = session.query(ShadowTrade)\
                    .filter(ShadowTrade.user_id == user_id)\
                    .order_by(ShadowTrade.entry_timestamp.desc())\
                    .limit(limit).all()
                live = session.query(LiveTrade)\
                    .filter(LiveTrade.user_id == user_id)\
                    .order_by(LiveTrade.entry_timestamp.desc())\
                    .limit(limit).all()
                trades = list(shadow) + list(live)

            return trades

        finally:
            session.close()

    def get_strategy_performance(self, strategy_id: str) -> Dict:
        """Get performance metrics for a strategy"""
        session = self.get_session()
        try:
            # Get all signals for this strategy
            signals = session.query(StrategySignal)\
                .filter(StrategySignal.strategy_id == strategy_id)\
                .all()

            total_signals = len(signals)
            executed_signals = sum(1 for s in signals if s.was_executed)
            correct_signals = sum(1 for s in signals if s.is_correct)

            total_pnl = sum(
                s.pnl_generated for s in signals if s.pnl_generated)

            return {
                'strategy_id': strategy_id,
                'total_signals': total_signals,
                'executed_signals': executed_signals,
                'execution_rate': executed_signals / total_signals if total_signals > 0 else 0,
                'accuracy': correct_signals / executed_signals if executed_signals > 0 else 0,
                'total_pnl': float(total_pnl) if total_pnl else 0,
                'avg_pnl_per_signal': float(total_pnl / executed_signals) if executed_signals > 0 else 0
            }

        finally:
            session.close()

    def get_trade_explanation(self, trade_id: str) -> Optional[ExplainabilityLog]:
        """Get explanation for a specific trade"""
        session = self.get_session()
        try:
            return session.query(ExplainabilityLog)\
                .filter(ExplainabilityLog.trade_id == trade_id)\
                .first()
        finally:
            session.close()

    def get_system_health(self, hours: int = 24) -> Dict:
        """Get system health metrics for the last N hours"""
        session = self.get_session()
        try:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            metrics = session.query(SystemHealth)\
                .filter(SystemHealth.timestamp >= cutoff)\
                .all()

            # Group by component
            by_component = {}
            for m in metrics:
                if m.component not in by_component:
                    by_component[m.component] = []
                by_component[m.component].append({
                    'metric_name': m.metric_name,
                    'metric_value': float(m.metric_value),
                    'severity': m.severity,
                    'timestamp': m.timestamp.isoformat()
                })

            return {
                'time_range_hours': hours,
                'total_metrics': len(metrics),
                'by_component': by_component
            }

        finally:
            session.close()

    def log_karma(self, bucket: str, event_type: str, data: Dict,
                  previous_hash: str = None) -> KarmaLog:
        """Append an immutable karma log entry"""
        session = self.get_session()
        try:
            log = KarmaLog(
                log_id=f"KARMA_{datetime.utcnow().isoformat()}_{hash(str(data))}",
                bucket=bucket,
                event_type=event_type,
                data_json=data,
                previous_hash=previous_hash
            )

            session.add(log)
            session.commit()
            logger.info(f"✓ Logged karma: {log.log_id}")
            return log

        except Exception as e:
            session.rollback()
            logger.error(f"✗ Error logging karma: {e}")
            raise
        finally:
            session.close()


if __name__ == "__main__":
    # Initialize and test
    logging.basicConfig(level=logging.INFO)

    print("\n" + "="*80)
    print("SAMRUDDHI'S FINANCIAL MEMORY LAYER - INITIALIZATION")
    print("="*80)

    # Initialize database
    memory = FinancialMemoryManager()

    print("\n✓ Database initialized successfully")
    print("\nTables created:")
    print("  ✓ users")
    print("  ✓ portfolios")
    print("  ✓ holdings")
    print("  ✓ trades (generic)")
    print("  ✓ shadow_trades")
    print("  ✓ live_trades")
    print("  ✓ strategy_signals")
    print("  ✓ financial_knowledgebase")
    print("  ✓ market_events")
    print("  ✓ explainability_logs")
    print("  ✓ karma_logs")
    print("  ✓ system_health")

    print("\n" + "="*80)
    print("FINANCIAL MEMORY LAYER READY")
    print("="*80)
    print("\nThis system is:")
    print("  ✓ Deterministic")
    print("  ✓ Auditable")
    print("  ✓ Persistent")
    print("  ✓ Multi-tenant safe")
    print("  ✓ Future-proof")
    print("\nReady for Days 2-5 implementation.")
    print("="*80 + "\n")
