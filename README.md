# Market Sirens

Market Sirens is a Flask-based web application for managing stock watchlists, integrating with the Marketstack API to fetch real-time stock data and PostgreSQL for persistent storage. Users can create watchlists, add/delete stocks, and view stock details in a user-friendly dashboard.

## Features
- Create and manage stock watchlists.
- Add/delete stocks to/from watchlists.
- Fetch real-time stock data via Marketstack API.
- PostgreSQL database for storing watchlists and stocks.
- Flash messages for user feedback.
- Secure environment variable management with `python-dotenv`.

## Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Marketstack API key
- Git

## Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/market-sirens.git
   cd market-sirens
   ```

2. **Set Up Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure PostgreSQL**:
   - Install PostgreSQL:
     ```bash
     sudo apt update
     sudo apt install postgresql postgresql-contrib
     ```
   - Start PostgreSQL:
     ```bash
     sudo systemctl start postgresql
     sudo systemctl enable postgresql
     ```
   - Create database and user:
     ```bash
     sudo -u postgres psql
     CREATE DATABASE marketsirens;
     CREATE USER sirenuser WITH PASSWORD 'yourpassword';
     GRANT ALL PRIVILEGES ON DATABASE marketsirens TO sirenuser;
     \q
     ```
   - Initialize schema:
     ```bash
     psql -U sirenuser -d marketsirens -f schema.sql
     ```

4. **Configure Environment**:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env`:
     ```
     DATABASE_URL=postgresql://sirenuser:yourpassword@localhost:5432/marketsirens
     SECRET_KEY=your_secret_key_here
     MARKETSTACK_API_KEY=your_marketstack_api_key_here
     ```

5. **Run the Application**:
   ```bash
   python app.py
   ```
   Access at `http://localhost:5002`.

## Project Structure
```
market-sirens/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── schema.sql          # Database schema
├── .env.example       # Example environment file
├── templates/         # HTML templates
│   ├── index.html
│   ├── stocks_list.html
│   ├── stock_data.html
│   ├── error.html
```

## Future Integrations and Features
1. **Alternative APIs**: Integrate Yahoo Finance or Alpha Vantage for stock data redundancy.
2. **User Authentication**: Add OAuth2/login for user accounts.
3. **Portfolio Tracking**: Calculate portfolio value and performance metrics.
4. **Price Alerts**: Notify users via email/SMS when stocks hit price thresholds.
5. **Charting**: Add interactive stock price charts using Chart.js.
6. **Mobile App**: Develop iOS/Android apps with React Native.
7. **WebSocket Updates**: Real-time stock price updates via WebSockets.
8. **Machine Learning**: Predict stock trends using scikit-learn.
9. **Export Data**: Allow CSV/Excel export of watchlists.
10. **Dark Mode**: Implement a dark theme for UI.
11. **Multi-Market Support**: Add support for crypto/forex markets.
12. **Watchlist Sharing**: Enable public/private watchlist sharing.
13. **API Endpoint**: Expose REST API for external integrations.
14. **Unit Tests**: Add pytest for automated testing.
15. **Docker Support**: Containerize app with Docker Compose.
16. **Rate Limiting**: Implement Flask-Limiter for API abuse prevention.
17. **Localization**: Support multiple languages for UI.
18. **News Integration**: Fetch stock-related news via NewsAPI.
19. **Performance Dashboard**: Visualize stock performance metrics.
20. **CI/CD Pipeline**: Set up GitHub Actions for automated deployment.

## Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/yourfeature`).
3. Commit changes (`git commit -m 'Add yourfeature'`).
4. Push to the branch (`git push origin feature/yourfeature`).
5. Open a pull request.

## License
MIT License. See `LICENSE` for details.

## Contact
For issues or suggestions, open a GitHub issue or contact [your.email@example.com](mailto:your.email@example.com).# MarketMachine
