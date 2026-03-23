"""
Example: Basic bot with QR login and message echo
"""

import asyncio
import logging

from app.bot import WeixinBot

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main():
    bot = WeixinBot()

    # Status updates
    @bot.on_status
    async def on_status(message: str):
        print(f"[Status] {message}")

    # Error handling
    @bot.on_error
    async def on_error(error: Exception):
        print(f"[Error] {error}")

    # Message handler
    @bot.on_message
    async def on_message(message):
        print(f"\n{'='*50}")
        print(f"New message from: {message.from_user_id}")
        print(f"Session: {message.session_id}")
        print(f"Context Token: {message.context_token}")

        # Process items
        for item in message.item_list:
            if item.type == 1:  # TEXT
                text = item.text_item.text if item.text_item else ""
                print(f"Text: {text}")

                # Echo back
                if message.from_user_id and message.context_token:
                    await bot.send_text(
                        to=message.from_user_id,
                        text=f"Echo: {text}",
                        context_token=message.context_token
                    )

            elif item.type == 2:  # IMAGE
                print("[Image received]")

            elif item.type == 3:  # VOICE
                print("[Voice received]")

            elif item.type == 4:  # FILE
                file_name = item.file_item.file_name if item.file_item else "unknown"
                print(f"[File received: {file_name}]")

            elif item.type == 5:  # VIDEO
                print("[Video received]")

        print(f"{'='*50}\n")

    # Try to load saved account first
    if await bot.load_saved_account():
        print("Loaded saved account")
    else:
        # Do QR login
        print("Starting QR login...")
        success = await bot.login(verbose=True)
        if not success:
            print("Login failed")
            return

    print("\nBot is running. Press Ctrl+C to stop.\n")

    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\nStopping...")
        await bot.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExited")
