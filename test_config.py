#!/usr/bin/env python3
"""Test config loading."""

import sys
sys.path.insert(0, "/home/bear2927/StockTradingSignals/src")

from src.common.config import load_config_from_yaml, get_settings

# Load config from YAML
settings = load_config_from_yaml("config/config.yaml")

print("=== Settings from load_config_from_yaml ===")
print(f"discord.user_token: {settings.discord.user_token[:20]}..." if settings.discord.user_token else "EMPTY")
print(f"discord.target_channel_ids: {settings.discord.target_channel_ids}")
print(f"discord.premium_webhook_url: {settings.discord.premium_webhook_url[:50]}..." if settings.discord.premium_webhook_url else "EMPTY")

print("\n=== Settings from get_settings() (cached) ===")
cached = get_settings()
print(f"discord.user_token: {cached.discord.user_token[:20]}..." if cached.discord.user_token else "EMPTY")
print(f"discord.target_channel_ids: {cached.discord.target_channel_ids}")
print(f"discord.premium_webhook_url: {cached.discord.premium_webhook_url[:50]}..." if cached.discord.premium_webhook_url else "EMPTY")

print("\n=== Same object? ===")
print(f"settings is cached: {settings is cached}")