"""
Simple launcher for the bot.
Usage: python run.py
"""

import asyncio
from bot.__main__ import main

if __name__ == "__main__":
    asyncio.run(main())
