# File: app.py
# Version: 2.3.6
# Date: 2025-07-14
# Time: 04:40 EDT
# Description: Market Siren watchlist application with real-time updates, enhanced logging, validation, and Holdings metrics
# Changes:
# - 2.3.0: Added Flask-SocketIO for real-time updates, loguru for structured logging, regex for symbol validation, CSRF protection
# - 2.3.1: Fixed Decimal serialization issue for SocketIO batch updates
# - 2.3.2: Removed invalid 'json' and 'cls' arguments from socketio.emit
# - 2.3.3: Added Holdings watchlist with purchase_price and shares, and Holdings Metrics calculation
# - 2.3.4: Made Holdings a button like All Symbols, displaying only Holdings stocks
# - 2.3.5: Fixed TypeError in calculate_holdings_metrics by converting Decimal to float
# - 2.3.6: Always compute holdings_metrics for Holdings watchlist

from flask import Flask, request, render_template, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, HiddenField, SubmitField, FloatField, IntegerField
from wtforms.validators import DataRequired, Regexp, Optional
from loguru import logger
import psycopg2
from dotenv import load_dotenv
import os
import requests
from time import sleep
from requests.exceptions import HTTPError
from datetime import datetime
import json
import re
import eventlet
from decimal import Decimal

# Custom JSON encoder to handle Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

# Initialize logging
logger.add("market_siren_{time}.log", rotation="1 MB", format="{time} {level} {message}")

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
csrf = CSRFProtect(app)
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins='*', logger=True, engineio_logger=True)

# API configurations
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
MARKETSTACK_API_KEY = os.getenv("MARKETSTACK_API_KEY")
MARKETSTACK_BASE_URL = "http://api.marketstack.com/v1"
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
NEWSAPI_BASE_URL = "https://newsapi.org/v2"

# Cache for stock data
STOCK_CACHE = {}
CACHE_TIMEOUT = 86400  # 24 hours

# Mock data
MOCK_BREAKING_NEWS = [
    "Amprius (AMPX) surges on new EV battery contract",
    "NVIDIA (NVDA) hits $4T market cap milestone",
    "Oklo (OKLO) gains on Trump nuclear policy support"
]

MOCK_NEWS_ITEMS = {
    "AMPX": [{"date": "2025-07-13 09:00 EDT", "text": "Bullish pennant breakout confirmed"}, {"date": "2025-07-12 15:30 EDT", "text": "New EV battery contract announced"}, {"date": "2025-07-11 10:00 EDT", "text": "Analyst upgrades AMPX"}],
    "ABCL": [{"date": "2025-07-13 07:00 EDT", "text": "Double bottom reversal triggered"}, {"date": "2025-07-12 11:00 EDT", "text": "New biotech partnership"}, {"date": "2025-07-11 09:00 EDT", "text": "Positive trial results"}],
    "RZLV": [{"date": "2025-07-13 10:00 EDT", "text": "Bull flag breakout confirmed"}, {"date": "2025-07-12 09:00 EDT", "text": "AI commerce platform expansion"}, {"date": "2025-07-11 08:00 EDT", "text": "New retail partnership"}],
    "SBET": [{"date": "2025-07-13 08:30 EDT", "text": "Crypto gaming surge reported"}, {"date": "2025-07-12 10:00 EDT", "text": "New Ethereum integration"}, {"date": "2025-07-11 11:00 EDT", "text": "Analyst coverage initiated"}],
    "KULR": [{"date": "2025-07-13 10:00 EDT", "text": "New battery tech patent filed"}, {"date": "2025-07-12 09:00 EDT", "text": "Partnership with aerospace firm"}, {"date": "2025-07-11 08:00 EDT", "text": "Q2 results expected next week"}],
    "JNJ": [{"date": "2025-07-13 08:00 EDT", "text": "Q2 earnings released"}, {"date": "2025-07-12 12:00 EDT", "text": "Dividend increase announced"}, {"date": "2025-07-11 14:00 EDT", "text": "New healthcare product launch"}],
    "PG": [{"date": "2025-07-13 07:00 EDT", "text": "New product line announced"}, {"date": "2025-07-12 11:00 EDT", "text": "Dividend payout confirmed"}, {"date": "2025-07-11 09:00 EDT", "text": "Q2 sales report released"}],
    "KO": [{"date": "2025-07-13 08:30 EDT", "text": "Global sales increase reported"}, {"date": "2025-07-12 10:00 EDT", "text": "Dividend payout announced"}, {"date": "2025-07-11 11:00 EDT", "text": "New marketing campaign launched"}],
    "PFE": [{"date": "2025-07-13 09:00 EDT", "text": "New vaccine trial results"}, {"date": "2025-07-12 15:30 EDT", "text": "Dividend increase planned"}, {"date": "2025-07-11 10:00 EDT", "text": "Partnership with biotech firm"}],
    "PM": [{"date": "2025-07-13 08:00 EDT", "text": "Q2 earnings beat expectations"}, {"date": "2025-07-12 12:00 EDT", "text": "Dividend payout confirmed"}, {"date": "2025-07-11 14:00 EDT", "text": "New product launch"}],
    "AAPL": [{"date": "2025-07-13 09:00 EDT", "text": "New iPhone launch announced"}, {"date": "2025-07-12 15:30 EDT", "text": "Q2 earnings preview"}, {"date": "2025-07-11 10:00 EDT", "text": "AI integration in iOS"}],
    "MSFT": [{"date": "2025-07-13 08:00 EDT", "text": "Cloud growth reported"}, {"date": "2025-07-12 12:00 EDT", "text": "New AI product launch"}, {"date": "2025-07-11 14:00 EDT", "text": "Q2 earnings beat"}],
    "GOOGL": [{"date": "2025-07-13 07:00 EDT", "text": "AI search improvements announced"}, {"date": "2025-07-12 11:00 EDT", "text": "Cloud revenue growth"}, {"date": "2025-07-11 09:00 EDT", "text": "Q2 results released"}],
    "JPM": [{"date": "2025-07-13 09:00 EDT", "text": "Strong Q2 earnings reported"}, {"date": "2025-07-12 15:30 EDT", "text": "New banking app launched"}, {"date": "2025-07-11 10:00 EDT", "text": "Analyst upgrades JPM"}],
    "XOM": [{"date": "2025-07-13 08:30 EDT", "text": "Oil demand increase reported"}, {"date": "2025-07-12 10:00 EDT", "text": "New drilling project"}, {"date": "2025-07-11 11:00 EDT", "text": "Q2 earnings preview"}],
    "NVDA": [{"date": "2025-07-13 08:00 EDT", "text": "New AI chip launch announced"}, {"date": "2025-07-12 12:00 EDT", "text": "Hits $4T market cap"}, {"date": "2025-07-11 14:00 EDT", "text": "Expands AI research lab"}],
    "AMD": [{"date": "2025-07-13 09:00 EDT", "text": "New semiconductor deal signed"}, {"date": "2025-07-12 15:30 EDT", "text": "Q2 earnings beat"}, {"date": "2025-07-11 10:00 EDT", "text": "AI chip production ramp-up"}],
    "TSLA": [{"date": "2025-07-13 07:00 EDT", "text": "Regulatory scrutiny on self-driving tech"}, {"date": "2025-07-12 11:00 EDT", "text": "Musk announces new factory"}, {"date": "2025-07-11 09:00 EDT", "text": "Q2 delivery numbers released"}],
    "RGTI": [{"date": "2025-07-13 10:00 EDT", "text": "Quantum computing partnership announced"}, {"date": "2025-07-12 09:00 EDT", "text": "New quantum chip prototype"}, {"date": "2025-07-11 08:00 EDT", "text": "Analyst upgrades RGTI"}],
    "MARA": [{"date": "2025-07-13 08:30 EDT", "text": "Bitcoin mining expansion announced"}, {"date": "2025-07-12 10:00 EDT", "text": "AI integration in mining"}, {"date": "2025-07-11 11:00 EDT", "text": "Q2 earnings preview"}],
    "OKLO": [{"date": "2025-07-13 09:00 EDT", "text": "Trump nuclear policy boost"}, {"date": "2025-07-12 15:30 EDT", "text": "New nuclear facility planned"}, {"date": "2025-07-11 10:00 EDT", "text": "Analyst upgrades OKLO"}],
    "UEC": [{"date": "2025-07-13 08:00 EDT", "text": "Uranium demand surge reported"}, {"date": "2025-07-12 12:00 EDT", "text": "New mining contract"}, {"date": "2025-07-11 14:00 EDT", "text": "Q2 earnings beat"}],
    "LTBR": [{"date": "2025-07-13 07:00 EDT", "text": "Nuclear fuel innovation announced"}, {"date": "2025-07-12 11:00 EDT", "text": "New patent filed"}, {"date": "2025-07-11 09:00 EDT", "text": "Analyst coverage initiated"}],
    "NEE": [{"date": "2025-07-13 08:30 EDT", "text": "Renewable energy expansion announced"}, {"date": "2025-07-12 10:00 EDT", "text": "New wind farm project"}, {"date": "2025-07-11 11:00 EDT", "text": "Q2 earnings preview"}],
    "ENPH": [{"date": "2025-07-13 09:00 EDT", "text": "Solar inverter demand increase"}, {"date": "2025-07-12 15:30 EDT", "text": "New product launch"}, {"date": "2025-07-11 10:00 EDT", "text": "Analyst upgrades ENPH"}]
}

MOCK_STOCK_DATA = {
    "AMPX": {"symbol": "AMPX", "close": 2.50, "open": 2.40, "high": 2.60, "low": 2.30, "volume": 300000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Bullish pennant breakout", "news_items": MOCK_NEWS_ITEMS["AMPX"], "change_percent": 4.17},
    "ABCL": {"symbol": "ABCL", "close": 3.00, "open": 2.90, "high": 3.10, "low": 2.80, "volume": 250000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Double bottom reversal", "news_items": MOCK_NEWS_ITEMS["ABCL"], "change_percent": 3.45},
    "RZLV": {"symbol": "RZLV", "close": 4.00, "open": 3.90, "high": 4.10, "low": 3.80, "volume": 200000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Bull flag breakout", "news_items": MOCK_NEWS_ITEMS["RZLV"], "change_percent": 2.56},
    "SBET": {"symbol": "SBET", "close": 1.50, "open": 1.40, "high": 1.60, "low": 1.30, "volume": 400000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Crypto gaming surge", "news_items": MOCK_NEWS_ITEMS["SBET"], "change_percent": 7.14},
    "KULR": {"symbol": "KULR", "close": 0.40, "open": 0.42, "high": 0.43, "low": 0.39, "volume": 500000, "trend": "Down", "macd_signal": "Sell", "mini_news": "New battery tech patent filed", "news_items": MOCK_NEWS_ITEMS["KULR"], "change_percent": -4.76},
    "JNJ": {"symbol": "JNJ", "close": 156.90, "open": 157.09, "high": 157.18, "low": 155.18, "volume": 2000000, "trend": "Down", "macd_signal": "Sell", "mini_news": "Q2 earnings released", "news_items": MOCK_NEWS_ITEMS["JNJ"], "change_percent": -0.12},
    "PG": {"symbol": "PG", "close": 157.05, "open": 158.05, "high": 158.05, "low": 156.44, "volume": 1500000, "trend": "Down", "macd_signal": "Sell", "mini_news": "New product line announced", "news_items": MOCK_NEWS_ITEMS["PG"], "change_percent": -0.63},
    "KO": {"symbol": "KO", "close": 69.87, "open": 69.57, "high": 70.16, "low": 69.25, "volume": 1800000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Global sales increase", "news_items": MOCK_NEWS_ITEMS["KO"], "change_percent": 0.43},
    "PFE": {"symbol": "PFE", "close": 25.65, "open": 25.65, "high": 25.72, "low": 25.42, "volume": 2200000, "trend": "Neutral", "macd_signal": "Neutral", "mini_news": "New vaccine trial results", "news_items": MOCK_NEWS_ITEMS["PFE"], "change_percent": 0.00},
    "PM": {"symbol": "PM", "close": 179.91, "open": 179.96, "high": 180.22, "low": 178.09, "volume": 1700000, "trend": "Down", "macd_signal": "Sell", "mini_news": "Q2 earnings beat expectations", "news_items": MOCK_NEWS_ITEMS["PM"], "change_percent": -0.03},
    "AAPL": {"symbol": "AAPL", "close": 211.16, "open": 210.57, "high": 212.13, "low": 209.86, "volume": 2500000, "trend": "Up", "macd_signal": "Buy", "mini_news": "New iPhone launch", "news_items": MOCK_NEWS_ITEMS["AAPL"], "change_percent": 0.28},
    "MSFT": {"symbol": "MSFT", "close": 503.32, "open": 498.47, "high": 505.03, "low": 497.80, "volume": 3000000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Cloud growth reported", "news_items": MOCK_NEWS_ITEMS["MSFT"], "change_percent": 0.97},
    "GOOGL": {"symbol": "GOOGL", "close": 180.19, "open": 176.79, "high": 181.43, "low": 176.48, "volume": 2800000, "trend": "Up", "macd_signal": "Buy", "mini_news": "AI search improvements", "news_items": MOCK_NEWS_ITEMS["GOOGL"], "change_percent": 1.93},
    "JPM": {"symbol": "JPM", "close": 286.86, "open": 285.52, "high": 287.38, "low": 283.66, "volume": 2200000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Strong Q2 earnings", "news_items": MOCK_NEWS_ITEMS["JPM"], "change_percent": 0.47},
    "XOM": {"symbol": "XOM", "close": 115.43, "open": 114.85, "high": 115.76, "low": 114.51, "volume": 2000000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Oil demand increase", "news_items": MOCK_NEWS_ITEMS["XOM"], "change_percent": 0.51},
    "NVDA": {"symbol": "NVDA", "close": 164.92, "open": 163.72, "high": 167.89, "low": 163.47, "volume": 3500000, "trend": "Up", "macd_signal": "Buy", "mini_news": "New AI chip launch", "news_items": MOCK_NEWS_ITEMS["NVDA"], "change_percent": 0.73},
    "AMD": {"symbol": "AMD", "close": 146.42, "open": 142.60, "high": 147.40, "low": 141.60, "volume": 3000000, "trend": "Up", "macd_signal": "Buy", "mini_news": "New semiconductor deal", "news_items": MOCK_NEWS_ITEMS["AMD"], "change_percent": 2.68},
    "TSLA": {"symbol": "TSLA", "close": 240.00, "open": 245.00, "high": 248.00, "low": 238.00, "volume": 1500000, "trend": "Down", "macd_signal": "Sell", "mini_news": "Regulatory scrutiny on self-driving tech", "news_items": MOCK_NEWS_ITEMS["TSLA"], "change_percent": -2.04},
    "RGTI": {"symbol": "RGTI", "close": 2.80, "open": 2.70, "high": 2.90, "low": 2.60, "volume": 250000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Quantum computing partnership", "news_items": MOCK_NEWS_ITEMS["RGTI"], "change_percent": 3.70},
    "MARA": {"symbol": "MARA", "close": 20.00, "open": 19.50, "high": 20.50, "low": 19.30, "volume": 4000000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Bitcoin mining expansion", "news_items": MOCK_NEWS_ITEMS["MARA"], "change_percent": 2.56},
    "OKLO": {"symbol": "OKLO", "close": 4.50, "open": 4.30, "high": 4.60, "low": 4.20, "volume": 300000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Trump nuclear policy boost", "news_items": MOCK_NEWS_ITEMS["OKLO"], "change_percent": 4.65},
    "UEC": {"symbol": "UEC", "close": 4.80, "open": 4.60, "high": 4.90, "low": 4.50, "volume": 350000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Uranium demand surge", "news_items": MOCK_NEWS_ITEMS["UEC"], "change_percent": 4.35},
    "LTBR": {"symbol": "LTBR", "close": 3.90, "open": 3.80, "high": 4.00, "low": 3.70, "volume": 200000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Nuclear fuel innovation", "news_items": MOCK_NEWS_ITEMS["LTBR"], "change_percent": 2.63},
    "NEE": {"symbol": "NEE", "close": 75.00, "open": 74.50, "high": 75.50, "low": 74.20, "volume": 1800000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Renewable energy expansion", "news_items": MOCK_NEWS_ITEMS["NEE"], "change_percent": 0.67},
    "ENPH": {"symbol": "ENPH", "close": 110.00, "open": 108.50, "high": 111.00, "low": 107.50, "volume": 1600000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Solar inverter demand increase", "news_items": MOCK_NEWS_ITEMS["ENPH"], "change_percent": 1.38}
}

MOCK_BENCHMARKS = [
    {"symbol": "^GSPC", "name": "S&P 500", "close": 5600.12, "change": 0.45},
    {"symbol": "^DJI", "name": "Dow Jones", "close": 40000.90, "change": -0.23},
    {"symbol": "^IXIC", "name": "Nasdaq", "close": 18300.45, "change": 0.67}
]

# WTForms for CSRF-protected forms
class WatchlistForm(FlaskForm):
    name = StringField('Watchlist Name', validators=[DataRequired()])
    submit = SubmitField('Add')

class RenameWatchlistForm(FlaskForm):
    new_name = StringField('New Name', validators=[DataRequired()])
    watchlist_id = HiddenField()
    submit = SubmitField('Rename')

class AddStockForm(FlaskForm):
    symbol = StringField('Stock Symbol', validators=[DataRequired(), Regexp(r'^[A-Z]{1,5}$', message="Invalid stock symbol")])
    watchlist_id = HiddenField(validators=[DataRequired()])
    purchase_price = FloatField('Purchase Price', validators=[Optional()])
    shares = IntegerField('Number of Shares', validators=[Optional()])
    submit = SubmitField('Add Stock')

# Database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        logger.info("Database connection established")
        return conn
    except psycopg2.Error as e:
        flash("Database connection failed.", "error")
        logger.error(f"Database connection error: {e}")
        return None

def save_stock_data_to_db(stock_id, stock_data):
    conn = get_db_connection()
    if not conn:
        return

    cur = conn.cursor()
    try:
        volume = stock_data['volume'] if isinstance(stock_data['volume'], (int, float)) else None
        news_items = json.dumps(stock_data['news_items'], cls=DecimalEncoder) if isinstance(stock_data['news_items'], list) else stock_data['news_items']
        cur.execute('''
            INSERT INTO stock_data (stock_id, symbol, close, open, high, low, volume, trend, macd_signal, mini_news, news_items, change_percent, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (stock_id) DO UPDATE
            SET symbol = EXCLUDED.symbol,
                close = EXCLUDED.close,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                volume = EXCLUDED.volume,
                trend = EXCLUDED.trend,
                macd_signal = EXCLUDED.macd_signal,
                mini_news = EXCLUDED.mini_news,
                news_items = EXCLUDED.news_items,
                change_percent = EXCLUDED.change_percent,
                created_at = EXCLUDED.created_at;
        ''', (
            stock_id,
            stock_data['symbol'],
            stock_data['close'],
            stock_data['open'],
            stock_data['high'],
            stock_data['low'],
            volume,
            stock_data['trend'],
            stock_data['macd_signal'],
            stock_data['mini_news'],
            news_items,
            stock_data['change_percent'],
            datetime.now()
        ))
        conn.commit()
        logger.info(f"Saved stock data for {stock_data['symbol']}")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Failed to save stock data to DB: {e}")
    finally:
        cur.close()
        conn.close()

def fetch_stock_data_from_db(stock_id, symbol):
    conn = get_db_connection()
    if not conn:
        return None

    cur = conn.cursor()
    try:
        cur.execute('SELECT symbol, close, open, high, low, volume, trend, macd_signal, mini_news, news_items, change_percent, created_at FROM stock_data WHERE stock_id = %s AND symbol = %s;', (stock_id, symbol))
        result = cur.fetchone()
        if result:
            created_at = result[11]
            if (datetime.now() - created_at).total_seconds() < CACHE_TIMEOUT:
                news_items = result[9] if isinstance(result[9], list) else json.loads(result[9]) if result[9] else []
                stock_data = {
                    'symbol': result[0],
                    'close': float(result[1]) if result[1] is not None else 'N/A',
                    'open': float(result[2]) if result[2] is not None else 'N/A',
                    'high': float(result[3]) if result[3] is not None else 'N/A',
                    'low': float(result[4]) if result[4] is not None else 'N/A',
                    'volume': result[5] if result[5] is not None else 'N/A',
                    'trend': result[6] if result[6] else 'N/A',
                    'macd_signal': result[7] if result[7] else 'N/A',
                    'mini_news': result[8] if result[8] else 'No recent news',
                    'news_items': news_items,
                    'change_percent': float(result[10]) if result[10] is not None else 0
                }
                logger.info(f"Fetched cached data for {symbol} from DB")
                return stock_data
        return None
    except psycopg2.Error as e:
        logger.error(f"Failed to fetch stock data from DB: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def fetch_stock_data_api(stock_id, symbol):
    symbol = symbol.upper()
    if symbol == "F":
        flash("Corrected symbol 'f' to 'F' (Ford).", "info")
    if not re.match(r'^[A-Z]{1,5}$', symbol):
        flash(f"Invalid symbol: {symbol}. Using fallback data.", "error")
        logger.warning(f"Invalid symbol attempted: {symbol}")
        stock_data = MOCK_STOCK_DATA.get(symbol, None)
        if stock_data:
            save_stock_data_to_db(stock_id, stock_data)
            STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
            socketio.emit('stock_update', stock_data)
        return stock_data

    if symbol in STOCK_CACHE:
        cached_data, timestamp = STOCK_CACHE[symbol]
        if (datetime.now().timestamp() - timestamp) < CACHE_TIMEOUT:
            logger.info(f"Cache hit for {symbol}")
            return cached_data
        else:
            del STOCK_CACHE[symbol]

    db_data = fetch_stock_data_from_db(stock_id, symbol)
    if db_data:
        STOCK_CACHE[symbol] = (db_data, datetime.now().timestamp())
        logger.info(f"DB cache hit for {symbol}")
        return db_data

    valid_symbols = ["AMPX", "ABCL", "RZLV", "SBET", "KULR", "JNJ", "PG", "KO", "PFE", "PM", "AAPL", "MSFT", "GOOGL", "JPM", "XOM", "NVDA", "AMD", "TSLA", "RGTI", "MARA", "OKLO", "UEC", "LTBR", "NEE", "ENPH"]
    if symbol not in valid_symbols:
        flash(f"Invalid symbol: {symbol}. Using fallback data.", "error")
        logger.warning(f"Symbol {symbol} not in valid list")
        stock_data = MOCK_STOCK_DATA.get(symbol, None)
        if stock_data:
            save_stock_data_to_db(stock_id, stock_data)
            STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
            socketio.emit('stock_update', stock_data)
        return stock_data

    finnhub_endpoint = f"{FINNHUB_BASE_URL}/quote"
    finnhub_params = {"symbol": symbol, "token": FINNHUB_API_KEY}
    try:
        response = requests.get(finnhub_endpoint, params=finnhub_params)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Fetched Finnhub data for {symbol}")
        if 'c' in data and data['c'] is not None:
            news_endpoint = f"{NEWSAPI_BASE_URL}/everything"
            news_params = {"q": symbol, "apiKey": NEWSAPI_KEY, "language": "en", "sortBy": "publishedAt", "pageSize": 3}
            news_items = []
            mini_news = "No recent news"
            try:
                news_response = requests.get(news_endpoint, params=news_params)
                news_response.raise_for_status()
                news_data = news_response.json()
                if news_data.get("articles"):
                    news_items = [{"date": article["publishedAt"], "text": article["title"]} for article in news_data["articles"]]
                    mini_news = news_items[0]["text"] if news_items else mini_news
                logger.info(f"Fetched NewsAPI data for {symbol}")
            except requests.RequestException as e:
                logger.error(f"NewsAPI error for {symbol}: {e}")
                news_items = MOCK_NEWS_ITEMS.get(symbol, [])
                mini_news = MOCK_NEWS_ITEMS.get(symbol, [{"text": "No recent news"}])[0]["text"]

            stock_data = {
                'symbol': symbol,
                'close': float(data['c']),
                'open': float(data['o']),
                'high': float(data['h']),
                'low': float(data['l']),
                'volume': data.get('v', None),
                'trend': "Up" if data['c'] > data['o'] else "Down" if data['c'] < data['o'] else "Neutral",
                'macd_signal': "Buy" if data['c'] > data['o'] else "Sell" if data['c'] < data['o'] else "Neutral",
                'mini_news': mini_news,
                'news_items': news_items,
                'change_percent': float((data['c'] - data['o']) / data['o'] * 100) if data['o'] != 0 else 0
            }
            save_stock_data_to_db(stock_id, stock_data)
            STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
            socketio.emit('stock_update', stock_data)
            return stock_data
    except HTTPError as e:
        if response.status_code == 429:
            logger.warning(f"Finnhub rate limit exceeded for {symbol}")
        else:
            logger.error(f"Finnhub API error for {symbol}: {response.status_code} - {response.text}")

    marketstack_endpoint = f"{MARKETSTACK_BASE_URL}/tickers/{symbol.lower()}/eod/latest"
    marketstack_params = {"access_key": MARKETSTACK_API_KEY}
    for attempt in range(5):
        try:
            response = requests.get(marketstack_endpoint, params=marketstack_params)
            response.raise_for_status()
            data = response.json()
            if 'error' not in data and data.get('close') is not None:
                news_items = MOCK_NEWS_ITEMS.get(symbol, [])
                mini_news = MOCK_NEWS_ITEMS.get(symbol, [{"text": "No recent news"}])[0]["text"]
                stock_data = {
                    'symbol': symbol,
                    'close': float(data.get('close', 'N/A')),
                    'open': float(data.get('open', 'N/A')),
                    'high': float(data.get('high', 'N/A')),
                    'low': float(data.get('low', 'N/A')),
                    'volume': data.get('volume', None),
                    'trend': "Up" if data.get('close', 0) > data.get('open', 0) else "Down" if data.get('close', 0) < data.get('open', 0) else "Neutral",
                    'macd_signal': "Buy" if data.get('close', 0) > data.get('open', 0) else "Sell" if data.get('close', 0) < data.get('open', 0) else "Neutral",
                    'mini_news': mini_news,
                    'news_items': news_items,
                    'change_percent': float((data.get('close', 0) - data.get('open', 0)) / data.get('open', 0) * 100) if data.get('open', 0) != 0 else 0
                }
                save_stock_data_to_db(stock_id, stock_data)
                STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
                socketio.emit('stock_update', stock_data)
                logger.info(f"Fetched Marketstack data for {symbol}")
                return stock_data
            flash(f"No data available for {symbol}. Using fallback data.", "error")
            stock_data = MOCK_STOCK_DATA.get(symbol, None)
            if stock_data:
                save_stock_data_to_db(stock_id, stock_data)
                STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
                socketio.emit('stock_update', stock_data)
            return stock_data
        except HTTPError as e:
            if response.status_code == 429:
                sleep(2 ** (attempt + 1))
                continue
            flash(f"Marketstack API error for {symbol}: {response.status_code}. Using fallback data.", "error")
            logger.error(f"Marketstack API error: {response.status_code} - {response.text}")
            stock_data = MOCK_STOCK_DATA.get(symbol, None)
            if stock_data:
                save_stock_data_to_db(stock_id, stock_data)
                STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
                socketio.emit('stock_update', stock_data)
            return stock_data
        except requests.RequestException as e:
            flash(f"Failed to fetch data for {symbol}. Using fallback data.", "error")
            logger.error(f"Request error: {e}")
            stock_data = MOCK_STOCK_DATA.get(symbol, None)
            if stock_data:
                save_stock_data_to_db(stock_id, stock_data)
                STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
                socketio.emit('stock_update', stock_data)
            return stock_data
    flash(f"Rate limit exceeded for {symbol}. Using fallback data.", "error")
    stock_data = MOCK_STOCK_DATA.get(symbol, None)
    if stock_data:
        save_stock_data_to_db(stock_id, stock_data)
        STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
        socketio.emit('stock_update', stock_data)
    return stock_data

def get_market_status():
    now = datetime.now()
    is_weekday = now.weekday() < 5
    market_open = datetime.strptime("09:30", "%H:%M").time()
    market_close = datetime.strptime("16:00", "%H:%M").time()
    return "Open" if is_weekday and market_open <= now.time() <= market_close else "Closed"

def fetch_breaking_news():
    endpoint = f"{NEWSAPI_BASE_URL}/top-headlines"
    params = {"category": "business", "apiKey": NEWSAPI_KEY, "language": "en", "pageSize": 3}
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()
        logger.info("Fetched breaking news from NewsAPI")
        return [article["title"] for article in data.get("articles", [])]
    except requests.RequestException as e:
        logger.error(f"NewsAPI error: {e}")
        return MOCK_BREAKING_NEWS

def calculate_holdings_metrics(watchlist_id):
    conn = get_db_connection()
    if not conn:
        return None
    cur = conn.cursor()
    try:
        cur.execute('SELECT id, symbol, purchase_price, shares FROM stocks WHERE watchlist_id = %s;', (watchlist_id,))
        holdings = cur.fetchall()
        if not holdings:
            return None

        total_value = 0
        total_cost = 0
        total_gain_loss = 0
        top_stock = None
        worst_stock = None
        max_gain = float('-inf')
        min_gain = float('inf')

        for holding in holdings:
            stock_id, symbol, purchase_price, shares = holding
            stock_data = fetch_stock_data_from_db(stock_id, symbol) or fetch_stock_data_api(stock_id, symbol)
            if stock_data and purchase_price is not None and shares is not None:
                purchase_price = float(purchase_price)  # Convert Decimal to float
                shares = float(shares)  # Convert Decimal to float
                current_value = stock_data['close'] * shares
                total_value += current_value
                total_cost += purchase_price * shares
                gain_loss = (stock_data['close'] - purchase_price) * shares
                total_gain_loss += gain_loss
                percentage_gain = ((stock_data['close'] - purchase_price) / purchase_price) * 100 if purchase_price != 0 else 0
                if percentage_gain > max_gain:
                    max_gain = percentage_gain
                    top_stock = symbol
                if percentage_gain < min_gain:
                    min_gain = percentage_gain
                    worst_stock = symbol

        return {
            'total_value': total_value,
            'total_cost': total_cost,
            'total_gain_loss': total_gain_loss,
            'top_stock': top_stock,
            'worst_stock': worst_stock
        }
    except psycopg2.Error as e:
        logger.error(f"Failed to calculate holdings metrics: {e}")
        return None
    finally:
        cur.close()
        conn.close()

# Background task for periodic stock updates
def background_task():
    while True:
        try:
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                cur.execute('SELECT id, symbol FROM stocks;')
                stocks = cur.fetchall()
                batch_updates = []
                for stock_id, symbol in stocks:
                    stock_data = fetch_stock_data_api(stock_id, symbol)
                    if stock_data:
                        batch_updates.append(stock_data)
                if batch_updates:
                    socketio.emit('stock_batch_update', batch_updates)
                    logger.info(f"Emitted batch update for {len(batch_updates)} stocks")
                cur.close()
                conn.close()
        except Exception as e:
            logger.error(f"Error in background task: {e}")
        eventlet.sleep(300)  # Fetch every 5 minutes

# Start background task on first connection
@socketio.on('connect')
def handle_connect():
    logger.info("Client connected")
    if not hasattr(app, 'background_thread'):
        app.background_thread = socketio.start_background_task(background_task)

@app.route('/', methods=['GET', 'POST'])
def index():
    watchlist_form = WatchlistForm()
    add_stock_form = AddStockForm()
    conn = get_db_connection()
    watchlists = []
    stocks = []
    stock_data_list = []
    selected_watchlist_id = request.args.get('watchlist_id', type=int)
    selected_stock_id = request.args.get('stock_id', type=int)
    show_all_symbols = request.args.get('show_all', type=int) == 1
    show_holdings = request.args.get('show_holdings', type=int) == 1
    selected_watchlist_name = None
    top_worst_stocks = []
    holdings_metrics = None

    if conn:
        cur = conn.cursor()
        try:
            # Always fetch Holdings watchlist ID for metrics
            cur.execute('SELECT id FROM watchlists WHERE name = \'Holdings\';')
            result = cur.fetchone()
            holdings_watchlist_id = result[0] if result else None
            if holdings_watchlist_id:
                holdings_metrics = calculate_holdings_metrics(holdings_watchlist_id)

            # Fetch watchlists, excluding Holdings from links
            cur.execute('SELECT id, name FROM watchlists WHERE name != \'Holdings\' ORDER BY name;')
            watchlists = cur.fetchall()

            if show_holdings:
                cur.execute('SELECT id FROM watchlists WHERE name = \'Holdings\';')
                result = cur.fetchone()
                if result:
                    selected_watchlist_id = result[0]
                    selected_watchlist_name = 'Holdings'
            elif selected_watchlist_id:
                cur.execute('SELECT name FROM watchlists WHERE id = %s;', (selected_watchlist_id,))
                result = cur.fetchone()
                selected_watchlist_name = result[0] if result else None

            if show_all_symbols:
                cur.execute('SELECT DISTINCT ON (symbol) id, symbol FROM stocks ORDER BY symbol, id;')
                stocks = cur.fetchall()
            elif show_holdings:
                cur.execute('SELECT id, symbol FROM stocks WHERE watchlist_id = (SELECT id FROM watchlists WHERE name = \'Holdings\') ORDER BY symbol;')
                stocks = cur.fetchall()
            elif selected_watchlist_id:
                cur.execute('SELECT id, symbol FROM stocks WHERE watchlist_id = %s ORDER BY symbol;', (selected_watchlist_id,))
                stocks = cur.fetchall()

            if selected_stock_id:
                cur.execute('SELECT id, symbol FROM stocks WHERE id = %s AND watchlist_id = %s;', (selected_stock_id, selected_watchlist_id))
                result = cur.fetchone()
                if result:
                    stock_id, symbol = result
                    stock_data = fetch_stock_data_from_db(stock_id, symbol) or fetch_stock_data_api(stock_id, symbol)
                    if stock_data:
                        stock_data_list.append(stock_data)
                else:
                    flash("Invalid stock ID.", "error")
            elif show_all_symbols or show_holdings or selected_watchlist_id:
                all_stocks_data = []
                for stock in stocks:
                    stock_id, symbol = stock
                    stock_data = fetch_stock_data_from_db(stock_id, symbol) or fetch_stock_data_api(stock_id, symbol)
                    if stock_data:
                        all_stocks_data.append(stock_data)
                all_stocks_data.sort(key=lambda x: x.get('change_percent', 0), reverse=True)
                top_worst_stocks = all_stocks_data[:3] + all_stocks_data[-3:] if len(all_stocks_data) >= 3 else all_stocks_data
                stock_data_list = all_stocks_data

        except psycopg2.Error as e:
            flash("Failed to fetch data from database.", "error")
            logger.error(f"Database error: {e}")
            stock_data_list = [MOCK_STOCK_DATA[symbol] for symbol in ["AMPX", "ABCL", "RZLV", "SBET", "KULR"] if symbol in MOCK_STOCK_DATA]
            top_worst_stocks = stock_data_list[:3] + stock_data_list[-3:] if len(stock_data_list) >= 3 else stock_data_list
            stocks = [(0, symbol) for symbol in ["AMPX", "ABCL", "RZLV", "SBET", "KULR"]]
        finally:
            cur.close()
            conn.close()

    breaking_news = fetch_breaking_news()
    return render_template('index.html', watchlists=watchlists, stocks=stocks, stock_data_list=stock_data_list, 
                           selected_watchlist_id=selected_watchlist_id, selected_stock_id=selected_stock_id, 
                           breaking_news=breaking_news, selected_watchlist_name=selected_watchlist_name,
                           benchmarks=MOCK_BENCHMARKS, top_worst_stocks=top_worst_stocks,
                           current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT"),
                           market_status=get_market_status(),
                           watchlist_form=watchlist_form, add_stock_form=add_stock_form,
                           holdings_metrics=holdings_metrics, show_all_symbols=show_all_symbols, show_holdings=show_holdings)

@app.route('/add_watchlist', methods=['POST'])
def add_watchlist():
    form = WatchlistForm()
    if form.validate_on_submit():
        name = form.name.data
        if name.lower() == 'holdings':
            flash("Cannot create a watchlist named 'Holdings'.", "error")
            return redirect(url_for('index'))
        conn = get_db_connection()
        if not conn:
            return redirect(url_for('index'))

        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO watchlists (name) VALUES (%s) RETURNING id;', (name,))
            conn.commit()
            flash("Watchlist added successfully.", "success")
            logger.info(f"Added watchlist: {name}")
        except psycopg2.Error as e:
            conn.rollback()
            flash("Failed to add watchlist.", "error")
            logger.error(f"Failed to add watchlist: {e}")
        finally:
            cur.close()
            conn.close()
    else:
        flash("Invalid watchlist name.", "error")
        logger.warning(f"Invalid watchlist form submission: {form.errors}")
    return redirect(url_for('index'))

@app.route('/rename_watchlist/<int:watchlist_id>', methods=['POST'])
def rename_watchlist(watchlist_id):
    form = RenameWatchlistForm()
    if form.validate_on_submit():
        new_name = form.new_name.data
        if new_name.lower() == 'holdings':
            flash("Cannot rename to 'Holdings'.", "error")
            return redirect(url_for('index', watchlist_id=watchlist_id))
        conn = get_db_connection()
        if not conn:
            return redirect(url_for('index', watchlist_id=watchlist_id))

        cur = conn.cursor()
        try:
            cur.execute('SELECT name FROM watchlists WHERE id = %s;', (watchlist_id,))
            if cur.fetchone()[0].lower() == 'holdings':
                flash("Cannot rename the Holdings watchlist.", "error")
            else:
                cur.execute('UPDATE watchlists SET name = %s WHERE id = %s;', (new_name, watchlist_id))
                conn.commit()
                flash("Watchlist renamed successfully.", "success")
                logger.info(f"Renamed watchlist {watchlist_id} to {new_name}")
        except psycopg2.Error as e:
            conn.rollback()
            flash("Failed to rename watchlist.", "error")
            logger.error(f"Failed to rename watchlist: {e}")
        finally:
            cur.close()
            conn.close()
    else:
        flash("Invalid watchlist name.", "error")
        logger.warning(f"Invalid rename watchlist form submission: {form.errors}")
    return redirect(url_for('index', watchlist_id=watchlist_id))

@app.route('/delete_watchlist/<int:watchlist_id>', methods=['POST'])
def delete_watchlist(watchlist_id):
    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('index'))

    cur = conn.cursor()
    try:
        cur.execute('SELECT name FROM watchlists WHERE id = %s;', (watchlist_id,))
        if cur.fetchone()[0].lower() == 'holdings':
            flash("Cannot delete the Holdings watchlist.", "error")
        else:
            cur.execute('DELETE FROM stock_data WHERE stock_id IN (SELECT id FROM stocks WHERE watchlist_id = %s);', (watchlist_id,))
            cur.execute('DELETE FROM stocks WHERE watchlist_id = %s;', (watchlist_id,))
            cur.execute('DELETE FROM watchlists WHERE id = %s;', (watchlist_id,))
            conn.commit()
            flash("Watchlist deleted successfully.", "success")
            logger.info(f"Deleted watchlist {watchlist_id}")
    except psycopg2.Error as e:
        conn.rollback()
        flash("Failed to delete watchlist.", "error")
        logger.error(f"Failed to delete watchlist: {e}")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('index'))

@app.route('/add_stock', methods=['POST'])
def add_stock():
    form = AddStockForm()
    if form.validate_on_submit():
        watchlist_id = form.watchlist_id.data
        symbol = form.symbol.data.upper()
        purchase_price = form.purchase_price.data
        shares = form.shares.data
        valid_symbols = ["AMPX", "ABCL", "RZLV", "SBET", "KULR", "JNJ", "PG", "KO", "PFE", "PM", "AAPL", "MSFT", "GOOGL", "JPM", "XOM", "NVDA", "AMD", "TSLA", "RGTI", "MARA", "OKLO", "UEC", "LTBR", "NEE", "ENPH"]
        if symbol == "F":
            flash("Corrected symbol 'f' to 'F' (Ford).", "info")
        elif symbol not in valid_symbols:
            flash(f"Invalid symbol: {symbol}.", "error")
            logger.warning(f"Attempted to add invalid stock symbol: {symbol}")
            return redirect(url_for('index', watchlist_id=watchlist_id))

        conn = get_db_connection()
        if not conn:
            return redirect(url_for('index', watchlist_id=watchlist_id))

        cur = conn.cursor()
        try:
            cur.execute('SELECT name FROM watchlists WHERE id = %s;', (watchlist_id,))
            watchlist_name = cur.fetchone()[0]
            if watchlist_name.lower() == 'holdings' and (not purchase_price or not shares):
                flash("Purchase price and shares are required for Holdings.", "error")
                cur.close()
                conn.close()
                return redirect(url_for('index', watchlist_id=watchlist_id))

            cur.execute('INSERT INTO stocks (watchlist_id, symbol, purchase_price, shares) VALUES (%s, %s, %s, %s) RETURNING id;', 
                        (watchlist_id, symbol, purchase_price, shares))
            stock_id = cur.fetchone()[0]
            conn.commit()
            flash("Stock added successfully.", "success")
            logger.info(f"Added stock {symbol} to watchlist {watchlist_id}")
            stock_data = fetch_stock_data_api(stock_id, symbol)
            if stock_data:
                save_stock_data_to_db(stock_id, stock_data)
        except psycopg2.Error as e:
            conn.rollback()
            flash("Failed to add stock.", "error")
            logger.error(f"Failed to add stock: {e}")
        finally:
            cur.close()
            conn.close()
    else:
        flash("Invalid stock symbol or watchlist ID.", "error")
        logger.warning(f"Invalid add stock form submission: {form.errors}")
    return redirect(url_for('index', watchlist_id=watchlist_id))

@app.route('/delete_stock/<int:stock_id>', methods=['POST'])
def delete_stock(stock_id):
    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('index'))

    cur = conn.cursor()
    try:
        cur.execute('SELECT watchlist_id FROM stocks WHERE id = %s;', (stock_id,))
        result = cur.fetchone()
        if not result:
            flash("Stock not found.", "error")
            return redirect(url_for('index'))

        watchlist_id = result[0]
        cur.execute('DELETE FROM stock_data WHERE stock_id = %s;', (stock_id,))
        cur.execute('DELETE FROM stocks WHERE id = %s;', (stock_id,))
        conn.commit()
        flash("Stock deleted successfully.", "success")
        logger.info(f"Deleted stock {stock_id}")
    except psycopg2.Error as e:
        conn.rollback()
        flash("Failed to delete stock.", "error")
        logger.error(f"Failed to delete stock: {e}")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('index', watchlist_id=watchlist_id))

@app.errorhandler(404)
def page_not_found(e):
    logger.error(f"404 error: {e}")
    return render_template('error.html', error="Page not found."), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"500 error: {e}")
    return render_template('error.html', error="Internal server error."), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5002)