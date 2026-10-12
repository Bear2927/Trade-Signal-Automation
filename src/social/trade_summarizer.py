"""Trade idea summarizer for social media posting."""

import re
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class TradeSummary:
    """Summarized trade for social media."""
    ticker: Optional[str] = None
    strike: Optional[str] = None
    entry_price: Optional[str] = None
    direction: Optional[str] = None
    trade_type: Optional[str] = None  # options, stock, etc
    final_result: Optional[str] = None  # percentage like "76%", "+50%", etc
    summary_text: str = ""


class TradeSummarizer:
    """Summarize trade ideas and results for social media posting."""

    @classmethod
    def summarize(cls, message: str) -> TradeSummary:
        """
        Summarize a trade message extracting key info and final result.

        Examples:
        - "$SPY 780C @.13 lotto size" → SPY call at .13, trade type: options
        - "76% profit" → Final result: 76%
        - "50%+ took more scales off" → Final result: 50%+
        """
        summary = TradeSummary()

        # Extract ticker and strike (for options)
        # Pattern: $TICKER STRIKEC/P
        option_pattern = r'\$([A-Z]{1,5})\s*(\d+)\s*([CP])'
        option_match = re.search(option_pattern, message, re.IGNORECASE)

        if option_match:
            summary.ticker = option_match.group(1)
            summary.strike = option_match.group(2)
            summary.direction = "CALL" if option_match.group(3).upper() == "C" else "PUT"
            summary.trade_type = "options"
        else:
            # Try to find just a ticker
            ticker_pattern = r'\$([A-Z]{1,5})\b'
            ticker_match = re.search(ticker_pattern, message)
            if ticker_match:
                summary.ticker = ticker_match.group(1)
                summary.trade_type = "stock"

        # Extract entry price (@ price)
        price_pattern = r'@[\s]*([0-9.]+)'
        price_match = re.search(price_pattern, message)
        if price_match:
            summary.entry_price = price_match.group(1)

        # Extract direction keywords
        message_lower = message.lower()
        if any(word in message_lower for word in ['long', 'buy', 'call', 'bull']):
            summary.direction = summary.direction or "LONG"
        elif any(word in message_lower for word in ['short', 'sell', 'put', 'bear']):
            summary.direction = summary.direction or "SHORT"

        # Extract final result percentage (last occurrence)
        # Patterns: "76%", "+50%", "50%+", "+76% profit", etc
        percent_pattern = r'([+-]?\d+%\+?|\d+%\+)'
        percent_matches = re.findall(percent_pattern, message)
        if percent_matches:
            # Take the last percentage as final result
            summary.final_result = percent_matches[-1]

        # Create summary text
        summary.summary_text = cls._create_summary_text(summary, message)

        return summary

    @classmethod
    def _create_summary_text(cls, summary: TradeSummary, original_message: str) -> str:
        """Create a formatted summary for social media."""
        parts = []

        # Trade identifier
        if summary.ticker:
            if summary.trade_type == "options":
                # Format: SPY 780C @.13
                trade_id = f"{summary.ticker} {summary.strike}{summary.direction[0]}"
                if summary.entry_price:
                    trade_id += f" @{summary.entry_price}"
            else:
                # Format: SPY
                trade_id = summary.ticker

            parts.append(f"📊 Trade: {trade_id}")

        # Direction
        if summary.direction and summary.trade_type == "stock":
            direction_text = "📈 Long" if "LONG" in summary.direction else "📉 Short"
            parts.append(direction_text)

        # Final result
        if summary.final_result:
            # Add emoji based on positive/negative
            if '+' in summary.final_result or summary.final_result[0].isdigit():
                emoji = "✅"
            else:
                emoji = "❌"

            parts.append(f"{emoji} Result: {summary.final_result}")

        # Combine
        if parts:
            return " | ".join(parts)
        else:
            # Fallback to original if can't parse
            return original_message[:100]

    @classmethod
    def format_for_social_media(cls, message: str, platform: str = "twitter") -> str:
        """
        Format a trade message for social media posting.

        Args:
            message: Original trade message
            platform: 'twitter', 'stocktwits', 'threads'

        Returns:
            Formatted message for the platform
        """
        summary = cls.summarize(message)

        if platform.lower() == "twitter":
            return cls._format_twitter(summary)
        elif platform.lower() == "stocktwits":
            return cls._format_stocktwits(summary)
        elif platform.lower() == "threads":
            return cls._format_threads(summary)
        else:
            return summary.summary_text

    @classmethod
    def _format_twitter(cls, summary: TradeSummary) -> str:
        """Format for Twitter/X (280 chars limit)."""
        text = summary.summary_text

        # Keep it concise for Twitter
        if len(text) > 280:
            # Truncate intelligently
            if summary.final_result:
                text = f"📊 {summary.ticker or 'Trade'} | {summary.final_result} ✅"
            else:
                text = text[:277] + "..."

        return text

    @classmethod
    def _format_stocktwits(cls, summary: TradeSummary) -> str:
        """Format for Stocktwits (more lenient on length)."""
        text = summary.summary_text

        # Add cashtag for stocktwits
        if summary.ticker:
            text += f" ${summary.ticker}"

        return text

    @classmethod
    def _format_threads(cls, summary: TradeSummary) -> str:
        """Format for Threads (500 chars limit)."""
        text = summary.summary_text

        # Can be more detailed than Twitter
        if summary.final_result and summary.ticker:
            text = f"{summary.summary_text}\n\n#trading #{summary.ticker.lower()}"

        return text


# Example usage
if __name__ == "__main__":
    test_messages = [
        "$SPY 780C @.13 lotto size",
        "76%",
        "50%+ took more scales off",
        "30% took some scales on chop session"
    ]

    for msg in test_messages:
        summary = TradeSummarizer.summarize(msg)
        print(f"Original: {msg}")
        print(f"Summary:  {summary.summary_text}")
        print(f"Twitter:  {TradeSummarizer.format_for_social_media(msg, 'twitter')}")
        print()
