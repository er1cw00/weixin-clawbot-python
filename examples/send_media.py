"""
Example: Send media files
"""

import asyncio

from app.bot import WeixinBot


async def main():
    bot = WeixinBot()

    # Load existing account
    if not await bot.load_saved_account():
        print("No saved account found. Please run echo_bot.py first to login.")
        return

    print("Logged in!")

    # Replace with actual user ID
    user_id = "user@im.wechat"
    context_token = "some_context_token"

    # Send text
    msg_id = await bot.send_text(
        to=user_id,
        text="Hello from WeixinBot! 👋",
        context_token=context_token
    )
    print(f"Text message sent: {msg_id}")

    # Send image
    # msg_id = await bot.send_image(
    #     to=user_id,
    #     file_path="/path/to/image.png",
    #     text="Check out this image!",
    #     context_token=context_token
    # )
    # print(f"Image message sent: {msg_id}")

    # Send file
    # msg_id = await bot.send_file(
    #     to=user_id,
    #     file_path="/path/to/document.pdf",
    #     text="Here is the document",
    #     context_token=context_token
    # )
    # print(f"File message sent: {msg_id}")


if __name__ == "__main__":
    asyncio.run(main())
