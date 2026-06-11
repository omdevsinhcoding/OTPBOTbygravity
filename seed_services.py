import asyncio
from bot.db import engine, async_session
from bot.db.models import Service
from sqlalchemy import select

async def seed():
    print("Seeding default services...")
    services_to_add = [
        {"name": "whatsapp", "display_name": "WhatsApp", "emoji": "📱", "keywords": ["whatsapp", "wa"]},
        {"name": "instagram", "display_name": "Instagram", "emoji": "📸", "keywords": ["instagram", "ig"]},
        {"name": "telegram", "display_name": "Telegram", "emoji": "✈️", "keywords": ["telegram", "tg"]},
        {"name": "google", "display_name": "Google", "emoji": "🌐", "keywords": ["google", "gmail"]},
        {"name": "facebook", "display_name": "Facebook", "emoji": "📘", "keywords": ["facebook", "fb"]},
    ]
    
    async with async_session() as session:
        for svc_data in services_to_add:
            stmt = select(Service).where(Service.name == svc_data["name"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if not existing:
                new_svc = Service(**svc_data)
                session.add(new_svc)
                print(f"Added: {svc_data['display_name']}")
            else:
                print(f"Already exists: {svc_data['display_name']}")
        
        await session.commit()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(seed())
