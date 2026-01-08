from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union, Any
from mcp.server.fastmcp import FastMCP
import random

# Section 1: Schema
class ExchangePriceData(BaseModel):
    """Represents price and volume data for an exchange."""
    price: float = Field(..., ge=0, description="Current price on exchange")
    volume: float = Field(..., ge=0, description="24h volume on exchange")

class CryptoData(BaseModel):
    """Represents current cryptocurrency data."""
    price_usd: float = Field(..., ge=0, description="Current price in USD")
    change_24h_percent: float = Field(..., description="24h price change percentage")
    volume_24h: float = Field(..., ge=0, description="24h trading volume in USD")
    market_cap: float = Field(..., ge=0, description="Market capitalization in USD")
    market_rank: int = Field(..., ge=1, description="Market cap rank")

class MarketAnalysis(BaseModel):
    """Represents market analysis data."""
    top_exchanges: List[Dict[str, Any]] = Field(default=[], description="Top 5 exchanges by volume")
    price_variations: Dict[str, Any] = Field(default={}, description="Price variation metrics")
    volume_distribution: Dict[str, Any] = Field(default={}, description="Volume distribution analysis")
    vwap: float = Field(..., ge=0, description="Volume weighted average price")

class HistoricalData(BaseModel):
    """Represents historical price analysis."""
    price_trends: List[float] = Field(default=[], description="Historical price time series")
    volatility_metrics: Dict[str, Any] = Field(default={}, description="Volatility analysis")
    high_price: float = Field(..., ge=0, description="Highest price in period")
    low_price: float = Field(..., ge=0, description="Lowest price in period")
    analysis_summary: str = Field(..., description="Human-readable analysis summary")

class CryptoScenario(BaseModel):
    """Main scenario model for cryptocurrency market data."""
    crypto_prices: Dict[str, CryptoData] = Field(default={}, description="Current crypto prices")
    exchange_data: Dict[str, Dict[str, ExchangePriceData]] = Field(default={}, description="Exchange-specific data")
    market_analyses: Dict[str, MarketAnalysis] = Field(default={}, description="Market analyses")
    historical_data: Dict[str, Dict[str, HistoricalData]] = Field(default={}, description="Historical price data")
    supported_symbols: List[str] = Field(default=["BTC", "ETH", "SOL", "ADA", "DOT", "LINK", "UNI", "AVAX", "MATIC", "LTC"], description="Supported cryptocurrency symbols")
    supported_exchanges: List[str] = Field(default=["binance", "coinbase", "kraken", "bitfinex", "huobi", "okex", "kucoin", "gateio", "bybit", "mexc"], description="Supported exchanges")
    random_seed: Optional[int] = Field(default=None, description="Random seed for reproducible results")

Scenario_Schema = [ExchangePriceData, CryptoData, MarketAnalysis, HistoricalData, CryptoScenario]

# Section 2: Class
class CryptoPriceAPI:
    def __init__(self):
        """Initialize crypto price API with empty state."""
        self.crypto_prices: Dict[str, CryptoData] = {}
        self.exchange_data: Dict[str, Dict[str, ExchangePriceData]] = {}
        self.market_analyses: Dict[str, MarketAnalysis] = {}
        self.historical_data: Dict[str, Dict[str, HistoricalData]] = {}
        self.supported_symbols: List[str] = []
        self.supported_exchanges: List[str] = []
        self.random_seed: Optional[int] = None
        
    def load_scenario(self, scenario: dict) -> None:
        """Load scenario data into the API instance."""
        model = CryptoScenario(**scenario)
        self.crypto_prices = model.crypto_prices
        self.exchange_data = model.exchange_data
        self.market_analyses = model.market_analyses
        self.historical_data = model.historical_data
        self.supported_symbols = model.supported_symbols
        self.supported_exchanges = model.supported_exchanges
        self.random_seed = model.random_seed

    def save_scenario(self) -> dict:
        """Save current state as scenario dictionary."""
        return {
            "crypto_prices": {k: v.dict() for k, v in self.crypto_prices.items()},
            "exchange_data": {
                symbol: {ex: data.dict() for ex, data in exchanges.items()}
                for symbol, exchanges in self.exchange_data.items()
            },
            "market_analyses": {k: v.dict() for k, v in self.market_analyses.items()},
            "historical_data": {
                symbol: {interval: data.dict() for interval, data in intervals.items()}
                for symbol, intervals in self.historical_data.items()
            },
            "supported_symbols": self.supported_symbols,
            "supported_exchanges": self.supported_exchanges,
            "random_seed": self.random_seed
        }

    def get_crypto_price(self, symbol: str, exchanges: Optional[List[str]] = None) -> dict:
        """Get current price and 24-hour statistics for a cryptocurrency."""
        if self.random_seed is not None:
            random.seed(self.random_seed)
            
        # Validate symbol is supported
        if symbol not in self.supported_symbols:
            raise ValueError(f"Symbol '{symbol}' is not supported. Supported symbols: {self.supported_symbols}")
            
        if symbol not in self.crypto_prices:
            # Generate mock data based on symbol
            base_price = {"BTC": 45000, "ETH": 3000, "SOL": 100, "ADA": 0.5, "DOT": 10,
                         "LINK": 15, "UNI": 20, "AVAX": 50, "MATIC": 1, "LTC": 80}.get(symbol, random.randint(10, 1000))
            
            self.crypto_prices[symbol] = CryptoData(
                price_usd=base_price * (1 + random.uniform(-0.1, 0.1)),
                change_24h_percent=random.uniform(-15, 15),
                volume_24h=random.randint(100000000, 5000000000),
                market_cap=random.randint(1000000000, 1000000000000),
                market_rank=random.randint(1, 100)
            )
        
        crypto_data = self.crypto_prices[symbol]
        result = {
            "price_usd": crypto_data.price_usd,
            "change_24h_percent": crypto_data.change_24h_percent,
            "volume_24h": crypto_data.volume_24h,
            "market_cap": crypto_data.market_cap,
            "market_rank": crypto_data.market_rank,
            "exchanges_prices": {}
        }
        
        # Add exchange-specific data if requested
        if exchanges:
            for exchange in exchanges:
                if exchange in self.supported_exchanges:
                    if symbol not in self.exchange_data:
                        self.exchange_data[symbol] = {}
                    if exchange not in self.exchange_data[symbol]:
                        self.exchange_data[symbol][exchange] = ExchangePriceData(
                            price=crypto_data.price_usd * (1 + random.uniform(-0.02, 0.02)),
                            volume=crypto_data.volume_24h * random.uniform(0.05, 0.3)
                        )
                    exchange_data = self.exchange_data[symbol][exchange]
                    result["exchanges_prices"][exchange] = {
                        "price": exchange_data.price,
                        "volume": exchange_data.volume
                    }
        
        return result

    def get_market_analysis(self, symbol: str, exchanges: Optional[List[str]] = None) -> dict:
        """Provide detailed market analysis for a cryptocurrency."""
        if self.random_seed is not None:
            random.seed(self.random_seed)
            
        # Validate symbol is supported
        if symbol not in self.supported_symbols:
            raise ValueError(f"Symbol '{symbol}' is not supported. Supported symbols: {self.supported_symbols}")
            
        if symbol not in self.market_analyses:
            # Ensure we have crypto data for this symbol first
            if symbol not in self.crypto_prices:
                self.get_crypto_price(symbol)
                
            # Generate top exchanges - ensure we don't sample more than available
            available_exchanges = self.supported_exchanges.copy()
            if exchanges:
                available_exchanges = [ex for ex in exchanges if ex in self.supported_exchanges]
            
            num_exchanges_to_sample = min(5, len(available_exchanges))
            if num_exchanges_to_sample == 0:
                # Use default exchanges if filtered list is empty
                available_exchanges = self.supported_exchanges[:5]
                num_exchanges_to_sample = min(5, len(available_exchanges))
            
            selected_exchanges = random.sample(available_exchanges, num_exchanges_to_sample)
            
            top_exchanges = []
            for i, exchange in enumerate(selected_exchanges):
                volume = random.randint(50000000, 500000000)
                base_price = self.crypto_prices[symbol].price_usd
                price = base_price * (1 + random.uniform(-0.05, 0.05))
                top_exchanges.append({
                    "rank": i + 1,
                    "exchange": exchange,
                    "price": price,
                    "volume": volume,
                    "market_share": random.uniform(5, 25)
                })
            
            # Calculate VWAP
            total_volume = sum(ex["volume"] for ex in top_exchanges)
            vwap = sum(ex["price"] * ex["volume"] for ex in top_exchanges) / total_volume if total_volume > 0 else 0
            
            self.market_analyses[symbol] = MarketAnalysis(
                top_exchanges=top_exchanges,
                price_variations={
                    "spread": random.uniform(0.1, 2.0),
                    "arbitrage_opportunities": random.randint(1, 5),
                    "price_std_dev": random.uniform(0.5, 5.0)
                },
                volume_distribution={
                    "total_volume": total_volume,
                    "exchange_count": len(self.supported_exchanges),
                    "concentration_ratio": random.uniform(0.3, 0.8)
                },
                vwap=vwap
            )
        
        analysis = self.market_analyses[symbol]
        result = {
            "top_exchanges": analysis.top_exchanges,
            "price_variations": analysis.price_variations,
            "volume_distribution": analysis.volume_distribution,
            "vwap": analysis.vwap,
            "exchanges_prices": {}
        }
        
        # Add exchange-specific data if requested
        if exchanges:
            for exchange in exchanges:
                if exchange in self.supported_exchanges:
                    if symbol not in self.exchange_data:
                        self.exchange_data[symbol] = {}
                    if exchange not in self.exchange_data[symbol]:
                        base_price = self.crypto_prices[symbol].price_usd
                        self.exchange_data[symbol][exchange] = ExchangePriceData(
                            price=base_price * (1 + random.uniform(-0.02, 0.02)),
                            volume=random.randint(10000000, 200000000)
                        )
                    exchange_data = self.exchange_data[symbol][exchange]
                    result["exchanges_prices"][exchange] = {
                        "price": exchange_data.price,
                        "volume": exchange_data.volume
                    }
        
        return result

    def get_historical_analysis(self, symbol: str, interval: str = "1d", days: int = 7) -> dict:
        """Analyze historical price data, trends, and volatility metrics."""
        if self.random_seed is not None:
            random.seed(self.random_seed)
            
        # Validate symbol is supported
        if symbol not in self.supported_symbols:
            raise ValueError(f"Symbol '{symbol}' is not supported. Supported symbols: {self.supported_symbols}")
            
        if symbol not in self.historical_data:
            self.historical_data[symbol] = {}
        
        if interval not in self.historical_data[symbol]:
            # Ensure we have crypto data for this symbol first
            if symbol not in self.crypto_prices:
                self.get_crypto_price(symbol)
                
            # Generate historical price trends
            current_price = self.crypto_prices[symbol].price_usd
            
            price_trends = []
            for i in range(days):
                if i == 0:
                    price = current_price
                else:
                    price = price * (1 + random.uniform(-0.05, 0.05))
                price_trends.append(price)
            
            high_price = max(price_trends)
            low_price = min(price_trends)
            
            # Calculate volatility metrics
            returns = [(price_trends[i] - price_trends[i-1]) / price_trends[i-1] * 100 
                      for i in range(1, len(price_trends))]
            volatility = (sum(r**2 for r in returns) / len(returns))**0.5 if returns else 0
            
            # Determine trend
            if price_trends[-1] > price_trends[0]:
                trend = "bullish"
            elif price_trends[-1] < price_trends[0]:
                trend = "bearish"
            else:
                trend = "neutral"
            
            self.historical_data[symbol][interval] = HistoricalData(
                price_trends=price_trends,
                volatility_metrics={
                    "standard_deviation": volatility,
                    "average_true_range": random.uniform(0.5, 5.0),
                    "sharpe_ratio": random.uniform(-2, 2),
                    "max_drawdown": random.uniform(5, 30)
                },
                high_price=high_price,
                low_price=low_price,
                analysis_summary=f"Historical analysis shows {trend} trend over {days} days with {volatility:.2f}% volatility. Price ranged from ${low_price:.2f} to ${high_price:.2f}."
            )
        
        historical = self.historical_data[symbol][interval]
        return {
            "price_trends": historical.price_trends,
            "volatility_metrics": historical.volatility_metrics,
            "high_price": historical.high_price,
            "low_price": historical.low_price,
            "analysis_summary": historical.analysis_summary
        }

# Section 3: MCP Tools
mcp = FastMCP(name="CryptoPrice")
api = CryptoPriceAPI()

@mcp.tool()
def load_scenario(scenario: dict) -> str:
    """
    Load scenario data into the crypto price API.
    
    Args:
        scenario (dict): Scenario dictionary matching CryptoScenario schema.
    
    Returns:
        success_message (str): Success message.
    """
    try:
        if not isinstance(scenario, dict):
            raise ValueError("Scenario must be a dictionary")
        api.load_scenario(scenario)
        return "Successfully loaded scenario"
    except Exception as e:
        raise e

@mcp.tool()
def save_scenario() -> dict:
    """
    Save current crypto state as scenario dictionary.
    
    Returns:
        scenario (dict): Dictionary containing all current state variables.
    """
    try:
        return api.save_scenario()
    except Exception as e:
        raise e

@mcp.tool()
def get_crypto_price(symbol: str, exchanges: Optional[List[str]] = None) -> dict:
    """
    Get current price and 24-hour statistics for a specific cryptocurrency.
    
    Args:
        symbol (str): The ticker symbol of the cryptocurrency to query.
        exchanges (list): [Optional] List of exchange names to retrieve prices from.
    
    Returns:
        price_usd (float): Current price in USD.
        change_24h_percent (float): 24h price change percentage.
        volume_24h (float): 24h trading volume in USD.
        market_cap (float): Market capitalization in USD.
        market_rank (int): Market cap rank.
        exchanges_prices (dict): Exchange-specific price and volume data.
    """
    try:
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")
        if exchanges and not isinstance(exchanges, list):
            raise ValueError("Exchanges must be a list")
        return api.get_crypto_price(symbol, exchanges)
    except Exception as e:
        raise e

@mcp.tool()
def get_market_analysis(symbol: str, exchanges: Optional[List[str]] = None) -> dict:
    """
    Provide detailed market analysis for a cryptocurrency.
    
    Args:
        symbol (str): The ticker symbol of the cryptocurrency to query.
        exchanges (list): [Optional] List of exchange names to analyze.
    
    Returns:
        top_exchanges (list): Top 5 exchanges by volume.
        price_variations (dict): Price variation metrics.
        volume_distribution (dict): Volume distribution analysis.
        vwap (float): Volume weighted average price.
        exchanges_prices (dict): Exchange-specific price and volume data.
    """
    try:
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")
        if exchanges and not isinstance(exchanges, list):
            raise ValueError("Exchanges must be a list")
        return api.get_market_analysis(symbol, exchanges)
    except Exception as e:
        raise e

@mcp.tool()
def get_historical_analysis(symbol: str, interval: str = "1d", days: int = 7) -> dict:
    """
    Analyze historical price data, trends, and volatility metrics.
    
    Args:
        symbol (str): The ticker symbol of the cryptocurrency to query.
        interval (str): [Optional] Time interval between data points. Default '1d'.
        days (int): [Optional] Number of days of data. Default 7.
    
    Returns:
        price_trends (list): Historical price time series.
        volatility_metrics (dict): Volatility analysis.
        high_price (float): Highest price in period.
        low_price (float): Lowest price in period.
        analysis_summary (str): Human-readable analysis summary.
    """
    try:
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")
        if not isinstance(interval, str):
            raise ValueError("Interval must be a string")
        if not isinstance(days, int) or days <= 0 or days > 30:
            raise ValueError("Days must be an integer between 1 and 30")
        if interval not in ["5m", "15m", "30m", "1h", "4h", "1d"]:
            raise ValueError("Interval must be one of: 5m, 15m, 30m, 1h, 4h, 1d")
        return api.get_historical_analysis(symbol, interval, days)
    except Exception as e:
        raise e

# Section 4: Entry Point
if __name__ == "__main__":
    mcp.run()