"""
Test script for notification system functionality
Run this after starting the bot to test notifications
"""

import asyncio
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)

async def test_notifications():
    """Test notification functionality"""
    print("🧪 Testing Notification System")
    print("=" * 50)
    
    # Import after setting up logging
    try:
        from app.config import settings
        from app.services.notifications import NotificationService
        from aiogram import Bot
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure to install dependencies and set up environment")
        return False
    
    # Check configuration
    print(f"📋 Configuration Check:")
    print(f"   Bot Token: {'✅ Set' if settings.bot_token else '❌ Missing'}")
    print(f"   Admin IDs: {settings.admin_ids if settings.admin_ids else '❌ Not configured'}")
    print()
    
    if not settings.bot_token:
        print("❌ BOT_TOKEN not configured in .env")
        return False
        
    if not settings.admin_ids:
        print("❌ ADMIN_IDS not configured in .env")
        return False
    
    # Initialize bot
    bot = Bot(token=settings.bot_token)
    
    # Test basic admin notification
    print("📨 Testing admin notification...")
    test_message = f"""
🧪 **Notification System Test**

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Status: System operational
Type: Test notification

This is an automated test of the notification system.
If you receive this message, notifications are working correctly! ✅
    """
    
    try:
        result = await NotificationService.notify_admins(
            bot, test_message, parse_mode="Markdown"
        )
        
        if result:
            print("✅ Test notification sent successfully!")
            print(f"   Sent to {len(settings.admin_ids)} admin(s)")
        else:
            print("❌ Failed to send test notification")
            
    except Exception as e:
        print(f"❌ Error sending notification: {e}")
        result = False
    
    finally:
        await bot.session.close()
    
    print()
    print("📊 Test Results:")
    print(f"   Configuration: {'✅ OK' if settings.admin_ids else '❌ Failed'}")
    print(f"   Notification: {'✅ Sent' if result else '❌ Failed'}")
    print()
    
    if result:
        print("🎉 Notification system is working correctly!")
        print("   Admins should have received the test message.")
    else:
        print("💥 Notification system has issues.")
        print("   Check logs for more details.")
    
    return result

if __name__ == "__main__":
    print("Starting notification system test...")
    print("Make sure your .env file is configured with BOT_TOKEN and ADMIN_IDS")
    print()
    
    # Run test
    try:
        result = asyncio.run(test_notifications())
        exit_code = 0 if result else 1
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        exit_code = 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        exit_code = 1
    
    exit(exit_code)
