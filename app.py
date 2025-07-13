# File: app.py
# Version: 1.0.8
# Date: 2025-07-13
# Time: 14:30 EDT
# Description: Market Siren watchlist application
# Changes:
# - 1.0.0: Initial version with watchlist management, stock data, news, and market benchmarks
# - 1.0.1: Added inline watchlist editing, compact menu styling, and breaking news
# - 1.0.2: Added Mini News modal, market movers, and Show All Symbols button
# - 1.0.3: Added thin header with dropdown, moved Show All Symbols to Watchlists, reorganized Row 3 Column 3 into three 30% divs
# - 1.0.4: Moved Market Movers, Benchmarks, and Status to Row 2 Column 3; enhanced layout
# - 1.0.5: Fixed layout to match desired structure; moved All Symbols to mini button; added fallback for rate limit errors
# - 1.0.6: Fixed stock data loading with robust fallback; ensured watchlist stocks display
# - 1.0.7: Added database storage for stock data; prioritized DB/cache over API
# - 1.0.8: Ensured watchlist stocks display with database fallback; fixed empty table issue

from flask import Flask, request, render_template, redirect, url_for, flash
import psycopg2
from dotenv import load_dotenv
import os
import logging
import requests
from time import sleep
from requests.exceptions import HTTPError
from datetime import datetime
import json

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Marketstack API configuration
MARKETSTACK_API_KEY = os.getenv("MARKETSTACK_API_KEY")
MARKETSTACK_BASE_URL = "http://api.marketstack.com/v1"

# Cache for stock data (symbol -> data, timestamp)
STOCK_CACHE = {}
CACHE_TIMEOUT = 86400  # Cache for 24 hours (in seconds)

# Mock breaking news (replace with real news API in production)
MOCK_BREAKING_NEWS = [
    "Levi Strauss (LEVI) rises 7% after beating Q2 earnings expectations",
    "Nvidia (NVDA) hits $4T market cap, first in history",
    "Tesla (TSLA) down 7% after Musk's political party announcement"
]

# Mock news items for modal (replace with API like Alpha Vantage or NewsAPI)
MOCK_NEWS_ITEMS = {
    "SOFI": [
        {"date": "2025-07-13 09:00 EDT", "text": "Q2 earnings beat expectations"},
        {"date": "2025-07-12 15:30 EDT", "text": "Announces new lending platform"},
        {"date": "2025-07-11 10:00 EDT", "text": "Partnership with fintech startup"}
    ],
    "NVDA": [
        {"date": "2025-07-13 08:00 EDT", "text": "New AI chip launch announced"},
        {"date": "2025-07-12 12:00 EDT", "text": "Hits $4T market cap"},
        {"date": "2025-07-11 14:00 EDT", "text": "Expands AI research lab"}
    ],
    "TSLA": [
        {"date": "2025-07-13 07:00 EDT", "text": "Regulatory scrutiny on self-driving tech"},
        {"date": "2025-07-12 11:00 EDT", "text": "Musk announces new factory"},
        {"date": "2025-07-11 09:00 EDT", "text": "Q2 delivery numbers released"}
    ],
    "KULR": [
        {"date": "2025-07-13 10:00 EDT", "text": "New battery tech patent filed"},
        {"date": "2025-07-12 09:00 EDT", "text": "Partnership with aerospace firm"},
        {"date": "2025-07-11 08:00 EDT", "text": "Q2 results expected next week"}
    ],
    "F": [
        {"date": "2025-07-13 08:30 EDT", "text": "Ford announces new EV model"},
        {"date": "2025-07-12 10:00 EDT", "text": "Q2 sales report released"},
        {"date": "2025-07-11 11:00 EDT", "text": "Expands production capacity"}
    ]
}

# Mock stock data for fallback (used when rate limit exceeded or invalid symbol)
MOCK_STOCK_DATA = {
    "SOFI": {"symbol": "SOFI", "close": 7.50, "open": 7.20, "high": 7.60, "low": 7.10, "volume": 1000000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Q2 earnings beat expectations", "news_items": MOCK_NEWS_ITEMS["SOFI"], "change_percent": 4.17},
    "NVDA": {"symbol": "NVDA", "close": 130.00, "open": 128.50, "high": 131.00, "low": 127.00, "volume": 2000000, "trend": "Up", "macd_signal": "Buy", "mini_news": "New AI chip launch announced", "news_items": MOCK_NEWS_ITEMS["NVDA"], "change_percent": 1.17},
    "TSLA": {"symbol": "TSLA", "close": 240.00, "open": 245.00, "high": 248.00, "low": 238.00, "volume": 1500000, "trend": "Down", "macd_signal": "Sell", "mini_news": "Regulatory scrutiny on self-driving tech", "news_items": MOCK_NEWS_ITEMS["TSLA"], "change_percent": -2.04},
    "KULR": {"symbol": "KULR", "close": 0.40, "open": 0.42, "high": 0.43, "low": 0.39, "volume": 500000, "trend": "Down", "macd_signal": "Sell", "mini_news": "New battery tech patent filed", "news_items": MOCK_NEWS_ITEMS["KULR"], "change_percent": -4.76},
    "F": {"symbol": "F", "close": 12.00, "open": 11.80, "high": 12.10, "low": 11.70, "volume": 1200000, "trend": "Up", "macd_signal": "Buy", "mini_news": "Ford announces new EV model", "news_items": MOCK_NEWS_ITEMS["F"], "change_percent": 1.69}
}

# Mock market benchmarks (replace with Marketstack API)
MOCK_BENCHMARKS = [
    {"symbol": "^GSPC", "name": "S&P 500", "close": 5600.12, "change": 0.45},
    {"symbol": "^DJI", "name": "Dow Jones", "close": 40000.90, "change": -0.23},
    {"symbol": "^IXIC", "name": "Nasdaq", "close": 18300.45, "change": 0.67}
]

# Database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except psycopg2.Error as e:
        flash("Database connection failed.", "error")
        logging.error(f"Database connection error: {e}")
        return None

def save_stock_data_to_db(stock_id, stock_data):
    conn = get_db_connection()
    if not conn:
        return

    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO stock_data (stock_id, symbol, close, open, high, low, volume, trend, macd_signal, mini_news, news_items, change_percent, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (stock_id) DO UPDATE
            SET close = EXCLUDED.close,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                volume = EXCLUDED.volume,
                trend = EXCLUDED.trend,
                macd_signal = EXCLUDED.macd_signal,
                mini_news = EXCLUDED.mini_news,
                news_items = EXCLUDED.news_items,
                change_percent = EXCLUDED.change_percent,
                updated_at = EXCLUDED.updated_at;
        ''', (
            stock_id,
            stock_data['symbol'],
            stock_data['close'],
            stock_data['open'],
            stock_data['high'],
            stock_data['low'],
            stock_data['volume'],
            stock_data['trend'],
            stock_data['macd_signal'],
            stock_data['mini_news'],
            json.dumps(stock_data['news_items']),
            stock_data['change_percent'],
            datetime.now()
        ))
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        logging.error(f"Failed to save stock data to DB: {e}")
    finally:
        cur.close()
        conn.close()

def fetch_stock_data_from_db(stock_id, symbol):
    conn = get_db_connection()
    if not conn:
        return None

    cur = conn.cursor()
    try:
        cur.execute('SELECT symbol, close, open, high, low, volume, trend, macd_signal, mini_news, news_items, change_percent, updated_at FROM stock_data WHERE stock_id = %s AND symbol = %s;', (stock_id, symbol))
        result = cur.fetchone()
        if result:
            # Check if data is recent (within 24 hours)
            updated_at = result[11]
            if (datetime.now() - updated_at).total_seconds() < CACHE_TIMEOUT:
                return {
                    'symbol': result[0],
                    'close': result[1] if result[1] is not None else 'N/A',
                    'open': result[2] if result[2] is not None else 'N/A',
                    'high': result[3] if result[3] is not None else 'N/A',
                    'low': result[4] if result[4] is not None else 'N/A',
                    'volume': result[5] if result[5] is not None else 'N/A',
                    'trend': result[6] if result[6] else 'N/A',
                    'macd_signal': result[7] if result[7] else 'N/A',
                    'mini_news': result[8] if result[8] else 'No recent news',
                    'news_items': result[9] if result[9] else [],
                    'change_percent': result[10] if result[10] is not None else 0
                }
        return None
    except psycopg2.Error as e:
        logging.error(f"Failed to fetch stock data from DB: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def fetch_stock_data_api(stock_id, symbol):
    # Normalize symbol
    symbol = symbol.upper()
    if symbol == "f":
        symbol = "F"
        flash("Corrected symbol 'f' to 'F' (Ford).", "info")

    # Check cache first
    if symbol in STOCK_CACHE:
        cached_data, timestamp = STOCK_CACHE[symbol]
        if (datetime.now().timestamp() - timestamp) < CACHE_TIMEOUT:
            return cached_data
        else:
            del STOCK_CACHE[symbol]  # Clear expired cache

    # Check database
    db_data = fetch_stock_data_from_db(stock_id, symbol)
    if db_data:
        STOCK_CACHE[symbol] = (db_data, datetime.now().timestamp())
        return db_data

    # Validate symbol
    valid_symbols = ["SOFI", "NVDA", "TSLA", "KULR", "F"]
    if symbol not in valid_symbols:
        flash(f"Invalid symbol: {symbol}. Using fallback data.", "error")
        stock_data = MOCK_STOCK_DATA.get(symbol, None)
        if stock_data:
            save_stock_data_to_db(stock_id, stock_data)
            STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
        return stock_data

    endpoint = f"{MARKETSTACK_BASE_URL}/tickers/{symbol.lower()}/eod/latest"
    params = {"access_key": MARKETSTACK_API_KEY}
    for attempt in range(5):
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            if 'error' not in data and data.get('close') is not None:
                trend = "Up" if data.get('close', 0) > data.get('open', 0) else "Down" if data.get('close', 0) < data.get('open', 0) else "Neutral"
                macd_signal = "Buy" if data.get('close', 0) > data.get('open', 0) else "Sell" if data.get('close', 0) < data.get('open', 0) else "Neutral"
                mini_news = MOCK_NEWS_ITEMS.get(symbol, [{"text": "No recent news"}])[0]["text"]
                news_items = MOCK_NEWS_ITEMS.get(symbol, [])
                stock_data = {
                    'symbol': symbol,
                    'close': data.get('close', 'N/A'),
                    'open': data.get('open', 'N/A'),
                    'high': data.get('high', 'N/A'),
                    'low': data.get('low', 'N/A'),
                    'volume': data.get('volume', 'N/A'),
                    'trend': trend,
                    'macd_signal': macd_signal,
                    'mini_news': mini_news,
                    'news_items': news_items,
                    'change_percent': ((data.get('close', 0) - data.get('open', 0)) / data.get('open', 0) * 100) if data.get('open', 0) != 0 else 0
                }
                save_stock_data_to_db(stock_id, stock_data)
                STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
                return stock_data
            flash(f"No data available for {symbol}. Using fallback data.", "error")
            stock_data = MOCK_STOCK_DATA.get(symbol, None)
            if stock_data:
                save_stock_data_to_db(stock_id, stock_data)
                STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
            return stock_data
        except HTTPError as e:
            if response.status_code == 429:  # Rate limit
                sleep(2 ** (attempt + 1))  # Exponential backoff: 2, 4, 8, 16, 32 seconds
                continue
            flash(f"API error for {symbol}: {response.status_code}. Using fallback data.", "error")
            logging.error(f"API error: {response.status_code} - {response.text}")
            stock_data = MOCK_STOCK_DATA.get(symbol, None)
            if stock_data:
                save_stock_data_to_db(stock_id, stock_data)
                STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
            return stock_data
        except requests.RequestException as e:
            flash(f"Failed to fetch data for {symbol}. Using fallback data.", "error")
            logging.error(f"Request error: {e}")
            stock_data = MOCK_STOCK_DATA.get(symbol, None)
            if stock_data:
                save_stock_data_to_db(stock_id, stock_data)
                STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
            return stock_data
    flash(f"Rate limit exceeded for {symbol}. Using fallback data.", "error")
    stock_data = MOCK_STOCK_DATA.get(symbol, None)
    if stock_data:
        save_stock_data_to_db(stock_id, stock_data)
        STOCK_CACHE[symbol] = (stock_data, datetime.now().timestamp())
    return stock_data

def get_market_status():
    now = datetime.now()
    # NYSE/Nasdaq hours: 9:30 AM–4:00 PM EDT, Mon–Fri
    is_weekday = now.weekday() < 5
    market_open = datetime.strptime("09:30", "%H:%M").time()
    market_close = datetime.strptime("16:00", "%H:%M").time()
    return "Open" if is_weekday and market_open <= now.time() <= market_close else "Closed"

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    watchlists = []
    stocks = []
    stock_data_list = []
    selected_watchlist_id = request.args.get('watchlist_id', type=int)
    selected_stock_id = request.args.get('stock_id', type=int)
    show_all_symbols = request.args.get('show_all', type=int) == 1
    selected_watchlist_name = None
    top_worst_stocks = []

    if conn:
        cur = conn.cursor()
        try:
            # Fetch all watchlists
            cur.execute('SELECT id, name FROM watchlists;')
            watchlists = cur.fetchall()

            # Fetch selected watchlist name
            if selected_watchlist_id:
                cur.execute('SELECT name FROM watchlists WHERE id = %s;', (selected_watchlist_id,))
                result = cur.fetchone()
                selected_watchlist_name = result[0] if result else None

            # Fetch stocks
            if show_all_symbols:
                cur.execute('SELECT id, symbol FROM stocks;')
                stocks = cur.fetchall()
            elif selected_watchlist_id:
                cur.execute('SELECT id, symbol FROM stocks WHERE watchlist_id = %s;', (selected_watchlist_id,))
                stocks = cur.fetchall()

            # Fetch stock data
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
            elif show_all_symbols or selected_watchlist_id:
                all_stocks_data = []
                for stock in stocks:
                    stock_id, symbol = stock
                    stock_data = fetch_stock_data_from_db(stock_id, symbol) or fetch_stock_data_api(stock_id, symbol)
                    if stock_data:
                        all_stocks_data.append(stock_data)
                # Sort for top/worst stocks
                all_stocks_data.sort(key=lambda x: x.get('change_percent', 0), reverse=True)
                top_worst_stocks = all_stocks_data[:3] + all_stocks_data[-3:] if len(all_stocks_data) >= 3 else all_stocks_data
                stock_data_list = all_stocks_data

        except psycopg2.Error as e:
            flash("Failed to fetch data from database.", "error")
            logging.error(f"Database error: {e}")
            # Fallback to mock data for stocks
            stock_data_list = [MOCK_STOCK_DATA[symbol] for symbol in ["SOFI", "TSLA", "KULR", "F"] if symbol in MOCK_STOCK_DATA]
            top_worst_stocks = stock_data_list[:3] + stock_data_list[-3:] if len(stock_data_list) >= 3 else stock_data_list
            stocks = [(0, symbol) for symbol in ["SOFI", "TSLA", "KULR", "F"]]
        finally:
            cur.close()
            conn.close()

    return render_template('index.html', watchlists=watchlists, stocks=stocks, stock_data_list=stock_data_list, 
                           selected_watchlist_id=selected_watchlist_id, selected_stock_id=selected_stock_id, 
                           breaking_news=MOCK_BREAKING_NEWS, selected_watchlist_name=selected_watchlist_name,
                           benchmarks=MOCK_BENCHMARKS, top_worst_stocks=top_worst_stocks,
                           current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT"),
                           market_status=get_market_status())

@app.route('/add_watchlist', methods=['POST'])
def add_watchlist():
    name = request.form['name']
    if not name:
        flash("Watchlist name cannot be empty.", "error")
        return redirect(url_for('index'))

    conn = get_db_connection()
    if not conn:
        return redirect(url_for('index'))

    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO watchlists (name) VALUES (%s) RETURNING id;', (name,))
        conn.commit()
        flash("Watchlist added successfully.", "success")
    except psycopg2.Error as e:
        conn.rollback()
        flash("Failed to add watchlist.", "error")
        logging.error(f"Failed to add watchlist: {e}")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('index'))

@app.route('/rename_watchlist/<int:watchlist_id>', methods=['POST'])
def rename_watchlist(watchlist_id):
    new_name = request.form['new_name']
    if not new_name:
        flash("New watchlist name cannot be empty.", "error")
        return redirect(url_for('index', watchlist_id=watchlist_id))

    conn = get_db_connection()
    if not conn:
        return redirect(url_for('index', watchlist_id=watchlist_id))

    cur = conn.cursor()
    try:
        cur.execute('UPDATE watchlists SET name = %s WHERE id = %s;', (new_name, watchlist_id))
        conn.commit()
        flash("Watchlist renamed successfully.", "success")
    except psycopg2.Error as e:
        conn.rollback()
        flash("Failed to rename watchlist.", "error")
        logging.error(f"Failed to rename watchlist: {e}")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('index', watchlist_id=watchlist_id))

@app.route('/delete_watchlist/<int:watchlist_id>', methods=['POST'])
def delete_watchlist(watchlist_id):
    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('index'))

    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM stock_data WHERE stock_id IN (SELECT id FROM stocks WHERE watchlist_id = %s);', (watchlist_id,))
        cur.execute('DELETE FROM stocks WHERE watchlist_id = %s;', (watchlist_id,))
        cur.execute('DELETE FROM watchlists WHERE id = %s;', (watchlist_id,))
        conn.commit()
        flash("Watchlist deleted successfully.", "success")
    except psycopg2.Error as e:
        conn.rollback()
        flash("Failed to delete watchlist.", "error")
        logging.error(f"Failed to delete watchlist: {e}")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('index'))

@app.route('/add_stock', methods=['POST'])
def add_stock():
    watchlist_id = request.form['watchlist_id']
    symbol = request.form['symbol'].upper()
    if not symbol or not watchlist_id:
        flash("Stock symbol or watchlist ID cannot be empty.", "error")
        return redirect(url_for('index'))

    # Validate symbol
    valid_symbols = ["SOFI", "NVDA", "TSLA", "KULR", "F"]
    if symbol == "f":
        symbol = "F"
        flash("Corrected symbol 'f' to 'F' (Ford).", "info")
    elif symbol not in valid_symbols:
        flash(f"Invalid symbol: {symbol}.", "error")
        return redirect(url_for('index'))

    conn = get_db_connection()
    if not conn:
        return redirect(url_for('index'))

    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO stocks (watchlist_id, symbol) VALUES (%s, %s) RETURNING id;', (watchlist_id, symbol))
        stock_id = cur.fetchone()[0]
        conn.commit()
        flash("Stock added successfully.", "success")
        # Fetch and save stock data
        stock_data = fetch_stock_data_api(stock_id, symbol)
        if stock_data:
            save_stock_data_to_db(stock_id, stock_data)
    except psycopg2.Error as e:
        conn.rollback()
        flash("Failed to add stock.", "error")
        logging.error(f"Failed to add stock: {e}")
    finally:
        cur.close()
        conn.close()

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
    except psycopg2.Error as e:
        conn.rollback()
        flash("Failed to delete stock.", "error")
        logging.error(f"Failed to delete stock: {e}")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('index', watchlist_id=watchlist_id))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="Page not found."), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error="Internal server error."), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)