from flask import Flask, request, render_template, redirect, url_for, flash
import psycopg2
from dotenv import load_dotenv
import os
import logging
import requests
from time import sleep
from requests.exceptions import HTTPError
from datetime import datetime

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
    ]
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

def fetch_stock_data_api(symbol):
    endpoint = f"{MARKETSTACK_BASE_URL}/tickers/{symbol.lower()}/eod/latest"
    params = {"access_key": MARKETSTACK_API_KEY}
    for attempt in range(3):
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            if 'error' not in data and data.get('close') is not None:
                # Mock trend and MACD (replace with Alpha Vantage API)
                trend = "Up" if data.get('close', 0) > data.get('open', 0) else "Down" if data.get('close', 0) < data.get('open', 0) else "Neutral"
                macd_signal = "Buy" if data.get('close', 0) > data.get('open', 0) else "Sell" if data.get('close', 0) < data.get('open', 0) else "Neutral"
                # Mock mini news and news items
                mini_news = {
                    "SOFI": "Q2 earnings beat expectations",
                    "NVDA": "New AI chip launch announced",
                    "TSLA": "Regulatory scrutiny on self-driving tech"
                }.get(symbol, "No recent news")
                news_items = MOCK_NEWS_ITEMS.get(symbol, [])
                return {
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
            flash(f"No data available for {symbol}.", "error")
            return None
        except HTTPError as e:
            if response.status_code == 429:  # Rate limit
                sleep(2 ** attempt)  # Exponential backoff
                continue
            flash(f"API error for {symbol}: {response.status_code}", "error")
            logging.error(f"API error: {response.status_code} - {response.text}")
            return None
        except requests.RequestException as e:
            flash(f"Failed to fetch data for {symbol}.", "error")
            logging.error(f"Request error: {e}")
            return None
    flash(f"Rate limit exceeded for {symbol}.", "error")
    return None

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

            # Fetch EOD data for selected stock or all stocks
            if selected_stock_id:
                cur.execute('SELECT symbol FROM stocks WHERE id = %s AND watchlist_id = %s;', (selected_stock_id, selected_watchlist_id))
                result = cur.fetchone()
                if result:
                    stock_data = fetch_stock_data_api(result[0])
                    if stock_data:
                        stock_data_list.append(stock_data)
                else:
                    flash("Invalid stock ID.", "error")
            else:
                all_stocks_data = []
                for stock in stocks:
                    stock_data = fetch_stock_data_api(stock[1])
                    if stock_data:
                        all_stocks_data.append(stock_data)
                # Sort for top/worst stocks
                all_stocks_data.sort(key=lambda x: x.get('change_percent', 0), reverse=True)
                top_worst_stocks = all_stocks_data[:3] + all_stocks_data[-3:] if len(all_stocks_data) >= 3 else all_stocks_data
                stock_data_list = all_stocks_data if show_all_symbols or selected_watchlist_id else []

        except psycopg2.Error as e:
            flash("Failed to fetch data.", "error")
            logging.error(f"Database error: {e}")
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
    symbol = request.form['symbol']
    if not symbol or not watchlist_id:
        flash("Stock symbol or watchlist ID cannot be empty.", "error")
        return redirect(url_for('index'))

    conn = get_db_connection()
    if not conn:
        return redirect(url_for('index'))

    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO stocks (watchlist_id, symbol) VALUES (%s, %s);', (watchlist_id, symbol.upper()))
        conn.commit()
        flash("Stock added successfully.", "success")
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