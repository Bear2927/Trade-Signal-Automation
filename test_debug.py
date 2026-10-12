#!/usr/bin/env python3
"""Quick debug of config loading."""

import sys
sys.path.insert(0, "/home/bear2927/StockTradingSignals/src")

# First, test loading from YAML
from src.common.config import load_config_from_yaml, get_settings, _cached_settings

print(f"Before load_config_from_yaml: _cached_settings = {_cached_settings}")

settings = load_config_from_yaml("config/config.yaml")

print(f"After load_config_from_yaml:")
print(f"  settings.discord.user_token = {settings.discord.user_token[:20] if settings.discord.user_token else 'EMPTY'}")
print(f"  _cached_settings = {_cached_settings}")

# Now test get_settings
cached = get_settings()
print(f"get_settings() returns:")
print(f"  cached.discord.user_token = {cached.discord.user_token[:20] if cached.discord.user_token else 'EMPTY'}")
print(f"  settings is cached: {settings is cached}")