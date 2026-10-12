#!/usr/bin/env python3
"""
Validate configuration file.

Checks that all required fields are present and valid.
"""

import sys
from pathlib import Path

# Fix path - scripts is at project root, src is at project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml
from src.common.config import Settings, load_config_from_yaml


def validate_config(config_path: str = "config/config.yaml") -> bool:
    """Validate configuration file."""
    path = Path(config_path)

    if not path.exists():
        print(f"❌ Config file not found: {config_path}")
        print(f"   Copy config/config.example.yaml to config/config.yaml and fill in your credentials")
        return False

    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        print(f"❌ Invalid YAML: {e}")
        return False

    # Validate using proper loading function
    try:
        settings = load_config_from_yaml(str(path))
        print(f"✅ Configuration is valid")

        # Check critical settings
        warnings = []

        if not settings.discord.user_token:
            warnings.append("Discord user_token not set")
        if not settings.discord.target_channel_ids:
            warnings.append("Discord target_channel_ids not set")
        if not settings.discord.premium_webhook_url:
            warnings.append("Discord premium_webhook_url not set")
        if not settings.messenger.session_path:
            warnings.append("Messenger session_path not set")

        social = settings.social
        enabled_platforms = []
        if social.twitter.enabled: enabled_platforms.append("Twitter")
        if social.stocktwits.enabled: enabled_platforms.append("Stocktwits")
        if social.threads.enabled: enabled_platforms.append("Threads")
        if social.reddit.enabled: enabled_platforms.append("Reddit")
        if social.telegram.enabled: enabled_platforms.append("Telegram")
        if social.linkedin.enabled: enabled_platforms.append("LinkedIn")
        if social.email.enabled: enabled_platforms.append("Email")

        if not enabled_platforms:
            warnings.append("No social media platforms enabled")

        if warnings:
            print("\n⚠️  Warnings:")
            for w in warnings:
                print(f"   - {w}")
        else:
            print("✅ All critical settings configured")

        return True

    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False


def main():
    """Main entry point."""
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/config.yaml"

    print("Validating configuration...")
    print(f"Config file: {config_path}")
    print()

    success = validate_config(config_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()