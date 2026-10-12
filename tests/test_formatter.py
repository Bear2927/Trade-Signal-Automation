"""Tests for signal formatter."""

import pytest
from src.common.formatter import SignalFormatter, TradeSignal, format_for_platform


class TestSignalFormatter:
    """Test signal parsing and formatting."""

    def test_parse_basic_signal(self):
        """Parse a basic trade signal."""
        text = "AAPL long entry 150 target 160 stop 145"
        signal = SignalFormatter.parse(text)

        assert signal.ticker == "AAPL"
        assert signal.direction == "LONG"
        assert signal.entry == "150"
        assert signal.target == "160"
        assert signal.stop_loss == "145"

    def test_parse_short_signal(self):
        """Parse a short signal."""
        text = "TSLA short entry 250 target 230 stop 260"
        signal = SignalFormatter.parse(text)

        assert signal.ticker == "TSLA"
        assert signal.direction == "SHORT"
        assert signal.entry == "250"

    def test_parse_option_signal(self):
        """Parse an options signal."""
        text = "SPY 03/15/2024 C 450 entry 5.50 target 8.00 stop 3.00"
        signal = SignalFormatter.parse(text)

        assert signal.ticker == "SPY"
        assert signal.expiry == "03/15/2024"
        assert signal.option_type == "C"
        assert signal.strike == "450"
        assert signal.entry == "5.50"

    def test_parse_put_option(self):
        """Parse a put option signal."""
        text = "QQQ 04/19/24 P 380 buy 4.20"
        signal = SignalFormatter.parse(text)

        assert signal.ticker == "QQQ"
        assert signal.expiry == "04/19/24"
        assert signal.option_type == "P"
        assert signal.strike == "380"
        assert signal.direction == "LONG"

    def test_false_positive_filter(self):
        """Common words should not be extracted as tickers."""
        text = "THE market is going up AND you should BUY"
        signal = SignalFormatter.parse(text)

        # THE, AND, BUY are false positives
        assert signal.ticker is None or signal.ticker not in {"THE", "AND", "BUY"}

    def test_format_discord_embed(self):
        """Format signal as Discord embed."""
        signal = TradeSignal(
            raw_text="AAPL long entry 150 target 160",
            ticker="AAPL",
            direction="LONG",
            entry="150",
            target="160",
            source="Discord#123",
            author="trader123",
        )

        embed = SignalFormatter.format_discord_embed(signal)

        assert embed["title"] == "📈 Trade Signal • AAPL"
        assert embed["color"] == 0x00FF00  # Green for long
        assert any(f["name"] == "Direction" for f in embed["fields"])
        assert any(f["name"] == "Entry" for f in embed["fields"])

    def test_format_discord_embed_short(self):
        """Format short signal with red color."""
        signal = TradeSignal(
            raw_text="TSLA short entry 250",
            ticker="TSLA",
            direction="SHORT",
            entry="250",
            source="Discord#123",
        )

        embed = SignalFormatter.format_discord_embed(signal)
        assert embed["color"] == 0xFF0000  # Red for short

    def test_format_twitter(self):
        """Format for Twitter (280 chars)."""
        signal = TradeSignal(
            raw_text="AAPL long entry 150 target 160 stop 145",
            ticker="AAPL",
            direction="LONG",
            entry="150",
            target="160",
            stop_loss="145",
        )

        tweet = SignalFormatter.format_twitter(signal)

        assert "$AAPL" in tweet
        assert "LONG" in tweet
        assert "Entry: $150" in tweet
        assert len(tweet) <= 280

    def test_format_twitter_truncation(self):
        """Long signal should be truncated."""
        signal = TradeSignal(
            raw_text="A" * 500,
            ticker="AAPL",
        )

        tweet = SignalFormatter.format_twitter(signal, max_chars=100)
        assert len(tweet) <= 100
        assert tweet.endswith("...")

    def test_format_stocktwits(self):
        """Format for Stocktwits."""
        signal = TradeSignal(
            raw_text="AAPL long entry 150",
            ticker="AAPL",
            direction="LONG",
        )

        st_text = SignalFormatter.format_stocktwits(signal)

        assert "$AAPL" in st_text
        assert "#Bullish" in st_text

    def test_format_threads(self):
        """Format for Threads."""
        signal = TradeSignal(
            raw_text="AAPL long entry 150",
            ticker="AAPL",
            direction="LONG",
            entry="150",
        )

        threads_text = SignalFormatter.format_threads(signal)

        assert "$AAPL" in threads_text
        assert "📈 LONG" in threads_text
        assert "💰 Entry: $150" in threads_text
        assert "#trading" in threads_text

    def test_format_telegram(self):
        """Format for Telegram (Markdown)."""
        signal = TradeSignal(
            raw_text="AAPL long entry 150",
            ticker="AAPL",
            direction="LONG",
            entry="150",
        )

        tg_text = SignalFormatter.format_telegram(signal)

        assert "*$AAPL*" in tg_text
        assert "*LONG*" in tg_text
        assert "`$150`" in tg_text

    def test_format_reddit(self):
        """Format for Reddit."""
        signal = TradeSignal(
            raw_text="AAPL long entry 150 target 160",
            ticker="AAPL",
            direction="LONG",
            entry="150",
            target="160",
            source="Discord#123",
        )

        title, body = SignalFormatter.format_reddit(signal)

        assert "$AAPL" in title
        assert "LONG" in title
        assert "Entry $150" in title
        assert "Source: Discord#123" in body

    def test_format_email(self):
        """Format for Email."""
        signal = TradeSignal(
            raw_text="AAPL long entry 150",
            ticker="AAPL",
            direction="LONG",
            entry="150",
            source="Discord#123",
        )

        subject, html = SignalFormatter.format_email(signal)

        assert "Trade Signal Alert" in subject
        assert "AAPL" in subject
        assert "LONG" in subject
        assert "<html>" in html
        assert "$150" in html

    def test_format_for_platform(self):
        """Test platform-specific formatting dispatcher."""
        signal = TradeSignal(
            raw_text="AAPL long entry 150",
            ticker="AAPL",
            direction="LONG",
            entry="150",
        )

        # Test each platform
        discord = format_for_platform(signal, 'discord')
        assert isinstance(discord, dict)
        assert "title" in discord

        twitter = format_for_platform(signal, 'twitter')
        assert isinstance(twitter, str)

        stocktwits = format_for_platform(signal, 'stocktwits')
        assert isinstance(stocktwits, str)

        threads = format_for_platform(signal, 'threads')
        assert isinstance(threads, str)

        telegram = format_for_platform(signal, 'telegram')
        assert isinstance(telegram, str)


class TestIsLikelySignal:
    """Test signal detection."""

    def test_detects_clear_signal(self):
        """Should detect clear trade signal."""
        text = "AAPL long entry 150 target 160 stop 145"
        assert SignalFormatter.is_likely_signal(text) is True

    def test_rejects_random_chat(self):
        """Should reject random chat messages."""
        text = "Hey guys how is everyone doing today?"
        assert SignalFormatter.is_likely_signal(text) is False

    def test_detects_option_signal(self):
        """Should detect option signals."""
        text = "SPY 03/15/24 C 450 entry 5.50"
        assert SignalFormatter.is_likely_signal(text) is True

    def test_detects_cashtag_signal(self):
        """Should detect cashtag format."""
        text = "$TSLA going to the moon 🚀 buy calls"
        assert SignalFormatter.is_likely_signal(text) is True