"""Parser for Facebook Messenger trade format."""

import re
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class MessengerTrade:
    """Parsed trade from Messenger format."""
    ticker: str
    expiration: str
    strike: str
    option_type: str  # C or P
    entry_price: str
    stop_loss: str
    profit_target: str
    notes: Optional[str] = None
    raw_text: str = ""
    is_valid: bool = False


class MessengerTradeParser:
    """Parse and validate trades from Facebook Messenger format."""

    # Pattern: TICKER MMMDD STRIKEC/P ENTRY s/l STOPLOSS pt PROFITTARGET
    # Example: MDB OCT16 425C 1.25 s/l 0.70 pt 2.10
    TRADE_PATTERN = re.compile(
        r'^([A-Z]{1,5})\s+'  # Ticker
        r'([A-Z]{3}\d{1,2})\s+'  # Expiration (OCT16)
        r'(\d+)\s*([CP])\s+'  # Strike and type
        r'([\d.]+)\s+'  # Entry price
        r's/l\s+'  # Stop loss label
        r'([\d.]+)\s+'  # Stop loss value
        r'pt\s+'  # Profit target label
        r'([\d.]+)',  # Profit target value
        re.IGNORECASE | re.MULTILINE
    )

    @classmethod
    def parse_message(cls, message: str) -> Optional[MessengerTrade]:
        """
        Parse a single Messenger message for trade format.

        Returns:
            MessengerTrade if valid format, None otherwise
        """
        message = message.strip()
        if not message:
            return None

        # Split by newlines to handle multi-line messages
        lines = message.split('\n')

        # Look for trade pattern in first line
        trade_line = lines[0].strip()
        match = cls.TRADE_PATTERN.match(trade_line)

        if not match:
            return None

        # Extract groups
        ticker = match.group(1).upper()
        expiration = match.group(2).upper()
        strike = match.group(3)
        option_type = match.group(4).upper()
        entry_price = match.group(5)
        stop_loss = match.group(6)
        profit_target = match.group(7)

        # Get notes from remaining lines
        notes = None
        if len(lines) > 1:
            notes = '\n'.join(lines[1:]).strip()

        trade = MessengerTrade(
            ticker=ticker,
            expiration=expiration,
            strike=strike,
            option_type=option_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            profit_target=profit_target,
            notes=notes,
            raw_text=message,
            is_valid=True
        )

        return trade

    @classmethod
    def is_trade_message(cls, message: str) -> bool:
        """Check if message contains a valid trade."""
        parsed = cls.parse_message(message)
        return parsed is not None and parsed.is_valid

    @classmethod
    def format_for_social_media(cls, trade: MessengerTrade) -> str:
        """Format parsed trade for social media posting."""
        # Format: TICKER EXPIRATION STRIKE[C/P] Entry: PRICE, SL: LOSS, PT: TARGET
        formatted = (
            f"📊 {trade.ticker} {trade.expiration} {trade.strike}{trade.option_type}\n"
            f"📈 Entry: ${trade.entry_price} | SL: ${trade.stop_loss} | PT: ${trade.profit_target}"
        )

        if trade.notes:
            formatted += f"\n💡 {trade.notes}"

        return formatted


# Test the parser
if __name__ == "__main__":
    test_messages = [
        "MDB OCT16 425C 1.25 s/l 0.70 pt 2.10\nrotation to software",
        "TSM OCT23 410P 1.20 s/l 0.64 pt 2.20\npattern",
        "Invalid message",
        "AAPL JAN24 150C 2.50 s/l 1.80 pt 4.00",
    ]

    print("="*70)
    print("MESSENGER TRADE PARSER TEST")
    print("="*70)
    print("")

    for msg in test_messages:
        print(f"Message:")
        print(f"  {msg}")
        print("")

        parsed = MessengerTradeParser.parse_message(msg)

        if parsed and parsed.is_valid:
            print(f"✅ Valid Trade:")
            print(f"   Ticker: {parsed.ticker}")
            print(f"   Expiration: {parsed.expiration}")
            print(f"   Strike: {parsed.strike}{parsed.option_type}")
            print(f"   Entry: ${parsed.entry_price}")
            print(f"   S/L: ${parsed.stop_loss}")
            print(f"   P/T: ${parsed.profit_target}")
            if parsed.notes:
                print(f"   Notes: {parsed.notes}")
            print("")
            print(f"Formatted for social media:")
            print(f"{MessengerTradeParser.format_for_social_media(parsed)}")
        else:
            print(f"❌ Not a valid trade format")

        print("")
        print("-" * 70)
        print("")
