"""Message formatting utilities for Discord embeds and plain text."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class TradeSignal:
    """Parsed trade signal components."""
    raw_text: str
    ticker: Optional[str] = None
    direction: Optional[str] = None  # LONG, SHORT, CALL, PUT
    entry: Optional[str] = None
    target: Optional[str] = None
    stop_loss: Optional[str] = None
    expiry: Optional[str] = None
    strike: Optional[str] = None
    option_type: Optional[str] = None  # CALL, PUT
    source: str = ""
    author: str = ""
    channel: str = ""


class SignalFormatter:
    """Formats trade signals for different output formats."""

    # Regex patterns for common signal formats
    TICKER_PATTERN = re.compile(r'\b[A-Z]{1,5}\b')
    PRICE_PATTERN = re.compile(r'\$?(\d+(?:\.\d+)?)(?:\s*[kcK]?\b)')
    DIRECTION_KEYWORDS = {
        'long': ['long', 'buy', 'bullish', 'calls'],
        'short': ['short', 'sell', 'bearish', 'puts'],
    }

    @classmethod
    def parse(cls, text: str, source: str = "", author: str = "", channel: str = "") -> TradeSignal:
        """Parse raw signal text into structured components."""
        signal = TradeSignal(
            raw_text=text,
            source=source,
            author=author,
            channel=channel,
        )

        # Extract ticker (first uppercase word 1-5 chars, common tickers)
        tickers = cls.TICKER_PATTERN.findall(text.upper())
        # Filter common false positives
        false_positives = {'THE', 'AND', 'FOR', 'ARE', 'YOU', 'THIS', 'THAT', 'WITH', 'FROM', 'HAVE', 'BEEN', 'WILL', 'WOULD', 'COULD', 'SHOULD', 'WHEN', 'WHERE', 'WHAT', 'WHY', 'HOW', 'ALL', 'ANY', 'SOME', 'ONE', 'TWO', 'NEW', 'OLD', 'HIGH', 'LOW', 'OPEN', 'CLOSE', 'VOL', 'VOLUME', 'PRICE', 'TRADE', 'SIGNAL', 'ALERT', 'UPDATE', 'ENTRY', 'EXIT', 'TARGET', 'STOP', 'LOSS', 'GAIN', 'PROFIT', 'RISK', 'REWARD'}
        valid_tickers = [t for t in tickers if t not in false_positives and len(t) <= 5]
        if valid_tickers:
            signal.ticker = valid_tickers[0]

        # Extract direction
        text_lower = text.lower()
        for direction, keywords in cls.DIRECTION_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                signal.direction = direction.upper()
                break

        # Extract prices (entry, target, stop)
        prices = cls.PRICE_PATTERN.findall(text)
        if prices:
            # Heuristic: first price is often entry, then target, then stop
            if len(prices) >= 1:
                signal.entry = prices[0]
            if len(prices) >= 2:
                signal.target = prices[1]
            if len(prices) >= 3:
                signal.stop_loss = prices[2]

        # Extract options specifics
        option_match = re.search(r'(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s*([CP])\s*(\d+)', text, re.IGNORECASE)
        if option_match:
            signal.expiry = option_match.group(1)
            signal.option_type = option_match.group(2).upper()
            signal.strike = option_match.group(3)

        return signal

    @classmethod
    def format_discord_embed(cls, signal: TradeSignal) -> dict:
        """Format signal as Discord embed."""
        color = 0x00FF00  # Green default
        if signal.direction == 'SHORT':
            color = 0xFF0000  # Red for short
        elif signal.direction == 'LONG':
            color = 0x00FF00  # Green for long

        title = "📈 Trade Signal"
        if signal.ticker:
            title += f" • {signal.ticker}"

        fields = []
        if signal.direction:
            emoji = "📈" if signal.direction == "LONG" else "📉"
            fields.append({"name": "Direction", "value": f"{emoji} {signal.direction}", "inline": True})
        if signal.entry:
            fields.append({"name": "Entry", "value": f"${signal.entry}", "inline": True})
        if signal.target:
            fields.append({"name": "Target", "value": f"${signal.target}", "inline": True})
        if signal.stop_loss:
            fields.append({"name": "Stop Loss", "value": f"${signal.stop_loss}", "inline": True})
        if signal.expiry and signal.strike and signal.option_type:
            fields.append({"name": "Option", "value": f"{signal.expiry} {signal.strike}{signal.option_type}", "inline": True})
        if signal.source:
            fields.append({"name": "Source", "value": signal.source, "inline": True})
        if signal.author:
            fields.append({"name": "Author", "value": signal.author, "inline": True})

        embed = {
            "title": title,
            "description": signal.raw_text[:4096],
            "color": color,
            "fields": fields,
            "footer": {"text": f"StockTradingSignals • {signal.source}"},
        }
        return embed

    @classmethod
    def format_twitter(cls, signal: TradeSignal, max_chars: int = 280) -> str:
        """Format signal for X/Twitter (character limited)."""
        parts = []
        if signal.ticker:
            parts.append(f"${signal.ticker}")
        if signal.direction:
            parts.append(signal.direction)
        if signal.entry:
            parts.append(f"Entry: ${signal.entry}")
        if signal.target:
            parts.append(f"Target: ${signal.target}")
        if signal.stop_loss:
            parts.append(f"SL: ${signal.stop_loss}")
        if signal.expiry and signal.strike and signal.option_type:
            parts.append(f"{signal.expiry} {signal.strike}{signal.option_type}")

        text = " | ".join(parts)
        if len(text) > max_chars:
            text = text[:max_chars - 3] + "..."
        return text

    @classmethod
    def format_stocktwits(cls, signal: TradeSignal) -> str:
        """Format signal for Stocktwits (supports cashtags and sentiment)."""
        parts = []
        if signal.ticker:
            parts.append(f"${signal.ticker}")
        if signal.direction:
            sentiment = "Bullish" if signal.direction == "LONG" else "Bearish"
            parts.append(f"#{sentiment}")
        parts.append(signal.raw_text[:1500])  # Stocktwits allows longer
        return " ".join(parts)

    @classmethod
    def format_threads(cls, signal: TradeSignal) -> str:
        """Format signal for Threads/Instagram."""
        lines = []
        if signal.ticker:
            lines.append(f"📊 ${signal.ticker}")
        if signal.direction:
            emoji = "📈" if signal.direction == "LONG" else "📉"
            lines.append(f"{emoji} {signal.direction}")
        if signal.entry:
            lines.append(f"💰 Entry: ${signal.entry}")
        if signal.target:
            lines.append(f"🎯 Target: ${signal.target}")
        if signal.stop_loss:
            lines.append(f"🛑 Stop: ${signal.stop_loss}")
        if signal.expiry and signal.strike and signal.option_type:
            lines.append(f"📅 {signal.expiry} {signal.strike}{signal.option_type}")
        lines.append(f"\n📍 Source: {signal.source}")
        if signal.author:
            lines.append(f"👤 {signal.author}")
        lines.append("\n#trading #stocks #signals #stockmarket")
        return "\n".join(lines)

    @classmethod
    def format_telegram(cls, signal: TradeSignal) -> str:
        """Format signal for Telegram (Markdown)."""
        lines = []
        if signal.ticker:
            lines.append(f"*${signal.ticker}*")
        if signal.direction:
            emoji = "📈" if signal.direction == "LONG" else "📉"
            lines.append(f"{emoji} *{signal.direction}*")
        if signal.entry:
            lines.append(f"💰 Entry: `${signal.entry}`")
        if signal.target:
            lines.append(f"🎯 Target: `${signal.target}`")
        if signal.stop_loss:
            lines.append(f"🛑 Stop Loss: `${signal.stop_loss}`")
        if signal.expiry and signal.strike and signal.option_type:
            lines.append(f"📅 Option: `{signal.expiry} {signal.strike}{signal.option_type}`")
        lines.append(f"\n📍 Source: {signal.source}")
        if signal.author:
            lines.append(f"👤 {signal.author}")
        lines.append(f"\n```\n{signal.raw_text[:500]}\n```")
        return "\n".join(lines)

    @classmethod
    def format_reddit(cls, signal: TradeSignal) -> tuple[str, str]:
        """Format signal for Reddit (title, body). Returns (title, body)."""
        title_parts = []
        if signal.ticker:
            title_parts.append(f"${signal.ticker}")
        if signal.direction:
            title_parts.append(signal.direction)
        if signal.entry:
            title_parts.append(f"Entry ${signal.entry}")
        title = " | ".join(title_parts) or "Trade Signal"

        body = f"**Source:** {signal.source}\n"
        if signal.author:
            body += f"**Author:** {signal.author}\n"
        body += f"\n{signal.raw_text}\n"
        body += "\n---\n*Posted via StockTradingSignals*"
        return title, body

    @classmethod
    def format_email(cls, signal: TradeSignal) -> tuple[str, str]:
        """Format signal for email (subject, body). Returns (subject, html_body)."""
        subject_parts = ["Trade Signal"]
        if signal.ticker:
            subject_parts.append(signal.ticker)
        if signal.direction:
            subject_parts.append(signal.direction)
        subject = " - ".join(subject_parts)

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">📈 Trade Signal Alert</h2>
            <table style="width: 100%; border-collapse: collapse;">
        """
        if signal.ticker:
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Ticker:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">${signal.ticker}</td></tr>'
        if signal.direction:
            color = "#00AA00" if signal.direction == "LONG" else "#CC0000"
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Direction:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee; color: {color};"><strong>{signal.direction}</strong></td></tr>'
        if signal.entry:
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Entry:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">${signal.entry}</td></tr>'
        if signal.target:
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Target:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">${signal.target}</td></tr>'
        if signal.stop_loss:
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Stop Loss:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">${signal.stop_loss}</td></tr>'
        if signal.expiry and signal.strike and signal.option_type:
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Option:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{signal.expiry} {signal.strike}{signal.option_type}</td></tr>'
        html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Source:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{signal.source}</td></tr>'
        if signal.author:
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Author:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{signal.author}</td></tr>'
        html += f"""
            </table>
            <hr style="margin: 20px 0;">
            <p style="white-space: pre-wrap; background: #f5f5f5; padding: 15px; border-radius: 5px;">{signal.raw_text}</p>
            <hr style="margin: 20px 0;">
            <p style="color: #888; font-size: 12px;">Sent via StockTradingSignals</p>
        </body>
        </html>
        """
        return subject, html


def format_for_platform(signal: TradeSignal, platform: str, max_chars: Optional[int] = None) -> str:
    """Format signal for a specific platform."""
    formatter_map = {
        'discord': lambda s: SignalFormatter.format_discord_embed(s),
        'twitter': lambda s: SignalFormatter.format_twitter(s, max_chars or 280),
        'stocktwits': SignalFormatter.format_stocktwits,
        'threads': SignalFormatter.format_threads,
        'telegram': SignalFormatter.format_telegram,
        'reddit': lambda s: SignalFormatter.format_reddit(s)[1],  # body only
        'email': lambda s: SignalFormatter.format_email(s)[1],  # html body only
    }
    formatter = formatter_map.get(platform.lower())
    if formatter:
        return formatter(signal)
    return signal.raw_text