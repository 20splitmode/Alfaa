from __future__ import annotations

import asyncio

from app import BusinessStartBot, load_settings


async def main() -> None:
    settings = load_settings()
    bot = BusinessStartBot(settings)
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
