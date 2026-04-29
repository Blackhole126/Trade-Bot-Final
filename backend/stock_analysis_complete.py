"""
Complete Stock Analysis Tool - All-in-One
Fetches and views financial data from Yahoo Finance
Integrated with 50+ Technical Indicators
"""

import sys
import os

# Force unbuffered output for immediate console display
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

import time
import yfinance as yf
import pandas as pd
import numpy as np
import pickle
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List, Union, Tuple
from datetime import datetime, timedelta
from tqdm import tqdm
import pandas_ta_classic as ta
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
import xgboost as xgb
import joblib
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from collections import deque, namedtuple
from enum import Enum
import zipfile
import io
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================================
# CONFIGURATION
# ============================================================================

# Directories
DATA_DIR = Path("data")
DATA_CACHE_DIR = DATA_DIR / "cache"
FEATURE_CACHE_DIR = DATA_DIR / "features"
MODEL_DIR = Path("models")
LOGS_DIR = DATA_DIR / "logs"  # Unified with config.py - all logs in data/logs
NSE_BHAV_CACHE_DIR = DATA_CACHE_DIR / "nse_bhav"  # NSE Bhav Copy cache

# Create directories
DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
FEATURE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
NSE_BHAV_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Historical data period
HISTORICAL_PERIOD = "2y"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prediction log file
PREDICTION_LOG_FILE = LOGS_DIR / "predictions.json"


def get_symbol_cache_path(symbol: str) -> Path:
    """Get cache path for a symbol"""
    return DATA_CACHE_DIR / f"{symbol}_all_data.json"


# Set random seeds for reproducibility
RANDOM_SEED = 42
torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# ============================================================================
# DQN COMPONENTS - REINFORCEMENT LEARNING
# ============================================================================

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


class QNetwork(nn.Module):
    """Deep Q-Network for estimating Q-values"""
    
    def __init__(self, state_size: int, action_size: int, hidden_sizes: List[int] = [256, 128, 64]):
        """Initialize Q-Network"""
        super(QNetwork, self).__init__()
        
        self.state_size = state_size
        self.action_size = action_size
        
        # Build network layers
        layers = []
        prev_size = state_size
        
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.2))
            layers.append(nn.LayerNorm(hidden_size))
            prev_size = hidden_size
        
        # Output layer
        layers.append(nn.Linear(prev_size, action_size))
        
        self.network = nn.Sequential(*layers)
        
        # Initialize weights
        self.apply(self._init_weights)
        
        logger.info(f"QNetwork initialized: {state_size} -> {hidden_sizes} -> {action_size}")
    
    def _init_weights(self, module):
        """Initialize network weights"""
        if isinstance(module, nn.Linear):
            nn.init.xavier_uniform_(module.weight)
            if module.bias is not None:
                nn.init.constant_(module.bias, 0)
    
    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """Forward pass through network"""
        return self.network(state)


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
        self.policy_net = QNetwork(n_features, self.n_actions, hidden_sizes).to(self.device)
        self.target_net = QNetwork(n_features, self.n_actions, hidden_sizes).to(self.device)
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
        
        # IMPORTANT: features_df is ALREADY filtered to contain only technical indicators
        # Do NOT filter again - use all columns as-is
        # The calling function has already ensured we have the right features
        
        X = features_df.fillna(0).values
        returns = returns_series.values
        
        # VALIDATION 1: Check dimensions
        logger.info(f"DQN input dimensions: {X.shape} (samples x features)")
        logger.info(f"Expected features: {self.n_features}")
        logger.info(f"Feature columns in df: {list(features_df.columns)[:5]}... (showing first 5)")
        
        if X.shape[1] != self.n_features:
            error_msg = f"CRITICAL: Feature dimension mismatch! Expected {self.n_features}, got {X.shape[1]}"
            logger.error(error_msg)
            print(f"\n[ERROR] {error_msg}")
            print(f"[ERROR] Expected columns: {self.n_features}")
            print(f"[ERROR] Received columns: {X.shape[1]}")
            print(f"[ERROR] This indicates the feature preparation is inconsistent.")
            print(f"[ERROR] Please ensure StockPricePredictor.get_feature_columns() is used everywhere.")
            raise ValueError(error_msg)
        
        # VALIDATION 2: Check if feature_columns are stored
        if not hasattr(self, 'feature_columns') or not self.feature_columns:
            logger.warning("feature_columns not set in DQN agent - this may cause prediction issues")
            print(f"[WARNING] feature_columns not stored - prediction may fail")
        
        if len(X) != len(returns):
            min_len = min(len(X), len(returns))
            X = X[:min_len]
            returns = returns[:min_len]
            logger.warning(f"Trimmed data to {min_len} samples to match returns")
        
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
            'episode_rewards': self.episode_rewards,  # FIX: Save episode rewards for metrics!
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
        self.policy_net = QNetwork(self.n_features, self.n_actions, hidden_sizes).to(self.device)
        self.target_net = QNetwork(self.n_features, self.n_actions, hidden_sizes).to(self.device)
        
        self.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
        self.target_net.load_state_dict(checkpoint['target_net_state_dict'])
        self.optimizer = optim.Adam(self.policy_net.parameters())
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epsilon = checkpoint['epsilon']
        self.episode = checkpoint['episode']
        self.cumulative_reward = checkpoint['cumulative_reward']
        self.episode_rewards = checkpoint.get('episode_rewards', [])  # FIX: Restore episode rewards!
        self.training_history = checkpoint['training_history']
        
        if checkpoint.get('scaler') is not None:
            self.scaler = checkpoint['scaler']
        
        if checkpoint.get('feature_columns') is not None:
            self.feature_columns = checkpoint['feature_columns']
            logger.info(f"Loaded feature_columns: {len(self.feature_columns)} columns")
        else:
            logger.warning("feature_columns not found in checkpoint - prediction may have dimension mismatch")
            print(f"[WARNING] DQN checkpoint missing feature_columns - may cause issues")
        
        # VALIDATION: Ensure feature_columns match n_features
        if hasattr(self, 'feature_columns') and self.feature_columns:
            if len(self.feature_columns) != self.n_features:
                error_msg = f"CHECKPOINT INCONSISTENCY: feature_columns has {len(self.feature_columns)} items but n_features={self.n_features}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        logger.info(f"DQN agent loaded from {model_path}")
        logger.info(f"Loaded with {self.n_features} features")


# ============================================================================
# ENHANCED DATA INGESTER
# ============================================================================

class EnhancedDataIngester:
    """
    Enhanced data ingester that fetches ALL available yfinance data
    Including: OHLCV, fundamentals, analyst data, ownership, earnings, options, etc.
    """
    
    def __init__(self, cache_dir: Path = DATA_CACHE_DIR):
        """Initialize Enhanced Data Ingester"""
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] EnhancedDataIngester initialized with cache dir: {cache_dir}")
    
    def fetch_live_data(
        self,
        symbols: Union[str, List[str]],
        period: str = HISTORICAL_PERIOD,
        interval: str = "1d",
        retry_count: int = 3,
        backoff_factor: float = 2.0
    ) -> pd.DataFrame:
        """
        Fetch live stock data from Yahoo Finance with exponential backoff
        Falls back to NSE Bhav Copy for Indian stocks if yfinance fails
        
        Args:
            symbols: Stock symbol(s) to fetch
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            retry_count: Number of retry attempts
            backoff_factor: Exponential backoff multiplier
            
        Returns:
            DataFrame with OHLCV data
        """
        if isinstance(symbols, list):
            symbol = symbols[0] if len(symbols) == 1 else " ".join(symbols)
        else:
            symbol = symbols
        
        # Try yfinance first
        for attempt in range(retry_count):
            try:
                print(f"[INFO] Fetching data for {symbol}, period={period}, interval={interval}")
                
                print(f"  -> Connecting to Yahoo Finance API...")
                ticker = yf.Ticker(symbol)
                print(f"  -> Downloading {period} of {interval} data...")
                df = ticker.history(period=period, interval=interval)
                print(f"  -> Download complete! Received {len(df)} rows")
                
                if df.empty:
                    print(f"[WARNING] No data returned for {symbol} from yfinance")
                else:
                    # Validate required columns
                    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                    if not all(col in df.columns for col in required_cols):
                        print(f"[ERROR] Missing required columns for {symbol}")
                    else:
                        # Clean data
                        df = self._clean_data(df)
                        print(f"[INFO] Successfully fetched {len(df)} rows for {symbol} from yfinance")
                        return df
                
            except Exception as e:
                wait_time = backoff_factor ** attempt
                print(f"[WARNING] Attempt {attempt + 1}/{retry_count} failed for {symbol}: {e}")
                
                if attempt < retry_count - 1:
                    print(f"[INFO] Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
        
        # Yfinance failed - try NSE Bhav Copy fallback for Indian stocks
        print(f"[INFO] yfinance failed for {symbol} after {retry_count} attempts")
        
        # Check if this is an Indian stock (.NS or .BO)
        if symbol.endswith('.NS') or symbol.endswith('.BO'):
            # Only use NSE fallback for daily data
            if interval == "1d":
                print(f"[INFO] Attempting NSE Bhav Copy fallback for {symbol}...")
                
                try:
                    # Parse period to date range
                    end_date = datetime.now()
                    
                    # Convert period string to days
                    if period.endswith('y'):
                        years = int(period[:-1])
                        start_date = end_date - timedelta(days=years * 365)
                    elif period.endswith('mo'):
                        months = int(period[:-2])
                        start_date = end_date - timedelta(days=months * 30)
                    elif period.endswith('d'):
                        days = int(period[:-1])
                        start_date = end_date - timedelta(days=days)
                    else:
                        # Default to 2 years
                        start_date = end_date - timedelta(days=730)
                    
                    # Fetch from NSE Bhav Copy
                    df = self.fetch_nse_bhav_historical(symbol, start_date, end_date)
                    
                    if not df.empty:
                        # Clean data
                        df = self._clean_data(df)
                        print(f"[OK] Successfully fetched {len(df)} rows from NSE Bhav Copy fallback")
                        return df
                    else:
                        print(f"[ERROR] NSE Bhav Copy fallback also failed for {symbol}")
                
                except Exception as e:
                    print(f"[ERROR] NSE Bhav Copy fallback error: {e}")
                    logger.error(f"NSE fallback failed for {symbol}: {e}")
            else:
                print(f"[INFO] NSE Bhav Copy only supports daily data (interval=1d), not {interval}")
                print(f"[INFO] Skipping NSE fallback")
        else:
            print(f"[INFO] {symbol} is not an Indian stock (.NS/.BO), NSE fallback not applicable")
        
        print(f"[ERROR] All data sources failed for {symbol}")
        return pd.DataFrame()
    
    def _download_nse_bhav_for_date(self, date: datetime, session: Optional[requests.Session] = None, retry_count: int = 2) -> Optional[pd.DataFrame]:
        """
        Download NSE Bhav Copy for a specific date
        Downloads CSV directly without caching the full file (saves space)
        
        Args:
            date: The date to download data for
            session: Optional requests.Session for connection reuse (faster)
            retry_count: Number of retries for 403 errors (with session refresh)
            
        Returns:
            DataFrame with NSE data for that date, or None if failed
        """
        # Format date as DDMMYYYY
        date_str = date.strftime("%d%m%Y")
        
        # NSE Bhav Copy URL
        url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"
        
        # Download from NSE (no full file caching - extract symbol-specific data only)
        for attempt in range(retry_count + 1):
            try:
                # Use session if provided (faster connection reuse), otherwise create new request
                if session:
                    response = session.get(url, timeout=15)
                else:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': 'https://www.nseindia.com/',
                    }
                    response = requests.get(url, headers=headers, timeout=15)
                
                response.raise_for_status()
                
                # Parse CSV from response directly (don't save full file)
                # Use low_memory=False for faster parsing when we know the data size
                df = pd.read_csv(io.StringIO(response.text), low_memory=False)
                
                logger.debug(f"Downloaded NSE Bhav Copy: {date_str}")
                
                return df
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # No data for this date (weekend/holiday)
                    logger.debug(f"No NSE data for {date_str} (likely weekend/holiday)")
                    return None
                elif e.response.status_code == 403:
                    # 403 Forbidden - NSE is blocking the request
                    # Try refreshing session if we have retries left
                    if attempt < retry_count and session:
                        try:
                            # Refresh session by visiting homepage again
                            session.get('https://www.nseindia.com', timeout=10)
                            time.sleep(0.3)  # Small delay
                            logger.debug(f"Refreshed NSE session, retrying {date_str}")
                            continue  # Retry the request
                        except:
                            pass
                    # If no retries left or no session, give up
                    logger.debug(f"NSE 403 Forbidden for {date_str} (after {attempt + 1} attempts)")
                    return None
                else:
                    logger.debug(f"HTTP error downloading NSE data for {date_str}: {e.response.status_code}")
                    return None
            except Exception as e:
                if attempt < retry_count:
                    time.sleep(0.2)  # Small delay before retry
                    continue
                logger.debug(f"Error downloading NSE Bhav Copy for {date_str}: {e}")
                return None
        
        return None
    
    def _parse_nse_bhav_csv(self, df: pd.DataFrame, symbol: str) -> Optional[pd.DataFrame]:
        """
        Parse NSE Bhav Copy CSV and extract data for specific symbol
        
        Args:
            df: Raw NSE Bhav Copy DataFrame
            symbol: Stock symbol to extract (e.g., 'RELIANCE', 'TCS')
            
        Returns:
            DataFrame with OHLCV data for the symbol
        """
        if df is None or df.empty:
            return None
        
        try:
            # NSE Bhav Copy column names have specific format with spaces
            # Columns: SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, 
            #          LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, etc.
            
            # Normalize column names (strip spaces and convert to uppercase)
            df.columns = df.columns.str.strip().str.upper()
            
            # Also strip values in SYMBOL and SERIES columns
            df['SYMBOL'] = df['SYMBOL'].str.strip().str.upper()
            df['SERIES'] = df['SERIES'].str.strip().str.upper()
            
            # Filter for the symbol
            # Remove .NS or .BO suffix if present
            clean_symbol = symbol.replace('.NS', '').replace('.BO', '').upper()
            
            # Filter for the symbol and EQ series (Equity)
            symbol_data = df[
                (df['SYMBOL'] == clean_symbol) & 
                (df['SERIES'] == 'EQ')
            ].copy()
            
            if symbol_data.empty:
                return None
            
            # Map NSE column names to OHLCV format (matching yfinance format exactly)
            # NSE uses: OPEN_PRICE, HIGH_PRICE, LOW_PRICE, CLOSE_PRICE, TTL_TRD_QNTY
            result_df = pd.DataFrame({
                'Open': pd.to_numeric(symbol_data['OPEN_PRICE'], errors='coerce'),
                'High': pd.to_numeric(symbol_data['HIGH_PRICE'], errors='coerce'),
                'Low': pd.to_numeric(symbol_data['LOW_PRICE'], errors='coerce'),
                'Close': pd.to_numeric(symbol_data['CLOSE_PRICE'], errors='coerce'),
                'Volume': pd.to_numeric(symbol_data['TTL_TRD_QNTY'], errors='coerce'),
                # Add yfinance-compatible columns (NSE Bhav doesn't have these, set to 0)
                'Dividends': 0.0,
                'Stock Splits': 0.0,
            })
            
            # Parse date from DATE1 column (format: DD-MMM-YYYY like 07-Nov-2025)
            # Strip whitespace from date values before parsing
            if 'DATE1' in symbol_data.columns:
                dates = symbol_data['DATE1'].str.strip()
                result_df.index = pd.to_datetime(dates, format='%d-%b-%Y', errors='coerce')
            elif 'TIMESTAMP' in symbol_data.columns:
                dates = symbol_data['TIMESTAMP'].str.strip()
                result_df.index = pd.to_datetime(dates, format='%d-%b-%Y', errors='coerce')
            else:
                # Fallback: use current date
                result_df.index = pd.DatetimeIndex([datetime.now()])
            
            # Remove rows with invalid dates (NaT)
            result_df = result_df[result_df.index.notna()]
            
            return result_df
            
        except Exception as e:
            logger.error(f"Error parsing NSE Bhav CSV for {symbol}: {e}")
            logger.error(f"Available columns: {df.columns.tolist()}")
            return None
    
    def fetch_nse_bhav_historical(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Fetch historical data from NSE Bhav Copy for a date range
        Only fetches and caches data for the requested symbol (like yfinance)
        Creates ONE JSON file per symbol with all historical data
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS', 'TCS.NS')
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with OHLCV data (yfinance format)
        """
        # Check if symbol-specific cache exists
        clean_symbol_for_file = symbol.replace('.NS', '_NS').replace('.BO', '_BO')
        symbol_cache_file = NSE_BHAV_CACHE_DIR / f"{clean_symbol_for_file}_historical.json"
        
        # Check cache first
        if symbol_cache_file.exists():
            try:
                with open(symbol_cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Check if cache covers the requested date range
                cached_start = datetime.fromisoformat(cached_data['start_date'])
                cached_end = datetime.fromisoformat(cached_data['end_date'])
                
                if cached_start <= start_date and cached_end >= end_date:
                    # Cache is valid, load it
                    df = pd.DataFrame(cached_data['data'])
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                    
                    # Filter to requested date range
                    df = df[(df.index >= start_date) & (df.index <= end_date)]
                    
                    print(f"[INFO] Loaded {symbol} from NSE cache: {len(df)} rows")
                    return df
            except Exception as e:
                logger.warning(f"Failed to load NSE cache for {symbol}: {e}")
        
        # Cache miss or invalid - fetch fresh data
        print(f"[INFO] Fetching NSE Bhav Copy historical data for {symbol}")
        print(f"  -> Date range: {start_date.date()} to {end_date.date()}")
        
        # Remove .NS or .BO suffix for NSE lookup
        clean_symbol = symbol.replace('.NS', '').replace('.BO', '').upper()
        
        # Generate list of trading days (skip weekends) - collect all dates first
        trading_dates = []
        temp_date = start_date
        while temp_date <= end_date:
            if temp_date.weekday() < 5:  # Monday=0, Friday=4
                trading_dates.append(temp_date)
            temp_date += timedelta(days=1)
        
        dates_tried = len(trading_dates)
        print(f"  -> Will fetch {dates_tried} trading days (using parallel downloads)")
        
        # Download in parallel for faster fetching
        # Use ThreadPoolExecutor to download multiple days concurrently
        # Reduced to 5 workers to avoid NSE rate limiting (403 errors)
        max_workers = min(5, dates_tried)  # Reduced from 20 to 5 to avoid 403 Forbidden errors
        
        # Create a session for connection reuse (faster than creating new connections)
        session = requests.Session()
        
        # NSE requires proper headers and cookies - visit homepage first to establish session
        try:
            # Visit NSE homepage first to get cookies (required for accessing archives)
            session.get('https://www.nseindia.com', timeout=10)
            time.sleep(0.5)  # Small delay after initial request
        except Exception as e:
            logger.debug(f"Could not establish NSE session: {e}")
        
        # Set proper headers that NSE expects
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.nseindia.com/',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Increase connection pool size to avoid "pool is full" warnings
        adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        
        def download_and_parse(date):
            """Download and parse data for a single date"""
            # Add small random delay to avoid rate limiting (0.1-0.3 seconds)
            time.sleep(0.1 + (hash(str(date)) % 20) / 100.0)
            
            bhav_df = self._download_nse_bhav_for_date(date, session=session)
            if bhav_df is not None:
                symbol_df = self._parse_nse_bhav_csv(bhav_df, clean_symbol)
                if symbol_df is not None and not symbol_df.empty:
                    return symbol_df
            return None
        
        # Use ThreadPoolExecutor for parallel downloads
        all_data = []
        dates_found = 0
        last_session_refresh = datetime.now()
        session_refresh_interval = 300  # Refresh session every 5 minutes (300 seconds)
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all download tasks
                future_to_date = {executor.submit(download_and_parse, date): date for date in trading_dates}
                
                # Process completed downloads with progress bar
                for future in tqdm(as_completed(future_to_date), total=len(trading_dates), 
                                 desc="Downloading NSE data", unit="day"):
                    try:
                        result = future.result()
                        if result is not None:
                            all_data.append(result)
                            dates_found += 1
                        
                        # Periodically refresh session to avoid 403 errors during long downloads
                        if (datetime.now() - last_session_refresh).total_seconds() > session_refresh_interval:
                            try:
                                session.get('https://www.nseindia.com', timeout=10)
                                last_session_refresh = datetime.now()
                                logger.debug("Refreshed NSE session during long download")
                            except:
                                pass
                    except Exception as e:
                        date = future_to_date[future]
                        logger.debug(f"Error downloading {date}: {e}")
        finally:
            # Close session to free resources
            session.close()
        
        print(f"  -> Tried {dates_tried} trading days, found data for {dates_found} days")
        
        if not all_data:
            print(f"  -> [ERROR] No NSE data found for {symbol}")
            return pd.DataFrame()
        
        # Combine all data
        combined_df = pd.concat(all_data)
        combined_df = combined_df.sort_index()
        
        # Remove duplicates
        combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
        
        # Ensure NSE Bhav data matches yfinance format exactly
        # Add missing columns if not present (should already be added in _parse_nse_bhav_csv)
        if 'Dividends' not in combined_df.columns:
            combined_df['Dividends'] = 0.0
        if 'Stock Splits' not in combined_df.columns:
            combined_df['Stock Splits'] = 0.0
        
        # Ensure column order matches yfinance: Open, High, Low, Close, Volume, Dividends, Stock Splits
        expected_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
        combined_df = combined_df[[col for col in expected_cols if col in combined_df.columns]]
        
        # Clean data (same as yfinance) - remove timezone, handle duplicates, etc.
        combined_df = self._clean_data(combined_df)
        
        print(f"  -> [OK] Fetched {len(combined_df)} rows from NSE Bhav Copy (formatted like yfinance)")
        
        # Cache symbol-specific data in yfinance-like format
        try:
            # Format cache data to match yfinance cache structure
            cache_data = {
                'symbol': symbol,
                'source': 'NSE Bhav Copy',
                'fetch_timestamp': datetime.now().isoformat(),
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'rows': len(combined_df),
                'data': combined_df.reset_index().to_dict('records')
            }
            
            with open(symbol_cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
            
            print(f"  -> Cached {symbol} data to {symbol_cache_file.name}")
        except Exception as e:
            logger.warning(f"Failed to cache symbol data: {e}")
        
        return combined_df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare data"""
        # Remove timezone info from index if present
        if df.index.tzinfo is not None:
            df.index = df.index.tz_localize(None)
        
        # Remove any duplicate indices
        df = df[~df.index.duplicated(keep='first')]
        
        # Forward fill missing values (limited to 5 days)
        df = df.ffill(limit=5)
        
        # Drop remaining NaN values
        df = df.dropna()
        
        # Ensure positive prices and volumes
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_cols:
            if col in df.columns:
                df = df[df[col] > 0]
        
        # Sort by date
        df = df.sort_index()
        
        return df
    
    def fetch_all_data(
        self,
        symbol: str,
        period: str = HISTORICAL_PERIOD,
        include_fundamentals: bool = True,
        include_analyst: bool = True,
        include_ownership: bool = True,
        include_earnings: bool = True,
        include_options: bool = False,
        include_news: bool = True
    ) -> Dict:
        """
        Fetch ALL available data for a symbol
        
        Returns:
            Dictionary containing all available data
        """
        print(f"[INFO] Fetching ALL data for {symbol}...")
        
        ticker = yf.Ticker(symbol)
        all_data = {}
        
        # 1. OHLCV Price Data
        data_source = 'yfinance'  # Track data source for metadata
        try:
            print(f"  [1/10] Fetching price history from Yahoo Finance...")
            all_data['price_history'] = ticker.history(period=period)
            all_data['price_history_metadata'] = {
                'rows': len(all_data['price_history']),
                'start_date': str(all_data['price_history'].index[0]) if not all_data['price_history'].empty else None,
                'end_date': str(all_data['price_history'].index[-1]) if not all_data['price_history'].empty else None,
                'data_source': 'yfinance'
            }
            if not all_data['price_history'].empty:
                print(f"    [OK] Price history: {len(all_data['price_history'])} rows from Yahoo Finance")
            else:
                raise ValueError("Empty DataFrame returned from yfinance")
        except Exception as e:
            print(f"    [ERROR] Error fetching price history from Yahoo Finance: {e}")
            logger.warning(f"yfinance failed for {symbol}, attempting NSE Bhav Copy fallback...")
            
            # FALLBACK: Try NSE Bhav Copy for Indian stocks
            if symbol.endswith('.NS') or symbol.endswith('.BO'):
                try:
                    print(f"    [FALLBACK] Attempting NSE Bhav Copy for {symbol}...")
                    
                    # Parse period to date range
                    end_date = datetime.now()
                    if period.endswith('y'):
                        years = int(period[:-1])
                        start_date = end_date - timedelta(days=years * 365)
                    elif period.endswith('mo'):
                        months = int(period[:-2])
                        start_date = end_date - timedelta(days=months * 30)
                    elif period.endswith('d'):
                        days = int(period[:-1])
                        start_date = end_date - timedelta(days=days)
                    else:
                        start_date = end_date - timedelta(days=730)  # Default 2 years
                    
                    # Fetch from NSE Bhav Copy
                    df_bhav = self.fetch_nse_bhav_historical(symbol, start_date, end_date)
                    
                    if not df_bhav.empty:
                        # Ensure NSE Bhav data matches yfinance format exactly
                        # Add missing columns if not present (should already be added in _parse_nse_bhav_csv)
                        if 'Dividends' not in df_bhav.columns:
                            df_bhav['Dividends'] = 0.0
                        if 'Stock Splits' not in df_bhav.columns:
                            df_bhav['Stock Splits'] = 0.0
                        
                        # Ensure column order matches yfinance: Open, High, Low, Close, Volume, Dividends, Stock Splits
                        expected_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
                        df_bhav = df_bhav[[col for col in expected_cols if col in df_bhav.columns]]
                        
                        # Clean data (same as yfinance)
                        df_bhav = self._clean_data(df_bhav)
                        
                        all_data['price_history'] = df_bhav
                        all_data['price_history_metadata'] = {
                            'rows': len(df_bhav),
                            'start_date': str(df_bhav.index[0]) if not df_bhav.empty else None,
                            'end_date': str(df_bhav.index[-1]) if not df_bhav.empty else None,
                            'data_source': 'nse_bhav'
                        }
                        data_source = 'nse_bhav'
                        print(f"    [OK] Price history: {len(df_bhav)} rows from NSE Bhav Copy (fallback, formatted like yfinance)")
                        logger.info(f"Successfully used NSE Bhav Copy fallback for {symbol}")
                    else:
                        print(f"    [ERROR] NSE Bhav Copy also returned empty data")
                        all_data['price_history'] = pd.DataFrame()
                        all_data['price_history_metadata'] = {'data_source': 'none', 'rows': 0}
                except Exception as e2:
                    print(f"    [ERROR] NSE Bhav Copy fallback also failed: {e2}")
                    logger.error(f"NSE Bhav Copy fallback failed for {symbol}: {e2}")
                    all_data['price_history'] = pd.DataFrame()
                    all_data['price_history_metadata'] = {'data_source': 'none', 'rows': 0}
            else:
                print(f"    [INFO] {symbol} is not an Indian stock (.NS/.BO), NSE fallback not applicable")
                all_data['price_history'] = pd.DataFrame()
                all_data['price_history_metadata'] = {'data_source': 'none', 'rows': 0}
        
        # 2. Company Information
        try:
            print(f"  [2/10] Fetching company info...")
            all_data['info'] = ticker.info
            print(f"    [OK] Company info: {len(all_data['info'])} fields")
            all_data['key_metrics'] = self._extract_key_metrics(all_data['info'])
        except Exception as e:
            print(f"    [ERROR] Error fetching company info: {e}")
            all_data['info'] = {}
            all_data['key_metrics'] = {}
        
        # 3. Fundamental Data
        if include_fundamentals:
            print(f"  [3/10] Fetching fundamental data...")
            try:
                all_data['financials'] = ticker.financials
                all_data['quarterly_financials'] = ticker.quarterly_financials
                all_data['balance_sheet'] = ticker.balance_sheet
                all_data['quarterly_balance_sheet'] = ticker.quarterly_balance_sheet
                all_data['cashflow'] = ticker.cashflow
                all_data['quarterly_cashflow'] = ticker.quarterly_cashflow
                print(f"    [OK] Fundamentals fetched")
            except Exception as e:
                logger.error(f"Error fetching fundamentals for {symbol}: {e}", exc_info=True)
                print(f"    [ERROR] Error fetching fundamentals: {e}")
                all_data['financials'] = pd.DataFrame()
        else:
            print(f"  [3/10] Skipping fundamentals...")
        
        # 4. Analyst Data
        if include_analyst:
            print(f"  [4/10] Fetching analyst data...")
            try:
                all_data['recommendations'] = ticker.recommendations
                all_data['analyst_price_targets'] = ticker.analyst_price_targets
                all_data['earnings_estimate'] = ticker.earnings_estimate
                all_data['revenue_estimate'] = ticker.revenue_estimate
                print(f"    [OK] Analyst data fetched")
            except Exception as e:
                logger.error(f"Error fetching analyst data for {symbol}: {e}", exc_info=True)
                print(f"    [ERROR] Error fetching analyst data: {e}")
                all_data['recommendations'] = pd.DataFrame()
        else:
            print(f"  [4/10] Skipping analyst data...")
        
        # 5. Ownership Data
        if include_ownership:
            print(f"  [5/10] Fetching ownership data...")
            try:
                all_data['major_holders'] = ticker.major_holders
                all_data['institutional_holders'] = ticker.institutional_holders
                all_data['mutualfund_holders'] = ticker.mutualfund_holders
                all_data['insider_transactions'] = ticker.insider_transactions
                all_data['insider_roster_holders'] = ticker.insider_roster_holders
                print(f"    [OK] Ownership data fetched")
            except Exception as e:
                print(f"    [ERROR] Error fetching ownership: {e}")
                all_data['major_holders'] = pd.DataFrame()
        else:
            print(f"  [5/10] Skipping ownership data...")
        
        # 6. Earnings Data
        if include_earnings:
            print(f"  [6/10] Fetching earnings data...")
            try:
                all_data['earnings'] = ticker.earnings
                all_data['quarterly_earnings'] = ticker.quarterly_earnings
                all_data['earnings_dates'] = ticker.earnings_dates
                all_data['earnings_history'] = ticker.earnings_history
                print(f"    [OK] Earnings data fetched")
            except Exception as e:
                print(f"    [ERROR] Error fetching earnings: {e}")
                all_data['earnings'] = pd.DataFrame()
        else:
            print(f"  [6/10] Skipping earnings data...")
        
        # 7. Corporate Actions
        try:
            print(f"  [7/10] Fetching corporate actions...")
            all_data['actions'] = ticker.actions
            all_data['dividends'] = ticker.dividends
            all_data['splits'] = ticker.splits
            print(f"    [OK] Corporate actions fetched")
        except Exception as e:
            print(f"    [ERROR] Error fetching corporate actions: {e}")
            all_data['actions'] = pd.DataFrame()
        
        # 8. Options Data (Optional - can be slow)
        if include_options:
            print(f"  [8/10] Fetching options data...")
            try:
                all_data['options_dates'] = ticker.options
                all_data['options_chains'] = {}
                for date in list(ticker.options)[:3]:
                    opt = ticker.option_chain(date)
                    all_data['options_chains'][date] = {
                        'calls': opt.calls,
                        'puts': opt.puts
                    }
                print(f"    [OK] Options data fetched ({len(all_data['options_chains'])} expirations)")
            except Exception as e:
                logger.error(f"Error fetching options for {symbol}: {e}", exc_info=True)
                print(f"    [ERROR] Error fetching options: {e}")
                all_data['options_dates'] = []
        else:
            print(f"  [8/10] Skipping options data...")
        
        # 9. Calendar & Events
        try:
            print(f"  [9/10] Fetching calendar...")
            all_data['calendar'] = ticker.calendar
            print(f"    [OK] Calendar fetched")
        except Exception as e:
            logger.error(f"Error fetching calendar for {symbol}: {e}", exc_info=True)
            print(f"    [ERROR] Error fetching calendar: {e}")
            all_data['calendar'] = {}
        
        # 10. News
        if include_news:
            # If data source is NSE Bhav, news is not available
            if data_source == 'nse_bhav':
                print(f"  [10/10] News not available (NSE Bhav Copy does not support news)")
                all_data['news'] = []
            else:
                print(f"  [10/10] Fetching news...")
                try:
                    all_data['news'] = ticker.news
                    print(f"    [OK] News fetched ({len(all_data['news'])} articles)")
                except Exception as e:
                    logger.error(f"Error fetching news for {symbol}: {e}", exc_info=True)
                    print(f"    [ERROR] Error fetching news: {e}")
                    all_data['news'] = []
        else:
            print(f"  [10/10] Skipping news...")
            all_data['news'] = []
        
        # Add metadata with data source tracking
        all_data['metadata'] = {
            'symbol': symbol,
            'fetch_timestamp': datetime.now().isoformat(),
            'period': period,
            'data_source': data_source,  # Track if data came from yfinance or nse_bhav
            'has_news': data_source == 'yfinance'  # BHAV doesn't support news
        }
        
        print(f"[OK] ALL data fetched for {symbol}")
        
        # Auto-save to cache
        self._save_to_cache(symbol, all_data)
        
        return all_data
    
    def fetch_price_only(self, symbol: str, period: str = "2y") -> Dict:
        """
        Fetch only OHLCV price history for prediction (fast path).
        Skips company info, fundamentals, earnings, news, etc. Saves to same cache format.
        """
        print(f"[INFO] Fetching price data only for {symbol} (fast path)...")
        ticker = yf.Ticker(symbol)
        all_data = {}
        data_source = "yfinance"
        try:
            print(f"  [1/1] Fetching price history...")
            all_data["price_history"] = ticker.history(period=period)
            all_data["price_history_metadata"] = {
                "rows": len(all_data["price_history"]),
                "start_date": str(all_data["price_history"].index[0]) if not all_data["price_history"].empty else None,
                "end_date": str(all_data["price_history"].index[-1]) if not all_data["price_history"].empty else None,
                "data_source": "yfinance",
            }
            if all_data["price_history"].empty:
                raise ValueError("Empty DataFrame from yfinance")
            print(f"    [OK] Price history: {len(all_data['price_history'])} rows")
        except Exception as e:
            print(f"    [ERROR] {e}")
            if (symbol.endswith(".NS") or symbol.endswith(".BO")) and hasattr(self, "fetch_nse_bhav_historical"):
                try:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=730)
                    df_bhav = self.fetch_nse_bhav_historical(symbol, start_date, end_date)
                    if not df_bhav.empty:
                        if "Dividends" not in df_bhav.columns:
                            df_bhav["Dividends"] = 0.0
                        if "Stock Splits" not in df_bhav.columns:
                            df_bhav["Stock Splits"] = 0.0
                        expected_cols = ["Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits"]
                        df_bhav = df_bhav[[c for c in expected_cols if c in df_bhav.columns]]
                        df_bhav = self._clean_data(df_bhav)
                        all_data["price_history"] = df_bhav
                        all_data["price_history_metadata"] = {"rows": len(df_bhav), "data_source": "nse_bhav"}
                        data_source = "nse_bhav"
                        print(f"    [OK] Price from NSE Bhav: {len(df_bhav)} rows")
                    else:
                        all_data["price_history"] = pd.DataFrame()
                except Exception as e2:
                    all_data["price_history"] = pd.DataFrame()
            else:
                all_data["price_history"] = pd.DataFrame()
        all_data["info"] = {}
        all_data["key_metrics"] = {}
        all_data["news"] = []
        all_data["metadata"] = {
            "symbol": symbol,
            "fetch_timestamp": datetime.now().isoformat(),
            "period": period,
            "data_source": data_source,
        }
        if not all_data.get("price_history", pd.DataFrame()).empty:
            self._save_to_cache(symbol, all_data)
        return all_data
    
    def _save_to_cache(self, symbol: str, all_data: Dict):
        """Save fetched data to JSON cache"""
        json_path = self.cache_dir / f"{symbol}_all_data.json"
        
        df = all_data.get('price_history', pd.DataFrame())
        if df.empty:
            print(f"[WARNING] No price history to save for {symbol}")
            return
        
        # Prepare for JSON
        df_copy = df.copy()
        df_copy['Date'] = df_copy.index.astype(str)
        
        json_data = {
            'symbol': symbol,
            'fetch_time': datetime.now().isoformat(),
            'metadata': all_data.get('metadata', {}),
            'price_history': df_copy.to_dict('records'),
            'info': all_data.get('info', {}),
            'key_metrics': all_data.get('key_metrics', {}),
            'news': all_data.get('news', [])
        }
        
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2, default=str)
        
        print(f"[OK] Data saved to {json_path}")
    
    def _extract_key_metrics(self, info: Dict) -> Dict:
        """Extract key financial metrics from company info"""
        key_fields = [
            'marketCap', 'enterpriseValue', 'priceToBook', 'priceToSalesTrailing12Months',
            'profitMargins', 'operatingMargins', 'returnOnAssets', 'returnOnEquity',
            'totalCash', 'totalDebt', 'debtToEquity', 'currentRatio', 'quickRatio',
            'trailingEps', 'forwardEps', 'trailingPE', 'forwardPE', 'pegRatio',
            'dividendRate', 'dividendYield', 'payoutRatio', 'fiveYearAvgDividendYield',
            'revenueGrowth', 'earningsGrowth', 'earningsQuarterlyGrowth',
            'beta', 'fiftyTwoWeekLow', 'fiftyTwoWeekHigh', 'fiftyDayAverage',
            'targetHighPrice', 'targetLowPrice', 'targetMeanPrice', 'targetMedianPrice',
            'recommendationMean', 'recommendationKey', 'numberOfAnalystOpinions',
            'sector', 'industry', 'country', 'fullTimeEmployees'
        ]
        
        metrics = {}
        for field in key_fields:
            if field in info:
                metrics[field] = info[field]
        
        return metrics
    
    # Removed save_all_data - we only use JSON and Parquet now
    
    def load_all_data(self, symbol: str) -> Optional[Dict]:
        """Load all data from JSON file"""
        json_path = self.cache_dir / f"{symbol}_all_data.json"
        
        if not json_path.exists():
            print(f"[WARNING] No saved data found for {symbol}")
            return None
        
        try:
            with open(json_path, 'r') as f:
                json_data = json.load(f)
            
            # Convert price_history back to DataFrame
            if 'price_history' in json_data and json_data['price_history']:
                price_df = pd.DataFrame(json_data['price_history'])
                if not price_df.empty:
                    # Try different date column names
                    date_col = None
                    for col in ['Date', 'date', 'Datetime', 'datetime', 'index']:
                        if col in price_df.columns:
                            date_col = col
                            break
                    
                    if date_col:
                        price_df[date_col] = pd.to_datetime(price_df[date_col])
                        price_df.set_index(date_col, inplace=True)
                        # Remove timezone if present
                        if price_df.index.tzinfo is not None:
                            price_df.index = price_df.index.tz_localize(None)
                    else:
                        # If no date column found, create DatetimeIndex from range
                        # This shouldn't happen but handle it gracefully
                        logger.warning("No date column found in price_history, using default index")
                
                json_data['price_history'] = price_df
            else:
                json_data['price_history'] = pd.DataFrame()
            
            # Convert other JSON data back to DataFrames
            if 'analyst_recommendations' in json_data and json_data['analyst_recommendations']:
                json_data['recommendations'] = pd.DataFrame(json_data['analyst_recommendations'])
            else:
                json_data['recommendations'] = pd.DataFrame()
            
            if 'earnings' in json_data and json_data['earnings']:
                json_data['earnings'] = pd.DataFrame(json_data['earnings'])
            else:
                json_data['earnings'] = pd.DataFrame()
            
            # Create empty DataFrames for financial statements (not stored in JSON)
            json_data['financials'] = pd.DataFrame()
            json_data['balance_sheet'] = pd.DataFrame()
            json_data['cashflow'] = pd.DataFrame()
            
            print(f"[INFO] All data loaded from {json_path}")
            return json_data
            
        except Exception as e:
            logger.error(f"Error loading data from JSON for {symbol}: {e}", exc_info=True)
            print(f"[ERROR] Error loading data from JSON: {e}")
            return None


# ============================================================================
# FEATURE ENGINEER - TECHNICAL INDICATORS
# ============================================================================

def _mfi_float64(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, length: int = 14) -> pd.Series:
    """
    Money Flow Index using float64 throughout. Avoids pandas_ta_classic bug where
    assigning float raw_money_flow into int64 '+mf' column raises on pandas 2.x.
    """
    high = high.astype(np.float64, copy=False)
    low = low.astype(np.float64, copy=False)
    close = close.astype(np.float64, copy=False)
    volume = volume.astype(np.float64, copy=False)
    typical_price = (high + low + close) / 3.0
    raw_money_flow = typical_price * volume
    diff = typical_price.diff(1)
    pos_mf = raw_money_flow.where(diff > 0, 0.0)
    neg_mf = raw_money_flow.where(diff < 0, 0.0)
    psum = pos_mf.rolling(length, min_periods=1).sum()
    nsum = neg_mf.rolling(length, min_periods=1).sum()
    mfi = 100.0 * psum / (psum + nsum + 1e-10)
    return mfi.fillna(0.0)


class FeatureEngineer:
    """
    Calculate technical indicators and features for stock data
    Calculates 50+ technical indicators including RSI, MACD, Bollinger Bands, etc.
    """
    
    def __init__(self):
        """Initialize FeatureEngineer"""
        self.feature_cache_dir = FEATURE_CACHE_DIR
        self.feature_cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("FeatureEngineer initialized")
    
    def calculate_all_features(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> pd.DataFrame:
        """
        Calculate all 50+ technical indicators
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol for logging
            
        Returns:
            DataFrame with all features added
        """
        # Minimum data requirement: Need at least 100 rows for basic indicators
        # Some indicators need up to 200 periods (SMA_200), but we can work with less
        # Indicators will have NaN initially until enough data accumulates
        min_rows = 100
        if df.empty:
            return pd.DataFrame()
        if len(df) < min_rows:
            logger.warning(f"Insufficient data for {symbol}: {len(df)} rows (need {min_rows}+)")
            print(f"[WARNING] Insufficient data for {symbol}: {len(df)} rows (need {min_rows}+)")
            print(f"[INFO] Some technical indicators (like SMA_200) may have limited data with fewer rows")
            # Still allow processing - indicators will calculate with available data (NaN for longer periods)
            if len(df) < 50:
                # Too little data - can't calculate meaningful indicators
                return pd.DataFrame()
        
        # Limit rows for faster feature calc on low-CPU (e.g. Render); keep enough for SMA_200
        max_rows = int(os.environ.get("FEATURE_MAX_ROWS", "300"))
        if len(df) > max_rows:
            n_orig = len(df)
            df = df.tail(max_rows).copy()
            logger.info(f"Using last {max_rows} rows for features (was {n_orig})")
        logger.info(f"Calculating features for {symbol} with {len(df)} rows")
        print(f"[INFO] Calculating 50+ technical indicators for {symbol} ({len(df)} rows)...", flush=True)
        
        # Create a copy to avoid modifying original
        features_df = df.copy()
        
        try:
            # Calculate features by category (flush so Render logs show where we are)
            print(f"  -> [1/7] Calculating momentum indicators (RSI, MACD, Stochastic, etc.)...", flush=True)
            features_df = self._calculate_momentum_indicators(features_df)
            
            print(f"  -> [2/7] Calculating trend indicators (SMA, EMA, ADX, etc.)...", flush=True)
            features_df = self._calculate_trend_indicators(features_df)
            
            print(f"  -> [3/7] Calculating volatility indicators (Bollinger Bands, ATR, etc.)...", flush=True)
            features_df = self._calculate_volatility_indicators(features_df)
            
            print(f"  -> [4/7] Calculating volume indicators (OBV, CMF, etc.)...", flush=True)
            features_df = self._calculate_volume_indicators(features_df)
            
            print(f"  -> [5/7] Calculating support/resistance levels...", flush=True)
            features_df = self._calculate_support_resistance(features_df)
            
            print(f"  -> [6/7] Calculating pattern features (Doji, Hammer, etc.)...", flush=True)
            features_df = self._calculate_pattern_features(features_df)
            
            print(f"  -> [7/7] Calculating advanced analytics (VWAP, Sharpe, etc.)...", flush=True)
            features_df = self._calculate_advanced_analytics(features_df)
            
            # Handle NaN values intelligently
            print("[feat] clean: replace inf...", flush=True)
            features_df.replace([np.inf, -np.inf], np.nan, inplace=True)
            print("[feat] clean: ffill...", flush=True)
            features_df.ffill(limit=5, inplace=True)
            print("[feat] clean: bfill...", flush=True)
            features_df.bfill(limit=5, inplace=True)
            print("[feat] clean: fillna(0)...", flush=True)
            features_df.fillna(0, inplace=True)
            print("[feat] clean: drop Close<=0...", flush=True)
            if 'Close' in features_df.columns:
                features_df = features_df[features_df['Close'] > 0]
            print("[feat] clean: done", flush=True)
            logger.info(f"Feature calculation complete for {symbol}: {features_df.shape[1]} columns, {len(features_df)} rows")
            print(f"[OK] Feature calculation complete: {features_df.shape[1]} columns, {len(features_df)} rows", flush=True)
            
            return features_df
            
        except Exception as e:
            logger.error(f"Error calculating features for {symbol}: {e}")
            print(f"[ERROR] Error calculating features: {e}")
            raise
    
    def _calculate_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate momentum indicators (14 indicators). Progress logged for debugging slow runs."""
        fast_features = os.environ.get("FAST_FEATURES", "").strip().lower() in ("1", "true", "yes")
        print("[feat] momentum: RSI...", flush=True)
        df['RSI_14'] = ta.rsi(df['Close'], length=14)
        print("[feat] momentum: MACD...", flush=True)
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df['MACD'] = macd['MACD_12_26_9']
            df['MACD_signal'] = macd['MACDs_12_26_9']
            df['MACD_hist'] = macd['MACDh_12_26_9']
        print("[feat] momentum: Stoch...", flush=True)
        if fast_features:
            # Fast path: simple pandas Stoch (avoids slow pandas_ta/numba on Render)
            low_14 = df['Low'].rolling(14).min()
            high_14 = df['High'].rolling(14).max()
            df['STOCH_k'] = 100 * (df['Close'] - low_14) / (high_14 - low_14 + 1e-10)
            df['STOCH_d'] = df['STOCH_k'].rolling(3).mean()
        else:
            stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=14, d=3)
            if stoch is not None:
                df['STOCH_k'] = stoch['STOCHk_14_3_3']
                df['STOCH_d'] = stoch['STOCHd_14_3_3']
        print("[feat] momentum: WILLR...", flush=True)
        df['WILLR'] = ta.willr(df['High'], df['Low'], df['Close'], length=14)
        print("[feat] momentum: CCI...", flush=True)
        df['CCI'] = ta.cci(df['High'], df['Low'], df['Close'], length=20)
        print("[feat] momentum: MFI...", flush=True)
        df['MFI'] = _mfi_float64(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        print("[feat] momentum: ROC...", flush=True)
        if fast_features:
            # Fast path: pandas ROC (avoids hang in ta.roc on Render)
            df['ROC'] = (df['Close'].pct_change(12) * 100).fillna(0)
        else:
            df['ROC'] = ta.roc(df['Close'], length=12)
        print("[feat] momentum: TRIX...", flush=True)
        if fast_features:
            # Fast path: simple triple-EMA percent change (avoids slow ta.trix on Render)
            ema1 = df['Close'].ewm(span=15, adjust=False).mean()
            ema2 = ema1.ewm(span=15, adjust=False).mean()
            ema3 = ema2.ewm(span=15, adjust=False).mean()
            df['TRIX'] = (ema3.pct_change() * 100).fillna(0)
        else:
            trix = ta.trix(df['Close'], length=15)
            if trix is not None:
                df['TRIX'] = trix.iloc[:, 0] if isinstance(trix, pd.DataFrame) else trix
        print("[feat] momentum: CMO...", flush=True)
        df['CMO'] = ta.cmo(df['Close'], length=14)
        print("[feat] momentum: Aroon...", flush=True)
        aroon = ta.aroon(df['High'], df['Low'], length=25)
        if aroon is not None:
            df['AROON_up'] = aroon['AROONU_25']
            df['AROON_down'] = aroon['AROOND_25']
            df['AROON_osc'] = df['AROON_up'] - df['AROON_down']
        print("[feat] momentum: UO...", flush=True)
        df['UO'] = ta.uo(df['High'], df['Low'], df['Close'])
        print("[feat] momentum: done", flush=True)
        return df
    
    def _calculate_trend_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate trend indicators (11+ indicators)"""
        print("[feat] trend: SMA_10...", flush=True)
        df['SMA_10'] = ta.sma(df['Close'], length=10)
        print("[feat] trend: SMA_20...", flush=True)
        df['SMA_20'] = ta.sma(df['Close'], length=20)
        print("[feat] trend: SMA_50...", flush=True)
        df['SMA_50'] = ta.sma(df['Close'], length=50)
        print("[feat] trend: SMA_200...", flush=True)
        df['SMA_200'] = ta.sma(df['Close'], length=200)
        print("[feat] trend: EMA_12...", flush=True)
        df['EMA_12'] = ta.ema(df['Close'], length=12)
        print("[feat] trend: EMA_26...", flush=True)
        df['EMA_26'] = ta.ema(df['Close'], length=26)
        print("[feat] trend: ADX...", flush=True)
        adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        if adx is not None:
            df['ADX'] = adx['ADX_14']
            df['DMP'] = adx['DMP_14']
            df['DMN'] = adx['DMN_14']
        print("[feat] trend: PSAR...", flush=True)
        psar = ta.psar(df['High'], df['Low'], df['Close'])
        if psar is not None:
            psar_long = psar.iloc[:, 0] if isinstance(psar, pd.DataFrame) else psar
            psar_short = psar.iloc[:, 1] if isinstance(psar, pd.DataFrame) and psar.shape[1] > 1 else None
            df['PSAR'] = psar_long.fillna(psar_short) if psar_short is not None else psar_long
        print("[feat] trend: KC...", flush=True)
        kc = ta.kc(df['High'], df['Low'], df['Close'], length=20)
        if kc is not None:
            df['KC_upper'] = kc['KCUe_20_2']
            df['KC_middle'] = kc['KCBe_20_2']
            df['KC_lower'] = kc['KCLe_20_2']
        print("[feat] trend: Donchian...", flush=True)
        dc = ta.donchian(df['High'], df['Low'], lower_length=20, upper_length=20)
        if dc is not None:
            df['DC_upper'] = dc['DCU_20_20']
            df['DC_middle'] = dc['DCM_20_20']
            df['DC_lower'] = dc['DCL_20_20']
        print("[feat] trend: MA_alignment, trend_direction...", flush=True)
        df['MA_alignment'] = (
            (df['SMA_10'] > df['SMA_20']).astype(int) +
            (df['SMA_20'] > df['SMA_50']).astype(int) +
            (df['SMA_50'] > df['SMA_200']).astype(int)
        ) / 3.0
        df['trend_direction'] = np.where(
            df['Close'] > df['SMA_50'], 1,
            np.where(df['Close'] < df['SMA_50'], -1, 0)
        )
        print("[feat] trend: done", flush=True)
        return df
    
    def _calculate_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate volatility indicators (5+ indicators)"""
        print("[feat] volatility: bbands...", flush=True)
        bbands = ta.bbands(df['Close'], length=20, std=2)
        if bbands is not None:
            cols = bbands.columns.tolist()
            if len(cols) >= 3:
                df['BB_lower'] = bbands.iloc[:, 0]
                df['BB_middle'] = bbands.iloc[:, 1]
                df['BB_upper'] = bbands.iloc[:, 2]
                if len(cols) >= 4:
                    df['BB_width'] = bbands.iloc[:, 3]
                if len(cols) >= 5:
                    df['BB_pct'] = bbands.iloc[:, 4]
        print("[feat] volatility: ATR...", flush=True)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        print("[feat] volatility: STD_20, volatility_20...", flush=True)
        df['STD_20'] = df['Close'].rolling(window=20).std()
        returns = df['Close'].pct_change()
        df['volatility_20'] = returns.rolling(window=20).std() * np.sqrt(252)
        print("[feat] volatility: done", flush=True)
        return df
    
    def _calculate_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate volume indicators (7+ indicators)"""
        fast_features = os.environ.get("FAST_FEATURES", "").strip().lower() in ("1", "true", "yes")
        print("[feat] volume: OBV...", flush=True)
        df['OBV'] = ta.obv(df['Close'], df['Volume'])
        print("[feat] volume: Volume_SMA_20...", flush=True)
        df['Volume_SMA_20'] = ta.sma(df['Volume'], length=20)
        print("[feat] volume: AD...", flush=True)
        if fast_features:
            # Fast path: pandas A/D line (avoids slow ta.ad on Render)
            hl_range = (df['High'] - df['Low']).replace(0, np.nan)
            mfm = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / hl_range
            df['AD'] = (mfm.fillna(0) * df['Volume']).cumsum()
        else:
            df['AD'] = ta.ad(df['High'], df['Low'], df['Close'], df['Volume'])
        print("[feat] volume: CMF...", flush=True)
        if fast_features:
            # Fast path: Chaikin Money Flow over 20 (pandas rolling)
            hl_range = (df['High'] - df['Low']).replace(0, np.nan)
            mfm = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / hl_range
            mfv = mfm.fillna(0) * df['Volume']
            df['CMF'] = (mfv.rolling(20).sum() / (df['Volume'].rolling(20).sum() + 1e-10)).fillna(0)
        else:
            df['CMF'] = ta.cmf(df['High'], df['Low'], df['Close'], df['Volume'], length=20)
        print("[feat] volume: VROC...", flush=True)
        if fast_features:
            df['VROC'] = (df['Volume'].pct_change(12) * 100).fillna(0)
        else:
            df['VROC'] = ta.roc(df['Volume'], length=12)
        print("[feat] volume: EMV...", flush=True)
        if fast_features:
            # Fast path: simple Ease of Movement approximation (distance / volume)
            dm = ((df['High'] + df['Low']) / 2) - ((df['High'].shift(1) + df['Low'].shift(1)) / 2)
            br = df['Volume'] / (df['High'] - df['Low'] + 1e-10)
            df['EMV'] = (dm / br).rolling(14).mean().fillna(0)
        else:
            df['EMV'] = ta.eom(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        print("[feat] volume: volume_ratio, volume_trend...", flush=True)
        df['volume_ratio'] = df['Volume'] / (df['Volume_SMA_20'] + 1e-10)
        df['volume_trend'] = np.where(df['Volume'] > df['Volume_SMA_20'], 1, -1)
        print("[feat] volume: done", flush=True)
        return df
    
    def _calculate_support_resistance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate support/resistance levels (5+ indicators)"""
        print("[feat] support_resistance: pivot...", flush=True)
        df['pivot'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['pivot_r1'] = 2 * df['pivot'] - df['Low']
        df['pivot_s1'] = 2 * df['pivot'] - df['High']
        df['pivot_r2'] = df['pivot'] + (df['High'] - df['Low'])
        df['pivot_s2'] = df['pivot'] - (df['High'] - df['Low'])
        print("[feat] support_resistance: rolling, fib, price_position...", flush=True)
        window = 50
        rolling_high = df['High'].rolling(window=window).max()
        rolling_low = df['Low'].rolling(window=window).min()
        diff = rolling_high - rolling_low
        df['fib_0.236'] = rolling_high - 0.236 * diff
        df['fib_0.382'] = rolling_high - 0.382 * diff
        df['fib_0.500'] = rolling_high - 0.500 * diff
        df['fib_0.618'] = rolling_high - 0.618 * diff
        df['price_position'] = (df['Close'] - rolling_low) / (diff + 1e-10)
        print("[feat] support_resistance: done", flush=True)
        return df
    
    def _calculate_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate pattern recognition features (5+ features)"""
        print("[feat] pattern: cdl_doji...", flush=True)
        doji = ta.cdl_doji(df['Open'], df['High'], df['Low'], df['Close'])
        if doji is not None:
            df['CDL_DOJI'] = doji.iloc[:, 0].fillna(0).astype(int) if isinstance(doji, pd.DataFrame) else doji.fillna(0).astype(int)
        else:
            df['CDL_DOJI'] = 0
        print("[feat] pattern: cdl_pattern hammer...", flush=True)
        hammer = ta.cdl_pattern(df['Open'], df['High'], df['Low'], df['Close'], name='hammer')
        if hammer is not None:
            df['CDL_HAMMER'] = hammer.iloc[:, 0].fillna(0).astype(int) if isinstance(hammer, pd.DataFrame) else hammer.fillna(0).astype(int)
        else:
            df['CDL_HAMMER'] = 0
        print("[feat] pattern: HH/LL, gaps, engulf...", flush=True)
        df['higher_high'] = (df['High'] > df['High'].shift(1)).astype(int)
        df['lower_low'] = (df['Low'] < df['Low'].shift(1)).astype(int)
        df['gap_up'] = (df['Low'] > df['High'].shift(1)).astype(int)
        df['gap_down'] = (df['High'] < df['Low'].shift(1)).astype(int)
        df['bullish_engulf'] = (
            (df['Close'] > df['Open']) &
            (df['Open'] < df['Close'].shift(1)) &
            (df['Close'] > df['Open'].shift(1))
        ).astype(int)
        df['bearish_engulf'] = (
            (df['Close'] < df['Open']) &
            (df['Open'] > df['Close'].shift(1)) &
            (df['Close'] < df['Open'].shift(1))
        ).astype(int)
        print("[feat] pattern: done", flush=True)
        return df
    
    def _calculate_advanced_analytics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate advanced analytics (8+ features)"""
        print("[feat] advanced: price_to_sma, divergence, bb_position...", flush=True)
        df['price_to_sma_10'] = df['Close'] / (df['SMA_10'] + 1e-10)
        df['price_to_sma_50'] = df['Close'] / (df['SMA_50'] + 1e-10)
        df['price_to_sma_200'] = df['Close'] / (df['SMA_200'] + 1e-10)
        price_trend = (df['Close'] - df['Close'].shift(5)) > 0
        rsi_trend = (df['RSI_14'] - df['RSI_14'].shift(5)) > 0
        df['rsi_divergence'] = (price_trend != rsi_trend).astype(int)
        df['macd_hist_increasing'] = (df['MACD_hist'] > df['MACD_hist'].shift(1)).astype(int)
        df['bb_position'] = (df['Close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'] + 1e-10)
        print("[feat] advanced: VWAP...", flush=True)
        df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
        print("[feat] advanced: daily_return, daily_return_ma_5...", flush=True)
        df['daily_return'] = df['Close'].pct_change()
        df['daily_return_ma_5'] = df['daily_return'].rolling(window=5).mean()
        returns = df['daily_return']
        print("[feat] advanced: sharpe_20...", flush=True)
        df['sharpe_20'] = (
            returns.rolling(window=20).mean() /
            (returns.rolling(window=20).std() + 1e-10)
        ) * np.sqrt(252)
        print("[feat] advanced: returns_autocorr...", flush=True)
        df['returns_autocorr'] = returns.rolling(window=20).apply(
            lambda x: x.autocorr(), raw=False
        )
        print("[feat] advanced: done", flush=True)
        return df
    
    def save_features(self, df: pd.DataFrame, symbol: str):
        """Save LIVE/CURRENT features only (latest values)"""
        if df.empty:
            logger.error(f"Cannot save features for {symbol}: DataFrame is empty")
            return
        
        latest_features = df.iloc[-1].to_dict()
        latest_date = str(df.index[-1])
        
        latest_timestamp = pd.to_datetime(df.index[-1])
        if hasattr(latest_timestamp, 'tz') and latest_timestamp.tz is not None:
            latest_timestamp = latest_timestamp.tz_localize(None)
        
        days_old = (pd.Timestamp.now() - latest_timestamp).days
        
        live_data = {
            'symbol': symbol,
            'fetch_time': str(pd.Timestamp.now()),
            'latest_date': latest_date,
            'data_freshness_days': days_old,
            'current_price': float(latest_features.get('Close', 0)),
            'current_features': latest_features,
            'total_features': len(df.columns),
            'feature_calculation_periods': {
                'RSI_14': 'Last 14 days',
                'MACD': 'Last 12-26 days',
                'SMA_10': 'Last 10 days',
                'SMA_20': 'Last 20 days',
                'SMA_50': 'Last 50 days',
                'SMA_200': 'Last 200 days',
                'BB_bands': 'Last 20 days',
                'ATR_14': 'Last 14 days',
                'OBV': 'Cumulative (all historical data)',
                'pivot_points': 'Current day High/Low/Close',
                'fibonacci': 'Last 50 days High/Low range'
            }
        }
        
        json_path = self.feature_cache_dir / f"{symbol}_features.json"
        
        try:
            with open(json_path, 'w') as f:
                json.dump(live_data, f, indent=2, default=str)
            
            logger.info(f"Saved LIVE features for {symbol} to {json_path}")
            
            # Print current indicators to console
            print(f"\n{'='*80}")
            print(f"LIVE FEATURES FOR {symbol} (Updated: {live_data['fetch_time']})")
            print(f"{'='*80}")
            print(f"\nCURRENT PRICE: Rs.{live_data['current_price']:.2f}")
            print(f"Latest Date: {latest_date}")
            print(f"Data Freshness: {days_old} days old {'[WARNING: STALE DATA!]' if days_old > 7 else '[OK]'}")
            print(f"\nKEY INDICATORS (Current Values):")
            print(f"  RSI_14:        {latest_features.get('RSI_14', 0):.2f}")
            print(f"  MACD:          {latest_features.get('MACD', 0):.4f}")
            print(f"  MACD_signal:   {latest_features.get('MACD_signal', 0):.4f}")
            print(f"  SMA_10:        Rs.{latest_features.get('SMA_10', 0):.2f}")
            print(f"  SMA_20:        Rs.{latest_features.get('SMA_20', 0):.2f}")
            print(f"  SMA_50:        Rs.{latest_features.get('SMA_50', 0):.2f}")
            print(f"  SMA_200:       Rs.{latest_features.get('SMA_200', 0):.2f}")
            print(f"  BB_upper:      Rs.{latest_features.get('BB_upper', 0):.2f}")
            print(f"  BB_middle:     Rs.{latest_features.get('BB_middle', 0):.2f}")
            print(f"  BB_lower:      Rs.{latest_features.get('BB_lower', 0):.2f}")
            print(f"  ATR_14:        {latest_features.get('ATR', 0):.2f}")
            print(f"  Volume:        {latest_features.get('Volume', 0):,.0f}")
            print(f"  OBV:           {latest_features.get('OBV', 0):,.0f}")
            print(f"  ADX:           {latest_features.get('ADX', 0):.2f}")
            print(f"\nTREND ANALYSIS:")
            print(f"  Price/SMA_50:  {latest_features.get('price_to_sma_50', 0):.4f} ({'Above' if latest_features.get('price_to_sma_50', 0) > 1 else 'Below'} 50-day avg)")
            print(f"  Price/SMA_200: {latest_features.get('price_to_sma_200', 0):.4f} ({'Above' if latest_features.get('price_to_sma_200', 0) > 1 else 'Below'} 200-day avg)")
            print(f"  MA_alignment:  {latest_features.get('MA_alignment', 0):.2f} (0=bearish, 1=bullish)")
            print(f"  Trend:         {'Uptrend' if latest_features.get('trend_direction', 0) > 0 else 'Downtrend'}")
            print(f"\nMOMENTUM:")
            print(f"  RSI Status:    {'Overbought' if latest_features.get('RSI_14', 50) > 70 else 'Oversold' if latest_features.get('RSI_14', 50) < 30 else 'Neutral'}")
            print(f"  MACD Signal:   {'Bullish' if latest_features.get('MACD_hist', 0) > 0 else 'Bearish'}")
            print(f"{'='*80}\n")
            
        except Exception as e:
            logger.error(f"Error saving features for {symbol}: {e}")
            raise
    
    def load_features(self, symbol: str) -> dict:
        """Load LIVE features from cache (current values only)"""
        json_path = self.feature_cache_dir / f"{symbol}_features.json"
        
        if not json_path.exists():
            logger.warning(f"No feature cache found for {symbol}")
            return {}
        
        try:
            with open(json_path, 'r') as f:
                live_data = json.load(f)
            
            logger.info(f"Loaded LIVE features for {symbol}")
            return live_data
        except Exception as e:
            logger.error(f"Error loading features for {symbol}: {e}")
            return {}


# ============================================================================
# ML MODELS - PRICE PREDICTION
# ============================================================================

class StockPricePredictor:
    """
    Stock price prediction using ensemble of 3 ML models:
    1. Random Forest
    2. LightGBM
    3. XGBoost
    
    Supports multiple horizons: intraday (1 day), short (5 days), long (30 days)
    """
    
    def __init__(self, horizon: str = "intraday"):
        """
        Initialize Stock Price Predictor
        
        Args:
            horizon: Prediction horizon (intraday/short/long)
        """
        self.model_dir = MODEL_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Set horizon and target days
        self.horizon = horizon
        self.horizon_map = {
            'intraday': 1,
            'short': 5,
            'long': 30
        }
        self.target_days = self.horizon_map.get(horizon, 1)
        
        # Initialize models
        self.models = {
            'random_forest': None,
            'lightgbm': None,
            'xgboost': None
        }
        
        self.feature_columns = []
        logger.info(f"StockPricePredictor initialized for {horizon} horizon ({self.target_days} days)")
    
    @staticmethod
    def get_feature_columns(df: pd.DataFrame, n_samples: int = None, use_feature_selection: bool = True) -> list:
        """
        Get consistent feature columns for ML models with intelligent feature selection
        CENTRALIZED function to prevent dimension mismatches
        
        Args:
            df: DataFrame with all calculated features
            n_samples: Number of training samples (for adaptive feature selection)
            use_feature_selection: If True, select top features based on importance
            
        Returns:
            list: Feature column names to use for training/prediction
        """
        # ALWAYS exclude these columns (they are targets or raw data, not features)
        exclude_cols = [
            'target',      # Training target (future price)
            'Open',        # Raw OHLCV data
            'High',
            'Low', 
            'Close',
            'Volume',
            'daily_return',  # Derived from Close, not a feature
            'Dividends',     # Event data
            'Stock Splits'   # Event data
        ]
        
        # Get all feature columns
        all_feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # Feature selection: Reduce features if we have limited data
        if use_feature_selection and n_samples is not None:
            # Rule of thumb: Need at least 10 samples per feature
            # If we have fewer, reduce features to top N most important ones
            max_features_by_data = max(10, n_samples // 10)  # At least 10 features, max based on data
            
            if len(all_feature_cols) > max_features_by_data:
                # Select top features based on importance (use correlation with target if available)
                if 'target' in df.columns:
                    # Calculate correlation with target
                    correlations = df[all_feature_cols + ['target']].corr()['target'].abs().sort_values(ascending=False)
                    # Remove 'target' from correlations
                    correlations = correlations.drop('target')
                    # Select top N features
                    top_features = correlations.head(max_features_by_data).index.tolist()
                    logger.info(f"Feature selection: Reduced from {len(all_feature_cols)} to {len(top_features)} features (data size: {n_samples})")
                    return top_features
                else:
                    # No target available, use priority-based selection
                    priority_features = [
                        # Core momentum indicators
                        'RSI_14', 'MACD', 'MACD_signal', 'MACD_hist', 'STOCH_k', 'STOCH_d',
                        # Core trend indicators
                        'SMA_10', 'SMA_20', 'SMA_50', 'SMA_200', 'EMA_12', 'EMA_26',
                        # Core volatility
                        'BB_upper', 'BB_middle', 'BB_lower', 'ATR',
                        # Core volume
                        'OBV', 'CMF',
                        # Core trend strength
                        'ADX',
                        # Price ratios
                        'price_to_sma_50', 'price_to_sma_200',
                        # Support/Resistance
                        'pivot', 'pivot_r1', 'pivot_s1'
                    ]
                    # Select features that exist and are in priority list
                    selected = [f for f in priority_features if f in all_feature_cols]
                    # If we need more, add remaining features
                    if len(selected) < max_features_by_data:
                        remaining = [f for f in all_feature_cols if f not in selected]
                        selected.extend(remaining[:max_features_by_data - len(selected)])
                    logger.info(f"Feature selection: Selected {len(selected)} priority features (data size: {n_samples})")
                    return selected
        
        return all_feature_cols
    
    def prepare_data(self, df: pd.DataFrame, target_days: int = None) -> tuple:
        """
        Prepare data for training/prediction
        
        Args:
            df: DataFrame with features
            target_days: Days ahead to predict (uses horizon default if None)
            
        Returns:
            X, y, feature_columns
        """
        if target_days is None:
            target_days = self.target_days
        
        # Create target variable (future price)
        df = df.copy()
        df['target'] = df['Close'].shift(-target_days)
        
        # Remove rows with NaN target
        df = df.dropna(subset=['target'])
        
        # Use centralized feature selection with adaptive selection based on data size
        # Estimate training size (80% split)
        n_samples = int(len(df) * 0.8)
        feature_cols = self.get_feature_columns(df, n_samples=n_samples, use_feature_selection=True)
        
        X = df[feature_cols]
        y = df['target']
        
        return X, y, feature_cols
    
    def train_models(self, X_train, y_train, X_test, y_test):
        """Train all three models with overfitting detection"""
        print("\n" + "="*80)
        print("TRAINING ML MODELS")
        print("="*80)
        
        results = {}
        overfitting_warnings = []
        
        # 1. Random Forest with adaptive complexity
        print("[train] RF: fitting...", flush=True)
        print("\n[1/3] Training Random Forest...")
        
        # Adaptive complexity based on data size
        n_train = len(X_train)
        n_features = X_train.shape[1]
        
        # Calculate optimal parameters based on data size
        # Rule: More data = can use more complex models
        if n_train < 200:
            # Very small dataset - very simple model
            n_estimators = 50
            max_depth = 3
            min_samples_split = max(20, n_train // 20)
            min_samples_leaf = max(10, n_train // 40)
        elif n_train < 500:
            # Small dataset - simple model
            n_estimators = 100
            max_depth = 4
            min_samples_split = max(15, n_train // 25)
            min_samples_leaf = max(8, n_train // 50)
        else:
            # Adequate dataset - moderate complexity
            n_estimators = 150
            max_depth = 5
            min_samples_split = 15
            min_samples_leaf = 8
        
        logger.info(f"RF adaptive params: n_est={n_estimators}, max_depth={max_depth}, min_split={min_samples_split}, min_leaf={min_samples_leaf} (data: {n_train} samples, {n_features} features)")
        
        rf_model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            max_features='sqrt',   # Reduce feature correlation
            min_impurity_decrease=0.01,  # Require significant improvement to split
            random_state=42,
            n_jobs=-1,
            verbose=0
        )
        rf_model.fit(X_train, y_train)
        
        # Calculate both train and test performance for overfitting detection
        rf_pred_train = rf_model.predict(X_train)
        rf_pred_test = rf_model.predict(X_test)
        
        rf_score_train = r2_score(y_train, rf_pred_train)
        rf_score_test = r2_score(y_test, rf_pred_test)
        rf_rmse_train = np.sqrt(mean_squared_error(y_train, rf_pred_train))
        rf_rmse_test = np.sqrt(mean_squared_error(y_test, rf_pred_test))
        rf_mae_test = mean_absolute_error(y_test, rf_pred_test)
        
        # Overfitting detection: Check if train performance is much better than test
        train_test_gap = rf_score_train - rf_score_test
        rmse_gap_ratio = rf_rmse_train / rf_rmse_test if rf_rmse_test > 0 else 1.0
        
        if train_test_gap > 0.15:  # Train R² > Test R² by more than 0.15
            warning = f"Random Forest: Possible overfitting detected! Train R²={rf_score_train:.4f} vs Test R²={rf_score_test:.4f} (gap={train_test_gap:.4f})"
            overfitting_warnings.append(warning)
            logger.warning(warning)
        elif rmse_gap_ratio < 0.7:  # Train RMSE much lower than test RMSE
            warning = f"Random Forest: Possible overfitting! Train RMSE={rf_rmse_train:.2f} vs Test RMSE={rf_rmse_test:.2f} (ratio={rmse_gap_ratio:.2f})"
            overfitting_warnings.append(warning)
            logger.warning(warning)
        
        self.models['random_forest'] = rf_model
        results['random_forest'] = {
            'r2_train': rf_score_train,
            'r2_test': rf_score_test,
            'r2': rf_score_test,  # Keep for backward compatibility
            'rmse_train': rf_rmse_train,
            'rmse_test': rf_rmse_test,
            'rmse': rf_rmse_test,  # Keep for backward compatibility
            'mae': rf_mae_test,
            'predictions': rf_pred_test,
            'overfitting_gap': train_test_gap
        }
        print(f"   Train R²: {rf_score_train:.4f} | Test R²: {rf_score_test:.4f} | Gap: {train_test_gap:+.4f}")
        print(f"   Train RMSE: {rf_rmse_train:.2f} | Test RMSE: {rf_rmse_test:.2f}")
        print(f"   Test MAE: {rf_mae_test:.2f}")
        print("[train] RF: done", flush=True)
        
        # 2. LightGBM with early stopping and adaptive complexity
        print("[train] LGB: fitting...", flush=True)
        print("\n[2/3] Training LightGBM...")
        
        # Split train into train and validation for early stopping
        from sklearn.model_selection import train_test_split as tts
        X_train_lgb, X_val_lgb, y_train_lgb, y_val_lgb = tts(
            X_train, y_train, test_size=0.15, shuffle=False, random_state=42
        )
        
        # Adaptive complexity based on data size
        if n_train < 200:
            n_estimators = 100
            max_depth = 3
            num_leaves = 8
            min_child_samples = max(30, n_train // 10)
            learning_rate = 0.01
            reg_alpha = 1.0
            reg_lambda = 2.0
        elif n_train < 500:
            n_estimators = 150
            max_depth = 4
            num_leaves = 15
            min_child_samples = 30
            learning_rate = 0.02
            reg_alpha = 0.7
            reg_lambda = 1.5
        else:
            n_estimators = 200
            max_depth = 5
            num_leaves = 20
            min_child_samples = 30
            learning_rate = 0.03
            reg_alpha = 0.5
            reg_lambda = 1.0
        
        logger.info(f"LGBM adaptive params: n_est={n_estimators}, max_depth={max_depth}, num_leaves={num_leaves}, min_child={min_child_samples} (data: {n_train} samples)")
        
        lgb_model = lgb.LGBMRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            num_leaves=num_leaves,
            min_child_samples=min_child_samples,
            subsample=0.7,         # Use less data
            colsample_bytree=0.7,  # Use fewer features
            reg_alpha=reg_alpha,    # L1 regularization
            reg_lambda=reg_lambda,  # L2 regularization
            min_gain_to_split=0.1, # Require significant gain to split
            random_state=42,
            verbose=-1
        )
        
        # Train with early stopping
        lgb_model.fit(
            X_train_lgb, y_train_lgb,
            eval_set=[(X_val_lgb, y_val_lgb)],
            callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
        )
        
        # Calculate both train and test performance
        lgb_pred_train = lgb_model.predict(X_train)
        lgb_pred_test = lgb_model.predict(X_test)
        
        lgb_score_train = r2_score(y_train, lgb_pred_train)
        lgb_score_test = r2_score(y_test, lgb_pred_test)
        lgb_rmse_train = np.sqrt(mean_squared_error(y_train, lgb_pred_train))
        lgb_rmse_test = np.sqrt(mean_squared_error(y_test, lgb_pred_test))
        lgb_mae_test = mean_absolute_error(y_test, lgb_pred_test)
        
        # Overfitting detection
        train_test_gap = lgb_score_train - lgb_score_test
        rmse_gap_ratio = lgb_rmse_train / lgb_rmse_test if lgb_rmse_test > 0 else 1.0
        
        if train_test_gap > 0.15:
            warning = f"LightGBM: Possible overfitting detected! Train R²={lgb_score_train:.4f} vs Test R²={lgb_score_test:.4f} (gap={train_test_gap:.4f})"
            overfitting_warnings.append(warning)
            logger.warning(warning)
        elif rmse_gap_ratio < 0.7:
            warning = f"LightGBM: Possible overfitting! Train RMSE={lgb_rmse_train:.2f} vs Test RMSE={lgb_rmse_test:.2f} (ratio={rmse_gap_ratio:.2f})"
            overfitting_warnings.append(warning)
            logger.warning(warning)
        
        self.models['lightgbm'] = lgb_model
        results['lightgbm'] = {
            'r2_train': lgb_score_train,
            'r2_test': lgb_score_test,
            'r2': lgb_score_test,
            'rmse_train': lgb_rmse_train,
            'rmse_test': lgb_rmse_test,
            'rmse': lgb_rmse_test,
            'mae': lgb_mae_test,
            'predictions': lgb_pred_test,
            'overfitting_gap': train_test_gap
        }
        print(f"   Train R²: {lgb_score_train:.4f} | Test R²: {lgb_score_test:.4f} | Gap: {train_test_gap:+.4f}")
        print(f"   Train RMSE: {lgb_rmse_train:.2f} | Test RMSE: {lgb_rmse_test:.2f}")
        print(f"   Test MAE: {lgb_mae_test:.2f}")
        print("[train] LGB: done", flush=True)
        
        # 3. XGBoost with early stopping and adaptive complexity
        print("[train] XGB: fitting...", flush=True)
        print("\n[3/3] Training XGBoost...")
        
        # Split train into train and validation for early stopping
        X_train_xgb, X_val_xgb, y_train_xgb, y_val_xgb = tts(
            X_train, y_train, test_size=0.15, shuffle=False, random_state=42
        )
        
        # Adaptive complexity based on data size
        if n_train < 200:
            n_estimators = 100
            max_depth = 3
            learning_rate = 0.01
            min_child_weight = max(15, n_train // 15)
            reg_alpha = 1.0
            reg_lambda = 3.0
            gamma = 0.3
        elif n_train < 500:
            n_estimators = 150
            max_depth = 4
            learning_rate = 0.02
            min_child_weight = 12
            reg_alpha = 0.7
            reg_lambda = 2.5
            gamma = 0.25
        else:
            n_estimators = 200
            max_depth = 5
            learning_rate = 0.03
            min_child_weight = 10
            reg_alpha = 0.5
            reg_lambda = 2.0
            gamma = 0.2
        
        logger.info(f"XGB adaptive params: n_est={n_estimators}, max_depth={max_depth}, min_child={min_child_weight}, lr={learning_rate} (data: {n_train} samples)")
        
        xgb_model = xgb.XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            min_child_weight=min_child_weight,
            subsample=0.7,         # Use less data
            colsample_bytree=0.7,  # Use fewer features
            gamma=gamma,            # Split threshold
            reg_alpha=reg_alpha,    # L1 regularization
            reg_lambda=reg_lambda,  # L2 regularization
            max_delta_step=1,      # Limit step size
            random_state=42,
            verbosity=0
        )
        
        # Train with early stopping (compatible with different XGBoost versions)
        # Note: Early stopping helps prevent overfitting, but strong regularization is already in place
        early_stopping_used = False
        try:
            # Try new callback API (XGBoost 2.0+)
            from xgboost.callback import EarlyStopping
            xgb_model.fit(
                X_train_xgb, y_train_xgb,
                eval_set=[(X_val_xgb, y_val_xgb)],
                callbacks=[EarlyStopping(rounds=20, save_best=True)],
                verbose=False
            )
            early_stopping_used = True
        except (ImportError, AttributeError, TypeError):
            # Fallback: Train without early stopping (regularization parameters still active)
            # The model already has strong regularization (reg_alpha=0.5, reg_lambda=2.0)
            # which helps prevent overfitting even without early stopping
            xgb_model.fit(
                X_train_xgb, y_train_xgb,
                eval_set=[(X_val_xgb, y_val_xgb)],  # Still evaluate for monitoring
                verbose=False
            )
            logger.info("XGBoost: Using regularization instead of early stopping (compatible with all versions)")
        
        # Calculate both train and test performance
        xgb_pred_train = xgb_model.predict(X_train)
        xgb_pred_test = xgb_model.predict(X_test)
        
        xgb_score_train = r2_score(y_train, xgb_pred_train)
        xgb_score_test = r2_score(y_test, xgb_pred_test)
        xgb_rmse_train = np.sqrt(mean_squared_error(y_train, xgb_pred_train))
        xgb_rmse_test = np.sqrt(mean_squared_error(y_test, xgb_pred_test))
        xgb_mae_test = mean_absolute_error(y_test, xgb_pred_test)
        
        # Overfitting detection
        train_test_gap = xgb_score_train - xgb_score_test
        rmse_gap_ratio = xgb_rmse_train / xgb_rmse_test if xgb_rmse_test > 0 else 1.0
        
        if train_test_gap > 0.15:
            warning = f"XGBoost: Possible overfitting detected! Train R²={xgb_score_train:.4f} vs Test R²={xgb_score_test:.4f} (gap={train_test_gap:.4f})"
            overfitting_warnings.append(warning)
            logger.warning(warning)
        elif rmse_gap_ratio < 0.7:
            warning = f"XGBoost: Possible overfitting! Train RMSE={xgb_rmse_train:.2f} vs Test RMSE={xgb_rmse_test:.2f} (ratio={rmse_gap_ratio:.2f})"
            overfitting_warnings.append(warning)
            logger.warning(warning)
        
        self.models['xgboost'] = xgb_model
        results['xgboost'] = {
            'r2_train': xgb_score_train,
            'r2_test': xgb_score_test,
            'r2': xgb_score_test,
            'rmse_train': xgb_rmse_train,
            'rmse_test': xgb_rmse_test,
            'rmse': xgb_rmse_test,
            'mae': xgb_mae_test,
            'predictions': xgb_pred_test,
            'overfitting_gap': train_test_gap
        }
        print(f"   Train R²: {xgb_score_train:.4f} | Test R²: {xgb_score_test:.4f} | Gap: {train_test_gap:+.4f}")
        print(f"   Train RMSE: {xgb_rmse_train:.2f} | Test RMSE: {xgb_rmse_test:.2f}")
        print(f"   Test MAE: {xgb_mae_test:.2f}")
        print("[train] XGB: done", flush=True)
        
        # Ensemble prediction with weighted average (exclude models with negative R²)
        # Weight models by their test R² performance (better models get more weight)
        model_weights = {}
        model_predictions_test = {}
        model_predictions_train = {}
        
        # Calculate weights based on test R² (only use models with positive or near-zero R²)
        for model_name, test_r2 in [('rf', rf_score_test), ('lgb', lgb_score_test), ('xgb', xgb_score_test)]:
            # Only include models with R² > -0.5 (exclude extremely bad models)
            if test_r2 > -0.5:
                # Convert R² to weight (negative R² gets very low weight)
                weight = max(0.1, test_r2 + 0.5)  # Shift so negative R² gets low but non-zero weight
                model_weights[model_name] = weight
            else:
                logger.warning(f"Excluding {model_name} from ensemble (test R²={test_r2:.4f} too negative)")
                model_weights[model_name] = 0.0
        
        # Normalize weights
        total_weight = sum(model_weights.values())
        if total_weight > 0:
            model_weights = {k: v / total_weight for k, v in model_weights.items()}
        else:
            # Fallback: equal weights if all models are bad
            logger.warning("All models have negative R², using equal weights")
            model_weights = {k: 1.0/3 for k in model_weights.keys()}
        
        # Weighted ensemble predictions
        ensemble_pred_test = (
            model_weights.get('rf', 0) * rf_pred_test +
            model_weights.get('lgb', 0) * lgb_pred_test +
            model_weights.get('xgb', 0) * xgb_pred_test
        )
        
        ensemble_pred_train = (
            model_weights.get('rf', 0) * rf_pred_train +
            model_weights.get('lgb', 0) * lgb_pred_train +
            model_weights.get('xgb', 0) * xgb_pred_train
        )
        
        ensemble_score = r2_score(y_test, ensemble_pred_test)
        ensemble_rmse = np.sqrt(mean_squared_error(y_test, ensemble_pred_test))
        ensemble_mae = mean_absolute_error(y_test, ensemble_pred_test)
        
        # Calculate ensemble train performance for overfitting detection
        ensemble_score_train = r2_score(y_train, ensemble_pred_train)
        ensemble_rmse_train = np.sqrt(mean_squared_error(y_train, ensemble_pred_train))
        ensemble_train_test_gap = ensemble_score_train - ensemble_score
        
        # Log ensemble weights
        logger.info(f"Ensemble weights: RF={model_weights.get('rf', 0):.3f}, LGBM={model_weights.get('lgb', 0):.3f}, XGB={model_weights.get('xgb', 0):.3f}")
        
        results['ensemble'] = {
            'r2_train': ensemble_score_train,
            'r2_test': ensemble_score,
            'r2': ensemble_score,
            'rmse_train': ensemble_rmse_train,
            'rmse_test': ensemble_rmse,
            'rmse': ensemble_rmse,
            'mae': ensemble_mae,
            'predictions': ensemble_pred_test,
            'overfitting_gap': ensemble_train_test_gap,
            'model_weights': model_weights  # Store weights for reference
        }
        
        print("\n" + "="*80)
        print("ENSEMBLE MODEL (Average of all 3)")
        print("="*80)
        print(f"   Train R²: {ensemble_score_train:.4f} | Test R²: {ensemble_score:.4f} | Gap: {ensemble_train_test_gap:+.4f}")
        print(f"   Train RMSE: {ensemble_rmse_train:.2f} | Test RMSE: {ensemble_rmse:.2f}")
        print(f"   Test MAE: {ensemble_mae:.2f}")
        
        # Display overfitting warnings if any
        if overfitting_warnings:
            print("\n" + "="*80)
            print("⚠️  OVERFITTING WARNINGS")
            print("="*80)
            for warning in overfitting_warnings:
                print(f"   ⚠️  {warning}")
            print("\n   💡 RECOMMENDATIONS:")
            print("      - Consider reducing model complexity (lower max_depth, fewer estimators)")
            print("      - Increase regularization (higher reg_alpha, reg_lambda)")
            print("      - Use more training data or reduce features")
            print("      - Consider ensemble methods to reduce variance")
            print("="*80)
        
        return results
    
    def save_models(self, symbol: str):
        """Save all trained models with horizon suffix"""
        for model_name, model in self.models.items():
            if model is not None:
                model_path = self.model_dir / f"{symbol}_{self.horizon}_{model_name}.pkl"
                joblib.dump(model, model_path)
                logger.info(f"Saved {model_name} model to {model_path}")
        
        # Save feature columns
        feature_path = self.model_dir / f"{symbol}_{self.horizon}_features.pkl"
        joblib.dump(self.feature_columns, feature_path)
        
        # Save horizon metadata
        metadata_path = self.model_dir / f"{symbol}_{self.horizon}_metadata.json"
        metadata = {
            'symbol': symbol,
            'horizon': self.horizon,
            'target_days': self.target_days,
            'trained_at': datetime.now().isoformat(),
            'feature_count': len(self.feature_columns)
        }
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n[OK] All models saved to {self.model_dir}/ with horizon: {self.horizon}")
    
    def load_models(self, symbol: str) -> bool:
        """Load trained models for this horizon"""
        try:
            for model_name in self.models.keys():
                model_path = self.model_dir / f"{symbol}_{self.horizon}_{model_name}.pkl"
                if model_path.exists():
                    print(f"[predict] load {model_name}...", flush=True)
                    self.models[model_name] = joblib.load(model_path)
                    print(f"[predict] load {model_name} done", flush=True)
                    logger.info(f"Loaded {model_name} model from {model_path}")
                else:
                    logger.warning(f"Model not found: {model_path}")
                    return False
            
            # Load feature columns
            feature_path = self.model_dir / f"{symbol}_{self.horizon}_features.pkl"
            if feature_path.exists():
                print("[predict] load features.pkl...", flush=True)
                self.feature_columns = joblib.load(feature_path)
                print("[predict] load features.pkl done", flush=True)
            else:
                logger.warning(f"Feature columns not found: {feature_path}")
                return False
            
            print(f"[OK] Models loaded successfully for horizon: {self.horizon}")
            return True
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            print(f"[ERROR] Could not load models: {e}")
            return False
    
    def predict(self, X: pd.DataFrame, current_price: float = None, historical_volatility: float = None) -> Dict:
        """Make predictions using all models with validation"""
        predictions = {}
        
        # Ensure we have the right features
        if self.feature_columns:
            X = X[self.feature_columns]
        
        # Get raw predictions
        raw_predictions = {}
        for model_name, model in self.models.items():
            if model is not None:
                pred = model.predict(X)
                raw_predictions[model_name] = pred
        
        # FIX 1: Cap predictions based on REALISTIC bounds for typical market conditions
        if current_price is not None and current_price > 0:
            # IMPROVED: More adaptive caps based on actual market behavior
            # Caps represent ~85th percentile of historical moves (more realistic)
            # Adjusted to allow for legitimate volatile stock movements
            base_max_move_pct = {
                'intraday': 0.05,  # 5% max per day (allows for volatile stocks)
                'short': 0.08,     # 8% max per 5 days (realistic for mid/small caps)
                'long': 0.20       # 20% max per 60 days (realistic for growth stocks)
            }.get(self.horizon, 0.20)
            
            # IMPROVED: More aggressive volatility-based adjustment
            if historical_volatility and historical_volatility > 0:
                # Enhanced volatility-based adjustment:
                # - Low volatility (0.01): 0.8x multiplier → 6.4% for short
                # - Normal volatility (0.02): 1.0x multiplier → 8% for short
                # - High volatility (0.04): 1.8x multiplier → 14.4% for short
                # - Very high volatility (0.06+): 2.5x multiplier → 20% for short (volatile stocks)
                volatility_factor = min(2.5, max(0.8, historical_volatility / 0.02))
                max_move_pct = base_max_move_pct * volatility_factor
            else:
                # No volatility data - use base cap (already more generous)
                max_move_pct = base_max_move_pct
            
            max_price = current_price * (1 + max_move_pct)
            min_price = current_price * (1 - max_move_pct)
            
            # Apply caps to each model and track if capping occurred
            capping_occurred = False
            max_uncapped_pct = 0.0  # Track maximum uncapped prediction for warning
            
            for model_name, pred in raw_predictions.items():
                # Cap prediction
                capped_pred = np.clip(pred, min_price, max_price)
                predictions[model_name] = capped_pred
                
                # Track uncapped percentage for warning logic
                uncapped_pct = abs((pred[0] - current_price) / current_price * 100)
                max_uncapped_pct = max(max_uncapped_pct, uncapped_pct)
                
                # Log if capping occurred (only if significant difference)
                if not np.array_equal(pred, capped_pred):
                    capped_pct = ((capped_pred[0] - current_price) / current_price * 100)
                    # Only warn if capping was significant (>2% difference)
                    if abs(uncapped_pct - abs(capped_pct)) > 2.0:
                        logger.info(f"{model_name}: Prediction adjusted from {uncapped_pct:+.1f}% to {capped_pct:+.1f}% (realistic bounds)")
                        print(f"[INFO] {model_name}: Prediction adjusted to realistic bounds ({capped_pct:+.1f}%)")
                    capping_occurred = True
            
            # Store capping info for later confidence adjustment
            if capping_occurred:
                predictions['_capping_occurred'] = True
                predictions['_max_uncapped_pct'] = max_uncapped_pct  # Store for warning logic
        else:
            # No current price for validation, use raw predictions
            predictions = raw_predictions
        
        # IMPROVED: Weighted ensemble prediction based on model agreement
        # Models that agree with each other get higher weight
        # This reduces impact of outliers and improves accuracy
        if 'random_forest' in predictions and 'lightgbm' in predictions and 'xgboost' in predictions:
            rf_pred = predictions['random_forest'][0]
            lgbm_pred = predictions['lightgbm'][0]
            xgb_pred = predictions['xgboost'][0]
            
            # Calculate pairwise agreement (inverse of distance)
            # Models closer to each other get higher weight
            rf_lgbm_dist = abs(rf_pred - lgbm_pred)
            rf_xgb_dist = abs(rf_pred - xgb_pred)
            lgbm_xgb_dist = abs(lgbm_pred - xgb_pred)
            
            # OVERFITTING DETECTION: High model disagreement suggests overfitting
            max_dist = max(rf_lgbm_dist, rf_xgb_dist, lgbm_xgb_dist)
            mean_pred = (rf_pred + lgbm_pred + xgb_pred) / 3
            std_pred = np.std([rf_pred, lgbm_pred, xgb_pred])
            cv_pred = std_pred / abs(mean_pred) if mean_pred != 0 else 0  # Coefficient of variation
            
            # Store disagreement metrics for overfitting detection
            predictions['_model_disagreement'] = {
                'max_distance': float(max_dist),
                'std': float(std_pred),
                'cv': float(cv_pred),  # High CV = high disagreement = possible overfitting
                'rf_lgbm_dist': float(rf_lgbm_dist),
                'rf_xgb_dist': float(rf_xgb_dist),
                'lgbm_xgb_dist': float(lgbm_xgb_dist)
            }
            
            # Calculate weights based on agreement
            # Lower distance = higher agreement = higher weight
            max_dist_for_weights = max(max_dist, 0.01)  # Avoid division by zero
            
            # RF weight: agreement with LGBM and XGB
            rf_weight = 1.0 / (1.0 + (rf_lgbm_dist + rf_xgb_dist) / max_dist_for_weights)
            # LGBM weight: agreement with RF and XGB
            lgbm_weight = 1.0 / (1.0 + (rf_lgbm_dist + lgbm_xgb_dist) / max_dist_for_weights)
            # XGB weight: agreement with RF and LGBM
            xgb_weight = 1.0 / (1.0 + (rf_xgb_dist + lgbm_xgb_dist) / max_dist_for_weights)
            
            # Normalize weights to sum to 1
            total_weight = rf_weight + lgbm_weight + xgb_weight
            rf_weight /= total_weight
            lgbm_weight /= total_weight
            xgb_weight /= total_weight
            
            # Weighted average
            ensemble_pred = (rf_pred * rf_weight + lgbm_pred * lgbm_weight + xgb_pred * xgb_weight)
            predictions['ensemble'] = np.array([ensemble_pred])
            
            # Store weights for debugging
            predictions['_ensemble_weights'] = {
                'random_forest': rf_weight,
                'lightgbm': lgbm_weight,
                'xgboost': xgb_weight
            }
            
            # OVERFITTING WARNING: If models disagree significantly, flag potential overfitting
            if current_price and current_price > 0:
                pred_pct = abs((ensemble_pred - current_price) / current_price * 100)
                # High disagreement (CV > 0.15) with significant prediction suggests overfitting
                if cv_pred > 0.15 and pred_pct > 2.0:
                    predictions['_overfitting_warning'] = (
                        f"High model disagreement (CV={cv_pred:.3f}) with significant prediction ({pred_pct:.2f}%). "
                        f"Possible overfitting - models may be memorizing noise."
                    )
                    logger.warning(predictions['_overfitting_warning'])
        else:
            # Fallback: if some models missing, use available ones with equal weight
            available_preds = []
            available_keys = []
            for key in ['random_forest', 'lightgbm', 'xgboost']:
                if key in predictions:
                    available_preds.append(predictions[key][0])
                    available_keys.append(key)
            
            if available_preds:
                predictions['ensemble'] = np.array([sum(available_preds) / len(available_preds)])
            else:
                # No predictions available, return 0 (should not happen)
                logger.error("No model predictions available for ensemble")
                predictions['ensemble'] = np.array([0.0])
        
        return predictions
    
    def get_feature_importance(self, top_n: int = 10) -> Dict:
        """Get feature importance from all models"""
        importance = {}
        
        if self.models['random_forest'] is not None:
            rf_imp = pd.DataFrame({
                'feature': self.feature_columns,
                'importance': self.models['random_forest'].feature_importances_
            }).sort_values('importance', ascending=False).head(top_n)
            importance['random_forest'] = rf_imp
        
        if self.models['lightgbm'] is not None:
            lgb_imp = pd.DataFrame({
                'feature': self.feature_columns,
                'importance': self.models['lightgbm'].feature_importances_
            }).sort_values('importance', ascending=False).head(top_n)
            importance['lightgbm'] = lgb_imp
        
        if self.models['xgboost'] is not None:
            xgb_imp = pd.DataFrame({
                'feature': self.feature_columns,
                'importance': self.models['xgboost'].feature_importances_
            }).sort_values('importance', ascending=False).head(top_n)
            importance['xgboost'] = xgb_imp
        
        return importance


# ============================================================================
# DATA FETCHING FUNCTION
# ============================================================================

def fetch_stock_data(symbols: List[str]):
    """Fetch data for multiple stock symbols"""
    print(f"\n{'='*80}")
    print(f"FETCHING DATA FOR {len(symbols)} STOCK(S)")
    print(f"{'='*80}")
    
    for i, sym in enumerate(symbols, 1):
        print(f"{i}. {sym}")
    
    print(f"{'='*80}\n")
    
    # Initialize ingester
    ingester = EnhancedDataIngester()
    
    # Fetch data for each symbol
    for i, symbol in enumerate(symbols, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(symbols)}] FETCHING: {symbol}")
        print(f"{'='*80}")
        
        try:
            # Fetch ALL available data
            print(f"\nFetching ALL yfinance data for {symbol}...")
            all_data = ingester.fetch_all_data(
                symbol,
                period="2y",
                include_fundamentals=True,
                include_analyst=True,
                include_ownership=True,
                include_earnings=True,
                include_options=False,
                include_news=True
            )
            
            # Get basic OHLCV
            df = all_data.get('price_history', pd.DataFrame())
            
            if not df.empty:
                # Save complete data in JSON format
                json_path = ingester.cache_dir / f"{symbol}_all_data.json"
                
                # Convert to JSON-serializable format
                company_info = all_data.get('info', {}).copy()
                fields_to_remove = ['bid', 'ask', 'bidSize', 'askSize']
                for field in fields_to_remove:
                    company_info.pop(field, None)
                
                json_data = {
                    'metadata': all_data.get('metadata', {}),
                    'price_history': df.to_dict('records') if not df.empty else [],
                    'price_summary': {
                        'rows': len(df),
                        'start_date': str(df.index[0]) if not df.empty else None,
                        'end_date': str(df.index[-1]) if not df.empty else None,
                        'latest_close': float(df['Close'].iloc[-1]) if not df.empty else None
                    },
                    'company_info': company_info,
                    'analyst_recommendations': all_data.get('recommendations').to_dict('records') if all_data.get('recommendations') is not None and not all_data.get('recommendations').empty else [],
                    'financials_available': not all_data.get('financials', pd.DataFrame()).empty,
                    'balance_sheet_available': not all_data.get('balance_sheet', pd.DataFrame()).empty,
                    'cashflow_available': not all_data.get('cashflow', pd.DataFrame()).empty,
                    'earnings': all_data.get('earnings').to_dict() if all_data.get('earnings') is not None and not all_data.get('earnings').empty else {},
                    'news': all_data.get('news', [])
                }
                
                with open(json_path, 'w') as f:
                    json.dump(json_data, f, indent=2, default=str)
                
                print(f"\n  -> Data saved in 2 formats:")
                print(f"     1. Parquet (fast, OHLCV data): {cache_path}")
                print(f"     2. JSON (complete, readable): {json_path}")
                
                # Display comprehensive data summary
                display_data_summary(symbol, all_data, df)
                
            else:
                print(f"\n[FAILED] {symbol}: No data received")
        
        except Exception as e:
            print(f"\n[ERROR] {symbol}: {e}")
    
    print(f"\n{'='*80}")
    print("DATA FETCHING COMPLETE FOR ALL STOCKS")
    print(f"{'='*80}")
    print(f"\nFetched data for {len(symbols)} stock(s)")
    print(f"\nData saved in JSON format:")
    print(f"   JSON (complete data): data/cache/SYMBOL_all_data.json")
    print(f"{'='*80}\n")


def display_data_summary(symbol: str, all_data: Dict, df: pd.DataFrame):
    """Display comprehensive summary of fetched data"""
    print(f"\n{'='*70}")
    print(f"[SUCCESS] {symbol} - COMPLETE DATA FETCHED")
    print(f"{'='*70}")
    
    print(f"\n{'='*70}")
    print(f"DATA FETCHED - ALL 10 CATEGORIES")
    print(f"{'='*70}")
    
    # 1. PRICE HISTORY
    print(f"\n[1/10] PRICE HISTORY:")
    print(f"   Total Rows: {len(df)}")
    print(f"   Date Range: {df.index[0]} to {df.index[-1]}")
    print(f"   Latest Price: Rs.{df['Close'].iloc[-1]:.2f}")
    print(f"\n   Last 5 Days:")
    print(f"   {df[['Open', 'High', 'Low', 'Close', 'Volume']].tail().to_string()}")
    
    # 2. COMPANY INFO
    info = all_data.get('info', {})
    print(f"\n[2/10] COMPANY INFO ({len(info)} fields):")
    print(f"   Company: {info.get('longName', 'N/A')}")
    print(f"   Sector: {info.get('sector', 'N/A')}")
    print(f"   Industry: {info.get('industry', 'N/A')}")
    print(f"   Market Cap: ${info.get('marketCap', 0)/1e9:.2f}B")
    print(f"   P/E Ratio: {info.get('trailingPE', 'N/A')}")
    print(f"   P/B Ratio: {info.get('priceToBook', 'N/A')}")
    print(f"   Dividend Yield: {info.get('dividendYield', 0)*100:.2f}%")
    print(f"   Beta: {info.get('beta', 'N/A')}")
    print(f"   52-Week High: Rs.{info.get('fiftyTwoWeekHigh', 0):.2f}")
    print(f"   52-Week Low: Rs.{info.get('fiftyTwoWeekLow', 0):.2f}")
    print(f"   ROE: {info.get('returnOnEquity', 0)*100:.2f}%")
    print(f"   Profit Margin: {info.get('profitMargins', 0)*100:.2f}%")
    
    # 3. FUNDAMENTALS
    financials = all_data.get('financials', pd.DataFrame())
    balance_sheet = all_data.get('balance_sheet', pd.DataFrame())
    cashflow = all_data.get('cashflow', pd.DataFrame())
    print(f"\n[3/10] FINANCIAL STATEMENTS:")
    if financials is not None and not financials.empty:
        print(f"   Income Statement: {financials.shape[0]} rows x {financials.shape[1]} periods")
        print(f"   Available: {', '.join(list(financials.index)[:5])}...")
    else:
        print(f"   Income Statement: Not available")
    
    if balance_sheet is not None and not balance_sheet.empty:
        print(f"   Balance Sheet: {balance_sheet.shape[0]} rows x {balance_sheet.shape[1]} periods")
    else:
        print(f"   Balance Sheet: Not available")
    
    if cashflow is not None and not cashflow.empty:
        print(f"   Cash Flow: {cashflow.shape[0]} rows x {cashflow.shape[1]} periods")
    else:
        print(f"   Cash Flow: Not available")
    
    # 4. ANALYST DATA
    recs = all_data.get('recommendations', pd.DataFrame())
    print(f"\n[4/10] ANALYST RECOMMENDATIONS:")
    if recs is not None and not recs.empty:
        print(f"   Total Records: {len(recs)}")
        print(f"   Latest 5 Recommendations:")
        print(f"   {recs.tail(5).to_string()}")
    else:
        print(f"   No analyst recommendations available")
    
    if info:
        print(f"\n   Analyst Price Targets:")
        print(f"   - Target Mean: Rs.{info.get('targetMeanPrice', 0):.2f}")
        print(f"   - Target High: Rs.{info.get('targetHighPrice', 0):.2f}")
        print(f"   - Target Low: Rs.{info.get('targetLowPrice', 0):.2f}")
        print(f"   - Recommendation: {info.get('recommendationKey', 'N/A').upper()}")
        print(f"   - Num Analysts: {info.get('numberOfAnalystOpinions', 0)}")
    
    # 5. OWNERSHIP DATA
    major_holders = all_data.get('major_holders', pd.DataFrame())
    institutional = all_data.get('institutional_holders', pd.DataFrame())
    print(f"\n[5/10] OWNERSHIP DATA:")
    if major_holders is not None and not major_holders.empty:
        print(f"   Major Holders:")
        print(f"   {major_holders.to_string()}")
    else:
        print(f"   Major Holders: Not available")
    
    if institutional is not None and not institutional.empty:
        print(f"\n   Top 3 Institutional Holders:")
        print(f"   {institutional.head(3).to_string()}")
    
    # 6. EARNINGS DATA
    earnings = all_data.get('earnings', pd.DataFrame())
    quarterly_earnings = all_data.get('quarterly_earnings', pd.DataFrame())
    print(f"\n[6/10] EARNINGS DATA:")
    if earnings is not None and not earnings.empty:
        print(f"   Annual Earnings:")
        print(f"   {earnings.to_string()}")
    else:
        print(f"   Annual Earnings: Not available")
    
    if quarterly_earnings is not None and not quarterly_earnings.empty:
        print(f"\n   Quarterly Earnings (latest 4):")
        print(f"   {quarterly_earnings.tail(4).to_string()}")
    
    # 7. CORPORATE ACTIONS
    dividends = all_data.get('dividends', pd.Series())
    splits = all_data.get('splits', pd.Series())
    print(f"\n[7/10] CORPORATE ACTIONS:")
    if dividends is not None and len(dividends) > 0:
        print(f"   Dividends (last 5):")
        print(f"   {dividends.tail().to_string()}")
    else:
        print(f"   Dividends: None")
    
    if splits is not None and len(splits) > 0:
        print(f"\n   Stock Splits:")
        print(f"   {splits.to_string()}")
    else:
        print(f"   Stock Splits: None")
    
    # 8. OPTIONS
    print(f"\n[8/10] OPTIONS DATA:")
    print(f"   Skipped (can be slow, enable with include_options=True)")
    
    # 9. CALENDAR
    calendar = all_data.get('calendar', {})
    print(f"\n[9/10] CALENDAR EVENTS:")
    if calendar:
        for key, value in calendar.items():
            print(f"   {key}: {value}")
    else:
        print(f"   No calendar events available")
    
    # 10. NEWS
    news = all_data.get('news', [])
    print(f"\n[10/10] RECENT NEWS:")
    if news:
        print(f"   Total Articles: {len(news)}")
        for idx, article in enumerate(news[:5], 1):
            print(f"\n   Article {idx}:")
            print(f"   Title: {article.get('title', 'No title')}")
            print(f"   Publisher: {article.get('publisher', 'Unknown')}")
            print(f"   Published: {article.get('providerPublishTime', 'Unknown')}")
            if 'link' in article:
                print(f"   Link: {article['link']}")
    else:
        print(f"   No news available")


# ============================================================================
# VIEW FINANCIAL STATEMENTS FUNCTION
# ============================================================================

def view_financial_statements(symbol: str):
    """View financial statements from JSON file"""
    print("\n" + "="*80)
    print(" " * 25 + "FINANCIAL STATEMENT VIEWER")
    print("="*80)
    
    # Load JSON file
    json_path = Path(f"data/cache/{symbol}_all_data.json")
    
    if not json_path.exists():
        print(f"\n[ERROR] No data found for {symbol}")
        print(f"Please fetch the data first using option 1.")
        return
    
    print(f"\nLoading data from: {json_path}")
    
    # Load the complete data using the EnhancedDataIngester
    ingester = EnhancedDataIngester()
    all_data = ingester.load_all_data(symbol)
    
    if not all_data:
        print(f"\n[ERROR] Could not load data for {symbol}")
        return
    
    print(f"\n{'='*80}")
    print(f"FINANCIAL STATEMENTS FOR {symbol}")
    print(f"{'='*80}")
    
    # 1. INCOME STATEMENT
    print(f"\n{'='*80}")
    print("[1/3] INCOME STATEMENT (Financials)")
    print(f"{'='*80}")
    
    financials = all_data.get('financials', pd.DataFrame())
    if financials is not None and not financials.empty:
        print(f"\nShape: {financials.shape[0]} line items  {financials.shape[1]} periods")
        print(f"\nAvailable Line Items:")
        for idx, item in enumerate(financials.index, 1):
            print(f"  {idx}. {item}")
        
        print(f"\n\nFull Income Statement:")
        print(financials.to_string())
        
        # Export to CSV
        csv_path = Path(f"data/cache/{symbol}_income_statement.csv")
        financials.to_csv(csv_path)
        print(f"\n[OK] Saved to: {csv_path}")
    else:
        print("\n[NOT AVAILABLE] No income statement data")
    
    # 2. BALANCE SHEET
    print(f"\n{'='*80}")
    print("[2/3] BALANCE SHEET")
    print(f"{'='*80}")
    
    balance_sheet = all_data.get('balance_sheet', pd.DataFrame())
    if balance_sheet is not None and not balance_sheet.empty:
        print(f"\nShape: {balance_sheet.shape[0]} line items  {balance_sheet.shape[1]} periods")
        print(f"\nAvailable Line Items:")
        for idx, item in enumerate(balance_sheet.index, 1):
            print(f"  {idx}. {item}")
        
        print(f"\n\nFull Balance Sheet:")
        print(balance_sheet.to_string())
        
        # Export to CSV
        csv_path = Path(f"data/cache/{symbol}_balance_sheet.csv")
        balance_sheet.to_csv(csv_path)
        print(f"\n[OK] Saved to: {csv_path}")
    else:
        print("\n[NOT AVAILABLE] No balance sheet data")
    
    # 3. CASH FLOW STATEMENT
    print(f"\n{'='*80}")
    print("[3/3] CASH FLOW STATEMENT")
    print(f"{'='*80}")
    
    cashflow = all_data.get('cashflow', pd.DataFrame())
    if cashflow is not None and not cashflow.empty:
        print(f"\nShape: {cashflow.shape[0]} line items  {cashflow.shape[1]} periods")
        print(f"\nAvailable Line Items:")
        for idx, item in enumerate(cashflow.index, 1):
            print(f"  {idx}. {item}")
        
        print(f"\n\nFull Cash Flow Statement:")
        print(cashflow.to_string())
        
        # Export to CSV
        csv_path = Path(f"data/cache/{symbol}_cashflow.csv")
        cashflow.to_csv(csv_path)
        print(f"\n[OK] Saved to: {csv_path}")
    else:
        print("\n[NOT AVAILABLE] No cash flow data")
    
    print(f"\n{'='*80}")
    print("FINANCIAL STATEMENTS VIEWING COMPLETE")
    print(f"{'='*80}")
    print(f"\nAll financial statements exported to CSV files in data/cache/")
    print(f"You can open them in Excel or any text editor.")
    print(f"{'='*80}\n")


# ============================================================================
# NEWS SENTIMENT ANALYSIS
# ============================================================================

def extract_key_technical_indicators(latest_features: pd.DataFrame) -> Dict[str, any]:
    """
    Extract key technical indicators that justify model predictions
    
    Args:
        latest_features: DataFrame with latest technical indicators (single row)
        
    Returns:
        Dictionary with key technical indicators and their interpretations
    """
    if latest_features.empty:
        return {'summary': 'No technical data available'}
    
    indicators = {}
    
    # RSI (Relative Strength Index) - Momentum
    if 'RSI_14' in latest_features.columns:
        rsi = latest_features['RSI_14'].iloc[0]
        if not pd.isna(rsi):
            indicators['RSI'] = round(float(rsi), 1)
            if rsi > 70:
                indicators['RSI_signal'] = 'Overbought (Bearish)'
            elif rsi < 30:
                indicators['RSI_signal'] = 'Oversold (Bullish)'
            else:
                indicators['RSI_signal'] = 'Neutral'
    
    # MACD - Trend momentum
    if 'MACD' in latest_features.columns and 'MACD_signal' in latest_features.columns:
        macd = latest_features['MACD'].iloc[0]
        macd_signal = latest_features['MACD_signal'].iloc[0]
        if not pd.isna(macd) and not pd.isna(macd_signal):
            indicators['MACD'] = round(float(macd), 2)
            indicators['MACD_signal'] = round(float(macd_signal), 2)
            if macd < macd_signal:
                indicators['MACD_trend'] = 'Bearish'
            elif macd > macd_signal:
                indicators['MACD_trend'] = 'Bullish'
            else:
                indicators['MACD_trend'] = 'Neutral'
    
    # Price vs Moving Averages - Trend direction
    if 'Close' in latest_features.columns:
        close = latest_features['Close'].iloc[0]
        ma_signals = []
        
        for ma_period in [10, 20, 50, 200]:
            ma_col = f'SMA_{ma_period}'
            if ma_col in latest_features.columns:
                ma_value = latest_features[ma_col].iloc[0]
                if not pd.isna(ma_value) and close > 0:
                    pct_diff = ((close - ma_value) / close) * 100
                    if abs(pct_diff) > 1:  # Only show if significant
                        ma_signals.append(f"SMA{ma_period}:{pct_diff:+.1f}%")
        
        if ma_signals:
            indicators['MA_position'] = ' | '.join(ma_signals[:2])  # Limit to 2 most relevant
    
    # Bollinger Bands - Volatility and support/resistance
    if 'BB_upper' in latest_features.columns and 'BB_lower' in latest_features.columns and 'Close' in latest_features.columns:
        bb_upper = latest_features['BB_upper'].iloc[0]
        bb_lower = latest_features['BB_lower'].iloc[0]
        close = latest_features['Close'].iloc[0]
        if not pd.isna(bb_upper) and not pd.isna(bb_lower) and not pd.isna(close):
            if close > bb_upper:
                indicators['BB_position'] = 'Above Upper (Overbought)'
            elif close < bb_lower:
                indicators['BB_position'] = 'Below Lower (Oversold)'
            else:
                bb_middle = (bb_upper + bb_lower) / 2
                if close > bb_middle:
                    indicators['BB_position'] = 'Upper Half'
                else:
                    indicators['BB_position'] = 'Lower Half'
    
    # ADX - Trend strength
    if 'ADX' in latest_features.columns:
        adx = latest_features['ADX'].iloc[0]
        if not pd.isna(adx):
            indicators['ADX'] = round(float(adx), 1)
            if adx > 25:
                indicators['ADX_strength'] = 'Strong Trend'
            elif adx > 20:
                indicators['ADX_strength'] = 'Moderate Trend'
            else:
                indicators['ADX_strength'] = 'Weak Trend'
    
    # Volume indicators
    if 'OBV' in latest_features.columns:
        # OBV trend (compare with previous if available)
        obv = latest_features['OBV'].iloc[0]
        if not pd.isna(obv):
            indicators['OBV'] = f"{obv/1e9:.2f}B" if obv > 1e9 else f"{obv/1e6:.2f}M"
    
    # Build detailed summary string with all available indicators
    summary_parts = []
    detailed_parts = []  # More detailed version for reason field
    
    if 'RSI_signal' in indicators:
        summary_parts.append(f"RSI:{indicators['RSI']}({indicators['RSI_signal']})")
        detailed_parts.append(f"RSI:{indicators['RSI']} ({indicators['RSI_signal']})")
    
    if 'MACD_trend' in indicators:
        macd_val = indicators.get('MACD', 'N/A')
        macd_sig = indicators.get('MACD_signal', 'N/A')
        summary_parts.append(f"MACD:{indicators['MACD_trend']}")
        detailed_parts.append(f"MACD:{macd_val}/{macd_sig} ({indicators['MACD_trend']})")
    
    if 'MA_position' in indicators:
        summary_parts.append(indicators['MA_position'])
        detailed_parts.append(indicators['MA_position'])
    
    if 'BB_position' in indicators:
        summary_parts.append(f"BB:{indicators['BB_position']}")
        detailed_parts.append(f"BB:{indicators['BB_position']}")
    
    if 'ADX_strength' in indicators:
        summary_parts.append(f"ADX:{indicators['ADX']}({indicators['ADX_strength']})")
        detailed_parts.append(f"ADX:{indicators['ADX']} ({indicators['ADX_strength']})")
    
    # Create both compact and detailed summaries
    indicators['summary'] = ' | '.join(summary_parts) if summary_parts else 'Limited indicators'
    indicators['detailed'] = ' | '.join(detailed_parts) if detailed_parts else 'Limited indicators'
    
    return indicators


def analyze_news_sentiment(news_data: List[Dict]) -> Dict[str, any]:
    """
    Analyze news sentiment from cached news data
    
    Args:
        news_data: List of news articles from cache
        
    Returns:
        Dictionary with sentiment analysis results
    """
    if not news_data or len(news_data) == 0:
        return {
            'sentiment': 'neutral',
            'score': 0.0,
            'count': 0,
            'summary': 'No news available'
        }
    
    # Simple keyword-based sentiment analysis
    positive_keywords = [
        'surge', 'gain', 'rise', 'up', 'growth', 'profit', 'beat', 'exceed',
        'strong', 'bullish', 'rally', 'soar', 'jump', 'climb', 'boost',
        'positive', 'outperform', 'upgrade', 'buy', 'outperform', 'breakthrough'
    ]
    
    negative_keywords = [
        'fall', 'drop', 'decline', 'down', 'loss', 'miss', 'below', 'weak',
        'bearish', 'crash', 'plunge', 'slump', 'dip', 'worry', 'concern',
        'negative', 'underperform', 'downgrade', 'sell', 'warning', 'risk'
    ]
    
    sentiment_scores = []
    recent_news_count = 0
    
    # Analyze recent news (last 10 articles)
    for article in news_data[:10]:
        title = article.get('title', '').lower()
        summary = article.get('summary', '').lower() if 'summary' in article else ''
        text = f"{title} {summary}"
        
        positive_count = sum(1 for keyword in positive_keywords if keyword in text)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text)
        
        if positive_count > negative_count:
            sentiment_scores.append(1)
        elif negative_count > positive_count:
            sentiment_scores.append(-1)
        else:
            sentiment_scores.append(0)
        
        recent_news_count += 1
    
    if len(sentiment_scores) == 0:
        return {
            'sentiment': 'neutral',
            'score': 0.0,
            'count': 0,
            'summary': 'No analyzable news'
        }
    
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
    
    if avg_sentiment > 0.2:
        sentiment = 'bullish'
        summary = f"Recent news is positive ({recent_news_count} articles analyzed)"
    elif avg_sentiment < -0.2:
        sentiment = 'bearish'
        summary = f"Recent news is negative ({recent_news_count} articles analyzed)"
    else:
        sentiment = 'neutral'
        summary = f"Recent news is mixed/neutral ({recent_news_count} articles analyzed)"
    
    return {
        'sentiment': sentiment,
        'score': round(avg_sentiment, 2),
        'count': recent_news_count,
        'summary': summary
    }


# ============================================================================
# FEATURE CALCULATION AND VIEWING FUNCTIONS
# ============================================================================

def calculate_technical_indicators(symbol: str):
    """Calculate technical indicators for a symbol"""
    print("\n" + "="*80)
    print(" " * 20 + "CALCULATE TECHNICAL INDICATORS")
    print("="*80)
    
    # Check if data exists
    cache_path = get_symbol_cache_path(symbol)
    json_path = DATA_CACHE_DIR / f"{symbol}_all_data.json"
    
    df = None
    
    # Load from JSON cache
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                cached_data = json.load(f)
            
            # Extract price_history from JSON
            if 'price_history' in cached_data and cached_data['price_history']:
                df = pd.DataFrame(cached_data['price_history'])
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                elif df.index.name != 'Date' and not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)
                print(f"\n[INFO] Loaded data from JSON cache: {len(df)} rows")
        except Exception as e:
            print(f"[WARNING] Could not load from JSON cache: {e}")
    
    # If no cache exists, return None
    if df is None or df.empty:
        if json_path.exists():
            try:
                ingester_temp = EnhancedDataIngester()
                all_data = ingester_temp.load_all_data(symbol)
                if all_data:
                    df = all_data.get('price_history', pd.DataFrame())
                    print(f"\n[INFO] Loaded data from JSON: {len(df)} rows")
            except Exception as e:
                print(f"[WARNING] Could not load from JSON: {e}")
    
    # If still no data, fetch fresh
    if df is None or df.empty:
        print(f"\n[INFO] No cached data found. Fetching fresh data for {symbol}...")
        ingester = EnhancedDataIngester()
        df = ingester.fetch_live_data(symbol, period="2y")
        
        if df.empty:
            print(f"\n[ERROR] Could not fetch data for {symbol}")
            return
    
    # Clean data - check if index is DatetimeIndex before accessing tzinfo
    if isinstance(df.index, pd.DatetimeIndex) and df.index.tzinfo is not None:
        df.index = df.index.tz_localize(None)
    
    # Calculate features
    engineer = FeatureEngineer()
    features_df = engineer.calculate_all_features(df, symbol)
    
    if not features_df.empty:
        # Save features
        engineer.save_features(features_df, symbol)
        print(f"\n[OK] Technical indicators calculated and saved!")
        print(f"Location: {FEATURE_CACHE_DIR / f'{symbol}_features.json'}")
    else:
        print(f"\n[ERROR] Feature calculation failed")


def view_technical_indicators(symbol: str):
    """View previously calculated technical indicators"""
    print("\n" + "="*80)
    print(" " * 20 + "VIEW TECHNICAL INDICATORS")
    print("="*80)
    
    engineer = FeatureEngineer()
    live_data = engineer.load_features(symbol)
    
    if not live_data:
        print(f"\n[ERROR] No technical indicators found for {symbol}")
        print(f"Please calculate indicators first using option 2.")
        return
    
    # Display the features
    current_features = live_data.get('current_features', {})
    print(f"\n{'='*80}")
    print(f"TECHNICAL INDICATORS FOR {symbol}")
    print(f"{'='*80}")
    print(f"\nFetch Time: {live_data.get('fetch_time', 'N/A')}")
    print(f"Latest Date: {live_data.get('latest_date', 'N/A')}")
    print(f"Data Freshness: {live_data.get('data_freshness_days', 0)} days old")
    print(f"Current Price: Rs.{live_data.get('current_price', 0):.2f}")
    print(f"Total Features: {live_data.get('total_features', 0)}")
    
    print(f"\nKEY INDICATORS (Current Values):")
    print(f"  RSI_14:        {current_features.get('RSI_14', 0):.2f}")
    print(f"  MACD:          {current_features.get('MACD', 0):.4f}")
    print(f"  MACD_signal:   {current_features.get('MACD_signal', 0):.4f}")
    print(f"  SMA_10:        Rs.{current_features.get('SMA_10', 0):.2f}")
    print(f"  SMA_20:        Rs.{current_features.get('SMA_20', 0):.2f}")
    print(f"  SMA_50:        Rs.{current_features.get('SMA_50', 0):.2f}")
    print(f"  SMA_200:       Rs.{current_features.get('SMA_200', 0):.2f}")
    print(f"  BB_upper:      Rs.{current_features.get('BB_upper', 0):.2f}")
    print(f"  BB_middle:     Rs.{current_features.get('BB_middle', 0):.2f}")
    print(f"  BB_lower:      Rs.{current_features.get('BB_lower', 0):.2f}")
    print(f"  ATR_14:        {current_features.get('ATR', 0):.2f}")
    print(f"  Volume:        {current_features.get('Volume', 0):,.0f}")
    print(f"  OBV:           {current_features.get('OBV', 0):,.0f}")
    print(f"  ADX:           {current_features.get('ADX', 0):.2f}")
    
    print(f"\nTREND ANALYSIS:")
    print(f"  Price/SMA_50:  {current_features.get('price_to_sma_50', 0):.4f} ({'Above' if current_features.get('price_to_sma_50', 0) > 1 else 'Below'} 50-day avg)")
    print(f"  Price/SMA_200: {current_features.get('price_to_sma_200', 0):.4f} ({'Above' if current_features.get('price_to_sma_200', 0) > 1 else 'Below'} 200-day avg)")
    print(f"  MA_alignment:  {current_features.get('MA_alignment', 0):.2f} (0=bearish, 1=bullish)")
    print(f"  Trend:         {'Uptrend' if current_features.get('trend_direction', 0) > 0 else 'Downtrend'}")
    
    print(f"\nMOMENTUM:")
    print(f"  RSI Status:    {'Overbought' if current_features.get('RSI_14', 50) > 70 else 'Oversold' if current_features.get('RSI_14', 50) < 30 else 'Neutral'}")
    print(f"  MACD Signal:   {'Bullish' if current_features.get('MACD_hist', 0) > 0 else 'Bearish'}")
    
    print(f"\n{'='*80}\n")


def complete_analysis(symbol: str):
    """Complete analysis: Fetch data, calculate features, and show everything"""
    print("\n" + "="*80)
    print(" " * 20 + "COMPLETE STOCK ANALYSIS")
    print("="*80)
    print(f"\nAnalyzing {symbol}...")
    print("This will:")
    print("  1. Fetch all stock data from Yahoo Finance")
    print("  2. Calculate 50+ technical indicators")
    print("  3. Display comprehensive analysis")
    print("="*80)
    
    # Step 1: Fetch data
    print(f"\n[STEP 1/3] Fetching stock data...")
    ingester = EnhancedDataIngester()
    
    # Check if data already exists
    json_path = DATA_CACHE_DIR / f"{symbol}_all_data.json"
    if json_path.exists():
        print(f"[INFO] Found existing data, loading...")
        all_data = ingester.load_all_data(symbol)
    else:
        print(f"[INFO] Fetching fresh data...")
        all_data = ingester.fetch_all_data(
            symbol,
            period="2y",
            include_fundamentals=True,
            include_analyst=True,
            include_ownership=True,
            include_earnings=True,
            include_options=False,
            include_news=True
        )
        
        # Get price history data
        df_temp = all_data.get('price_history', pd.DataFrame())
        
        if not df_temp.empty:
            # Save complete data in JSON format
            json_path = ingester.cache_dir / f"{symbol}_all_data.json"
            company_info = all_data.get('info', {}).copy()
            fields_to_remove = ['bid', 'ask', 'bidSize', 'askSize']
            for field in fields_to_remove:
                company_info.pop(field, None)
            
            json_data = {
                'metadata': all_data.get('metadata', {}),
                'price_history': df_temp.to_dict('records') if not df_temp.empty else [],
                'price_summary': {
                    'rows': len(df_temp),
                    'start_date': str(df_temp.index[0]) if not df_temp.empty else None,
                    'end_date': str(df_temp.index[-1]) if not df_temp.empty else None,
                    'latest_close': float(df_temp['Close'].iloc[-1]) if not df_temp.empty else None
                },
                'company_info': company_info,
                'analyst_recommendations': all_data.get('recommendations').to_dict('records') if all_data.get('recommendations') is not None and not all_data.get('recommendations').empty else [],
                'financials_available': not all_data.get('financials', pd.DataFrame()).empty,
                'balance_sheet_available': not all_data.get('balance_sheet', pd.DataFrame()).empty,
                'cashflow_available': not all_data.get('cashflow', pd.DataFrame()).empty,
                'earnings': all_data.get('earnings').to_dict() if all_data.get('earnings') is not None and not all_data.get('earnings').empty else {},
                'news': all_data.get('news', [])
            }
            
            with open(json_path, 'w') as f:
                json.dump(json_data, f, indent=2, default=str)
            
            print(f"[INFO] Data saved in 2 formats:")
            print(f"  1. Parquet (OHLCV data): {get_symbol_cache_path(symbol)}")
            print(f"  2. JSON (complete data): {json_path}")
    
    if not all_data:
        print(f"\n[ERROR] Could not fetch data for {symbol}")
        return
    try:
        import pandas_ta as ta  # Technical indicators
    except ImportError:
        print("Warning: pandas_ta not available. Some technical indicators may not work.")
        ta = None

    # Try classic import - comment out if causes issues
    # try:
    #     from pandas_ta_classic import pandas_ta_classic
    # except ImportError:
    #     pandas_ta_classic = None
    
    # Step 2: Calculate technical indicators
    print(f"\n[STEP 2/3] Calculating technical indicators...")
    df = all_data.get('price_history', pd.DataFrame())
    
    if df.empty:
        print(f"[ERROR] No price data available")
        return
    
    # Clean data - check if index is DatetimeIndex before accessing tzinfo
    if isinstance(df.index, pd.DatetimeIndex) and df.index.tzinfo is not None:
        df.index = df.index.tz_localize(None)
    
    engineer = FeatureEngineer()
    features_df = engineer.calculate_all_features(df, symbol)
    
    if not features_df.empty:
        engineer.save_features(features_df, symbol)
    
    # Step 3: Display comprehensive analysis
    print(f"\n[STEP 3/3] Displaying comprehensive analysis...")
    print(f"\n{'='*80}")
    print(f"COMPLETE ANALYSIS FOR {symbol}")
    print(f"{'='*80}")
    
    # Show data summary
    display_data_summary(symbol, all_data, df)
    
    # Show technical indicators if available
    if not features_df.empty:
        print(f"\n{'='*80}")
        print("TECHNICAL INDICATORS SUMMARY")
        print(f"{'='*80}")
        engineer.save_features(features_df, symbol)  # This will print the indicators
    
    print(f"\n{'='*80}")
    print("COMPLETE ANALYSIS FINISHED")
    print(f"{'='*80}\n")


# ============================================================================
# PREDICTION LOGGING
# ============================================================================

def load_feedback_memory() -> List[Dict]:
    """Load feedback memory from JSON"""
    feedback_path = LOGS_DIR / "feedback_memory.json"
    if feedback_path.exists():
        try:
            with open(feedback_path, 'r') as f:
                return json.load(f)
        except:
            return []
    return []


def provide_feedback(symbol: str, predicted_action: str, user_feedback: str, actual_return: Optional[float] = None):
    """
    Provide feedback for RL fine-tuning with logical validation
    
    Args:
        symbol: Stock symbol
        predicted_action: The action that was predicted (LONG/SHORT/HOLD)
        user_feedback: User's feedback (correct/incorrect)
        actual_return: Actual return percentage (optional)
    
    Returns:
        dict: Feedback entry with validation status
    """
    feedback_path = LOGS_DIR / "feedback_memory.json"
    feedback_memory = load_feedback_memory()
    
    # VALIDATION: Check if feedback is logically consistent with actual_return
    validation_warning = None
    suggested_feedback = None
    
    if actual_return is not None:
        # Define thresholds
        HOLD_THRESHOLD = 2.0  # ±2% is considered HOLD range
        SIGNIFICANT_MOVE = 1.0  # >1% is considered significant
        
        # Validate SHORT predictions
        if predicted_action.upper() == 'SHORT':
            if actual_return > SIGNIFICANT_MOVE:
                # Predicted DOWN but price went UP significantly
                suggested_feedback = 'incorrect'
                if user_feedback.lower() == 'correct':
                    validation_warning = f"LOGIC ERROR: Predicted SHORT but return was +{actual_return:.1f}%. Feedback should be 'incorrect'."
            elif actual_return < -SIGNIFICANT_MOVE:
                # Predicted DOWN and price went DOWN - correct
                suggested_feedback = 'correct'
                if user_feedback.lower() == 'incorrect':
                    validation_warning = f"LOGIC ERROR: Predicted SHORT and return was {actual_return:.1f}%. Feedback should be 'correct'."
        
        # Validate LONG predictions
        elif predicted_action.upper() == 'LONG':
            if actual_return < -SIGNIFICANT_MOVE:
                # Predicted UP but price went DOWN significantly
                suggested_feedback = 'incorrect'
                if user_feedback.lower() == 'correct':
                    validation_warning = f"LOGIC ERROR: Predicted LONG but return was {actual_return:.1f}%. Feedback should be 'incorrect'."
            elif actual_return > SIGNIFICANT_MOVE:
                # Predicted UP and price went UP - correct
                suggested_feedback = 'correct'
                if user_feedback.lower() == 'incorrect':
                    validation_warning = f"LOGIC ERROR: Predicted LONG and return was +{actual_return:.1f}%. Feedback should be 'correct'."
        
        # Validate HOLD predictions
        elif predicted_action.upper() == 'HOLD':
            if abs(actual_return) > HOLD_THRESHOLD:
                # Predicted small movement but got significant movement
                suggested_feedback = 'incorrect'
                if user_feedback.lower() == 'correct':
                    validation_warning = f"LOGIC ERROR: Predicted HOLD but return was {actual_return:+.1f}% (> {HOLD_THRESHOLD}%). Feedback should be 'incorrect'."
            elif abs(actual_return) <= HOLD_THRESHOLD:
                # Predicted small movement and got small movement - correct
                suggested_feedback = 'correct'
                if user_feedback.lower() == 'incorrect':
                    validation_warning = f"LOGIC ERROR: Predicted HOLD and return was {actual_return:+.1f}% (<= {HOLD_THRESHOLD}%). Feedback should be 'correct'."
    
    feedback_entry = {
        'timestamp': datetime.now().isoformat(),
        'symbol': symbol,
        'predicted_action': predicted_action,
        'user_feedback': user_feedback,
        'actual_return': actual_return
    }
    
    # REJECT contradictory feedback to prevent training data corruption
    if validation_warning:
        feedback_entry['validation_warning'] = validation_warning
        feedback_entry['suggested_feedback'] = suggested_feedback
        logger.warning(f"Feedback validation error for {symbol}: {validation_warning}")
        print(f"\n[ERROR] {validation_warning}")
        print(f"[SUGGESTION] Please use feedback='{suggested_feedback}' instead")
        print(f"[ACTION] Feedback NOT saved to prevent training data corruption")
        
        # Return error without saving
        return {
            'status': 'error',
            'error': 'Feedback contradicts actual return',
            'validation_warning': validation_warning,
            'suggested_feedback': suggested_feedback,
            'feedback_saved': None
        }
    
    # Save only if validation passes
    feedback_memory.append(feedback_entry)
    
    with open(feedback_path, 'w') as f:
        # Use default=str to handle any numpy types (e.g., if actual_return is numpy type)
        json.dump(feedback_memory, f, indent=2, default=str)
    
    logger.info(f"Feedback saved for {symbol}: {user_feedback}")
    
    return {
        'status': 'success',
        'feedback_saved': feedback_entry,
        'validation_warning': None,
        'suggested_feedback': None
    }


def log_prediction(
    symbol: str,
    current_price: float,
    predicted_price: float,
    action: str,
    confidence: float,
    individual_predictions: Dict,
    ensemble_details: Dict,
    features: Dict = None
):
    """
    Log prediction to JSON file in specified format
    
    Args:
        symbol: Stock symbol
        current_price: Current stock price
        predicted_price: Ensemble predicted price
        action: Trading action (LONG/SHORT/HOLD)
        confidence: Confidence score
        individual_predictions: Dict with individual model predictions
        ensemble_details: Dict with ensemble analysis details
        features: Dict with all feature values used for prediction
    """
    # Calculate predicted return
    predicted_return = ((predicted_price - current_price) / current_price) * 100
    
    # Create prediction entry - ensure all values are JSON serializable (convert numpy types to Python types)
    prediction_entry = {
        "symbol": str(symbol),
        "timestamp": datetime.now().isoformat(),
        "current_price": round(float(current_price), 2),
        "predicted_price": round(float(predicted_price), 2),
        "predicted_return": round(float(predicted_return), 2),
        "action": str(action),
        "score": round(float(confidence), 4),
        "confidence": round(float(confidence), 4),
        "reason": str(ensemble_details.get('reason', 'Ensemble prediction')),
        "model_version": "ensemble-v3(rf+lgbm+xgb+dqn)",
        "ensemble_details": {
            "decision_maker": str(ensemble_details.get('decision_maker', '')),
            "price_agreement": bool(ensemble_details.get('price_agreement', False)),
            "models_align": bool(ensemble_details.get('models_align', False)),
            "total_vote": round(float(ensemble_details.get('total_vote', 0.0)), 4),
            "reason": str(ensemble_details.get('reason', ''))
        },
        "individual_predictions": individual_predictions
    }
    
    # Features are stored separately in data/features/ - not needed in prediction logs
    # This keeps logs/predictions.json clean and focused on prediction results only
    
    # Load existing predictions or create new list
    predictions_list = []
    if PREDICTION_LOG_FILE.exists():
        try:
            with open(PREDICTION_LOG_FILE, 'r') as f:
                predictions_list = json.load(f)
                if not isinstance(predictions_list, list):
                    predictions_list = []
        except Exception as e:
            logger.warning(f"Could not load existing predictions: {e}")
            predictions_list = []
    
    # Append new prediction
    predictions_list.append(prediction_entry)
    
    # Keep only last 1000 predictions to prevent file from growing too large
    if len(predictions_list) > 1000:
        predictions_list = predictions_list[-1000:]
    
    # Save to file
    try:
        with open(PREDICTION_LOG_FILE, 'w') as f:
            # Use default=str to handle any numpy types that slip through explicit conversions
            json.dump(predictions_list, f, indent=2, default=str)
        
        logger.info(f"Prediction logged to {PREDICTION_LOG_FILE}")
        print(f"\n[OK] Prediction logged to: {PREDICTION_LOG_FILE}")
    except Exception as e:
        logger.error(f"Error logging prediction: {e}")
        print(f"\n[WARNING] Could not log prediction: {e}")


# ============================================================================
# ML MODEL TRAINING AND PREDICTION FUNCTIONS
# ============================================================================

def train_ml_models(symbol: str, horizon: str = "intraday", verbose: bool = True):
    """
    Train ALL 4 ML models (RF, LightGBM, XGBoost, DQN) for price prediction
    
    Args:
        symbol: Stock symbol
        horizon: "intraday" (1 day), "short" (5 days), or "long" (30 days)
        verbose: Whether to print output (False for API usage)
    
    Returns:
        bool: True if training successful, False otherwise
    """
    horizon_days = {"intraday": 1, "short": 5, "long": 30}
    target_days = horizon_days.get(horizon, 1)
    
    if verbose:
        print("\n" + "="*80)
        print(f" TRAIN ALL ML MODELS - {horizon.upper()} ({target_days} days)")
        print("="*80)
        print("\nThis will train 4 models:")
        print("  1. Random Forest (Tree-based ensemble)")
        print("  2. LightGBM (Gradient boosting)")
        print("  3. XGBoost (Extreme gradient boosting)")
        print("  4. DQN Agent (Deep Reinforcement Learning)")
        print("="*80)
    
    print("[train] start", flush=True)
    # Check if features exist
    cache_path = get_symbol_cache_path(symbol)
    
    if not cache_path.exists():
        if verbose:
            print(f"\n[ERROR] No data found for {symbol}")
            print(f"Please fetch data and calculate features first (Option 1 & 2)")
        return False
    
    print("[train] load cache...", flush=True)
    # Load data from JSON
    with open(cache_path, 'r') as f:
        cached_data = json.load(f)
    
    # Extract price_history from JSON
    if 'price_history' in cached_data and cached_data['price_history']:
        df = pd.DataFrame(cached_data['price_history'])
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
        elif df.index.name != 'Date' and not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
    else:
        if verbose:
            print(f"\n[ERROR] No price history found in cached data")
        return False
    print("[train] load cache done", flush=True)
    
    # Calculate features if not already done
    engineer = FeatureEngineer()
    print("[train] calculate_all_features (in train_ml_models)...", flush=True)
    if verbose:
        print(f"\n[INFO] Calculating technical indicators...")
    features_df = engineer.calculate_all_features(df, symbol)
    print("[train] calculate_all_features done", flush=True)
    
    if features_df.empty:
        if verbose:
            print(f"\n[ERROR] Feature calculation failed")
        return False
    
    # Prepare data for ML (for price prediction models)
    print("[train] prepare_data...", flush=True)
    if verbose:
        print(f"\n[INFO] Preparing data for machine learning...")
    predictor = StockPricePredictor(horizon=horizon)
    X, y, feature_cols = predictor.prepare_data(features_df, target_days=target_days)
    print("[train] prepare_data done", flush=True)
    predictor.feature_columns = feature_cols
    
    if verbose:
        print(f"   Total samples: {len(X)}")
        print(f"   Total features: {len(feature_cols)}")
    
    # Split data
    test_size = 0.2
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, shuffle=False, random_state=42
    )
    
    if verbose:
        print(f"   Training samples: {len(X_train)}")
        print(f"   Testing samples: {len(X_test)}")
    
    # ========== PART 1: Train Price Prediction Models (RF, LightGBM, XGBoost) ==========
    print("[train] train_models (RF+LGB+XGB)...", flush=True)
    results = predictor.train_models(X_train, y_train, X_test, y_test)
    print("[train] train_models done", flush=True)
    
    # Display model comparison
    if verbose:
        print(f"\n{'='*80}")
        print("PRICE PREDICTION MODELS PERFORMANCE")
        print(f"{'='*80}")
        print(f"{'Model':<20} {'R Score':<15} {'RMSE':<15} {'MAE':<15}")
        print("-"*80)
        
        for model_name, metrics in results.items():
            print(f"{model_name.upper():<20} {metrics['r2']:<15.4f} {metrics['rmse']:<15.2f} {metrics['mae']:<15.2f}")
    
    # Save price prediction models
    print("[train] save_models...", flush=True)
    predictor.save_models(symbol)
    print("[train] save_models done", flush=True)
    
    # Show feature importance
    if verbose:
        print(f"\n{'='*80}")
        print("TOP 10 MOST IMPORTANT FEATURES")
        print(f"{'='*80}")
        
        importance = predictor.get_feature_importance(top_n=10)
        
        for model_name, imp_df in importance.items():
            print(f"\n{model_name.upper()}:")
            for idx, row in imp_df.iterrows():
                print(f"   {row['feature']:<30} {row['importance']:.4f}")
    
    # ========== PART 2: Train DQN Agent (Reinforcement Learning) ==========
    print("[train] DQN: prepare data...", flush=True)
    if verbose:
        print(f"\n{'='*80}")
        print("TRAINING DQN AGENT (REINFORCEMENT LEARNING)")
        print(f"{'='*80}")
        print(f"\n[INFO] Preparing DQN training data...")
        print(f"   Feature columns count: {len(feature_cols)}")
        print(f"   Sample feature names: {feature_cols[:5]}")
    
    # Create properly structured DataFrame for DQN with EXACT same features
    dqn_features_df = features_df[feature_cols].copy()
    print("[train] DQN: data prepared", flush=True)
    
    # Extract returns for reward calculation (must match the length)
    returns_series = features_df['daily_return'].iloc[:len(dqn_features_df)]
    
    # Initialize DQN agent with EXACT same number of features as price models
    if verbose:
        print(f"\n[INFO] Initializing DQN agent...")
        print(f"   Input features:     {len(feature_cols)}")
        print(f"   Training samples:   {len(dqn_features_df)}")
        print(f"   Returns samples:    {len(returns_series)}")
    
    print("[train] DQN: init agent...", flush=True)
    dqn_agent = DQNTradingAgent(
        n_features=len(feature_cols),  # EXACT same as other models
        learning_rate=0.001,
        gamma=0.99,
        epsilon_start=1.0,
        epsilon_end=0.01,
        epsilon_decay=0.995,
        buffer_size=10000,
        batch_size=32,
        target_update_freq=10
    )
    
    # CRITICAL: Store feature columns in agent for consistency
    # This ensures training and prediction use EXACTLY the same features
    dqn_agent.feature_columns = feature_cols.copy()  # Use copy to prevent mutation
    print("[train] DQN: init done", flush=True)
    
    # VALIDATION: Verify feature dimensions match
    if len(feature_cols) != dqn_agent.n_features:
        error_msg = f"CRITICAL: Feature dimension mismatch! feature_cols={len(feature_cols)} but DQN initialized with n_features={dqn_agent.n_features}"
        logger.error(error_msg)
        print(f"\n[ERROR] {error_msg}")
        return {"success": False, "error": error_msg}
    
    if verbose:
        print(f"\n[INFO] Starting DQN training...")
        print(f"   Episodes: {len(dqn_features_df)}")
        print(f"   Device: {dqn_agent.device}")
        print(f"   Expected input shape: (batch_size, {len(feature_cols)})")
        print(f"   Feature columns saved: {len(feature_cols)} (will be used in prediction)")
    
    # Train DQN with the properly prepared features (cap episodes on Render so first request completes in ~1-2 min)
    _dqn_ep = os.environ.get("DQN_EPISODES", "").strip()
    if _dqn_ep.isdigit():
        n_episodes = min(int(_dqn_ep), len(dqn_features_df))
    else:
        # On Render/server, cap at 50 so async predict job completes before frontend gives up; locally use full data
        default_cap = 50 if os.environ.get("RENDER") else len(dqn_features_df)
        n_episodes = min(default_cap, len(dqn_features_df))
    print(f"[train] DQN: train (episodes={n_episodes})...", flush=True)
    dqn_metrics = dqn_agent.train(dqn_features_df, returns_series, n_episodes=n_episodes)
    print("[train] DQN: train done", flush=True)
    
    if verbose:
        print(f"\n{'='*80}")
        print("DQN AGENT PERFORMANCE")
        print(f"{'='*80}")
        print(f"   Total Episodes:     {dqn_metrics['total_episodes']}")
        print(f"   Cumulative Reward:  {dqn_metrics['cumulative_reward']:.4f}")
        print(f"   Average Reward:     {dqn_metrics['average_reward']:.6f}")
        print(f"   Sharpe Ratio:       {dqn_metrics['sharpe_ratio']:.4f}")
        print(f"   Win Rate:           {dqn_metrics['win_rate']:.2%}")
        print(f"   Final Epsilon:      {dqn_metrics['epsilon']:.4f}")
        print(f"   Replay Buffer Size: {dqn_metrics['buffer_size']}")
    
    # Save DQN agent
    print("[train] DQN: save...", flush=True)
    dqn_agent.save(symbol, horizon)
    print("[train] DQN: save done", flush=True)
    print("[train] all done", flush=True)
    
    if verbose:
        print(f"\n{'='*80}")
        print(f"ALL 4 MODELS TRAINING COMPLETE - {horizon.upper()}")
        print(f"{'='*80}")
        print(f"\nOK Models saved:")
        print(f"   1. Random Forest:   models/{symbol}_{horizon}_random_forest.pkl")
        print(f"   2. LightGBM:        models/{symbol}_{horizon}_lightgbm.pkl")
        print(f"   3. XGBoost:         models/{symbol}_{horizon}_xgboost.pkl")
        print(f"   4. DQN Agent:       models/{symbol}_{horizon}_dqn_agent.pt")
        print(f"\nYou can now use Option 8 to make predictions with all 4 models!")
        print(f"{'='*80}\n")
    
    # Return True for backward compatibility, but also include DQN metrics
    return {"success": True, "dqn_metrics": dqn_metrics}


def predict_stock_price(symbol: str, horizon: str = "intraday", verbose: bool = True):
    """
    Predict future stock price using ALL 4 trained models (RF, LightGBM, XGBoost, DQN)
    
    Args:
        symbol: Stock symbol
        horizon: "intraday" (1 day), "short" (5 days), or "long" (30 days)
        verbose: Whether to print output (False for API usage)
    
    Returns:
        dict: Prediction results with all model outputs and features
    """
    # Initialize warning flags list (used throughout the function)
    warning_flags = []
    
    print("[predict] start", flush=True)
    if verbose:
        print("\n" + "="*80)
        print(" " * 15 + f"STOCK PRICE PREDICTION - {horizon.upper()}")
        print("="*80)
    
    # Load price prediction models (RF, LightGBM, XGBoost)
    predictor = StockPricePredictor(horizon=horizon)
    print("[predict] load_models (RF+LGB+XGB+features)...", flush=True)
    if not predictor.load_models(symbol):
        if verbose:
            print(f"\n[INFO] No trained models found for {symbol} ({horizon})")
            print(f"[INFO] Auto-training models now... (this will take 60-90 seconds)")
        
        # AUTO-TRAIN: Train models automatically if they don't exist
        training_result = train_ml_models(symbol, horizon=horizon, verbose=verbose)
        
        if not training_result or (isinstance(training_result, dict) and not training_result.get('success', False)):
            if verbose:
                print(f"\n[ERROR] Auto-training failed for {symbol} ({horizon})")
            return None
        
        # Try loading again after training
        if not predictor.load_models(symbol):
            if verbose:
                print(f"\n[ERROR] Models still not available after training")
            return None
        
        if verbose:
            print(f"[OK] Models auto-trained and loaded successfully!")
    print("[predict] load_models done", flush=True)
    
    # Load DQN agent
    print("[predict] load DQN...", flush=True)
    dqn_agent = DQNTradingAgent(n_features=1)  # Will be updated when loading
    try:
        dqn_agent.load(symbol, horizon)
        dqn_available = True
        print("[predict] load DQN done", flush=True)
        if verbose:
            print(f"[OK] DQN agent loaded successfully")
    except FileNotFoundError as e:
        if verbose:
            print(f"\n[INFO] DQN agent not found for {symbol} ({horizon})")
            print(f"[INFO] DQN is optional - continuing with 3 price prediction models")
            print(f"[INFO] For better accuracy, train DQN using the training endpoint")
        dqn_available = False
        logger.info(f"DQN agent not found for {symbol} ({horizon}): {e}")
    except ValueError as e:
        # Dimension mismatch or checkpoint inconsistency
        if verbose:
            print(f"\n[ERROR] DQN checkpoint dimension mismatch: {e}")
            print(f"        This usually means the model was trained with different features")
            print(f"        Solution: Retrain DQN using /tools/train_rl endpoint")
            print(f"        Continuing with price prediction models only...")
        dqn_available = False
        logger.error(f"DQN dimension mismatch for {symbol} ({horizon}): {e}")
    except KeyError as e:
        # Missing required keys in checkpoint
        if verbose:
            print(f"\n[ERROR] DQN checkpoint is missing required data: {e}")
            print(f"        The checkpoint file may be corrupted or incomplete")
            print(f"        Solution: Delete the checkpoint and retrain DQN")
            print(f"        Continuing with price prediction models only...")
        dqn_available = False
        logger.error(f"DQN checkpoint missing keys for {symbol} ({horizon}): {e}")
    except RuntimeError as e:
        # State dict mismatch or device issues
        if verbose:
            print(f"\n[ERROR] DQN model structure mismatch: {e}")
            print(f"        This may be due to model architecture changes or device mismatch")
            print(f"        Solution: Retrain DQN or check CUDA/CPU compatibility")
            print(f"        Continuing with price prediction models only...")
        dqn_available = False
        logger.error(f"DQN runtime error for {symbol} ({horizon}): {e}")
    except (EOFError, PermissionError, OSError) as e:
        # File corruption or access issues
        if verbose:
            print(f"\n[ERROR] DQN checkpoint file issue: {e}")
            print(f"        The checkpoint file may be corrupted or inaccessible")
            print(f"        Solution: Check file permissions or delete and retrain")
            print(f"        Continuing with price prediction models only...")
        dqn_available = False
        logger.error(f"DQN file error for {symbol} ({horizon}): {e}")
    except Exception as e:
        # Catch-all for any other unexpected errors
        if verbose:
            print(f"\n[ERROR] Failed to load DQN agent: {e}")
            print(f"        Error type: {type(e).__name__}")
            print(f"        Continuing with price prediction models only...")
        dqn_available = False
        logger.error(f"DQN loading failed for {symbol} ({horizon}): {type(e).__name__}: {e}", exc_info=True)
    
    # Load historical 2y data + latest live prices
    print("[predict] load data (ingester)...", flush=True)
    ingester = EnhancedDataIngester()
    
    if verbose:
        print(f"\n[INFO] Loading data strategy:")
        print(f"  -> Step 1: Load 2-year historical data (patterns & context)")
        print(f"  -> Step 2: Fetch latest live prices (current market)")
        print(f"  -> Step 3: Merge for comprehensive analysis")
    
    # Try to load 2y cached data first
    all_data = ingester.load_all_data(symbol)
    print("[predict] load data done", flush=True)
    
    # Extract news data for sentiment analysis
    news_data = all_data.get('news', []) if all_data else []
    
    # Check data source to determine if news is available
    data_source = 'yfinance'  # Default
    if all_data:
        if 'metadata' in all_data:
            data_source = all_data['metadata'].get('data_source', 'yfinance')
        elif 'price_history_metadata' in all_data:
            data_source = all_data['price_history_metadata'].get('data_source', 'yfinance')
        else:
            # Infer from news availability - if no news and Indian stock, likely BHAV
            news_data_check = all_data.get('news', [])
            if (not news_data_check or len(news_data_check) == 0) and (symbol.endswith('.NS') or symbol.endswith('.BO')):
                # Check if news was explicitly set to empty vs just not available
                # If metadata says has_news=False, it's BHAV
                if all_data.get('metadata', {}).get('has_news') is False:
                    data_source = 'nse_bhav'
                # Otherwise assume yfinance (news might just be unavailable for other reasons)
    
    if all_data and 'price_history' in all_data:
        df_historical = all_data['price_history'].copy()
        if verbose:
            print(f"  -> [OK] Loaded {len(df_historical)} days of historical data from cache")
    else:
        # No cache, fetch 2y data (will fallback to NSE Bhav if yfinance fails)
        if verbose:
            print(f"  -> Cache not found, fetching 2y historical data (will fallback to NSE Bhav if needed)...")
        df_historical = ingester.fetch_live_data(symbol, period="2y")
        
        # If still empty after fallback, try fetch_all_data which also has fallback
        if df_historical.empty:
            if verbose:
                print(f"  -> fetch_live_data returned empty, trying fetch_all_data with fallback...")
            try:
                all_data_fresh = ingester.fetch_all_data(symbol, period="2y")
                if all_data_fresh and 'price_history' in all_data_fresh:
                    df_historical = all_data_fresh['price_history']
                    # Update all_data with fresh data
                    all_data = all_data_fresh
                    # Update data_source
                    if all_data and 'metadata' in all_data:
                        data_source = all_data['metadata'].get('data_source', 'yfinance')
            except Exception as e:
                logger.error(f"fetch_all_data also failed for {symbol}: {e}")
    
    # Fetch latest live data (last 5 days to ensure we have today's prices)
    # Only fetch if historical data is older than 2 days (to avoid redundant fetches)
    need_latest = True
    if not df_historical.empty:
        latest_date_in_historical = df_historical.index.max()
        # Remove timezone for comparison
        if hasattr(latest_date_in_historical, 'tz_localize'):
            latest_date_naive = latest_date_in_historical.tz_localize(None) if latest_date_in_historical.tzinfo else latest_date_in_historical
        else:
            latest_date_naive = latest_date_in_historical.replace(tzinfo=None) if hasattr(latest_date_in_historical, 'tzinfo') and latest_date_in_historical.tzinfo else latest_date_in_historical
        
        now_naive = datetime.now()
        days_old = (now_naive - latest_date_naive).days
        
        if days_old <= 2:
            # Historical data is recent enough (within 2 days), skip redundant fetch
            if verbose:
                print(f"  -> Historical data is recent (latest: {latest_date_naive.date()}, {days_old} days old), skipping redundant 5-day fetch")
            need_latest = False
            df_latest = pd.DataFrame()  # Empty - will use historical data only
    
    if need_latest:
        # This will also fallback to NSE Bhav if yfinance fails
        if verbose:
            print(f"  -> Fetching latest 5-day live prices (will fallback to NSE Bhav if needed)...")
        df_latest = ingester.fetch_live_data(symbol, period="5d")
    
    # Merge: Use historical + update with latest prices
    if not df_latest.empty and not df_historical.empty:
        # Normalize timezones to naive for consistent comparison
        if isinstance(df_historical.index, pd.DatetimeIndex) and df_historical.index.tzinfo is not None:
            df_historical.index = df_historical.index.tz_localize(None)
        if isinstance(df_latest.index, pd.DatetimeIndex) and df_latest.index.tzinfo is not None:
            df_latest.index = df_latest.index.tz_localize(None)
        
        # Sort both DataFrames to ensure correct date ordering
        df_historical = df_historical.sort_index()
        df_latest = df_latest.sort_index()
        
        # Get the minimum (oldest) date from latest data to remove overlap
        # This ensures we don't remove historical data that's newer than the oldest latest data
        min_latest_date = df_latest.index.min()
        
        # Remove historical data that overlaps with latest data (keep only data before latest)
        df_historical = df_historical[df_historical.index < min_latest_date]
        
        # Concatenate historical and latest data
        df = pd.concat([df_historical, df_latest])
        
        # Sort before deduplication to ensure correct order
        df = df.sort_index()
        
        # Remove duplicates, keeping the last (newest) value for each date
        df = df[~df.index.duplicated(keep='last')]
        
        if verbose:
            print(f"  -> [OK] Combined dataset: {len(df)} days total")
            print(f"       Historical: {len(df_historical)} days")
            print(f"       Latest: {len(df_latest)} days")
            print(f"       Latest price date: {df.index[-1]}")
    elif not df_latest.empty:
        df = df_latest
        if verbose:
            print(f"  -> Using only latest data: {len(df)} days")
    elif not df_historical.empty:
        df = df_historical
        if verbose:
            print(f"  -> Using only historical data: {len(df)} days")
    else:
        if verbose:
            print(f"\n[ERROR] No data available for {symbol}")
        return None
    
    if df.empty:
        if verbose:
            print(f"\n[ERROR] No data found for {symbol}")
        return None
    
    # Calculate features
    print("[predict] calculate_all_features (for prediction)...", flush=True)
    engineer = FeatureEngineer()
    if verbose:
        print(f"\n[INFO] Calculating technical indicators...")
    
    # Clean data before calculating features
    if isinstance(df.index, pd.DatetimeIndex) and df.index.tzinfo is not None:
        df.index = df.index.tz_localize(None)
    
    features_df = engineer.calculate_all_features(df, symbol)
    print("[predict] calculate_all_features done", flush=True)
    
    if features_df.empty:
        print(f"\n[ERROR] Feature calculation failed")
        return
    
    # Get latest data point for prediction
    latest_features = features_df.tail(1)
    latest_price = latest_features['Close'].iloc[0]
    latest_date = latest_features.index[0]
    
    # Extract key technical indicators for reason field
    tech_indicators = extract_key_technical_indicators(latest_features)
    
    # ========== VALIDATION: Explicit check for invalid price data ==========
    # Defensive programming - prevent division by zero in return calculations
    if latest_price <= 0 or np.isnan(latest_price) or np.isinf(latest_price):
        error_msg = f"Invalid latest_price={latest_price} for {symbol}. Unable to calculate returns."
        logger.error(error_msg)
        if verbose:
            print(f"\n[ERROR] {error_msg}")
            print(f"[ERROR] This indicates a data quality issue with {symbol}")
        return None
    
    # ========== PART 1: Price Prediction Models ==========
    print(f"\n[INFO] Making price predictions...")
    
    # Calculate historical volatility for validation
    if len(df) > 30:
        returns = df['Close'].pct_change().dropna()
        historical_volatility = returns.std()
    else:
        historical_volatility = None
    
    # Make predictions with validation
    print("[predict] ensemble predict (RF+LGB+XGB)...", flush=True)
    price_predictions = predictor.predict(latest_features, current_price=latest_price, historical_volatility=historical_volatility)
    print("[predict] ensemble predict done", flush=True)
    
    # ========== OVERFITTING ANALYSIS: Analyze what prices models are predicting ==========
    prediction_analysis = {}
    if 'random_forest' in price_predictions and 'lightgbm' in price_predictions and 'xgboost' in price_predictions:
        rf_pred = float(price_predictions['random_forest'][0])
        lgbm_pred = float(price_predictions['lightgbm'][0])
        xgb_pred = float(price_predictions['xgboost'][0])
        
        predictions_list = [rf_pred, lgbm_pred, xgb_pred]
        pred_returns = [((p - latest_price) / latest_price * 100) for p in predictions_list]
        
        # Calculate prediction spread (high disagreement = possible overfitting)
        pred_std = np.std(pred_returns)
        pred_range = max(pred_returns) - min(pred_returns)
        
        prediction_analysis = {
            'rf_price': round(rf_pred, 2),
            'lgbm_price': round(lgbm_pred, 2),
            'xgb_price': round(xgb_pred, 2),
            'rf_return': round(pred_returns[0], 2),
            'lgbm_return': round(pred_returns[1], 2),
            'xgb_return': round(pred_returns[2], 2),
            'prediction_std': round(pred_std, 2),
            'prediction_range': round(pred_range, 2),
            'high_disagreement': bool(pred_range > 3.0),  # More than 3% spread suggests overfitting - convert to Python bool
            'avg_prediction': round(np.mean(predictions_list), 2),
            'avg_return': round(np.mean(pred_returns), 2)
        }
        
        # Validate against historical volatility
        if historical_volatility and historical_volatility > 0:
            # For 5-day horizon, expected move = volatility * sqrt(5) * z-score
            expected_5d_vol = historical_volatility * np.sqrt(5) * 1.5  # 1.5 sigma (reasonable)
            avg_abs_return = abs(prediction_analysis['avg_return'])
            
            prediction_analysis['historical_volatility'] = round(historical_volatility * 100, 2)
            prediction_analysis['expected_5d_move'] = round(expected_5d_vol * 100, 2)
            prediction_analysis['realistic'] = bool(avg_abs_return <= (expected_5d_vol * 100 * 1.5))  # Allow 1.5x for extreme moves - convert to Python bool
            
            if not prediction_analysis['realistic']:
                logger.warning(f"Prediction may be unrealistic: {avg_abs_return:.2f}% predicted vs {expected_5d_vol * 100:.2f}% expected based on volatility")
        
        # Log prediction analysis
        if verbose:
            print(f"\n[INFO] Prediction Analysis:")
            print(f"   RF: Rs.{rf_pred:.2f} ({pred_returns[0]:+.2f}%)")
            print(f"   LGBM: Rs.{lgbm_pred:.2f} ({pred_returns[1]:+.2f}%)")
            print(f"   XGB: Rs.{xgb_pred:.2f} ({pred_returns[2]:+.2f}%)")
            print(f"   Prediction Spread: {pred_range:.2f}% (std: {pred_std:.2f}%)")
            if prediction_analysis.get('high_disagreement'):
                print(f"   ⚠️  HIGH DISAGREEMENT: Models disagree by {pred_range:.2f}% - possible overfitting")
            if historical_volatility:
                print(f"   Historical Volatility: {historical_volatility * 100:.2f}%")
                print(f"   Expected 5-day move: ±{expected_5d_vol * 100:.2f}%")
                if not prediction_analysis.get('realistic', True):
                    print(f"   ⚠️  UNREALISTIC: Prediction exceeds expected volatility range")
    
    # Check if capping occurred (only warn if significant)
    prediction_was_capped = price_predictions.get('_capping_occurred', False)
    if prediction_was_capped:
        # Only add warning if predictions were significantly adjusted
        # This reduces false alarms for minor adjustments
        max_uncapped_pct = price_predictions.get('_max_uncapped_pct', 0.0)
        
        # Only warn if raw predictions were very extreme (>12% for short horizon, >15% for long)
        threshold = 12.0 if horizon == 'short' else (15.0 if horizon == 'long' else 10.0)
        if max_uncapped_pct > threshold:
            warning_flags.append(f"PREDICTION_ADJUSTED: Raw predictions ({max_uncapped_pct:.1f}%) were adjusted to realistic bounds")
    
    # Check for overfitting warnings from model disagreement
    if '_overfitting_warning' in price_predictions:
        warning_flags.append(f"OVERFITTING_WARNING: {price_predictions['_overfitting_warning']}")
    
    # Check model disagreement metrics
    if '_model_disagreement' in price_predictions:
        disagreement = price_predictions['_model_disagreement']
        cv = disagreement.get('cv', 0)
        if cv > 0.20:  # Very high disagreement
            warning_flags.append(
                f"HIGH_MODEL_DISAGREEMENT: Models disagree significantly (CV={cv:.3f}). "
                f"RF-LGBM: {disagreement.get('rf_lgbm_dist', 0):.2f}, "
                f"RF-XGB: {disagreement.get('rf_xgb_dist', 0):.2f}, "
                f"LGBM-XGB: {disagreement.get('lgbm_xgb_dist', 0):.2f}. "
                f"Possible overfitting - predictions may be unreliable."
            )
    
    # Add prediction analysis warnings
    if prediction_analysis:
        if prediction_analysis.get('high_disagreement'):
            warning_flags.append(
                f"PREDICTION_SPREAD: Models predict different prices (spread={prediction_analysis['prediction_range']:.2f}%). "
                f"RF:{prediction_analysis['rf_price']:.2f} | LGBM:{prediction_analysis['lgbm_price']:.2f} | XGB:{prediction_analysis['xgb_price']:.2f}. "
                f"High disagreement suggests possible overfitting."
            )
        if not prediction_analysis.get('realistic', True):
            warning_flags.append(
                f"UNREALISTIC_PREDICTION: Average prediction ({prediction_analysis['avg_return']:+.2f}%) exceeds expected volatility range "
                f"(±{prediction_analysis.get('expected_5d_move', 0):.2f}%). Models may be overfitting to noise."
            )
    
    # ========== PART 2: DQN Agent Action ==========
    dqn_action = None
    dqn_confidence = 0
    dqn_q_value = 0
    
    if dqn_available:
        print(f"[INFO] Getting DQN trading signal...")
        
        # Use the SAME feature extraction logic as during training
        # Get feature columns from saved DQN agent
        if hasattr(dqn_agent, 'feature_columns') and dqn_agent.feature_columns:
            # Use saved feature columns from training (BEST - guaranteed match)
            dqn_feature_cols = dqn_agent.feature_columns
            logger.info(f"Using saved DQN feature columns: {len(dqn_feature_cols)} features")
        else:
            # Fallback: Use SAME logic as prepare_data() to ensure consistency
            dqn_feature_cols = StockPricePredictor.get_feature_columns(features_df)
            logger.warning(f"DQN feature_columns not saved, using fallback: {len(dqn_feature_cols)} features")
            print(f"[WARNING] Using fallback feature extraction - may cause dimension mismatch")
        
        # Validate feature count matches DQN's expected dimensions
        if len(dqn_feature_cols) != dqn_agent.n_features:
            error_msg = f"FEATURE MISMATCH: DQN expects {dqn_agent.n_features} features but got {len(dqn_feature_cols)}"
            logger.error(error_msg)
            print(f"\n[ERROR] {error_msg}")
            print(f"[ERROR] This indicates inconsistent feature preparation between training and prediction")
            print(f"[ERROR] DQN prediction will be skipped to avoid crash")
            dqn_available = False
        else:
            # Extract features in the EXACT same order as training
            try:
                latest_feature_array = latest_features[dqn_feature_cols].fillna(0).values[0]
                
                # VALIDATION 3: Verify extracted feature array dimensions
                if len(latest_feature_array) != dqn_agent.n_features:
                    error_msg = f"ARRAY SIZE MISMATCH: Extracted {len(latest_feature_array)} features but DQN expects {dqn_agent.n_features}"
                    logger.error(error_msg)
                    print(f"\n[ERROR] {error_msg}")
                    dqn_available = False
                    
            except KeyError as e:
                logger.error(f"Missing feature column during extraction: {e}")
                print(f"\n[ERROR] Feature column missing: {e}")
                print(f"[ERROR] DQN prediction skipped")
                dqn_available = False
        
        # Make prediction only if validation passed
        if dqn_available:
            print("[predict] DQN predict...", flush=True)
            dqn_action, dqn_q_value, dqn_confidence = dqn_agent.predict(latest_feature_array)
            print("[predict] DQN predict done", flush=True)
    
    # ========== PART 3: Display All Predictions ==========
    print(f"\n{'='*80}")
    print(f"COMPREHENSIVE PREDICTIONS FOR {symbol}")
    print(f"{'='*80}")
    print(f"\n Current Status:")
    print(f"   Price:       Rs.{latest_price:.2f}")
    print(f"   Date:        {latest_date}")
    
    print(f"\n{'='*80}")
    print("PRICE PREDICTIONS (Next Day)")
    print(f"{'='*80}")
    print(f"{'Model':<20} {'Predicted Price':<20} {'Change':<20} {'%Change'}")
    print("-"*80)
    
    pred_prices = []
    for model_name, pred_price in price_predictions.items():
        # Skip internal metadata keys (like '_capping_occurred')
        if model_name.startswith('_'):
            continue
            
        price = pred_price[0]
        pred_prices.append(price)
        change = price - latest_price
        change_pct = (change / latest_price) * 100
        direction = "" if change > 0 else ""
        
        print(f"{model_name.upper():<20} Rs.{price:<18.2f} {change:+8.2f} ({change_pct:+6.2f}%) {direction}")
    
    # ========== PART 4: DQN Trading Signal ==========
    if dqn_available and dqn_action:
        print(f"\n{'='*80}")
        print("DQN TRADING SIGNAL (Reinforcement Learning)")
        print(f"{'='*80}")
        
        action_symbols = {
            'LONG': 'GREEN BUY/LONG',
            'SHORT': 'RED SELL/SHORT',
            'HOLD': 'BLUE HOLD'
        }
        
        print(f"   Recommended Action:  {action_symbols.get(dqn_action, dqn_action)}")
        print(f"   Confidence:          {dqn_confidence:.2%}")
        
        # Action explanation
        if dqn_action == 'LONG':
            print(f"   Meaning:             DQN expects price to increase")
        elif dqn_action == 'SHORT':
            print(f"   Meaning:             DQN expects price to decrease")
        else:
            print(f"   Meaning:             DQN suggests waiting/neutral stance")
    
    # ========== PART 5: Unified Ensemble Recommendation ==========
    ensemble_pred = price_predictions.get('ensemble', [0])[0]
    ensemble_change = ensemble_pred - latest_price
    ensemble_pct = (ensemble_change / latest_price) * 100
    
    print(f"\n{'='*80}")
    print(" UNIFIED ENSEMBLE RECOMMENDATION")
    print(f"{'='*80}")
    
    # Combine price prediction with DQN signal
    price_signal = "BULLISH" if ensemble_pct > 0 else "BEARISH" if ensemble_pct < 0 else "NEUTRAL"
    
    print(f"\n Price Model Consensus:")
    print(f"   Average Prediction:  Rs.{ensemble_pred:.2f}")
    print(f"   Expected Change:     {ensemble_pct:+.2f}%")
    print(f"   Price Signal:        {price_signal}")
    
    if dqn_available and dqn_action:
        print(f"\n DQN Agent Signal:")
        print(f"   Action:              {dqn_action}")
        print(f"   Confidence:          {dqn_confidence:.2%}")
        
        # Unified recommendation combining both
        print(f"\n{'='*80}")
        print("* FINAL RECOMMENDATION (Combined Analysis)")
        print(f"{'='*80}")
        
        # Logic: Combine price prediction direction with DQN action
        agreement_score = 0
        
        # Check if models agree
        if (ensemble_pct > 0 and dqn_action == 'LONG') or (ensemble_pct < 0 and dqn_action == 'SHORT'):
            agreement_score = 2  # Strong agreement
            final_signal = "STRONG BUY" if dqn_action == 'LONG' else "STRONG SELL"
            confidence_level = "HIGH"
            emoji = "GREENGREEN" if dqn_action == 'LONG' else "REDRED"
        elif dqn_action == 'HOLD' or abs(ensemble_pct) < 0.5:
            agreement_score = 1  # Neutral
            final_signal = "HOLD/WAIT"
            confidence_level = "MEDIUM"
            emoji = "BLUE"
        else:
            agreement_score = 0  # Disagreement
            final_signal = "MIXED SIGNALS - CAUTION"
            confidence_level = "LOW"
            emoji = "WARNING"
        
        print(f"   Signal:              {emoji} {final_signal}")
        print(f"   Confidence:          {confidence_level}")
        print(f"   Agreement Score:     {agreement_score}/2")
        
        # Detailed breakdown
        print(f"\n   Analysis:")
        print(f"    Price models suggest: {price_signal} ({ensemble_pct:+.2f}%)")
        print(f"    DQN agent suggests:   {dqn_action} (confidence: {dqn_confidence:.2%})")
        
        if agreement_score == 2:
            print(f"    OK Both approaches AGREE - High confidence recommendation")
        elif agreement_score == 1:
            print(f"    WHITE Models suggest caution - Wait for clearer signals")
        else:
            print(f"    WARNING Models DISAGREE - Exercise caution, wait for confirmation")
    
    else:
        # Only price prediction models available
        print(f"\n* RECOMMENDATION (Price Models Only):")
        
        if ensemble_pct > 1:
            print(f"   Signal: STRONG BUY GREEN")
        elif ensemble_pct > 0:
            print(f"   Signal: BUY YELLOW")
        elif ensemble_pct > -1:
            print(f"   Signal: HOLD BLUE")
        else:
            print(f"   Signal: SELL RED")
        
        print(f"   Expected Change: {ensemble_pct:+.2f}%")
        print(f"   Confidence: Based on ensemble of 3 price models")
    
    print(f"\n{'='*80}")
    print(" TRADING INSIGHTS")
    print(f"{'='*80}")
    
    # Add risk warning
    avg_pred = np.mean(pred_prices)
    std_pred = np.std(pred_prices)
    
    print(f"   Model Agreement:     {1 - (std_pred / (avg_pred + 1e-10)):.2%}")
    print(f"   Prediction Spread:   Rs.{std_pred:.2f}")
    
    if std_pred > latest_price * 0.02:
        print(f"   WARNING  High prediction variance - exercise caution")
    else:
        print(f"   OK Low prediction variance - models agree")
    
    # ========== PART 6: Log Prediction to JSON ==========
    # ENFORCE LIVE PRICE VALIDATION BEFORE LOGGING
    from live_price_validator import LivePriceValidator
    validator = LivePriceValidator()
    
    # Get live price to ensure accuracy
    live_price_data = validator.get_live_price_data(symbol)
    
    if 'error' not in live_price_data:
        live_price = live_price_data['current_price']
        price_diff_pct = ((live_price - latest_price) / latest_price) * 100 if latest_price > 0 else 0
        
        # If significant difference, use live price and recalculate
        if abs(price_diff_pct) > 0.5:  # More than 0.5% difference
            logger.warning(f"Price correction for {symbol}: cached={latest_price:.2f} vs live={live_price:.2f} ({price_diff_pct:+.2f}%)")
            print(f"[PRICE CORRECTION] Using live price: Rs.{live_price:.2f} (was Rs.{latest_price:.2f}, {price_diff_pct:+.2f}% difference)")
            
            # Update latest_price for return calculations
            latest_price = live_price
            
            # Recalculate ensemble return with live price
            ensemble_pct = (ensemble_pred - live_price) / live_price * 100
    
    # Prepare individual predictions
    individual_preds = {}
    
    # Price models - Convert to float to avoid numpy float32 serialization issues
    if 'random_forest' in price_predictions:
        rf_pred = float(price_predictions['random_forest'][0])
        rf_return = ((rf_pred - latest_price) / latest_price) * 100
        individual_preds['random_forest'] = {
            "return": round(float(rf_return), 2),
            "price": round(float(rf_pred), 2)
        }
    
    if 'lightgbm' in price_predictions:
        lgb_pred = float(price_predictions['lightgbm'][0])
        lgb_return = ((lgb_pred - latest_price) / latest_price) * 100
        individual_preds['lightgbm'] = {
            "return": round(float(lgb_return), 2),
            "price": round(float(lgb_pred), 2)
        }
    
    if 'xgboost' in price_predictions:
        xgb_pred = float(price_predictions['xgboost'][0])
        xgb_return = ((xgb_pred - latest_price) / latest_price) * 100
        individual_preds['xgboost'] = {
            "return": round(float(xgb_return), 2),
            "price": round(float(xgb_pred), 2)
        }
    
    # DQN agent - ONLY add if DQN was actually loaded and made a prediction
    if dqn_available and dqn_action:
        individual_preds['dqn'] = {
            "action": str(dqn_action),
            "q_value": round(float(dqn_q_value), 4),
            "confidence": round(float(dqn_confidence), 4)
        }
        print(f"[DEBUG] DQN logged: action={dqn_action}, q_value={dqn_q_value:.4f}, confidence={dqn_confidence:.4f}")
    else:
        print(f"[DEBUG] DQN not available - not included in log")
    
    # Prepare ensemble details
    ensemble_details = {
        "decision_maker": "",
        "price_agreement": False,
        "models_align": False,
        "total_vote": 0.0,
        "reason": ""
    }
    
    # Determine final action and confidence for logging
    final_action = "HOLD"
    final_confidence = 0.5
    # warning_flags already initialized at function start
    
    # STEP 1: Detect extreme disagreement
    extreme_disagreement = False
    if dqn_available and dqn_action:
        # Check if DQN expects opposite of price models
        if (ensemble_pct > 20 and dqn_action == 'SHORT') or (ensemble_pct < -20 and dqn_action == 'LONG'):
            extreme_disagreement = True
            warning_flags.append(f"EXTREME_DISAGREEMENT: Price models predict {ensemble_pct:+.1f}% but DQN says {dqn_action}")
        
        # Check if DQN Q-value is negative while price models very positive
        if dqn_q_value < 0 and ensemble_pct > 15:
            warning_flags.append(f"CONFLICTING_SIGNALS: DQN Q-value is negative ({dqn_q_value:.2f}) but price models bullish (+{ensemble_pct:.1f}%)")
    
    # STEP 2: Cap unrealistic predictions
    if abs(ensemble_pct) > 40:
        warning_flags.append(f"UNREALISTIC_PREDICTION: {ensemble_pct:+.1f}% is unusually high, treat with caution")
    
    if dqn_available and dqn_action:
        # With DQN - use agreement logic
        if (ensemble_pct > 0 and dqn_action == 'LONG') or (ensemble_pct < 0 and dqn_action == 'SHORT'):
            # Strong agreement
            final_action = dqn_action
            final_confidence = min(0.95, (dqn_confidence + 0.3))  # Boost confidence when agree
            ensemble_details['decision_maker'] = "Price Models (Strong Agreement)"
            ensemble_details['price_agreement'] = True
            ensemble_details['models_align'] = True
            ensemble_details['total_vote'] = round((abs(ensemble_pct) / 100 + dqn_confidence) / 2, 4)
            
            # Build reason string - include ALL 4 models + news sentiment
            model_reasons = []
            if 'random_forest' in individual_preds:
                model_reasons.append(f"RF:{individual_preds['random_forest']['return']:+.2f}%")
            if 'lightgbm' in individual_preds:
                model_reasons.append(f"LGBM:{individual_preds['lightgbm']['return']:+.2f}%")
            if 'xgboost' in individual_preds:
                model_reasons.append(f"XGB:{individual_preds['xgboost']['return']:+.2f}%")
            model_reasons.append(f"DQN:{dqn_action}")
            
            # Add news sentiment - handle BHAV data source
            if data_source == 'nse_bhav':
                model_reasons.append("News:BHAV_NOT_SUPPORTED")
            else:
                news_sentiment = analyze_news_sentiment(news_data)
                if news_sentiment['count'] > 0:
                    model_reasons.append(f"News:{news_sentiment['sentiment'].upper()}")
            
            # Add detailed technical indicators (show all available, not limited)
            if tech_indicators.get('detailed') and tech_indicators['detailed'] != 'Limited indicators':
                # Use detailed version with all indicators
                tech_summary = tech_indicators['detailed']
                model_reasons.append(f"Tech:{tech_summary}")
            elif tech_indicators.get('summary') and tech_indicators['summary'] != 'Limited indicators':
                # Fallback to summary if detailed not available
                tech_summary = tech_indicators['summary']
                model_reasons.append(f"Tech:{tech_summary}")
            
            ensemble_details['reason'] = " | ".join(model_reasons) + " | Price Models (Strong Agreement)"
            
        elif dqn_action == 'HOLD' and abs(ensemble_pct) < 5.0:
            # DQN says HOLD with small price change (<5%)
            # BUT: Always respect price direction, even if small
            
            if abs(ensemble_pct) < 0.3:
                # TRUE Neutral: Movement too small to matter (<0.3%)
                final_action = "HOLD"
                final_confidence = 0.5
                ensemble_details['decision_maker'] = "Neutral Stance (Minimal Movement)"
            
            elif ensemble_pct > 0:
                # Small positive movement (0.3% - 5%) → LONG
                final_action = "LONG"
                final_confidence = min(0.6, 0.4 + abs(ensemble_pct) / 10)  # 40-60% confidence
                ensemble_details['decision_maker'] = "Price Models (Small Upside)"
            
            else:  # ensemble_pct < 0
                # Small negative movement (0.3% - 5%) → SHORT
                final_action = "SHORT"
                final_confidence = min(0.6, 0.4 + abs(ensemble_pct) / 10)  # 40-60% confidence
                ensemble_details['decision_maker'] = "Price Models (Small Downside)"
            
            ensemble_details['price_agreement'] = True
            ensemble_details['models_align'] = True
            ensemble_details['total_vote'] = round(final_confidence, 4)
            
            # Build reason string with all price models + news sentiment
            model_reasons = []
            if 'random_forest' in individual_preds:
                model_reasons.append(f"RF:{individual_preds['random_forest']['return']:+.2f}%")
            if 'lightgbm' in individual_preds:
                model_reasons.append(f"LGBM:{individual_preds['lightgbm']['return']:+.2f}%")
            if 'xgboost' in individual_preds:
                model_reasons.append(f"XGB:{individual_preds['xgboost']['return']:+.2f}%")
            model_reasons.append(f"DQN:HOLD")
            
            # Add news sentiment - handle BHAV data source
            if data_source == 'nse_bhav':
                model_reasons.append("News:BHAV_NOT_SUPPORTED")
            else:
                news_sentiment = analyze_news_sentiment(news_data)
                if news_sentiment['count'] > 0:
                    model_reasons.append(f"News:{news_sentiment['sentiment'].upper()}")
            
            # Add detailed technical indicators (show all available)
            if tech_indicators.get('detailed') and tech_indicators['detailed'] != 'Limited indicators':
                tech_summary = tech_indicators['detailed']
                model_reasons.append(f"Tech:{tech_summary}")
            elif tech_indicators.get('summary') and tech_indicators['summary'] != 'Limited indicators':
                tech_summary = tech_indicators['summary']
                model_reasons.append(f"Tech:{tech_summary}")
            
            # Context based on direction
            if abs(ensemble_pct) < 0.3:
                context = "Minimal movement, neutral stance"
            elif ensemble_pct > 0:
                context = f"Small upside ({ensemble_pct:+.2f}%), going LONG"
            else:
                context = f"Small downside ({ensemble_pct:+.2f}%), going SHORT"
            
            ensemble_details['reason'] = " | ".join(model_reasons) + f" | {context}"
        
        elif dqn_action == 'HOLD' and abs(ensemble_pct) >= 5.0:
            # DQN says HOLD but price models predict significant move (>=5%)
            # Need intelligent handling based on disagreement magnitude
            
            if ensemble_pct > 0:
                final_action = "LONG"
            else:
                final_action = "SHORT"
            
            # SMART CONFIDENCE CALCULATION based on disagreement
            if abs(ensemble_pct) > 40:
                # Extreme prediction (>40%) - Very suspicious, cap confidence
                final_confidence = 0.35  # Low confidence for unrealistic predictions
                ensemble_details['decision_maker'] = "Price Models Override (EXTREME - Low Confidence)"
                warning_flags.append("Prediction >40% is suspicious - models may be overfitting")
            
            elif abs(ensemble_pct) > 25:
                # Large prediction (25-40%) with DQN disagreement
                final_confidence = 0.45  # Moderate-low confidence
                ensemble_details['decision_maker'] = "Price Models Override (High Disagreement)"
            
            elif abs(ensemble_pct) > 15:
                # Moderate prediction (15-25%) with DQN disagreement
                final_confidence = 0.55  # Moderate confidence
                ensemble_details['decision_maker'] = "Price Models Override (Moderate Disagreement)"
            
            else:  # 5-15% range
                # Reasonable prediction (5-15%) with DQN disagreement
                final_confidence = 0.65  # Good confidence
                ensemble_details['decision_maker'] = "Price Models Override (Minor Disagreement)"
            
            # Further reduce confidence if DQN Q-value is very negative
            if dqn_q_value < -20:
                final_confidence *= 0.8  # Reduce by 20%
                warning_flags.append(f"DQN very bearish (Q={dqn_q_value:.1f}), reducing confidence")
            
            ensemble_details['price_agreement'] = False  # DQN disagrees
            ensemble_details['models_align'] = False
            ensemble_details['total_vote'] = round(final_confidence, 4)
            
            # Build reason string
            model_reasons = []
            if 'random_forest' in individual_preds:
                model_reasons.append(f"RF:{individual_preds['random_forest']['return']:+.2f}%")
            if 'lightgbm' in individual_preds:
                model_reasons.append(f"LGBM:{individual_preds['lightgbm']['return']:+.2f}%")
            if 'xgboost' in individual_preds:
                model_reasons.append(f"XGB:{individual_preds['xgboost']['return']:+.2f}%")
            model_reasons.append(f"DQN:HOLD(Q={dqn_q_value:.1f})")
            
            # Add news sentiment - handle BHAV data source
            if data_source == 'nse_bhav':
                model_reasons.append("News:BHAV_NOT_SUPPORTED")
            else:
                news_sentiment = analyze_news_sentiment(news_data)
                if news_sentiment['count'] > 0:
                    model_reasons.append(f"News:{news_sentiment['sentiment'].upper()}")
            
            # Add detailed technical indicators (show all available)
            if tech_indicators.get('detailed') and tech_indicators['detailed'] != 'Limited indicators':
                tech_summary = tech_indicators['detailed']
                model_reasons.append(f"Tech:{tech_summary}")
            elif tech_indicators.get('summary') and tech_indicators['summary'] != 'Limited indicators':
                tech_summary = tech_indicators['summary']
                model_reasons.append(f"Tech:{tech_summary}")
            
            # Add context based on magnitude
            if abs(ensemble_pct) > 40:
                context = "EXTREME prediction - High caution advised"
            elif abs(ensemble_pct) > 25:
                context = "Large move predicted but DQN disagrees"
            else:
                context = "Price models show move, overriding DQN"
            
            ensemble_details['reason'] = " | ".join(model_reasons) + f" | {context}"
        
        elif abs(ensemble_pct) < 0.5:
            # Very small predicted movement (<0.5%), stay neutral
            final_action = "HOLD"
            final_confidence = 0.5
            ensemble_details['decision_maker'] = "Neutral Stance (Minimal Change)"
            ensemble_details['price_agreement'] = True
            ensemble_details['models_align'] = True
            ensemble_details['total_vote'] = 0.5
            
            model_reasons = []
            if 'random_forest' in individual_preds:
                model_reasons.append(f"RF:{individual_preds['random_forest']['return']:+.2f}%")
            if 'lightgbm' in individual_preds:
                model_reasons.append(f"LGBM:{individual_preds['lightgbm']['return']:+.2f}%")
            if 'xgboost' in individual_preds:
                model_reasons.append(f"XGB:{individual_preds['xgboost']['return']:+.2f}%")
            if dqn_action:
                model_reasons.append(f"DQN:{dqn_action}")
            
            # Add news sentiment - handle BHAV data source
            if data_source == 'nse_bhav':
                model_reasons.append("News:BHAV_NOT_SUPPORTED")
            else:
                news_sentiment = analyze_news_sentiment(news_data)
                if news_sentiment['count'] > 0:
                    model_reasons.append(f"News:{news_sentiment['sentiment'].upper()}")
            
            # Add detailed technical indicators (show all available)
            if tech_indicators.get('detailed') and tech_indicators['detailed'] != 'Limited indicators':
                tech_summary = tech_indicators['detailed']
                model_reasons.append(f"Tech:{tech_summary}")
            elif tech_indicators.get('summary') and tech_indicators['summary'] != 'Limited indicators':
                tech_summary = tech_indicators['summary']
                model_reasons.append(f"Tech:{tech_summary}")
            
            ensemble_details['reason'] = " | ".join(model_reasons) + " | Minimal predicted change"
        else:
            # Disagreement between price models and DQN
            # Need intelligent resolution based on confidence and magnitude
            
            disagreement_magnitude = abs(ensemble_pct)
            
            # RULE 1: Strong price model conviction (>10% move) overrides DQN
            if disagreement_magnitude > 10:
                # Price models show strong conviction
                if ensemble_pct > 0:
                    final_action = "LONG"
                else:
                    final_action = "SHORT"
                
                # Use same scaling as DQN low confidence path for consistency
                # Starts at 60% for 10% moves, reaches 65% cap at 15%+
                final_confidence = min(0.65, 0.5 + abs(ensemble_pct) / 100)
                ensemble_details['decision_maker'] = "Price Models (Strong Conviction Override)"
                warning_flags.append(f"DQN disagrees but price models show strong {final_action} signal ({ensemble_pct:+.1f}%)")
            
            # RULE 2: Moderate disagreement (3-10%) - intelligent confidence-based approach
            elif disagreement_magnitude >= 3:
                # Check DQN confidence level to decide who to trust
                if dqn_confidence > 0.7:
                    # DQN very confident - trust it
                    final_action = dqn_action
                    final_confidence = max(0.4, dqn_confidence * 0.6)
                    ensemble_details['decision_maker'] = "DQN Agent (High Confidence)"
                else:
                    # DQN not highly confident (≤0.7) - trust price models instead
                    # This ensures action ALWAYS matches predicted return direction
                    if ensemble_pct > 0:
                        final_action = "LONG"
                    else:
                        final_action = "SHORT"
                    
                    # Scale confidence based on DQN's confidence level
                    # Lower DQN confidence → Higher trust in price models
                    if dqn_confidence < 0.5:
                        # DQN has LOW confidence - higher trust in price models
                        base_confidence = 0.5 + (abs(ensemble_pct) / 100)
                        final_confidence = min(0.65, base_confidence)
                        ensemble_details['decision_maker'] = "Price Models (DQN Low Confidence)"
                        warning_flags.append(f"DQN uncertain (conf={dqn_confidence:.2f}), following price models {ensemble_pct:+.1f}%")
                    else:
                        # DQN moderately confident (0.5-0.7) - follow price models with lower confidence
                        base_confidence = 0.4 + (abs(ensemble_pct) / 100)
                        final_confidence = min(0.55, base_confidence)
                        ensemble_details['decision_maker'] = "Price Models (Moderate Disagreement)"
                        warning_flags.append(f"Moderate disagreement: Price models {ensemble_pct:+.1f}% vs DQN {dqn_action} (conf={dqn_confidence:.2f})")
            
            # RULE 3: Small disagreement (<3%) - ALWAYS respect price direction
            else:
                # ALWAYS follow price models direction, regardless of DQN
                if abs(ensemble_pct) < 0.3:
                    # Truly minimal (<0.3%) - neutral
                    final_action = "HOLD"
                    final_confidence = 0.5
                    ensemble_details['decision_maker'] = "Neutral (Minimal Movement)"
                elif ensemble_pct > 0:
                    # Positive - go LONG
                    final_action = "LONG"
                    final_confidence = 0.5
                    ensemble_details['decision_maker'] = "Price Models (Small Upside)"
                else:
                    # Negative - go SHORT
                    final_action = "SHORT"
                    final_confidence = 0.5
                    ensemble_details['decision_maker'] = "Price Models (Small Downside)"
                
                # Add warning if DQN disagrees on direction (only if significant)
                if (ensemble_pct < 0 and dqn_action == 'LONG') or (ensemble_pct > 0 and dqn_action == 'SHORT'):
                    # Only warn if disagreement is significant (>3% predicted move)
                    if abs(ensemble_pct) > 3.0:
                        warning_flags.append(f"DQN disagrees (DQN:{dqn_action}, Price:{ensemble_pct:+.1f}%) - following price models")
            
            ensemble_details['price_agreement'] = False
            ensemble_details['models_align'] = False
            ensemble_details['total_vote'] = round(final_confidence, 4)
            
            # Build reason string with all price models
            model_reasons = []
            if 'random_forest' in individual_preds:
                model_reasons.append(f"RF:{individual_preds['random_forest']['return']:+.2f}%")
            if 'lightgbm' in individual_preds:
                model_reasons.append(f"LGBM:{individual_preds['lightgbm']['return']:+.2f}%")
            if 'xgboost' in individual_preds:
                model_reasons.append(f"XGB:{individual_preds['xgboost']['return']:+.2f}%")
            model_reasons.append(f"DQN:{dqn_action}")
            
            # Add news sentiment - handle BHAV data source
            if data_source == 'nse_bhav':
                model_reasons.append("News:BHAV_NOT_SUPPORTED")
            else:
                news_sentiment = analyze_news_sentiment(news_data)
                if news_sentiment['count'] > 0:
                    model_reasons.append(f"News:{news_sentiment['sentiment'].upper()}")
            
            # Add detailed technical indicators (show all available)
            if tech_indicators.get('detailed') and tech_indicators['detailed'] != 'Limited indicators':
                tech_summary = tech_indicators['detailed']
                model_reasons.append(f"Tech:{tech_summary}")
            elif tech_indicators.get('summary') and tech_indicators['summary'] != 'Limited indicators':
                tech_summary = tech_indicators['summary']
                model_reasons.append(f"Tech:{tech_summary}")
            
            ensemble_details['reason'] = " | ".join(model_reasons) + " | Mixed signals (disagreement resolved)"
    else:
        # Without DQN - use price models only (respect direction always)
        if abs(ensemble_pct) < 0.3:
            # Movement too small (<0.3%)
            final_action = "HOLD"
            final_confidence = 0.5
        elif ensemble_pct > 0:
            # Positive prediction → LONG
            final_action = "LONG"
            # Scale confidence: 0.3-5% → 40-60%, 5-15% → 60-75%, >15% → 75-80%
            if abs(ensemble_pct) < 5:
                final_confidence = min(0.6, 0.4 + abs(ensemble_pct) / 10)
            elif abs(ensemble_pct) < 15:
                final_confidence = min(0.75, 0.6 + abs(ensemble_pct) / 50)
            else:
                final_confidence = 0.8
        else:  # ensemble_pct < 0
            # Negative prediction → SHORT
            final_action = "SHORT"
            # Same scaling as LONG
            if abs(ensemble_pct) < 5:
                final_confidence = min(0.6, 0.4 + abs(ensemble_pct) / 10)
            elif abs(ensemble_pct) < 15:
                final_confidence = min(0.75, 0.6 + abs(ensemble_pct) / 50)
            else:
                final_confidence = 0.8
        
        ensemble_details['decision_maker'] = "Price Models Only"
        ensemble_details['price_agreement'] = True
        ensemble_details['models_align'] = True
        ensemble_details['total_vote'] = round(final_confidence, 4)
        
        model_reasons = []
        if 'random_forest' in individual_preds:
            model_reasons.append(f"RF:{individual_preds['random_forest']['return']:+.2f}%")
        if 'lightgbm' in individual_preds:
            model_reasons.append(f"LGBM:{individual_preds['lightgbm']['return']:+.2f}%")
        if 'xgboost' in individual_preds:
            model_reasons.append(f"XGB:{individual_preds['xgboost']['return']:+.2f}%")
        
        # Add news sentiment - handle BHAV data source
        if data_source == 'nse_bhav':
            model_reasons.append("News:BHAV_NOT_SUPPORTED")
        else:
            news_sentiment = analyze_news_sentiment(news_data)
            if news_sentiment['count'] > 0:
                model_reasons.append(f"News:{news_sentiment['sentiment'].upper()}")
        
        # Add detailed technical indicators (show all available)
        if tech_indicators.get('detailed') and tech_indicators['detailed'] != 'Limited indicators':
            tech_summary = tech_indicators['detailed']
            model_reasons.append(f"Tech:{tech_summary}")
        elif tech_indicators.get('summary') and tech_indicators['summary'] != 'Limited indicators':
            tech_summary = tech_indicators['summary']
            model_reasons.append(f"Tech:{tech_summary}")
        
        ensemble_details['reason'] = " | ".join(model_reasons) + " | Price Models Consensus"
    
    # APPLY CONFIDENCE PENALTY IF CAPPING OCCURRED (only if significant)
    if prediction_was_capped:
        max_uncapped_pct = price_predictions.get('_max_uncapped_pct', 0.0)
        # Only reduce confidence if capping was significant (>10% adjustment)
        if max_uncapped_pct > 10.0:
            # Reduce confidence by 15% when predictions were significantly capped
            original_confidence = final_confidence
            final_confidence *= 0.85
            logger.info(f"Confidence reduced due to significant capping: {original_confidence:.2%} -> {final_confidence:.2%}")
            print(f"[INFO] Confidence reduced due to prediction adjustment: {original_confidence:.0%} -> {final_confidence:.0%}")
    
    # Log the prediction (features are stored separately in data/features/)
    log_prediction(
        symbol=symbol,
        current_price=latest_price,
        predicted_price=ensemble_pred,
        action=final_action,
        confidence=final_confidence,
        individual_predictions=individual_preds,
        ensemble_details=ensemble_details,
        features=None  # Features stored in data/features/, not in predictions.json
    )
    
    if verbose:
        print(f"\n{'='*80}\n")
    
    # Determine horizon details and risk profile
    horizon_info = {
        "intraday": {"description": "Same day / Next day", "target_days": 1, "type": "intraday", "risk_profile": "high"},
        "short": {"description": "5-day swing trading", "target_days": 5, "type": "short", "risk_profile": "moderate"},
        "long": {"description": "30-day position trading", "target_days": 30, "type": "long", "risk_profile": "low"}
    }
    
    horizon_detail = horizon_info.get(horizon, horizon_info["intraday"])
    
    # IMPROVED: Only warn on significant disagreements (>5% difference or major DQN conflict)
    warning_message = None
    models_align = ensemble_details.get('models_align', False)
    price_agreement = ensemble_details.get('price_agreement', False)
    
    if not models_align or not price_agreement:
        # Check if disagreement is significant
        # Calculate price model variance
        price_returns = []
        if 'random_forest' in individual_preds:
            price_returns.append(individual_preds['random_forest']['return'])
        if 'lightgbm' in individual_preds:
            price_returns.append(individual_preds['lightgbm']['return'])
        if 'xgboost' in individual_preds:
            price_returns.append(individual_preds['xgboost']['return'])
        
        if len(price_returns) >= 2:
            # Calculate variance in price model predictions
            price_variance = np.var(price_returns)
            max_price_diff = max(price_returns) - min(price_returns)
            
            # Only warn if:
            # 1. Price models disagree significantly (>5% difference), OR
            # 2. DQN strongly disagrees with price models (>10% difference)
            dqn_disagreement = False
            if dqn_available and dqn_action and 'dqn' in individual_preds:
                price_avg = np.mean(price_returns)
                if (price_avg > 0 and dqn_action == 'SHORT') or (price_avg < 0 and dqn_action == 'LONG'):
                    dqn_disagreement = abs(price_avg) > 10.0
            
            if max_price_diff > 5.0 or dqn_disagreement:
                warning_message = "Models disagree - reduced confidence"
            # For minor disagreements, don't show warning (already reflected in confidence)
    
    # Format individual predictions - include ALL 4 models (rf, lgbm, xgb, dqn)
    formatted_individual = {}
    
    if 'random_forest' in individual_preds:
        formatted_individual['random_forest'] = {
            "price": individual_preds['random_forest']['price'],
            "return": individual_preds['random_forest']['return'],
            "horizon": horizon
        }
    
    if 'lightgbm' in individual_preds:
        formatted_individual['lightgbm'] = {
            "price": individual_preds['lightgbm']['price'],
            "return": individual_preds['lightgbm']['return'],
            "horizon": horizon
        }
    
    if 'xgboost' in individual_preds:
        formatted_individual['xgboost'] = {
            "price": individual_preds['xgboost']['price'],
            "return": individual_preds['xgboost']['return'],
            "horizon": horizon
        }
    
    if 'dqn' in individual_preds:
        formatted_individual['dqn'] = individual_preds['dqn']
    
    print("[predict] done", flush=True)
    # Build prediction response
    prediction_response = {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "horizon": horizon,
        "horizon_details": {
            "description": horizon_detail["description"],
            "target_days": horizon_detail["target_days"],
            "type": horizon_detail["type"]
        },
        "risk_profile": horizon_detail["risk_profile"],
        "current_price": round(float(latest_price), 2),
        "predicted_price": round(float(ensemble_pred), 2),
        "predicted_return": round(float((ensemble_pred - latest_price) / latest_price * 100), 2),
        "action": final_action,
        "confidence": round(float(final_confidence), 4),
        "score": round(float(final_confidence * abs((ensemble_pred - latest_price) / latest_price)), 4),
        "reason": ensemble_details.get('reason', ''),
        "model_version": f"ensemble-v3(rf+lgbm+xgb+dqn)-{horizon}",
        "ensemble_details": {
            "decision_maker": ensemble_details.get('decision_maker', ''),
            "price_agreement": bool(ensemble_details.get('price_agreement', False)),  # Convert to Python bool for JSON
            "models_align": bool(ensemble_details.get('models_align', False)),  # Convert to Python bool for JSON
            "total_vote": round(float(ensemble_details.get('total_vote', 0.0)), 4)
        },
        "individual_predictions": formatted_individual,
        "prediction_analysis": prediction_analysis if prediction_analysis else {}
    }
    
    # Add warnings if models disagree or other issues detected
    all_warnings = []
    if warning_message:
        all_warnings.append(warning_message)
    if warning_flags:
        all_warnings.extend(warning_flags)
    
    if all_warnings:
        prediction_response["warnings"] = all_warnings
        prediction_response["warning"] = " | ".join(all_warnings)  # Combined for backward compatibility
    
    return prediction_response


# ============================================================================
# MAIN PROGRAM
# ============================================================================

def main():
    """Main program with interactive menu"""
    print("\n" + "="*80)
    print(" " * 15 + "STOCK ANALYSIS & ML PREDICTION TOOL")
    print("="*80)
    print("\n Complete Stock Analysis with 4 ML Models:")
    print("    Random Forest, LightGBM, XGBoost (Price Prediction)")
    print("    DQN Agent (Deep Reinforcement Learning)")
    print("\n Features:")
    print("    50+ Technical Indicators (RSI, MACD, Bollinger Bands, etc.)")
    print("    Financial Statements (Income, Balance Sheet, Cash Flow)")
    print("    Intelligent Ensemble Predictions")
    print("\n Supported Markets:")
    print("    Indian NSE: RPOWER.NS, TCS.NS, INFY.NS, RELIANCE.NS")
    print("    Indian BSE: RPOWER.BO, TCS.BO, INFY.BO")
    print("    US stocks: AAPL, MSFT, TSLA, GOOGL")
    print("="*80)
    
    while True:
        print("\n" + "="*80)
        print("MAIN MENU")
        print("="*80)
        print("\n DATA & ANALYSIS:")
        print("  1. Fetch Stock Data (Downloads ALL data from Yahoo Finance)")
        print("  2. Calculate Technical Indicators (50+ indicators: RSI, MACD, Bollinger Bands, etc.)")
        print("  3. View Financial Statements (View previously downloaded data)")
        print("  4. View Technical Indicators (View previously calculated indicators)")
        print("  5. Complete Analysis (Fetch data + Calculate indicators + Show everything)")
        print("\n MACHINE LEARNING:")
        print("  7. Train ALL 4 Models (RF + LightGBM + XGBoost + DQN)")
        print("  8. Predict with Ensemble (Unified prediction from all 4 models)")
        print("\n  9. Exit")
        print("\n" + "="*80)
        
        choice = input("\nEnter your choice (1-9): ").strip()
        
        if choice == '1':
            # Fetch data
            print("\n" + "="*80)
            print("FETCH STOCK DATA")
            print("="*80)
            print("\nEnter stock symbols (separate with spaces):")
            print("Example: RPOWER.NS TCS.NS INFY.NS RELIANCE.NS HDFCBANK.NS")
            print()
            
            symbols_input = input("Stock symbols: ").strip()
            
            if not symbols_input:
                print("\n[ERROR] No symbols entered.")
                continue
            
            symbols = symbols_input.split()
            fetch_stock_data(symbols)
            
        elif choice == '2':
            # Calculate technical indicators
            print("\n" + "="*80)
            print("CALCULATE TECHNICAL INDICATORS")
            print("="*80)
            print("\nEnter stock symbol to calculate technical indicators:")
            symbol = input("Symbol (e.g., INFY.NS, RPOWER.NS, AAPL): ").strip()
            
            if not symbol:
                print("\n[ERROR] No symbol entered.")
                continue
            
            calculate_technical_indicators(symbol)
            
        elif choice == '3':
            # View financial statements
            print("\n" + "="*80)
            print("VIEW FINANCIAL STATEMENTS")
            print("="*80)
            print("\nEnter stock symbol to view financials:")
            symbol = input("Symbol (e.g., INFY.NS, RPOWER.NS): ").strip()
            
            if not symbol:
                print("\n[ERROR] No symbol entered.")
                continue
            
            view_financial_statements(symbol)
            
        elif choice == '4':
            # View technical indicators
            print("\n" + "="*80)
            print("VIEW TECHNICAL INDICATORS")
            print("="*80)
            print("\nEnter stock symbol to view technical indicators:")
            symbol = input("Symbol (e.g., INFY.NS, RPOWER.NS, AAPL): ").strip()
            
            if not symbol:
                print("\n[ERROR] No symbol entered.")
                continue
            
            view_technical_indicators(symbol)
            
        elif choice == '5':
            # Complete analysis
            print("\n" + "="*80)
            print("COMPLETE ANALYSIS")
            print("="*80)
            print("\nEnter stock symbol for complete analysis:")
            print("(This will fetch data, calculate indicators, and show everything)")
            symbol = input("Symbol (e.g., INFY.NS, RPOWER.NS, AAPL): ").strip()
            
            if not symbol:
                print("\n[ERROR] No symbol entered.")
                continue
            
            complete_analysis(symbol)
            
        elif choice == '7':
            # Train ML models
            print("\n" + "="*80)
            print("TRAIN ML MODELS")
            print("="*80)
            print("\nEnter stock symbol to train ML models:")
            print("(This will train Random Forest, LightGBM, and XGBoost)")
            symbol = input("Symbol (e.g., INFY.NS, RPOWER.NS, AAPL): ").strip()
            
            if not symbol:
                print("\n[ERROR] No symbol entered.")
                continue
            
            train_ml_models(symbol)
            
        elif choice == '8':
            # Predict stock price
            print("\n" + "="*80)
            print("PREDICT STOCK PRICE")
            print("="*80)
            print("\nEnter stock symbol to predict price:")
            symbol = input("Symbol (e.g., INFY.NS, RPOWER.NS, AAPL): ").strip()
            
            if not symbol:
                print("\n[ERROR] No symbol entered.")
                continue
            
            predict_stock_price(symbol)
            
        elif choice == '9':
            print("\n" + "="*80)
            print("Thank you for using Stock Analysis Tool!")
            print("="*80 + "\n")
            break
            
        else:
            print("\n[ERROR] Invalid choice. Please enter 1-9.")


if __name__ == "__main__":
    main()