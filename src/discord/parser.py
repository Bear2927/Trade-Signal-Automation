"""Discord message parsing utilities."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedSignal:
    """Parsed trade signal from Discord message."""
    ticker: Optional[str] = None
    direction: Optional[str] = None  # LONG, SHORT
    entry: Optional[float] = None
    target: Optional[float] = None
    stop_loss: Optional[float] = None
    expiry: Optional[str] = None
    strike: Optional[float] = None
    option_type: Optional[str] = None  # CALL, PUT
    confidence: float = 0.0  # 0-1 confidence score
    raw_text: str = ""


class DiscordParser:
    """Parse Discord messages for trade signals."""

    # Common signal patterns
    TICKER_PATTERN = re.compile(r'\$?([A-Z]{1,5})\b')
    PRICE_PATTERN = re.compile(r'[\$]?(\d+(?:\.\d+)?)\s*[kK]?\b')
    OPTION_PATTERN = re.compile(r'(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s*([CPcp])\s*(\d+(?:\.\d+)?)')

    # Direction keywords
    LONG_KEYWORDS = ['long', 'buy', 'bullish', 'calls', 'call', 'going up', 'moon', '🚀', '📈']
    SHORT_KEYWORDS = ['short', 'sell', 'bearish', 'puts', 'put', 'going down', 'tank', '📉', '🔻']

    @classmethod
    def parse(cls, text: str) -> ParsedSignal:
        """Parse message text for trade signal components."""
        signal = ParsedSignal(raw_text=text)
        text_lower = text.lower()

        # Extract ticker
        tickers = cls.TICKER_PATTERN.findall(text.upper())
        false_positives = {
            'THE', 'AND', 'FOR', 'ARE', 'YOU', 'THIS', 'THAT', 'WITH', 'FROM',
            'HAVE', 'BEEN', 'WILL', 'WOULD', 'COULD', 'SHOULD', 'WHEN', 'WHERE',
            'WHAT', 'WHY', 'HOW', 'ALL', 'ANY', 'SOME', 'ONE', 'TWO', 'NEW',
            'OLD', 'HIGH', 'LOW', 'OPEN', 'CLOSE', 'VOL', 'VOLUME', 'PRICE',
            'TRADE', 'SIGNAL', 'ALERT', 'UPDATE', 'ENTRY', 'EXIT', 'TARGET',
            'STOP', 'LOSS', 'GAIN', 'PROFIT', 'RISK', 'REWARD', 'SPY', 'QQQ',
            'IWM', 'DIA', 'VIX', 'UVXY', 'SVXY', 'TLT', 'GLD', 'SLV', 'USO',
            'UNG', 'XLE', 'XLF', 'XLK', 'XLI', 'XLP', 'XLU', 'XLV', 'XLY'
        }
        valid_tickers = [t for t in tickers if t not in false_positives and 1 <= len(t) <= 5]
        if valid_tickers:
            signal.ticker = valid_tickers[0]
            signal.confidence += 0.3

        # Extract direction
        for kw in cls.LONG_KEYWORDS:
            if kw in text_lower:
                signal.direction = 'LONG'
                signal.confidence += 0.2
                break
        if not signal.direction:
            for kw in cls.SHORT_KEYWORDS:
                if kw in text_lower:
                    signal.direction = 'SHORT'
                    signal.confidence += 0.2
                    break

        # Extract option contract
        option_match = cls.OPTION_PATTERN.search(text)
        if option_match:
            signal.expiry = option_match.group(1)
            signal.option_type = option_match.group(2).upper()
            signal.strike = float(option_match.group(3))
            signal.confidence += 0.3

        # Extract prices
        prices = cls.PRICE_PATTERN.findall(text)
        if prices:
            prices = [float(p) for p in prices]
            # Heuristic: entry is often first mentioned, target second, stop third
            if len(prices) >= 1:
                signal.entry = prices[0]
                signal.confidence += 0.1
            if len(prices) >= 2:
                signal.target = prices[1]
                signal.confidence += 0.1
            if len(prices) >= 3:
                signal.stop_loss = prices[2]
                signal.confidence += 0.1

        # Cap confidence
        signal.confidence = min(signal.confidence, 1.0)

        return signal

    @classmethod
    def is_likely_signal(cls, text: str, min_confidence: float = 0.3) -> bool:
        """Quick check if message looks like a trade signal."""
        signal = cls.parse(text)
        return signal.confidence >= min_confidence