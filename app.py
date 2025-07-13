from flask import Flask, request, render_template, redirect, url_for, flash
import psycopg2
from dotenv import load_dotenv
import os
import logging
import requests

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

# Database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except psycopg2.Error as e:
        flash("Database connection failed.", "error")
        logging.error(f"Database connection error: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    watchlists = []
    stocks = []
    stock_data_list = []
    selected_watchlist_id = request.args.get('watchlist_id', type=int)

    if conn:
        cur = conn.cursor()
        try:
            # Fetch all watchlists
            cur.execute('SELECT id, name FROM watchlists;')
            watchlists = cur.fetchall()

            # Fetch stocks for selected watchlist
            if selected_watchlist_id:
                cur.execute('SELECT id, symbol FROM stocks WHERE watchlist_id = %s;', (selected_watchlist_id,))
                stocks = cur.fetchall()

                # Fetch EOD data for all stocks in the watchlist
                for stock in stocks:
                    stock_id, symbol = stock
                    endpoint = f"{MARKETSTACK_BASE_URL}/tickers/{symbol.lower()}/eod/latest"
                    params = {"access_key": MARKETSTACK_API_KEY}
                    try:
                        response = requests.get(endpoint, params=params)
                        if response.status_code == 200:
                            data = response.json()
                            if 'error' not in data and data.get('close') is not None:
                                stock_data = {
                                    'symbol': symbol,
                                    'close': data.get('close', 'N/A'),
                                    'open': data.get('open', 'N/A'),
                                    'high': data.get('high', 'N/A'),
                                    'low': data.get('low', 'N/A'),
                                    'volume': data.get('volume', 'N/A')
                                }
                                stock_data_list.append(stock_data)
                                logging.debug(f"Stock data for {symbol}: {stock_data}")
                            else:
                                flash(f"No data available for {symbol}.", "error")
                        else:
                            flash(f"API error for {symbol}: {response.status_code}", "error")
                            logging.error(f"API error: {response.status_code} - {response.text}")
                    except requests.RequestException as e:
                        flash(f"Failed to fetch data for {symbol}.", "error")
                        logging.error(f"Request error: {e}")
        except psycopg2.Error as e:
            flash("Failed to fetch data.", "error")
            logging.error(f"Database error: {e}")
        finally:
            cur.close()
            conn.close()

    return render_template('index.html', watchlists=watchlists, stocks=stocks, stock_data_list=stock_data_list, selected_watchlist_id=selected_watchlist_id)

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)