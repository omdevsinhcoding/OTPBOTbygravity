"""
Simple launcher for the bot.
Usage: python run.py
"""

import asyncio
import logging
from alembic.config import Config
from alembic import command
from bot.__main__ import main

def run_migrations():
    """Run Alembic database migrations automatically."""
    logging.info("Running database migrations...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    logging.info("Database migrations applied successfully!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        run_migrations()
    except Exception as e:
        logging.error(f"Failed to run migrations: {e}")
        
    asyncio.run(main())
