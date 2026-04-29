import numpy as np
import random
import logging
from typing import List, Tuple, Optional, Dict, Union
from collections import deque, namedtuple
from enum import Enum
from pathlib import Path
import pandas as pd

# Lazy imports for torch and sklearn to save memory on startup
torch = None
nn = None
optim = None
F = None
StandardScaler = None

logger = logging.getLogger(__name__)

# Import MODEL_DIR from config
# Assuming backend/config.py is accessible via sys.path or relative import
# We will use a try-except block to handle potential import issues
try:
    from backend.config import MODEL_DIR
except ImportError:
    try:
        from config import MODEL_DIR
    except ImportError:
        # Fallback if config cannot be imported
        MODEL_DIR = Path("models")
        logger.warning(f"Could not import MODEL_DIR from config, using default: {MODEL_DIR}")

def _ensure_torch():
    """Lazy load torch and related modules"""
    global torch, nn, optim, F
    if torch is None:
        import torch as _torch
        import torch.nn as _nn
        import torch.optim as _optim
        import torch.nn.functional as _F
        torch = _torch
        nn = _nn
        optim = _optim
        F = _F

def _ensure_sklearn_scaler():
    """Lazy load StandardScaler"""
    global StandardScaler
    if StandardScaler is None:
        from sklearn.preprocessing import StandardScaler as _StandardScaler
        StandardScaler = _StandardScaler

class Action(Enum):
    """Trading actions"""
    LONG = 0    # Buy/Long position
    SHORT = 1   # Sell/Short position
    HOLD = 2    # Hold position


# Experience tuple for replay buffer
Experience = namedtuple('Experience', ['state', 'action', 'reward', 'next_state', 'done'])


class ReplayBuffer:
    """Experience Replay Buffer for DQN"""
    
    def __init__(self, capacity: int = 10000):
        """Initialize replay buffer"""
        self.buffer = deque(maxlen=capacity)
        self.capacity = capacity
        logger.info(f"ReplayBuffer initialized with capacity: {capacity}")
    
    def push(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool):
        """Add experience to buffer"""
        self.buffer.append(Experience(state, action, reward, next_state, done))
    
    def sample(self, batch_size: int) -> List[Experience]:
        """Sample random batch of experiences"""
        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        return [self.buffer[idx] for idx in indices]
    
    def __len__(self) -> int:
        """Get current size of buffer"""
        return len(self.buffer)


class QNetwork:
    """Wrapper for Q-Network to handle lazy loading of torch.nn.Module"""
    
    def __init__(self, state_size: int, action_size: int, hidden_sizes: List[int] = [256, 128, 64]):
        _ensure_torch()
        self.state_size = state_size
        self.action_size = action_size
        self.hidden_sizes = hidden_sizes
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self._build_model().to(self.device)
        
    def _build_model(self):
        class _Net(nn.Module):
            def __init__(self, state_size, action_size, hidden_sizes):
                super(_Net, self).__init__()
                layers = []
                prev_size = state_size
                for hidden_size in hidden_sizes:
                    layers.append(nn.Linear(prev_size, hidden_size))
                    layers.append(nn.ReLU())
                    layers.append(nn.Dropout(0.2))
                    layers.append(nn.LayerNorm(hidden_size))
                    prev_size = hidden_size
                layers.append(nn.Linear(prev_size, action_size))
                self.network = nn.Sequential(*layers)
                self.apply(self._init_weights)

            def _init_weights(self, module):
                if isinstance(module, nn.Linear):
                    nn.init.xavier_uniform_(module.weight)
                    if module.bias is not None:
                        nn.init.constant_(module.bias, 0)

            def forward(self, state):
                return self.network(state)

        return _Net(self.state_size, self.action_size, self.hidden_sizes)

    def __call__(self, x):
        return self.model(x)
    
    def parameters(self):
        return self.model.parameters()
    
    def state_dict(self):
        return self.model.state_dict()
    
    def load_state_dict(self, state_dict):
        self.model.load_state_dict(state_dict)
        
    def eval(self):
        self.model.eval()
        
    def to(self, device):
        self.model.to(device)
        return self


class DQNTradingAgent:
    """DQN Trading Agent using Deep Reinforcement Learning"""
    
    def __init__(
        self,
        n_features: int,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.995,
        buffer_size: int = 10000,
        batch_size: int = 64,
        target_update_freq: int = 10,
        hidden_sizes: List[int] = [256, 128, 64]
    ):
        """Initialize DQN Agent"""
        _ensure_torch()
        _ensure_sklearn_scaler()
        
        self.n_features = n_features
        self.n_actions = len(Action)
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        
        # Device configuration
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
        # Q-Networks
        # Note: QNetwork wrapper handles lazy loading internally
        self.policy_net = QNetwork(n_features, self.n_actions, hidden_sizes)
        self.target_net = QNetwork(n_features, self.n_actions, hidden_sizes)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        # Optimizer
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        
        # Replay buffer
        self.replay_buffer = ReplayBuffer(buffer_size)
        
        # Training metrics
        self.episode = 0
        self.training_history = {
            'episodes': [],
            'losses': [],
            'rewards': [],
            'epsilon': [],
            'q_values': []
        }
        
        # Performance tracking
        self.cumulative_reward = 0
        self.episode_rewards = []
        
        logger.info(f"DQNTradingAgent initialized with {n_features} features")
    
    def select_action(self, state: np.ndarray, explore: bool = True) -> Tuple[int, float]:
        """Select action using epsilon-greedy policy"""
        if explore and np.random.random() < self.epsilon:
            action = np.random.randint(self.n_actions)
            q_value = 0.0
            return action, q_value
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            # Use policy_net.model directly if using wrapper calling convention, or just call()
            # The wrapper implements __call__ so we can use it like a module
            q_values = self.policy_net(state_tensor)
            action = q_values.argmax().item()
            q_value = q_values.max().item()
        
        return action, q_value
    
    def train_step(self) -> Optional[float]:
        """Perform one training step using experience replay"""
        if len(self.replay_buffer) < self.batch_size:
            return None
        
        experiences = self.replay_buffer.sample(self.batch_size)
        
        states = torch.FloatTensor([e.state for e in experiences]).to(self.device)
        actions = torch.LongTensor([e.action for e in experiences]).to(self.device)
        rewards = torch.FloatTensor([e.reward for e in experiences]).to(self.device)
        next_states = torch.FloatTensor([e.next_state for e in experiences]).to(self.device)
        dones = torch.FloatTensor([e.done for e in experiences]).to(self.device)
        
        current_q_values = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        
        with torch.no_grad():
            next_actions = self.policy_net(next_states).argmax(1)
            next_q_values = self.target_net(next_states).gather(1, next_actions.unsqueeze(1)).squeeze(1)
            target_q_values = rewards + (self.gamma * next_q_values * (1 - dones))
        
        loss = F.smooth_l1_loss(current_q_values, target_q_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), max_norm=1.0)
        self.optimizer.step()
        
        return loss.item()
    
    def train(self, features_df: pd.DataFrame, returns_series: pd.Series, n_episodes: Optional[int] = None) -> Dict:
        """Train the DQN agent on historical data"""
        logger.info(f"Training DQN agent on {len(features_df)} samples...")
        
        X = features_df.fillna(0).values
        returns = returns_series.values
        
        # VALIDATION 1: Check dimensions
        logger.info(f"DQN input dimensions: {X.shape} (samples x features)")
        logger.info(f"Expected features: {self.n_features}")
        
        if X.shape[1] != self.n_features:
            error_msg = f"CRITICAL: Feature dimension mismatch! Expected {self.n_features}, got {X.shape[1]}"
            logger.error(error_msg)
            # Just log error and return empty dict or raise, following original logic
            raise ValueError(error_msg)
        
        # VALIDATION 2: Check if feature_columns are stored
        if not hasattr(self, 'feature_columns') or not self.feature_columns:
            logger.warning("feature_columns not set in DQN agent - this may cause prediction issues")
        
        if len(X) != len(returns):
            min_len = min(len(X), len(returns))
            X = X[:min_len]
            returns = returns[:min_len]
            logger.warning(f"Trimmed data to {min_len} samples to match returns")
        
        _ensure_sklearn_scaler()
        scaler = StandardScaler()
        X_normalized = scaler.fit_transform(X)
        self.scaler = scaler
        
        if n_episodes is None:
            n_episodes = len(X)
        
        losses = []
        episode_rewards = []
        
        for episode in range(n_episodes):
            state = X_normalized[episode]
            actual_return = returns[episode]
            
            action_idx, q_value = self.select_action(state, explore=True)
            action = list(Action)[action_idx]
            
            reward = self._calculate_reward(action, actual_return)
            
            next_state = X_normalized[min(episode + 1, len(X) - 1)]
            done = (episode == len(X) - 1)
            
            self.replay_buffer.push(state, action_idx, reward, next_state, done)
            
            loss = self.train_step()
            if loss is not None:
                losses.append(loss)
            
            episode_rewards.append(reward)
            self.cumulative_reward += reward
            
            if (episode + 1) % self.target_update_freq == 0:
                self.target_net.load_state_dict(self.policy_net.state_dict())
            
            if (episode + 1) % 10 == 0:
                self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
            
            if (episode + 1) % 50 == 0:
                logger.info(f"DQN training progress: episode {episode + 1}/{n_episodes}")
            
            self.episode += 1
        
        self.episode_rewards = episode_rewards
        self.training_history['losses'].extend(losses)
        self.training_history['rewards'].extend(episode_rewards)
        
        final_metrics = self._calculate_performance_metrics()
        
        logger.info("DQN Training Complete")
        logger.info(f"Cumulative reward: {final_metrics['cumulative_reward']:.4f}")
        logger.info(f"Sharpe ratio: {final_metrics['sharpe_ratio']:.4f}")
        
        return final_metrics
    
    def predict(self, features: np.ndarray) -> Tuple[str, float, float]:
        """Predict action for given features"""
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        if hasattr(self, 'scaler'):
            features = self.scaler.transform(features)
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(features).to(self.device)
            q_values = self.policy_net(state_tensor)
            action_idx = q_values.argmax(1).item()
            max_q_value = q_values.max(1).values.item()
        
        action = list(Action)[action_idx]
        
        with torch.no_grad():
            q_values_np = q_values.cpu().numpy()[0]
            q_max = q_values_np.max()
            q_min = q_values_np.min()
            q_spread = q_max - q_min
            
            if q_spread > 0:
                confidence = min(1.0, (q_max - q_values_np.mean()) / (q_spread + 1e-6))
            else:
                confidence = 0.33
        
        return action.name, float(max_q_value), float(confidence)
    
    def _calculate_reward(self, action: Action, actual_return: float) -> float:
        """Calculate reward based on action and actual return"""
        if action == Action.LONG:
            reward = actual_return
        elif action == Action.SHORT:
            reward = -actual_return
        else:  # HOLD
            reward = -0.0001 - abs(actual_return) * 0.1
        
        return reward
    
    def _calculate_performance_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if len(self.episode_rewards) == 0:
            return {
                'total_episodes': 0,
                'cumulative_reward': 0,
                'average_reward': 0,
                'sharpe_ratio': 0,
                'win_rate': 0
            }
        
        rewards = np.array(self.episode_rewards)
        
        total_episodes = len(rewards)
        cumulative_reward = np.sum(rewards)
        average_reward = np.mean(rewards)
        std_reward = np.std(rewards)
        sharpe_ratio = (average_reward / (std_reward + 1e-10)) * np.sqrt(252)
        win_rate = np.sum(rewards > 0) / len(rewards) if len(rewards) > 0 else 0
        
        return {
            'total_episodes': total_episodes,
            'cumulative_reward': round(cumulative_reward, 4),
            'average_reward': round(average_reward, 6),
            'std_reward': round(std_reward, 6),
            'sharpe_ratio': round(sharpe_ratio, 4),
            'win_rate': round(win_rate, 4),
            'epsilon': round(self.epsilon, 4),
            'buffer_size': len(self.replay_buffer)
        }
    
    def save(self, symbol: str, horizon: str = "intraday"):
        """Save DQN agent with horizon suffix"""
        model_path = MODEL_DIR / f"{symbol}_{horizon}_dqn_agent.pt"
        
        checkpoint = {
            'policy_net_state_dict': self.policy_net.state_dict(),
            'target_net_state_dict': self.target_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'episode': self.episode,
            'cumulative_reward': self.cumulative_reward,
            'episode_rewards': self.episode_rewards,
            'training_history': self.training_history,
            'n_features': self.n_features,
            'scaler': self.scaler if hasattr(self, 'scaler') else None,
            'feature_columns': self.feature_columns if hasattr(self, 'feature_columns') else None,
            'horizon': horizon,
            'model_version': 'DQN-v1'
        }
        
        torch.save(checkpoint, model_path)
        logger.info(f"DQN agent saved to {model_path}")
    
    def load(self, symbol: str, horizon: str = "intraday"):
        """Load DQN agent from checkpoint with horizon"""
        model_path = MODEL_DIR / f"{symbol}_{horizon}_dqn_agent.pt"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
        
        # Update n_features from checkpoint to match saved model
        self.n_features = checkpoint['n_features']
        
        # Reinitialize networks with correct dimensions
        hidden_sizes = [256, 128, 64]
        self.policy_net = QNetwork(self.n_features, self.n_actions, hidden_sizes)
        self.target_net = QNetwork(self.n_features, self.n_actions, hidden_sizes)
        
        self.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
        self.target_net.load_state_dict(checkpoint['target_net_state_dict'])
        self.optimizer = optim.Adam(self.policy_net.parameters())
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epsilon = checkpoint['epsilon']
        self.episode = checkpoint['episode']
        self.cumulative_reward = checkpoint['cumulative_reward']
        self.episode_rewards = checkpoint.get('episode_rewards', [])
        self.training_history = checkpoint['training_history']
        
        if checkpoint.get('scaler') is not None:
            self.scaler = checkpoint['scaler']
        
        if checkpoint.get('feature_columns') is not None:
            self.feature_columns = checkpoint['feature_columns']
            logger.info(f"Loaded feature_columns: {len(self.feature_columns)} columns")
        else:
            logger.warning("feature_columns not found in checkpoint - prediction may have dimension mismatch")
        
        # VALIDATION: Ensure feature_columns match n_features
        if hasattr(self, 'feature_columns') and self.feature_columns:
            if len(self.feature_columns) != self.n_features:
                error_msg = f"CHECKPOINT INCONSISTENCY: feature_columns has {len(self.feature_columns)} items but n_features={self.n_features}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        logger.info(f"DQN agent loaded from {model_path}")
        logger.info(f"Loaded with {self.n_features} features")
