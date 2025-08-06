# Stock Price Scraper

A FastAPI-based web scraper that extracts real-time stock prices from Google Finance.

## Features

- Scrapes stock prices, percentage changes, and calculated absolute changes
- RESTful API endpoint for easy integration
- Handles multiple price formats and selectors
- Filters out market index data to focus on individual stocks
- Built-in caching and error handling

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python3 -m venv stock_scraper_env
   source stock_scraper_env/bin/activate  # On Windows: stock_scraper_env\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the server:
   ```bash
   python "price scraper.py"
   ```

2. The API will be available at `http://localhost:8002`

3. Get stock data:
   ```bash
   curl "http://localhost:8002/quote?symbol=AAPL"
   ```

## API Endpoints

- `GET /` - API information and usage instructions
- `GET /quote?symbol=SYMBOL` - Get stock quote for the specified symbol

### Example Response
```json
{
  "symbol": "AAPL",
  "price": 202.92,
  "abs_change": "-3.23",
  "pct_change": "-1.59%",
  "market_cap": null
}
```

## Supported Symbols

Any stock symbol available on Google Finance (AAPL, GOOGL, MSFT, etc.)

## Deployment

This application can be deployed on various platforms:

- **Railway**: Connect your GitHub repo for automatic deployment
- **Render**: Easy Python app deployment
- **DigitalOcean**: VPS hosting with full control
- **AWS/GCP**: Cloud platform deployment

## Important Notes

- This scraper is for educational purposes
- Be mindful of rate limiting and Google's Terms of Service
- Consider using official financial APIs for production use
- Web scraping can break when websites change their structure

## License

MIT License