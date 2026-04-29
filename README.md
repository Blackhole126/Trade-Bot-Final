# 📈 AI-Powered Stock Trading Bot

> **Advanced ML-based stock prediction system with React dashboard and FastAPI backend**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 Overview

A complete stock trading prediction system powered by **4 ML models** (Random Forest, XGBoost, LightGBM, DQN) with **50+ technical indicators**, real-time predictions, and a modern React dashboard.

### Key Features

- 🤖 **4 ML Models**: Random Forest, XGBoost, LightGBM, Deep Q-Network (DQN)
- 📊 **50+ Technical Indicators**: RSI, MACD, Bollinger Bands, Moving Averages, etc.
- 🎯 **3 Time Horizons**: Intraday (1 day), Short (5 days), Long (30 days)
- 🌐 **Real-time Data**: Live prices from Yahoo Finance
- 📱 **Modern Dashboard**: React + TypeScript + TailwindCSS
- 🔒 **Open Access API**: No authentication required
- 📈 **Market Scan**: Analyze multiple stocks simultaneously
- 🎨 **Multiple Themes**: Light, Dark, Space

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Node.js 16+**
- **npm or yarn**

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd Trade_Bot-master

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../trading-dashboard
npm install
```

### Running the Application

#### Option 1: Using Batch Files (Windows - Easiest)

1. **Start Backend**: Double-click `START_BACKEND.bat`
2. **Start Frontend**: Double-click `START_FRONTEND.bat`
3. **Open Browser**: http://localhost:5173

#### Option 2: Command Line

**Terminal 1 - Backend:**
```bash
cd backend
python api_server.py
```

**Terminal 2 - Frontend:**
```bash
cd trading-dashboard
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 📁 Project Structure

```
Trade_Bot-master/
├── backend/                    # FastAPI Backend
│   ├── api_server.py          # Main API server
│   ├── stock_analysis_complete.py  # ML engine
│   ├── core/
│   │   └── mcp_adapter.py     # Orchestration layer
│   ├── data/                  # Data cache
│   ├── models/                # Trained ML models
│   └── requirements.txt       # Python dependencies
│
├── trading-dashboard/         # React Frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/            # Page components
│   │   ├── services/         # API services
│   │   └── config.ts         # Configuration
│   ├── .env                  # Environment variables
│   └── package.json          # Node dependencies
│
├── START_BACKEND.bat         # Backend launcher
├── START_FRONTEND.bat        # Frontend launcher
└── README.md                 # This file
```

---

## 🔧 Configuration

### Backend Configuration

**File:** `backend/config.py` or `backend/.env`

```python
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100
```

### Frontend Configuration

**File:** `trading-dashboard/.env`

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_ENABLE_AUTH=false
```

---

## 🎮 Usage

### 1. Search for Stocks

- Enter stock symbol (e.g., `AAPL`, `TCS.NS`, `RELIANCE.NS`)
- Select time horizon (Intraday, Short, Long)
- Click **Search** or press Enter

### 2. Quick Access Tabs

- Click any stock tab (TCS, RELIANCE, TATAMOTORS, etc.)
- Instant prediction with ML analysis

### 3. Advanced Features

- **Deep Analyze**: Comprehensive analysis with all indicators
- **Complete Analysis**: Multi-horizon analysis
- **Force Refresh**: Re-fetch data and retrain models
- **Near-Live Mode**: Auto-refresh predictions (30s-5min intervals)

### 4. Prediction Output

Each prediction includes:
- **Action**: LONG (Buy), SHORT (Sell), or HOLD
- **Confidence**: Model confidence (0-1)
- **Expected Return**: Predicted return percentage
- **Current Price**: Latest market price
- **Predicted Price**: Target price
- **Risk Analysis**: Volatility, Sharpe ratio, max drawdown
- **Reasoning**: Why the model made this prediction

---

## 🤖 ML Models

### 1. Random Forest
- Ensemble of decision trees
- Robust to overfitting
- Feature importance analysis

### 2. XGBoost
- Gradient boosting
- High accuracy
- Fast training

### 3. LightGBM
- Efficient gradient boosting
- Low memory usage
- Fast inference

### 4. Deep Q-Network (DQN)
- Reinforcement learning
- Learns from market dynamics
- Adaptive strategy

### Ensemble Prediction
- Combines all 4 models
- Weighted voting
- Confidence scoring

---

## 📊 Technical Indicators (50+)

### Trend Indicators
- SMA (5, 10, 20, 50, 200)
- EMA (12, 26)
- MACD
- ADX

### Momentum Indicators
- RSI (14)
- Stochastic Oscillator
- Williams %R
- CCI

### Volatility Indicators
- Bollinger Bands
- ATR
- Standard Deviation

### Volume Indicators
- OBV
- Volume SMA
- Volume Ratio

### And many more...

---

## 🌐 API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/tools/health` | GET | System health check |
| `/tools/predict` | POST | Generate predictions |
| `/tools/scan_all` | POST | Scan multiple symbols |
| `/tools/analyze` | POST | Deep analysis |
| `/tools/feedback` | POST | Submit feedback |
| `/tools/train_rl` | POST | Train RL agent |
| `/tools/fetch_data` | POST | Fetch market data |

### Example: Predict

```bash
curl -X POST http://localhost:8000/tools/predict \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "TCS.NS"],
    "horizon": "intraday"
  }'
```

**Response:**
```json
{
  "metadata": {
    "count": 2,
    "horizon": "intraday",
    "timestamp": "2024-01-01T12:00:00"
  },
  "predictions": [
    {
      "symbol": "AAPL",
      "action": "LONG",
      "confidence": 0.85,
      "predicted_return": 2.5,
      "current_price": 150.00,
      "predicted_price": 153.75,
      "reason": "Strong bullish momentum with RSI confirmation"
    }
  ]
}
```

---

## 🔍 Troubleshooting

### Backend Issues

**Problem:** Port 8000 already in use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /F /PID <PID>
```

**Problem:** Module not found
```bash
cd backend
pip install -r requirements.txt
```

### Frontend Issues

**Problem:** Cannot connect to backend
- Ensure backend is running on port 8000
- Check `.env` file: `VITE_API_BASE_URL=http://127.0.0.1:8000`
- Restart frontend after `.env` changes

**Problem:** npm install fails
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Data Issues

**Problem:** No predictions for symbol
- Symbol may not have sufficient historical data
- Try different symbol or time horizon
- Check backend logs: `backend/data/logs/api_server.log`

---

## 📈 Performance

### First-Time Prediction
- **Time**: 60-90 seconds
- **Reason**: Data fetch + feature calculation + model training
- **Cached**: Subsequent predictions are instant

### Cached Prediction
- **Time**: < 1 second
- **Uses**: Pre-trained models and cached features

### Model Training
- **Random Forest**: ~10 seconds
- **XGBoost**: ~15 seconds
- **LightGBM**: ~10 seconds
- **DQN**: ~30 seconds (10 episodes)

---

## 🛡️ Security & Rate Limiting

### Rate Limits
- **Per Minute**: 10 requests
- **Per Hour**: 100 requests
- **Per IP**: Tracked automatically

### Authentication
- **Status**: Disabled (Open Access)
- **Can be enabled**: Set `ENABLE_AUTH=true` in config

### Data Privacy
- **No user data stored**
- **No tracking**
- **Local processing only**

---

## 🎨 Themes

### Available Themes
1. **Light**: Clean, professional
2. **Dark**: Easy on eyes
3. **Space**: Futuristic, gradient-based

### Switching Themes
- Click theme toggle in top-right corner
- Preference saved in localStorage

---

## 📝 Development

### Backend Development

```bash
cd backend

# Run with auto-reload
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000

# Run tests
python -m pytest tests/

# Check logs
tail -f data/logs/api_server.log
```

### Frontend Development

```bash
cd trading-dashboard

# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run type-check
```

---

## 🧪 Testing

### Test Backend API

```bash
# Health check
curl http://localhost:8000/tools/health

# Predict
curl -X POST http://localhost:8000/tools/predict \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL"], "horizon": "intraday"}'
```

### Test Frontend

1. Open http://localhost:5173
2. Open browser console (F12)
3. Click stock tabs
4. Verify console logs:
   ```
   [TAB] Clicked: TCS.NS
   [API] POST /tools/predict called for TCS.NS
   [RENDER] Success card: TCS.NS
   ```

---

## 📚 Documentation

### Additional Docs
- `QUICK_START_GUIDE.md` - Detailed setup guide
- `CONFIGURATION_SUMMARY.md` - Configuration details
- `MARKET_SCAN_INTEGRATION_FIX.md` - Integration verification
- `VERIFICATION_CHECKLIST.md` - Testing checklist

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

**This software is for educational and research purposes only.**

- **Not Financial Advice**: Predictions are based on historical data and ML models
- **No Guarantees**: Past performance does not guarantee future results
- **Use at Your Own Risk**: Always do your own research before trading
- **No Liability**: Authors are not responsible for any financial losses

---

## 🙏 Acknowledgments

- **Yahoo Finance** - Market data provider
- **FastAPI** - Modern Python web framework
- **React** - Frontend library
- **scikit-learn, XGBoost, LightGBM** - ML libraries
- **PyTorch** - Deep learning framework

---

## 📞 Support

### Issues
- Report bugs: [GitHub Issues](https://github.com/your-repo/issues)
- Feature requests: [GitHub Discussions](https://github.com/your-repo/discussions)

### Contact
- Email: your-email@example.com
- Twitter: @yourhandle

---

## 🎯 Roadmap

### Planned Features
- [ ] Cryptocurrency support
- [ ] Commodities support
- [ ] Portfolio management
- [ ] Backtesting engine
- [ ] Mobile app
- [ ] Real-time alerts
- [ ] Social trading features

---

## 📊 Stats

- **ML Models**: 4 (RF, XGB, LGB, DQN)
- **Technical Indicators**: 50+
- **Supported Markets**: Stocks (NSE, NYSE, NASDAQ)
- **Time Horizons**: 3 (Intraday, Short, Long)
- **API Endpoints**: 10+
- **Frontend Components**: 20+

---

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

---

**Made with ❤️ by the Trading Bot Team**

**Happy Trading! 📈🚀**
