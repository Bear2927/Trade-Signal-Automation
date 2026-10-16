"""Formatter for social media posts with Discord timestamp and CTA."""

from datetime import datetime
from zoneinfo import ZoneInfo
from src.common.formatter import TradeSignal


# Enforced by the posting API regardless of the limit the web app advertises.
STOCKTWITS_POST_LIMIT = 140

# Posts are labelled "ET", so they must actually be rendered in Eastern time.
# This host runs in Central, so formatting local time and calling it ET was
# putting every alert an hour early.
EASTERN = ZoneInfo("America/New_York")


def _as_eastern(dt):
    if dt is None:
        return datetime.now(EASTERN)
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.astimezone(EASTERN)

# The footer is reserved rather than appended: the body is trimmed to whatever
# space is left over, so a long alert can never push the CTA or tags off the
# end the way the original full-length format did.
STOCKTWITS_CTA = "🔗 Alerts first - Discord in bio"
STOCKTWITS_TAGS = "#options #trading #stocks"
STOCKTWITS_FOOTER = f"{STOCKTWITS_CTA}\n{STOCKTWITS_TAGS}"


def _cashtag(ticker):
    """$-prefix a ticker so Stocktwits and X link it to the symbol page."""
    return f"${ticker}" if ticker else "Trade"


class SocialMediaFormatter:
    """Format trades for social media with Discord timestamps and CTAs."""

    @staticmethod
    def format_with_discord_timestamp(
        trade_text: str,
        discord_post_time: datetime = None,
        platform: str = "stocktwits"
    ) -> str:
        """
        Format a trade with Discord posting time and call-to-action.

        Args:
            trade_text: The original trade message
            discord_post_time: When it was posted to Discord (defaults to now)
            platform: 'stocktwits', 'twitter', or 'threads'

        Returns:
            Formatted message for the platform
        """
        if discord_post_time is None:
            discord_post_time = datetime.now()

        # Format the timestamp
        time_str = _as_eastern(discord_post_time).strftime("%I:%M %p ET")
        date_str = _as_eastern(discord_post_time).strftime("%b %d, %Y")

        # Build the post
        if platform.lower() == "stocktwits":
            return SocialMediaFormatter._format_stocktwits(
                trade_text, time_str, date_str
            )
        elif platform.lower() == "twitter":
            return SocialMediaFormatter._format_twitter(
                trade_text, time_str, date_str
            )
        elif platform.lower() == "threads":
            return SocialMediaFormatter._format_threads(
                trade_text, time_str, date_str
            )
        else:
            return trade_text

    @staticmethod
    def _format_stocktwits(trade_text: str, time_str: str, date_str: str) -> str:
        """Format for Stocktwits with full details."""
        post = (
            f"📊 TRADE ALERT\n\n"
            f"{trade_text}\n\n"
            f"⏰ Posted to Discord: {time_str}\n"
            f"📅 {date_str}\n\n"
            f"🔥 Join our Discord community for REAL-TIME trade alerts!\n"
            f"👉 Link in BIO\n\n"
            f"#trading #stocks #options #daytrading"
        )
        return post

    @staticmethod
    def _format_twitter(trade_text: str, time_str: str, date_str: str) -> str:
        """Format for Twitter/X (concise, 280 char limit)."""
        # Extract just the trade line for Twitter (more concise)
        trade_line = trade_text.split('\n')[0]

        post = (
            f"📊 {trade_line}\n"
            f"⏰ Discord: {time_str}\n"
            f"🔥 Join us! Link in BIO 🔗\n"
            f"#trading #stocks"
        )

        # Ensure under 280 chars
        if len(post) > 280:
            # Truncate and add ellipsis
            post = post[:277] + "..."

        return post

    @staticmethod
    def _format_threads(trade_text: str, time_str: str, date_str: str) -> str:
        """Format for Threads with details and hashtags."""
        post = (
            f"📊 Trade Alert\n\n"
            f"{trade_text}\n\n"
            f"⏰ Posted to our Discord at {time_str}\n"
            f"📅 {date_str}\n\n"
            f"🔥 Want real-time trade alerts like this?\n"
            f"👉 Join our Discord community\n"
            f"Link in BIO\n\n"
            f"#trading #stocks #options #daytrader #stockmarket"
        )
        return post

    @staticmethod
    def format_messenger_trade_for_social(
        trade_text: str,
        discord_timestamp: datetime = None,
        platform: str = "stocktwits"
    ) -> str:
        """
        Format a Messenger trade for social media with Discord timestamp.

        Includes the full trade details + timestamp + CTA.
        """
        if discord_timestamp is None:
            discord_timestamp = datetime.now()

        # Parse the trade details if it's Messenger format
        from src.social.messenger_trade_parser import MessengerTradeParser

        parsed = MessengerTradeParser.parse_message(trade_text)

        from src.common.webhook import extract_ticker
        fallback_ticker = extract_ticker(trade_text)

        if parsed and parsed.is_valid:
            # Build detailed trade info
            trade_info = (
                f"📊 ${parsed.ticker} {parsed.expiration} {parsed.strike}{parsed.option_type}\n"
                f"Entry: ${parsed.entry_price} | Stop: ${parsed.stop_loss} | Target: ${parsed.profit_target}"
            )
            if parsed.notes:
                trade_info += f"\nNotes: {parsed.notes}"
        else:
            trade_info = trade_text

        # Add timestamp and CTA
        time_str = _as_eastern(discord_timestamp).strftime("%I:%M %p ET")
        date_str = _as_eastern(discord_timestamp).strftime("%b %d, %Y")

        if platform.lower() == "stocktwits":
            # Observed behaviour: the API posting path silently drops anything
            # past ~140 chars, even though the web app documents a 1,000-char
            # limit. Everything here is built to fit inside that budget, most
            # important first, so nothing valuable is the thing that gets cut.
            lines = []
            if parsed and parsed.is_valid:
                lines.append(
                    f"⚡ ${parsed.ticker} {parsed.expiration} "
                    f"{parsed.strike}{parsed.option_type}"
                )
                nums = f"Entry {parsed.entry_price} | SL {parsed.stop_loss}"
                if parsed.profit_target:
                    nums += f" | PT {parsed.profit_target}"
                    try:
                        pct = ((float(parsed.profit_target) - float(parsed.entry_price))
                               / float(parsed.entry_price) * 100)
                        nums += f" (+{pct:.0f}%)"
                    except (TypeError, ValueError, ZeroDivisionError):
                        pass
                lines.append(nums)
            else:
                # No structured parse: at least cashtag the leading ticker so
                # the post still lands on the symbol page.
                text = trade_info
                if fallback_ticker and text.upper().startswith(fallback_ticker):
                    text = "$" + text
                lines.append(text)
            lines.append(f"🕐 {time_str}")

            budget = STOCKTWITS_POST_LIMIT - len(STOCKTWITS_FOOTER) - 1
            body = "\n".join(lines)[:budget].rstrip()
            return f"{body}\n{STOCKTWITS_FOOTER}"
        elif platform.lower() == "twitter":
            return (
                f"⚡ {_cashtag(parsed.ticker if parsed and parsed.is_valid else fallback_ticker)} Alert!\n"
                f"{trade_info if len(trade_info) <= 100 else trade_info[:97] + chr(46)*3}\n"
                f"🕐 {time_str}\n"
                f"🔗 Discord link in BIO"
            )
        elif platform.lower() == "threads":
            return (
                f"⚡ LIVE TRADE ALERT ⚡\n\n"
                f"{trade_info}\n\n"
                f"This was called in our Discord at {time_str}\n"
                f"📅 {date_str}\n\n"
                f"Want REAL-TIME alerts before they hit social?\n"
                f"Join our Discord community 🔗\n"
                f"Link in BIO\n\n"
                f"#trading #stocks #options #daytrader"
            )
        else:
            return trade_info


# Example usage
if __name__ == "__main__":
    from datetime import datetime, timedelta

    # Sample trade
    trade = """MDB OCT16 425C 1.25 s/l 0.70 pt 2.10
rotation to software"""

    # Use a past time to show it works
    post_time = datetime.now() - timedelta(hours=2)

    print("="*70)
    print("SOCIAL MEDIA FORMATTING WITH DISCORD TIMESTAMP")
    print("="*70)
    print("")

    for platform in ["stocktwits", "twitter", "threads"]:
        print(f"\n{platform.upper()}:")
        print("-" * 70)
        formatted = SocialMediaFormatter.format_messenger_trade_for_social(
            trade, post_time, platform
        )
        print(formatted)
        print("")
