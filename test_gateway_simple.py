import asyncio
import sys
import os

sys.path.insert(0, '/home/bear2927/StockTradingSignals/src')
os.environ['FAKEREDIS'] = '1'

import fakeredis.aioredis
import src.common.redis_client as redis_client_module

async def fake_initialize(self):
    self._pool = None
    self._client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await self.health_check()
    print('Using fakeredis')

redis_client_module.RedisClient.initialize = fake_initialize

from src.common.config import load_config_from_yaml, get_settings
load_config_from_yaml('config/config.yaml')
s = get_settings()
print('Token:', s.discord.user_token[:20] + '...' if s.discord.user_token else 'EMPTY')
print('Channels:', s.discord.target_channel_ids)
print('Webhook:', s.discord.premium_webhook_url[:50] + '...' if s.discord.premium_webhook_url else 'EMPTY')

from src.discord.gateway import DiscordGateway

gateway = DiscordGateway()
print('Gateway token:', gateway._token[:20] + '...' if gateway._token else 'EMPTY')
print('Gateway channels:', gateway._target_channels)

# Mock webhook
from src.common import webhook
async def mock_send(self, signal_text, source, author, channel, color=0x00FF00):
    print(f'WEBHOOK: {source} - {author} - {channel}')
    print(f'  Text: {signal_text[:200]}...')
    return True
webhook.WebhookSender.send_signal = mock_send

# Mock social queue
from src.social import queue
async def mock_enqueue(self, signal, source, timestamp, platforms=None, priority=0):
    print(f'QUEUED: {signal}')
    return 'fake-id'
queue.SocialQueue.enqueue = mock_enqueue

async def test():
    try:
        print('Connecting to Discord gateway...')
        await asyncio.wait_for(gateway.connect(), timeout=30)
    except asyncio.TimeoutError:
        print('Timeout - connection working!')
    except Exception as e:
        print(f'Error: {type(e).__name__}: {e}')
    finally:
        await gateway.close()

asyncio.run(test())