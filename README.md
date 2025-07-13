Market Siren
Market Siren is a Flask-based web application designed for managing stock watchlists and fetching real-time financial data. It integrates with Finnhub (primary), Marketstack (fallback), and NewsAPI for stock prices and news, using PostgreSQL for persistent storage and caching. Users can create, rename, and delete watchlists, add/remove stocks, and view detailed stock data in a modern, responsive dashboard optimized for trillion-dollar-scale performance.
Features

Create, rename, and delete stock watchlists.
Add/delete stocks to/from watchlists.
Fetch real-time stock data from Finnhub (primary) and Marketstack (fallback).
Retrieve stock-related news via NewsAPI.
Cache data in PostgreSQL to minimize API calls.
Display stock prices, trends, and news in a user-friendly, grid-based UI.
Support for curated watchlists: Penny Stocks, Dividend Stocks, Industry Leaders, AI and Tech Innovation, Clean Energy.
Flash messages for user feedback.
Secure environment variable management with python-dotenv.

Prerequisites

Python 3.8+
PostgreSQL 14+
API keys for Finnhub, Marketstack, and NewsAPI
Git

Setup Instructions

Clone the Repository:
git clone https://github.com/yourusername/market-siren.git
cd market-siren


Set Up Virtual Environment:
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt


Configure PostgreSQL:

Install PostgreSQL:sudo apt update
sudo apt install postgresql postgresql-contrib


Start PostgreSQL:sudo systemctl start postgresql
sudo systemctl enable postgresql


Create database and user:sudo -u postgres psql
CREATE DATABASE market_db;
CREATE USER sirenuser WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE market_db TO sirenuser;
\q


Initialize schema:psql -U sirenuser -d market_db -f schema.sql




Configure Environment:

Copy .env.example to .env:cp .env.example .env


Edit .env with your credentials:SECRET_KEY=your_secret_key_here
DATABASE_URL=postgresql://sirenuser:yourpassword@localhost:5432/market_db
FINNHUB_API_KEY=your_finnhub_api_key
MARKETSTACK_API_KEY=your_marketstack_api_key
NEWSAPI_KEY=your_newsapi_api_key




Run the Application:
python app.py


Access at http://localhost:5002.



Project Structure
market-siren/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── schema.sql          # Database schema and initial data
├── .env.example       # Example environment file
├── templates/         # HTML templates
│   ├── index.html    # Main dashboard
│   ├── error.html    # Error page

Data Pipeline and Lifecycle

User Interaction: Users select a watchlist or stock via the UI, triggering a request.
Database Query: The app checks the stock_data table for cached data (<24 hours old).
API Calls: If data is missing or outdated:
Finnhub: Fetches stock quotes (primary source, 60 calls/minute).
Marketstack: Fallback for stock data (1000 calls/month).
NewsAPI: Retrieves stock news (100 calls/day, non-commercial).


Caching: Fetched data is stored in PostgreSQL with a timestamp to reduce API calls.
UI Rendering: Data is displayed in a responsive grid with watchlists, stock details, news, market movers, and benchmarks.

Database Structure

watchlists: Stores watchlist metadata (id, name).
stocks: Links stocks to watchlists (id, watchlist_id, symbol).
stock_data: Caches stock data (stock_id, symbol, close, open, high, low, volume, trend, macd_signal, mini_news, news_items, change_percent, created_at).
Indexes: Optimize queries for symbol, watchlist_id, trend, volume, and created_at.

Watchlists

Penny Stocks: High-volatility stocks under $5 (AMPX, ABCL, RZLV, SBET, KULR).
Dividend Stocks: Stable, high-yield stocks (JNJ, PG, KO, PFE, PM).
Industry Leaders: Large-cap market leaders (AAPL, MSFT, GOOGL, JPM, XOM).
AI and Tech Innovation: High-growth tech (NVDA, AMD, TSLA, RGTI, MARA).
Clean Energy: Renewable and nuclear energy (OKLO, UEC, LTBR, NEE, ENPH).

Future Integrations and Features

User Authentication: Add OAuth2/login for personalized watchlists.
Real-time Alerts: Notify via email or Telegram (using TELEGRAM_BOT_TOKEN) for price spikes.
Sentiment Analysis: Use X API or Reddit for social media sentiment.
Portfolio Tracking: Calculate portfolio value and performance.
Technical Indicators: Display RSI, MACD, or moving averages.
Stock Screener: Filter stocks by criteria (e.g., P/E ratio, volume).
Historical Data: Show past stock prices and trends.
Dividend Calendar: List upcoming dividend dates.
Charting: Add interactive charts with Chart.js or Plotly.
Export Data: Allow CSV/Excel export of watchlists.
Dark Mode: Implement a dark theme for UI.
Mobile App: Develop iOS/Android apps with React Native.
WebSocket Updates: Enable real-time updates via WebSockets.
Machine Learning: Predict trends using scikit-learn.
Multi-Market Support: Add crypto/forex markets.
Watchlist Sharing: Enable public/private watchlist sharing.
API Endpoint: Expose REST API for external integrations.
Unit Tests: Add pytest for automated testing.
Docker Support: Containerize with Docker Compose.
Rate Limiting: Implement Flask-Limiter for API abuse prevention.

Contributing

Fork the repository.
Create a feature branch: git checkout -b feature/yourfeature.
Commit changes: git commit -m 'Add yourfeature'.
Push to the branch: git push origin feature/yourfeature.
Open a pull request.

License
MIT License. See LICENSE for details.
Contact
For issues or suggestions, open a GitHub issue or contact your.email@example.com.