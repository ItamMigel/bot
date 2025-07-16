# Notifications System Documentation

## Overview

The NotificationService provides real-time notifications for administrators and users about important events in the bot. It integrates seamlessly with all major user actions and admin operations.

## Features

### ✅ Implemented Notifications

1. **New Order Notifications**
   - Sent to all admins when a user creates a new order
   - Includes order details, user info, and total amount
   - Triggered: After order creation with any payment method

2. **Payment Screenshot Notifications**
   - Sent to admins when user uploads payment screenshot  
   - Requires admin approval/rejection
   - Triggered: After card payment screenshot upload

3. **Feedback/Contact Form Notifications**
   - Sent to admins when user submits feedback
   - Includes user details and message content
   - Triggered: Through FAQ → Contact Us form

4. **Order Status Change Notifications**
   - Sent to users when admin changes order status
   - Shows old status → new status transition
   - Triggered: Admin panel status changes

5. **Order Cancellation Notifications**
   - Sent to admins when user cancels order
   - Sent to user confirming cancellation
   - Triggered: User cancels order during payment

## Configuration

### Environment Variables

Add admin IDs to `.env`:
```bash
# Comma-separated list of admin Telegram IDs
ADMIN_IDS=123456789,987654321
```

### Admin Management

Administrators receive notifications for:
- New orders requiring attention
- Payment screenshots needing verification
- User feedback and support requests
- Order cancellations

## Technical Implementation

### Core Service

```python
from app.services.notifications import NotificationService

# Send to all admins
await NotificationService.notify_admins(bot, message, parse_mode="HTML")

# Send to specific user  
await NotificationService.notify_user(bot, user_id, message)

# Specialized notifications
await NotificationService.notify_new_order(bot, order, user)
await NotificationService.notify_payment_received(bot, order, user)
await NotificationService.notify_feedback(bot, user, feedback_text)
await NotificationService.notify_order_status_change(bot, order, user, old_status, new_status)
await NotificationService.notify_order_cancelled(bot, order, user)
```

### Error Handling

- Failed notifications are logged with detailed error messages
- Service continues operating even if some admins are unreachable
- Returns success/failure status for integration tracking

### Message Templates

All notification messages are defined in `app/utils/texts.py`:
- `NEW_ORDER_NOTIFICATION` - New order alerts
- `PAYMENT_RECEIVED_NOTIFICATION` - Payment screenshot alerts  
- `ADMIN_FEEDBACK_NOTIFICATION` - User feedback alerts
- `ORDER_STATUS_CHANGED_USER` - Status change confirmations

## Integration Points

### User Handlers

1. **Order Creation** (`app/handlers/user/orders.py`)
   - `choose_cash_payment()` - Cash order notifications
   - `receive_payment_screenshot()` - Card payment notifications

2. **Feedback System** (`app/handlers/user/faq.py`)
   - `receive_feedback()` - Contact form submissions

3. **Order Management** (`app/handlers/user/orders.py`)
   - `cancel_payment_order()` - Order cancellation alerts

### Admin Handlers

1. **Payment Management** (`app/handlers/admin/admin_panel.py`)
   - `confirm_payment()` - Payment approval notifications
   - `reject_payment()` - Payment rejection notifications

2. **Status Management** (`app/handlers/admin/admin_panel.py`)
   - `set_order_status()` - Status change notifications

## Usage Examples

### For New Features

When adding new user actions that require admin attention:

```python
# In your handler
from app.services.notifications import NotificationService

# Create custom notification
message = f"🔔 New event: {event_details}"
await NotificationService.notify_admins(message.bot, message)

# Or use specific notification
await NotificationService.notify_new_order(message.bot, order, user)
```

### Admin Response Workflow

1. Admin receives notification about new order/payment/feedback
2. Admin opens admin panel to review and take action
3. Admin approves/rejects/changes status
4. User receives confirmation notification automatically

## Testing

### Manual Testing Steps

1. **Test New Order Notifications:**
   - Create order as user → Check admin receives notification
   - Verify notification contains correct order details

2. **Test Payment Notifications:**
   - Upload payment screenshot → Check admin notification
   - Admin approve/reject → Check user notification

3. **Test Feedback Notifications:**
   - Submit feedback via FAQ → Check admin notification
   - Verify user details are included

4. **Test Status Notifications:**
   - Change order status in admin panel → Check user notification
   - Verify status transition is clear

### Logs Monitoring

Monitor logs for notification delivery:
```bash
# Successful notifications
INFO - Notification sent to admin 123456789
INFO - Notification sent to user 987654321

# Failed notifications  
ERROR - Failed to send notification to admin 123456789: Forbidden: bot was blocked by the user
```

## Future Enhancements

- [ ] Notification preferences for admins
- [ ] Custom notification templates
- [ ] Notification scheduling
- [ ] SMS/Email integration
- [ ] Notification analytics and tracking
- [ ] Bulk notifications for announcements

## Troubleshooting

### Common Issues

1. **"No admin IDs configured"**
   - Solution: Add `ADMIN_IDS` to `.env` file

2. **"Failed to send notification: Forbidden"**
   - Cause: Admin blocked the bot or bot not started by admin
   - Solution: Admin needs to start conversation with bot

3. **Notifications not received**
   - Check admin IDs are correct in `.env`
   - Verify bot token has proper permissions
   - Check bot is not blocked by admin users

### Debug Mode

Enable detailed notification logging:
```python
import logging
logging.getLogger('app.services.notifications').setLevel(logging.DEBUG)
```

## Security Considerations

- Admin IDs stored in environment variables (not in code)
- Sensitive user data included in notifications should be minimal
- Failed notification attempts are logged but don't expose user data
- Bot token security is critical for notification delivery
