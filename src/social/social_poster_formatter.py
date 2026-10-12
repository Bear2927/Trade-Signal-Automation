"""Formatter for social media posts with Discord timestamp and CTA."""

from datetime import datetime
from src.common.formatter import TradeSignal


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
        time_str = discord_post_time.strftime("%I:%M %p ET")  # 02:30 PM ET
        date_str = discord_post_time.strftime("%b %d, %Y")     # Oct 12, 2026

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
            f"⏰ Posted to Discord: {time_str} ET\n"
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
            f"⏰ Discord: {time_str} ET\n"
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
            f"⏰ Posted to our Discord at {time_str} ET\n"
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

        if parsed and parsed.is_valid:
            # Build detailed trade info
            trade_info = (
                f"📊 {parsed.ticker} {parsed.expiration} {parsed.strike}{parsed.option_type}\n"
                f"Entry: ${parsed.entry_price} | Stop: ${parsed.stop_loss} | Target: ${parsed.profit_target}"
            )
            if parsed.notes:
                trade_info += f"\nNotes: {parsed.notes}"
        else:
            trade_info = trade_text

        # Add timestamp and CTA
        time_str = discord_timestamp.strftime("%I:%M %p ET")
        date_str = discord_timestamp.strftime("%b %d, %Y")

        if platform.lower() == "stocktwits":
            return (
                f"⚡ LIVE TRADE ALERT ⚡\n\n"
                f"{trade_info}\n\n"
                f"🕐 Called in Discord at {time_str} ET\n"
                f"📅 {date_str}\n\n"
                f"Get alerts BEFORE they hit social media!\n"
                f"🔗 Join our Discord - Link in BIO\n\n"
                f"#trading #stocks #options #alerts"
            )
        elif platform.lower() == "twitter":
            return (
                f"⚡ {parsed.ticker if parsed else 'Trade'} Alert!\n"
                f"{trade_info[:100]}...\n"
                f"🕐 {time_str} ET\n"
                f"🔗 Discord link in BIO"
            )
        elif platform.lower() == "threads":
            return (
                f"⚡ LIVE TRADE ALERT ⚡\n\n"
                f"{trade_info}\n\n"
                f"This was called in our Discord at {time_str} ET\n"
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
