# WeiXin ClawBot Python

Python reimplementation of the openclaw-weixin, implementing QR code login and long-poll message monitoring.

[![GitHub](https://img.shields.io/badge/GitHub-er1cw00/weixin--clawbot--python-blue)](https://github.com/er1cw00/weixin-clawbot-python)

## Features

- QR Code login with automatic refresh
- Long-poll message monitoring
- Send text, image, and file messages
- Session management with auto-recovery
- Async/await support

## Installation

```bash
pip install git+https://github.com/er1cw00/weixin-clawbot-python.git
```

Or clone and install locally:

```bash
git clone https://github.com/er1cw00/weixin-clawbot-python.git
cd weixin-clawbot-python
pip install -e .
```

## Quick Start

```python
import asyncio
from app.bot import WeixinBot

async def main():
    bot = WeixinBot()

    # Set up message handler
    @bot.on_message
    async def handle_message(message):
        print(f"From: {message.from_user_id}")
        print(f"Content: {message.item_list}")

        # Reply
        await bot.send_text(
            to=message.from_user_id,
            text="Hello! Received your message.",
            context_token=message.context_token
        )

    # Login with QR code
    await bot.login()

    # Start monitoring (blocking)
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

See [doc/USAGE.md](doc/USAGE.md) for detailed API documentation.

## License

MIT
