"""Tests for Discord and Messenger parsers."""

import pytest
from src.discord.parser import DiscordParser, ParsedSignal


class TestDiscordParser:
    """Test Discord message parsing."""

    def test_parse_clear_signal(self):
        """Parse a clear trade signal."""
        text = "AAPL long entry 150 target 160 stop 145"
        signal = DiscordParser.parse(text)

        assert signal.ticker == "AAPL"
        assert signal.direction == "LONG"
        assert signal.entry == 150.0
        assert signal.target == 160.0
        assert signal.stop_loss == 145.0
        assert signal.confidence > 0.5

    def test_parse_short_signal(self):
        """Parse a short signal."""
        text = "TSLA short entry 250 target 230 stop 260"
        signal = DiscordParser.parse(text)

        assert signal.ticker == "TSLA"
        assert signal.direction == "SHORT"
        assert signal.entry == 250.0

    def test_parse_option_signal(self):
        """Parse an options signal."""
        text = "SPY 03/15/2024 C 450 entry 5.50 target 8.00"
        signal = DiscordParser.parse(text)

        assert signal.ticker == "SPY"
        assert signal.expiry == "03/15/2024"
        assert signal.option_type == "C"
        assert signal.strike == 450.0
        assert signal.entry == 5.50
        assert signal.confidence > 0.6

    def test_parse_put_option(self):
        """Parse a put option."""
        text = "QQQ 04/19/24 P 380 buy 4.20"
        signal = DiscordParser.parse(text)

        assert signal.ticker == "QQQ"
        assert signal.option_type == "P"
        assert signal.strike == 380.0
        assert signal.direction == "LONG"

    def test_parse_cashtag_format(self):
        """Parse cashtag format ($TSLA)."""
        text = "$TSLA going to moon 🚀 buy calls"
        signal = DiscordParser.parse(text)

        assert signal.ticker == "TSLA"
        assert signal.direction == "LONG"

    def test_false_positive_filtering(self):
        """Common words should not be detected as tickers."""
        text = "THE market AND you should BUY when price IS high"
        signal = DiscordParser.parse(text)

        # None of the false positives should be the ticker
        false_positives = {"THE", "AND", "BUY", "WHEN", "PRICE", "IS", "HIGH"}
        assert signal.ticker not in false_positives or signal.ticker is None

    def test_confidence_scoring(self):
        """Test confidence scoring."""
        # High confidence signal
        text1 = "AAPL long entry 150 target 160 stop 145 03/15/24 C 150"
        signal1 = DiscordParser.parse(text1)

        # Low confidence (just a ticker mention)
        text2 = "AAPL looking good today"
        signal2 = DiscordParser.parse(text2)

        assert signal1.confidence > signal2.confidence
        assert signal1.confidence > 0.7
        assert signal2.confidence < 0.5

    def test_is_likely_signal(self):
        """Test signal detection threshold."""
        # Should be detected
        assert DiscordParser.is_likely_signal("AAPL long entry 150 target 160") is True
        assert DiscordParser.is_likely_signal("SPY 03/15/24 C 450") is True
        assert DiscordParser.is_likely_signal("$TSLA calls") is True

        # Should not be detected
        assert DiscordParser.is_likely_signal("Hey everyone") is False
        assert DiscordParser.is_likely_signal("What do you think about the market?") is False
        assert DiscordParser.is_likely_signal("") is False

    def test_multiple_tickers_picks_first_valid(self):
        """Should pick first valid ticker."""
        text = "AAPL and TSLA both long entry 150"
        signal = DiscordParser.parse(text)

        # AAPL comes first and is valid
        assert signal.ticker == "AAPL"

    def test_price_extraction_order(self):
        """Prices should be extracted in order: entry, target, stop."""
        text = "AAPL entry 150.50 target 160.75 stop 145.25"
        signal = DiscordParser.parse(text)

        assert signal.entry == 150.50
        assert signal.target == 160.75
        assert signal.stop_loss == 145.25

    def test_emoji_direction_detection(self):
        """Should detect direction from emojis."""
        text1 = "AAPL 🚀 entry 150"
        signal1 = DiscordParser.parse(text1)
        assert signal1.direction == "LONG"

        text2 = "TSLA 📉 entry 250"
        signal2 = DiscordParser.parse(text2)
        assert signal2.direction == "SHORT"

    def test_option_expiry_formats(self):
        """Should parse various expiry formats."""
        formats = [
            "03/15/2024",
            "03/15/24",
            "3/15/2024",
            "3/15/24",
        ]

        for fmt in formats:
            text = f"SPY {fmt} C 450"
            signal = DiscordParser.parse(text)
            assert signal.expiry == fmt, f"Failed for format: {fmt}"
            assert signal.option_type == "C"
            assert signal.strike == 450.0