Market Watchlist
Market Watchlist is a web application for managing stock watchlists and fetching real-time financial data. It integrates with Finnhub (primary), Marketstack (fallback), and NewsAPI for stock prices and news, using PostgreSQL for persistent storage and caching. Users can create, rename, and delete watchlists, add/remove stocks, and view detailed stock data in a modern, responsive dashboard optimized for high performance.
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
Clone the Repository
git clone https://github.com/mediumbase/marketwatchlist
cd marketwatchlist

Set Up Virtual Environment
python3 -m venv menv
source menv/bin/activate  # On Windows: menv\Scripts\activate
pip install -r requirements.txt

Configure PostgreSQL

Install PostgreSQL:
sudo apt update
sudo apt install postgresql postgresql-contrib

Start PostgreSQL:
sudo systemctl start postgresql
sudo systemctl enable postgresql

Create Database and User:
sudo -u postgres psql
CREATE DATABASE market_db;
CREATE USER marketuser WITH PASSWORD 'adminpg';
GRANT ALL PRIVILEGES ON DATABASE market_db TO marketuser;
\q


Initialize Schema:
psql -U marketuser -d market_db -f tools/schema_marketwatchlist.txt


Configure Environment

Copy .env.example to .env:
cp .env.example .env


Edit .env with your credentials:
SECRET_KEY=yourAPIkeyhere
DATABASE_URL=postgresql://marketuser:adminpg@localhost:5432/market_db
FINNHUB_API_KEY=yourAPIkeyhere
MARKETSTACK_API_KEY=yourAPIkeyhere
NEWSAPI_KEY=yourAPIkeyhere
X_API_KEY=yourAPIkeyhere
X_BEARER_TOKEN=yourAPIkeyhere
TELEGRAM_BOT_TOKEN=yourAPIkeyhere
TELEGRAM_CHAT_ID=yourAPIkeyhere
REDDIT_CLIENT_ID=yourAPIkeyhere
REDDIT_CLIENT_SECRET=yourAPIkeyhere
FMP_API_KEY=yourAPIkeyhere



Run the Application
python app.py

Access at http://localhost:8000.


Project Structure

marketwatchlist/
├── app.py              # Main application
├── menv/              # Virtual environment
│   ├── bin/          # Executable scripts
│   │   ├── activate
│   │   ├── activate.csh
│   │   ├── activate.fish
│   │   ├── Activate.ps1
│   │   ├── dotenv
│   │   ├── flask
│   │   ├── normalizer
│   │   ├── pip
│   │   ├── pip3
│   │   ├── pip3.8
│   │   ├── python -> python3
│   │   └── python3 -> /home/boss/.pyenv/versions/3.8.20/bin/python3
│   ├── include/      # Header files
│   │   └── site
│   ├── lib/          # Python libraries
│   │   └── python3.8
│   ├── lib64 -> lib  # Symlink to lib
│   └── pyvenv.cfg    # Virtual environment configuration
├── requirements.txt    # Python dependencies
├── templates/         # HTML templates
│   ├── error.html    # Error page
│   ├── index.html    # Main dashboard
├── tools/            # Utility scripts
│   ├── keygen.py    # Script for generating API keys
│   ├── schema_marketwatchlist.txt  # Database schema
│   ├── test-db.py   # Database testing script

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
stocks: Links stocks to watchlists (id, watchlist_id, symbol, purchase_price, shares).
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
Real-time Alerts: Notify via email or Telegram for price spikes.
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
Rate Limiting: Implement rate limiting for API abuse prevention.

Contributing

Fork the repository.
Create a feature branch: git checkout -b feature/yourfeature.
Commit changes: git commit -m 'Add yourfeature'.
Push to the branch: git push origin feature/yourfeature.
Open a pull request.

License
MIT License. See LICENSE for details.
Contact
For issues or suggestions, open a GitHub issue or contact mediumbase.llc@gmail.com.

About schema_marketwatchlist.txt

The schema_marketwatchlist.txt file, located in the tools/ directory, contains the SQL schema and initial data for the PostgreSQL database. It defines the structure for the watchlists, stocks, and stock_data tables, including indexes for performance optimization. Additionally, it populates the database with predefined watchlists and mock stock data for testing and demonstration purposes. This file is critical for setting up the database and should be executed as part of the setup process using the psql command.

About .env

The .env file, located in the root directory, stores environment variables required for the application, such as API keys for Finnhub, Marketstack, and NewsAPI, database connection details, and other sensitive configuration data. It is loaded using python-dotenv to securely manage credentials and ensure they are not hardcoded in the application. This file is essential for the application to connect to external APIs and the database, and it should be configured with valid credentials before running the application.