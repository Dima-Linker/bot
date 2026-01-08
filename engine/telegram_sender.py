#!/usr/bin/env python3
"""
Clean Async Telegram Sender
Single writer pattern with proper thread-safe handling
"""

import os
import asyncio
import threading
from typing import Optional
from telegram import Bot
from engine.topic_router import route_message, TopicType

class TelegramSender:
    """Singleton Telegram sender with thread-safe locking"""
    
    _instance = None
    _lock = threading.Lock()  # Changed from asyncio.Lock to threading.Lock for cross-thread safety
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self.bot_token = os.getenv("BOT_TOKEN")
        self.chat_id = os.getenv("CHAT_ID")
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("Missing BOT_TOKEN or CHAT_ID in environment")
        
        # Ensure chat_id is not None for type safety
        if self.chat_id is None:
            raise ValueError("CHAT_ID cannot be None")
            
        self.bot = Bot(token=self.bot_token)
        self._initialized = True
    
    async def send_message(self, text: str, signal_data: dict, chart_path: Optional[str] = None):
        """
        Send message with hard topic routing enforcement
        Thread-safe single writer pattern - prevents race conditions
        """
        # Use threading.Lock for cross-thread safety
        with self._lock:
            try:
                # Route to correct topic
                topic_type, thread_id = route_message(text, signal_data)
                
                print(f"📤 Routing signal to {topic_type.value} topic (Thread {thread_id})")
                
                # Type assertion - we checked this in __init__
                assert self.chat_id is not None, "CHAT_ID should not be None here"
                
                if chart_path and os.path.exists(chart_path):
                    # Send chart with caption to specific topic
                    with open(chart_path, 'rb') as chart_file:
                        await self.bot.send_photo(
                            chat_id=self.chat_id,
                            photo=chart_file,
                            caption=text,
                            message_thread_id=thread_id
                        )
                else:
                    # Send text message to specific topic
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=text,
                        message_thread_id=thread_id
                    )
                
                print(f"✅ Message sent successfully to {topic_type.value} topic")
                return True
                
            except Exception as e:
                print(f"❌ Failed to send message: {e}")
                return False

# Global singleton instance
_sender_instance = None

def get_telegram_sender() -> TelegramSender:
    """Get singleton Telegram sender instance"""
    global _sender_instance
    if _sender_instance is None:
        _sender_instance = TelegramSender()
    return _sender_instance

async def send_telegram_message(text: str, signal_data: dict, chart_path: Optional[str] = None):
    """Convenience function for sending messages"""
    sender = get_telegram_sender()
    return await sender.send_message(text, signal_data, chart_path)

# Backward compatibility function
def create_async_telegram_send_fn():
    """Create async send function for backward compatibility"""
    async def telegram_send_fn(chat_id: str, text: str, **kwargs):
        chart_path = kwargs.get('chart_path')
        signal_data = kwargs.get('signal_data', {})
        await send_telegram_message(text, signal_data, chart_path)
    return telegram_send_fn

__all__ = ['TelegramSender', 'get_telegram_sender', 'send_telegram_message', 'create_async_telegram_send_fn']