"""
Core Bot implementation
"""

import asyncio
import logging
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from .auth import WeixinAuth
from .api import WeixinAPI
from .monitor import MessageMonitor
from .types import WeixinMessage, GetUpdatesResp
from .exceptions import WeixinBotError, LoginError
from .storage import AccountStorage

logger = logging.getLogger(__name__)


@dataclass
class BotConfig:
    """Bot configuration"""
    base_url: str = "https://ilinkai.weixin.qq.com"
    cdn_base_url: str = "https://novac2c.cdn.weixin.qq.com/c2c"
    bot_type: str = "3"
    long_poll_timeout_ms: int = 35000
    max_consecutive_failures: int = 3
    backoff_delay_ms: int = 30000
    retry_delay_ms: int = 2000
    session_pause_duration_ms: int = 60 * 60 * 1000  # 1 hour


class WeixinBot:
    """
    Weixin Bot main class

    Example:
        bot = WeixinBot()

        # Set up message callback
        @bot.on_message
        async def handle_message(message: WeixinMessage):
            print(f"Received: {message}")

        # Login with QR code
        await bot.login()

        # Start monitoring (blocking)
        await bot.start()
    """

    def __init__(
        self,
        config: Optional[BotConfig] = None,
        storage_path: Optional[str] = None,
    ):
        self.config = config or BotConfig()
        self.storage = AccountStorage(storage_path)

        # Components
        self.auth = WeixinAuth(self.config)
        self.api: Optional[WeixinAPI] = None
        self.monitor: Optional[MessageMonitor] = None

        # State
        self._account_id: Optional[str] = None
        self._token: Optional[str] = None
        self._is_logged_in = False
        self._is_running = False
        self._stop_event = asyncio.Event()

        # Callbacks
        self._message_callback: Optional[Callable[[WeixinMessage], Any]] = None
        self._error_callback: Optional[Callable[[Exception], Any]] = None
        self._status_callback: Optional[Callable[[str], Any]] = None

    @property
    def is_logged_in(self) -> bool:
        """Check if bot is logged in"""
        return self._is_logged_in and self._token is not None

    @property
    def account_id(self) -> Optional[str]:
        """Get current account ID"""
        return self._account_id

    def on_message(self, callback: Callable[[WeixinMessage], Any]) -> Callable:
        """
        Set message received callback

        Args:
            callback: Async or sync function that receives WeixinMessage

        Returns:
            The callback function (for use as decorator)
        """
        self._message_callback = callback
        return callback

    def on_error(self, callback: Callable[[Exception], Any]) -> Callable:
        """
        Set error callback

        Args:
            callback: Async or sync function that receives Exception
        """
        self._error_callback = callback
        return callback

    def on_status(self, callback: Callable[[str], Any]) -> Callable:
        """
        Set status update callback

        Args:
            callback: Async or sync function that receives status string
        """
        self._status_callback = callback
        return callback

    async def _notify_status(self, message: str):
        """Notify status update"""
        logger.info(message)
        if self._status_callback:
            try:
                if asyncio.iscoroutinefunction(self._status_callback):
                    await self._status_callback(message)
                else:
                    self._status_callback(message)
            except Exception as e:
                logger.error(f"Status callback error: {e}")

    async def _notify_message(self, message: WeixinMessage):
        """Notify message received"""
        if self._message_callback:
            try:
                if asyncio.iscoroutinefunction(self._message_callback):
                    await self._message_callback(message)
                else:
                    self._message_callback(message)
            except Exception as e:
                logger.error(f"Message callback error: {e}")
                if self._error_callback:
                    try:
                        if asyncio.iscoroutinefunction(self._error_callback):
                            await self._error_callback(e)
                        else:
                            self._error_callback(e)
                    except:
                        pass

    async def login(
        self,
        timeout_ms: int = 480000,
        verbose: bool = False,
    ) -> bool:
        """
        Login with QR code

        Args:
            timeout_ms: Login timeout in milliseconds (default: 8 minutes)
            verbose: Print verbose output

        Returns:
            True if login successful

        Raises:
            LoginError: If login fails
        """
        await self._notify_status("Starting Weixin login with QR code...")

        try:
            # Step 1: Start login and get QR code
            start_result = await self.auth.start_login(
                base_url=self.config.base_url,
                bot_type=self.config.bot_type,
            )

            if not start_result.qrcode_url:
                raise LoginError(f"Failed to get QR code: {start_result.message}")

            await self._notify_status(f"QR Code URL: {start_result.qrcode_url}")

            # Print QR code to console if qrcode-terminal is available
            try:
                import qrcode
                print("\n" + "="*50)
                print("Scan this QR code with Weixin:")
                print("="*50)
                qr = qrcode.QRCode(version=1, box_size=2, border=1)
                qr.add_data(start_result.qrcode_url)
                qr.make(fit=True)
                qr.print_ascii(invert=True)
                print("="*50 + "\n")
            except ImportError:
                print(f"\nPlease scan this QR code URL: {start_result.qrcode_url}\n")

            # Step 2: Wait for scan and confirmation
            await self._notify_status("Waiting for QR code scan...")

            wait_result = await self.auth.wait_for_login(
                session_key=start_result.session_key,
                base_url=self.config.base_url,
                bot_type=self.config.bot_type,
                timeout_ms=timeout_ms,
                verbose=verbose,
                status_callback=self._notify_status,
            )

            if not wait_result.connected:
                raise LoginError(f"Login failed: {wait_result.message}")

            # Step 3: Save credentials
            self._token = wait_result.bot_token
            self._account_id = wait_result.account_id

            # Save to storage
            self.storage.save_account(
                account_id=self._account_id,
                token=self._token,
                base_url=wait_result.base_url or self.config.base_url,
                user_id=wait_result.user_id,
            )

            # Initialize API client
            self.api = WeixinAPI(
                base_url=self.config.base_url,
                token=self._token,
                config=self.config,
            )

            self._is_logged_in = True
            await self._notify_status(f"Login successful! Account: {self._account_id}")

            return True

        except Exception as e:
            await self._notify_status(f"Login failed: {e}")
            raise LoginError(f"Login failed: {e}")

    async def login_with_token(
        self,
        account_id: str,
        token: str,
        base_url: Optional[str] = None,
    ) -> bool:
        """
        Login with existing token

        Args:
            account_id: Account ID
            token: Bot token
            base_url: Optional base URL (uses config default if not provided)

        Returns:
            True if login successful
        """
        self._account_id = account_id
        self._token = token
        self.api = WeixinAPI(
            base_url=base_url or self.config.base_url,
            token=token,
            config=self.config,
        )
        self._is_logged_in = True
        await self._notify_status(f"Logged in with token. Account: {account_id}")
        return True

    async def load_saved_account(self, account_id: Optional[str] = None) -> bool:
        """
        Load saved account from storage

        Args:
            account_id: Optional account ID (loads first available if not specified)

        Returns:
            True if account loaded successfully
        """
        accounts = self.storage.list_accounts()
        if not accounts:
            return False

        target_account = account_id or accounts[0]
        account_data = self.storage.load_account(target_account)

        if not account_data or not account_data.get("token"):
            return False

        return await self.login_with_token(
            account_id=target_account,
            token=account_data["token"],
            base_url=account_data.get("base_url"),
        )

    async def send_text(
        self,
        to: str,
        text: str,
        context_token: Optional[str] = None,
    ) -> str:
        """
        Send text message

        Args:
            to: Recipient user ID
            text: Message text
            context_token: Optional conversation context token

        Returns:
            Message ID

        Raises:
            WeixinBotError: If not logged in or send fails
        """
        if not self.api:
            raise WeixinBotError("Not logged in")

        return await self.api.send_text(to, text, context_token)

    async def send_image(
        self,
        to: str,
        file_path: str,
        text: str = "",
        context_token: Optional[str] = None,
    ) -> str:
        """
        Send image message

        Args:
            to: Recipient user ID
            file_path: Path to image file
            text: Optional caption text
            context_token: Optional conversation context token

        Returns:
            Message ID
        """
        if not self.api:
            raise WeixinBotError("Not logged in")

        return await self.api.send_image(to, file_path, text, context_token)

    async def send_file(
        self,
        to: str,
        file_path: str,
        text: str = "",
        context_token: Optional[str] = None,
    ) -> str:
        """
        Send file attachment

        Args:
            to: Recipient user ID
            file_path: Path to file
            text: Optional caption text
            context_token: Optional conversation context token

        Returns:
            Message ID
        """
        if not self.api:
            raise WeixinBotError("Not logged in")

        return await self.api.send_file(to, file_path, text, context_token)

    async def start(self):
        """
        Start message monitoring (blocking)

        This method starts the long-poll loop and blocks until stop() is called.
        """
        if not self.is_logged_in:
            raise WeixinBotError("Not logged in. Call login() first.")

        if self._is_running:
            raise WeixinBotError("Already running")

        self._is_running = True
        self._stop_event.clear()

        await self._notify_status("Starting message monitor...")

        # Initialize monitor
        self.monitor = MessageMonitor(
            api=self.api,
            config=self.config,
            storage=self.storage,
            account_id=self._account_id,
        )

        # Load sync buffer if exists
        sync_buf = self.storage.load_sync_buf(self._account_id)

        try:
            await self.monitor.run(
                message_callback=self._notify_message,
                error_callback=self._error_callback,
                status_callback=self._notify_status,
                stop_event=self._stop_event,
                initial_sync_buf=sync_buf,
            )
        finally:
            self._is_running = False
            await self._notify_status("Monitor stopped")

    async def stop(self):
        """Stop message monitoring"""
        await self._notify_status("Stopping...")
        self._stop_event.set()

    def run(self):
        """
        Run bot (blocking, sync interface)

        Example:
            bot = WeixinBot()
            # ... setup callbacks and login ...
            bot.run()
        """
        asyncio.run(self.start())
