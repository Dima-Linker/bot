#!/usr/bin/env python3
"""
Complete Topic Routing Test
Tests all forum topics with confirmed thread IDs
"""
import asyncio
import os
from telegram import Bot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_all_topics():
    """Test sending to all confirmed forum topics"""
    bot_token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    
    if not bot_token or not chat_id:
        print("❌ Missing BOT_TOKEN or CHAT_ID in .env")
        return
    
    bot = Bot(token=bot_token)
    
    # All confirmed thread IDs
    topics = [
        {
            'id': 114,
            'name': 'IDEA',
            'emoji': '🟡',
            'message': '🟡 IDEA ALERT TEST\nThis should appear in the IDEA forum topic.\nRouting verification test.'
        },
        {
            'id': 5,
            'name': 'COMBO',
            'emoji': '🧠',
            'message': '🧠 COMBO ALERT TEST\nThis should appear in the COMBO forum topic.\nRouting verification test.'
        },
        {
            'id': 9,
            'name': 'FIBONACCI',
            'emoji': '📐',
            'message': '📐 FIBONACCI ALERT TEST\nThis should appear in the FIBONACCI forum topic.\nRouting verification test.'
        },
        {
            'id': 11,
            'name': 'LIQUIDITY',
            'emoji': '💧',
            'message': '💧 LIQUIDITY ALERT TEST\nThis should appear in the LIQUIDITY forum topic.\nRouting verification test.'
        },
        {
            'id': 15,
            'name': 'PUMP',
            'emoji': '🔥',
            'message': '🔥 PUMP ALERT TEST\nThis should appear in the PUMP forum topic.\nRouting verification test.'
        },
        {
            'id': 13,
            'name': 'TEST',
            'emoji': '🧪',
            'message': '🧪 DEBUG TEST\nThis should appear in the TEST forum topic.\nRouting verification test.'
        }
    ]
    
    print(f"🚀 Testing complete topic routing for chat: {chat_id}")
    print("=" * 60)
    
    success_count = 0
    total_tests = len(topics)
    
    for i, topic in enumerate(topics, 1):
        try:
            print(f"\n[{i}/{total_tests}] {topic['emoji']} {topic['name']} (Thread {topic['id']})")
            
            await bot.send_message(
                chat_id=chat_id,
                text=topic['message'],
                message_thread_id=topic['id']
            )
            
            print(f"✅ SUCCESS: Message sent to {topic['name']} topic")
            success_count += 1
            
        except Exception as e:
            print(f"❌ FAILED: {topic['name']} - Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"📊 COMPLETE ROUTING TEST RESULTS: {success_count}/{total_tests} topics working")
    
    if success_count == total_tests:
        print("🎉 ALL TOPIC ROUTING IS WORKING PERFECTLY!")
        print("✅ Automatic routing can now be implemented")
    else:
        print("⚠️  Some topic routing failed")
        print("🔧 Check thread IDs and forum configuration")

if __name__ == "__main__":
    print("🧪 Complete Topic Routing Test")
    print("Testing all forum topics with confirmed thread IDs")
    
    try:
        asyncio.run(test_all_topics())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")