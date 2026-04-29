"""
Trade State Machine

Enforces explicit state transitions for shadow trades.
NO SKIPPING STATES ALLOWED.
Validates state before each transition.
"""
from enum import Enum
from typing import Optional, List, Dict
from datetime import datetime
from dataclasses import dataclass, field


class TradeState(Enum):
    """
    Explicit trade states with allowed transitions.

    State Flow:
    INIT → SIGNALLED → PENDING_APPROVAL → FILLED_PARTIAL → FILLED_FULL
                                              ↓
                                          EXIT_PENDING → EXITED → LOGGED

    Alternative terminals:
    - CANCELLED (from any non-terminal state)
    - REJECTED (from PENDING_APPROVAL)
    """
    INIT = "INIT"
    SIGNALLED = "SIGNALLED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    FILLED_PARTIAL = "FILLED_PARTIAL"
    FILLED_FULL = "FILLED_FULL"
    EXIT_PENDING = "EXIT_PENDING"
    EXITED = "EXITED"
    LOGGED = "LOGGED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


# Define valid state transitions
VALID_TRANSITIONS: Dict[TradeState, List[TradeState]] = {
    TradeState.INIT: [
        TradeState.SIGNALLED,
        TradeState.CANCELLED
    ],
    TradeState.SIGNALLED: [
        TradeState.PENDING_APPROVAL,
        TradeState.CANCELLED
    ],
    TradeState.PENDING_APPROVAL: [
        TradeState.FILLED_PARTIAL,
        TradeState.FILLED_FULL,
        TradeState.REJECTED,
        TradeState.CANCELLED
    ],
    TradeState.FILLED_PARTIAL: [
        TradeState.FILLED_PARTIAL,  # Another partial fill
        TradeState.FILLED_FULL,
        TradeState.EXIT_PENDING,
        TradeState.CANCELLED
    ],
    TradeState.FILLED_FULL: [
        TradeState.EXIT_PENDING,
        TradeState.CANCELLED
    ],
    TradeState.EXIT_PENDING: [
        TradeState.EXITED,
        TradeState.CANCELLED
    ],
    TradeState.EXITED: [
        TradeState.LOGGED
    ],
    TradeState.LOGGED: [],  # Terminal state - no transitions allowed
    TradeState.CANCELLED: [],  # Terminal state
    TradeState.REJECTED: []  # Terminal state
}

TERMINAL_STATES = {
    TradeState.LOGGED,
    TradeState.CANCELLED,
    TradeState.REJECTED
}


@dataclass
class StateTransition:
    """Records a state transition event."""
    from_state: TradeState
    to_state: TradeState
    timestamp: datetime
    reason: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "metadata": self.metadata
        }


class TradeStateMachine:
    """
    Enforces valid state transitions for shadow trades.

    Usage:
        fsm = TradeStateMachine(trade_id="trade_123")

        # Valid transitions
        fsm.transition_to(TradeState.SIGNALLED, reason="Signal received")
        fsm.transition_to(TradeState.PENDING_APPROVAL, reason="Risk check initiated")
        fsm.transition_to(TradeState.FILLED_FULL, reason="Order filled")

        # Invalid - will raise exception
        fsm.transition_to(TradeState.LOGGED)  # Cannot skip EXITED state
    """

    def __init__(self, trade_id: str, initial_state: TradeState = TradeState.INIT):
        """
        Initialize state machine.

        Args:
            trade_id: Unique trade identifier
            initial_state: Starting state (default: INIT)
        """
        self.trade_id = trade_id
        self._current_state = initial_state
        self._transitions: List[StateTransition] = []
        self._created_at = datetime.now()

    @property
    def current_state(self) -> TradeState:
        """Get current state."""
        return self._current_state

    @property
    def is_terminal(self) -> bool:
        """Check if in terminal state."""
        return self._current_state in TERMINAL_STATES

    @property
    def transition_history(self) -> List[StateTransition]:
        """Get full transition history."""
        return self._transitions.copy()

    def can_transition_to(self, target_state: TradeState) -> bool:
        """
        Check if transition to target state is valid.

        Args:
            target_state: Desired state

        Returns:
            True if transition allowed
        """
        allowed_states = VALID_TRANSITIONS.get(self._current_state, [])
        return target_state in allowed_states

    def transition_to(self, target_state: TradeState, reason: str, metadata: dict = None):
        """
        Attempt to transition to target state.

        Args:
            target_state: Desired state
            reason: Reason for transition
            metadata: Additional context

        Raises:
            ValueError: If transition is invalid
            RuntimeError: If already in terminal state
        """
        # Check if already in terminal state
        if self.is_terminal:
            raise RuntimeError(
                f"Cannot transition from terminal state {self._current_state.value}. "
                f"Trade {self.trade_id} is complete."
            )

        # Validate transition
        if not self.can_transition_to(target_state):
            allowed = VALID_TRANSITIONS.get(self._current_state, [])
            allowed_str = ", ".join(s.value for s in allowed)
            raise ValueError(
                f"Invalid state transition: {self._current_state.value} → {target_state.value}\n"
                f"Allowed transitions from {self._current_state.value}: [{allowed_str}]"
            )

        # Record transition
        transition = StateTransition(
            from_state=self._current_state,
            to_state=target_state,
            timestamp=datetime.now(),
            reason=reason,
            metadata=metadata or {}
        )

        self._transitions.append(transition)
        self._current_state = target_state

    def get_state_duration(self) -> float:
        """
        Get time spent in current state (seconds).

        Returns:
            Duration in seconds
        """
        if not self._transitions:
            return (datetime.now() - self._created_at).total_seconds()

        last_transition = self._transitions[-1]
        return (datetime.now() - last_transition.timestamp).total_seconds()

    def get_transition_chain(self) -> str:
        """
        Get visual representation of state transitions.

        Returns:
            String like "INIT → SIGNALLED → PENDING_APPROVAL"
        """
        if not self._transitions:
            return self._current_state.value

        chain = [self._transitions[0].from_state.value]
        for t in self._transitions:
            chain.append(t.to_state.value)

        return " → ".join(chain)

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "trade_id": self.trade_id,
            "current_state": self._current_state.value,
            "is_terminal": self.is_terminal,
            "state_duration_seconds": self.get_state_duration(),
            "transition_chain": self.get_transition_chain(),
            "transitions": [t.to_dict() for t in self._transitions],
            "created_at": self._created_at.isoformat()
        }


def validate_state_machine_flow(
    states: List[TradeState],
    trade_id: str = "test"
) -> bool:
    """
    Validate a complete state machine flow.

    Args:
        states: List of states in order
        trade_id: Trade ID for error messages

    Returns:
        True if valid flow

    Raises:
        ValueError: If flow is invalid
    """
    if not states:
        return True

    fsm = TradeStateMachine(trade_id=trade_id, initial_state=states[0])

    for i in range(1, len(states)):
        fsm.transition_to(states[i], reason=f"Test transition {i}")

    return True


# Example valid flows
EXAMPLE_VALID_FLOWS = [
    # Normal full flow
    [
        TradeState.INIT,
        TradeState.SIGNALLED,
        TradeState.PENDING_APPROVAL,
        TradeState.FILLED_PARTIAL,
        TradeState.FILLED_FULL,
        TradeState.EXIT_PENDING,
        TradeState.EXITED,
        TradeState.LOGGED
    ],

    # Quick flow (no partial fills)
    [
        TradeState.INIT,
        TradeState.SIGNALLED,
        TradeState.PENDING_APPROVAL,
        TradeState.FILLED_FULL,
        TradeState.EXIT_PENDING,
        TradeState.EXITED,
        TradeState.LOGGED
    ],

    # Cancelled flow
    [
        TradeState.INIT,
        TradeState.SIGNALLED,
        TradeState.CANCELLED
    ],

    # Rejected at risk gate
    [
        TradeState.INIT,
        TradeState.SIGNALLED,
        TradeState.PENDING_APPROVAL,
        TradeState.REJECTED
    ]
]


__all__ = [
    'TradeState',
    'StateTransition',
    'TradeStateMachine',
    'validate_state_machine_flow',
    'TERMINAL_STATES',
    'VALID_TRANSITIONS'
]
