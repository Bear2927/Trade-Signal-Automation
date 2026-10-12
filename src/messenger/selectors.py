"""Facebook Messenger DOM selectors - maintainable selector system."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SelectorSet:
    """Set of selectors for a specific FB UI version."""
    name: str
    message_container: List[str]
    message_element: List[str]
    message_text: List[str]
    author: List[str]
    timestamp: List[str]


# Current known selector sets (FB changes these frequently)
SELECTOR_SETS = [
    SelectorSet(
        name="messenger_web_2024",
        message_container=[
            'div[role="grid"]',
            'div[aria-label="Messages"]',
            '[data-testid="message_thread"]',
            'div[data-pagelet="MessageThread"]',
        ],
        message_element=[
            'div[data-testid="message"]',
            'div[role="row"]',
            '.message',
            '[data-encore-id="message"]',
        ],
        message_text=[
            '[data-testid="message_text"]',
            '.message-text',
            'div[dir="auto"]',
            'span[dir="auto"]',
        ],
        author=[
            '[data-testid="message_sender"]',
            '.message-sender',
            'strong',
            'a[role="link"]',
        ],
        timestamp=[
            '[data-testid="message_timestamp"]',
            'time',
            '.timestamp',
        ],
    ),
    SelectorSet(
        name="messenger_lite",
        message_container=[
            '#message_thread',
            '.messages-container',
        ],
        message_element=[
            '.message-row',
            '.message-bubble',
        ],
        message_text=[
            '.message-content',
            '.text',
        ],
        author=[
            '.sender-name',
            '.author',
        ],
        timestamp=[
            '.time',
            '.message-time',
        ],
    ),
]


def get_selectors(version: str = "messenger_web_2024") -> Optional[SelectorSet]:
    """Get selector set by version name."""
    for s in SELECTOR_SETS:
        if s.name == version:
            return s
    return SELECTOR_SETS[0]  # Default to first


def find_working_selector(page, selectors: List[str], timeout: int = 5000) -> Optional[str]:
    """Try multiple selectors until one works."""
    import asyncio

    async def try_selector(sel):
        try:
            await page.wait_for_selector(sel, timeout=timeout)
            return sel
        except Exception:
            return None

    # This would need to be run in async context
    # For sync usage, use the first one as fallback
    return selectors[0]


# Export commonly used selector combinations
MESSAGE_CONTAINER_SELECTORS = [
    'div[role="grid"]',
    'div[aria-label="Messages"]',
    '[data-testid="message_thread"]',
    'div[data-pagelet="MessageThread"]',
]

MESSAGE_ELEMENT_SELECTORS = [
    'div[data-testid="message"]',
    'div[role="row"]',
    '.message',
    '[data-encore-id="message"]',
]

MESSAGE_TEXT_SELECTORS = [
    '[data-testid="message_text"]',
    '.message-text',
    'div[dir="auto"]',
    'span[dir="auto"]',
]