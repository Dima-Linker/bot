#!/usr/bin/env python3
"""
Test the new hard topic routing system
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.topic_router import classify_signal, get_thread_id, TopicType
from engine.telegram_sender import send_telegram_message

async def test_hard_routing():
    """Test the hard topic routing system"""
    
    print("🧪 TESTING HARD TOPIC ROUTING SYSTEM")
    print("=" * 50)
    
    # Test cases for each topic type
    test_signals = [
        {
            'name': 'FIBONACCI ALERT',
            'text': '📐 FIB ALERT\nBTCUSDT | TF: 1h\nGolden Ratio retracement at 0.618 level hit',
            'data': {'module': 'fibonacci', 'score': 85},
            'expected': TopicType.FIBONACCI
        },
        {
            'name': 'LIQUIDITY ALERT', 
            'text': '💧 LIQUIDITY SWEEP\nETHUSDT | TF: 15m\nStop hunt detected at equal high level',
            'data': {'module': 'smc', 'score': 75},
            'expected': TopicType.LIQUIDITY
        },
        {
            'name': 'PUMP ALERT',
            'text': '🔥 PUMP DETECTION\nXRPUSDT | TF: 1h\nVolume spike + momentum breakout detected',
            'data': {'module': 'pump', 'score': 90},
            'expected': TopicType.PUMP
        },
        {
            'name': 'COMBO SIGNAL (High Quality)',
            'text': '🧠 COMBO SETUP\nBNBUSDT | TF: 4h\nScore: 350/400\nStructure confirmed with combo and CHoCH breakout',
            'data': {'score': 350},
            'expected': TopicType.COMBO
        },
        {
            'name': 'IDEA SIGNAL (Watchlist)',
            'text': '🟡 WATCHLIST SETUP\nSOLUSDT | TF: 1h\nScore: 250/400\nInteresting setup for monitoring',
            'data': {'score': 250},
            'expected': TopicType.IDEA
        }
    ]
    
    print("📋 CLASSIFICATION TESTS:")
    print("-" * 30)
    
    all_passed = True
    
    for i, test in enumerate(test_signals, 1):
        actual_topic = classify_signal(test['text'], test['data'])
        expected_thread = get_thread_id(test['expected'])
        actual_thread = get_thread_id(actual_topic)
        
        passed = actual_topic == test['expected']
        status = "✅ PASS" if passed else "❌ FAIL"
        
        print(f"{i}. {test['name']}")
        print(f"   Expected: {test['expected'].value} (Thread {expected_thread})")
        print(f"   Actual:   {actual_topic.value} (Thread {actual_thread})")
        print(f"   Status:   {status}")
        print()
        
        if not passed:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 ALL CLASSIFICATION TESTS PASSED!")
        print("✅ Hard topic routing is working correctly")
    else:
        print("⚠️  SOME CLASSIFICATION TESTS FAILED")
        print("🔧 Check routing logic")
    
    # Test actual sending (dry run)
    print("\n📤 TELEGRAM SENDING TEST:")
    print("-" * 30)
    
    try:
        # Test one signal
        test_signal = test_signals[0]  # FIBONACCI
        result = await send_telegram_message(
            test_signal['text'], 
            test_signal['data']
        )
        print(f"✅ Telegram send test: {'SUCCESS' if result else 'FAILED'}")
    except Exception as e:
        print(f"⚠️  Telegram send test failed: {e}")
        print("   (This might be expected if not connected)")

if __name__ == "__main__":
    asyncio.run(test_hard_routing())