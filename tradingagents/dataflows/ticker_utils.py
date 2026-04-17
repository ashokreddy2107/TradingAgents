import yfinance as yf
import logging

logger = logging.getLogger(__name__)

def resolve_yfinance_ticker(symbol: str) -> str:
    """
    Attempts to resolve a ticker symbol by trying common exchange suffixes if the base symbol yields no data.
    
    Args:
        symbol (str): The ticker symbol to resolve.
        
    Returns:
        str: The resolved ticker symbol (e.g., adds .NS if OLECTRA was provided).
    """
    if not symbol:
        return symbol
        
    symbol = symbol.strip().upper()
    
    # If it already has an exchange suffix, trust it
    if "." in symbol:
        return symbol
        
    # Standard common suffixes to try if the base symbol fails
    # .NS = NSE (India), .BO = BSE (India), .TO = Toronto, .L = London, .HK = Hong Kong, .T = Tokyo
    suffixes = [".NS", ".BO", ".TO", ".L", ".HK", ".T"]
    
    # Try the base symbol first
    try:
        ticker = yf.Ticker(symbol)
        # We use fast_info or history(period="1d") to verify the ticker exists
        # history is more reliable as some "invalid" tickers might still have metadata but no price data
        hist = ticker.history(period="1d")
        if not hist.empty:
            return symbol
    except Exception:
        pass
        
    # If base symbol failed, try suffixes
    for suffix in suffixes:
        alt_symbol = symbol + suffix
        try:
            ticker = yf.Ticker(alt_symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                logger.info(f"Resolved ticker '{symbol}' to '{alt_symbol}'")
                return alt_symbol
        except Exception:
            continue
            
    # Default to original symbol if no working suffix found
    return symbol
