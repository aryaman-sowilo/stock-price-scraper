from functools   import lru_cache
from fastapi     import FastAPI, HTTPException
from bs4         import BeautifulSoup
import requests, re
import uvicorn
import os

HEADERS = {
    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
}

@lru_cache(maxsize=256)                # -- 60-second cache avoids hammering Google
def scrape_google_finance(symbol: str) -> dict:
    """Return price, abs change, % change and market-cap scraped from Google Finance."""
    url  = f"https://www.google.com/finance/quote/{symbol}?hl=en"
    print(f"Fetching data from: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        print(f"Response status: {response.status_code}")
        html = response.text
    except Exception as e:
        print(f"Error fetching URL: {e}")
        raise ValueError(f"Failed to fetch data: {e}")
    
    soup = BeautifulSoup(html, "lxml")

    # Debug: Print the first 2000 characters of HTML to see structure
    print("HTML preview (first 2000 chars):")
    print(html[:2000])
    print("\n" + "="*50 + "\n")

    # First try to get price from data attribute (most reliable)
    # Look for the main stock container with the symbol data
    price_container = soup.find('div', {'data-entity-type': '0'}) or soup.find('div', {'data-last-price': True})
    if price_container:
        price_data = price_container.get('data-last-price')
        if price_data:
            try:
                price = float(price_data)
                print(f"✓ Found price from data-last-price attribute: {price}")
            except (ValueError, TypeError):
                price = None
                print(f"✗ Failed to parse data-last-price: {price_data}")
        else:
            price = None
            print("Found container but no data-last-price attribute")
    else:
        price = None
        print("No data-last-price attribute found, trying CSS selectors...")
        
    # Fallback to CSS selectors if data attribute method failed
    price_selectors = [
        "main div.YMlKec.fxKbKc",  # More specific - look in main content area
        "div.AHmHk div.YMlKec.fxKbKc",  # Target the main price display area
        "div.YMlKec.fxKbKc",
        "main div.YMlKec",  # More specific for main content
        "div.YMlKec",
        "span.YMlKec",
        ".YMlKec",
        "div[data-last-price]",
        "span[data-last-price]",
        "div[data-price]",
        "span[data-price]",
        "div[data-value]",
        "span[data-value]",
        ".price",
        "[data-price]",
        "div[class*='price']",
        "span[class*='price']",
        "div[class*='value']",
        "span[class*='value']",
        "div[class*='last']",
        "span[class*='last']",
        "div[class*='quote']",
        "span[class*='quote']"
    ]
    
    # Only try CSS selectors if data attribute method failed
    if price is None:
        price_tag = None
        print("Trying price selectors:")
        
        # Filter out prices that look like market indices (too high for stock prices)
        for selector in price_selectors:
            elements = soup.select(selector)
            print(f"Found {len(elements)} elements with selector: {selector}")
            
            for i, element in enumerate(elements):
                print(f"  Element {i+1} text: '{element.text}'")
                try:
                    # Clean the text and extract number
                    clean_text = element.text.replace(",", "").replace("$", "").strip()
                    potential_price = float(clean_text)
                    
                    # Skip market index prices (typically over 1000) and focus on stock prices
                    if 1 <= potential_price <= 1000:  # Reasonable US stock price range
                        price = potential_price
                        price_tag = element
                        print(f"  ✓ Using stock price: {price} (skipping market indices)")
                        break
                    else:
                        print(f"  ✗ Skipping market index price: {potential_price}")
                        
                except ValueError as e:
                    print(f"  ✗ Failed to parse element text: {e}")
                    continue
            
            if price is not None:
                break
    
    if price is None:
        print("\nNo price found with any method. Looking for any number that might be a price...")
        # Try to find any element with a number that looks like a price
        for element in soup.find_all(text=re.compile(r'\$?\d+\.?\d*')):
            print(f"Found potential price text: {element}")
            try:
                clean_text = element.replace(",", "").replace("$", "").strip()
                potential_price = float(clean_text)
                if 1 < potential_price < 10000:  # Reasonable stock price range
                    price = potential_price
                    print(f"Using potential price: {price}")
                    break
            except ValueError:
                continue

    # Try multiple selectors for change - updated with current Google Finance classes
    change_selectors = [
        "div.JwB6zf",  # Current class for change display
        "span.NydbP",  # Container for change information
        "div[data-change]",
        "span[data-change]",
        ".change",
        "[data-change]",
        "div[class*='change']",
        "span[class*='change']",
        "div[class*='diff']",
        "span[class*='diff']"
    ]
    
    print("\nTrying change selectors:")
    chg_block = None
    for selector in change_selectors:
        chg_block = soup.select_one(selector)
        if chg_block:
            print(f"✓ Found change block with selector: {selector}")
            print(f"  Change block text: '{chg_block.text}'")
            break
        else:
            print(f"✗ No match for selector: {selector}")
    
    abs_chg, pct_chg = (None, None)
    if chg_block:
        change_text = chg_block.text.strip()
        print(f"  Raw change text: '{change_text}'")
        
        # Current Google Finance format is just the percentage like "-0.31%"
        if '%' in change_text:
            pct_chg = change_text
            print(f"  ✓ Parsed percent change: {pct_chg}")
            
            # Calculate absolute change from percentage and current price
            if price:
                try:
                    pct_val = float(pct_chg.replace('%', '').replace('+', ''))
                    abs_val = price * (pct_val / 100)
                    abs_chg = f"{abs_val:+.2f}"
                    print(f"  ✓ Calculated absolute change: {abs_chg}")
                except (ValueError, TypeError):
                    pass
        else:
            # Fallback: try traditional format like "+1.50 (+0.74%)"  
            full_match = re.search(r"([+\-]?[0-9.,]+)\s*\(([+\-]?[0-9.,%]+)\)", change_text)
            if full_match:
                abs_chg, pct_chg = full_match.groups()
                print(f"  ✓ Parsed absolute change: {abs_chg}")
                print(f"  ✓ Parsed percent change: {pct_chg}")

    # Try multiple selectors for market cap - updated patterns
    market_cap_selectors = [
        "div.P6K39c",   # Value container class seen in HTML
        "div.KFglDc",   # Legacy class
        "div[data-market-cap]",
        "span[data-market-cap]",
        ".market-cap",
        "[data-market-cap]",
        "div[class*='cap']",
        "span[class*='cap']",
        "div[class*='P6K39c']",  # Current value display class
        "span[class*='P6K39c']"
    ]
    
    print("\nTrying market cap selectors:")
    mkt_cap = None
    for selector in market_cap_selectors:
        rows = soup.select(selector)
        print(f"Found {len(rows)} elements with selector: {selector}")
        for i, row in enumerate(rows):
            print(f"  Row {i+1} text: '{row.text}'")
            if "Mkt cap" in row.text or "Market cap" in row.text:
                val = row.select_one("div.P6K39c") or row.select_one("span") or row
                mkt_cap = val.text if val else None
                print(f"  ✓ Market cap value: {mkt_cap}")
                break
        if mkt_cap:
            break

    if price is None:
        print("\nERROR: Could not find price with any selector")
        print("This suggests Google Finance has completely changed their HTML structure")
        raise ValueError("Unable to parse quote — Google changed its markup?")

    result = {
        "symbol":      symbol,
        "price":       price,
        "abs_change":  abs_chg,
        "pct_change":  pct_chg,
        "market_cap":  mkt_cap,
    }
    
    print(f"\nFinal result: {result}")
    return result


app = FastAPI(title="Stock Price Scraper", description="Scrape stock prices from Google Finance")

@app.get("/quote")
def get_quote(symbol: str = "AAPL"):
    """Get stock quote for a given symbol."""
    try:
        return scrape_google_finance(symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quote: {str(e)}")

@app.get("/")
def root():
    """Root endpoint with usage instructions."""
    return {
        "message": "Stock Price Scraper API",
        "usage": "GET /quote?symbol=AAPL to get stock quote",
        "example": "/quote?symbol=GOOGL"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)