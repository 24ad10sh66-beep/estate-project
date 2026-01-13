"""
Real-time Notification Service for Estate Management System
==========================================================
Centralized notification management for buyers, sellers, and admins.
Handles creation, delivery, and tracking of all system notifications.
"""

from django.utils import timezone
from .models import SellerNotification, BuyerNotification, EstateUser, Property, Booking, SupportTicket
import logging

logger = logging.getLogger(__name__)


# ===========================
# Notification Type Constants
# ===========================

class NotificationType:
    """Notification type constants for consistency"""
    
    # Booking Related
    BOOKING_RECEIVED = "booking_received"
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_DENIED = "booking_denied"
    BOOKING_CANCELLED = "booking_cancelled"
    
    # Payment Related
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_RECEIVED = "payment_received"
    
    # Property Related
    PROPERTY_ADDED = "property_added"
    PROPERTY_APPROVED = "property_approved"
    PROPERTY_REJECTED = "property_rejected"
    PROPERTY_SOLD = "property_sold"
    PROPERTY_SAVED = "property_saved"
    PROPERTY_STATUS_CHANGED = "property_status_changed"
    
    # Support Ticket Related
    TICKET_CREATED = "ticket_created"
    TICKET_RESPONDED = "ticket_responded"
    TICKET_ASSIGNED = "ticket_assigned"
    TICKET_RESOLVED = "ticket_resolved"
    TICKET_UPDATED = "ticket_updated"
    
    # System Messages
    SYSTEM_MESSAGE = "system_message"
    WELCOME = "welcome"


# ===========================
# Core Notification Functions
# ===========================

def create_seller_notification(seller_id, title, message, notification_type, property_obj=None, booking_obj=None):
    """
    Create a notification for seller
    
    Args:
        seller_id: Seller's user ID
        title: Notification title
        message: Notification message
        notification_type: Type of notification (use NotificationType constants)
        property_obj: Related Property object (optional)
        booking_obj: Related Booking object (optional)
    
    Returns:
        SellerNotification object or None if failed
    """
    try:
        seller = EstateUser.objects.get(user_id=seller_id, role='seller')
        
        notification = SellerNotification.objects.create(
            seller=seller,
            property=property_obj,
            booking=booking_obj,
            notification_type=notification_type,
            title=title,
            message=message,
            is_read=False
        )
        
        logger.info(f"✅ Seller notification created: {title} for seller #{seller_id}")
        return notification
        
    except EstateUser.DoesNotExist:
        logger.error(f"❌ Seller not found: {seller_id}")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to create seller notification: {str(e)}")
        return None


def create_buyer_notification(buyer_id, title, message, notification_type, support_ticket=None):
    """
    Create a notification for buyer
    
    Args:
        buyer_id: Buyer's user ID
        title: Notification title
        message: Notification message
        notification_type: Type of notification (use NotificationType constants)
        support_ticket: Related SupportTicket object (optional)
    
    Returns:
        BuyerNotification object or None if failed
    """
    try:
        buyer = EstateUser.objects.get(user_id=buyer_id, role='buyer')
        
        notification = BuyerNotification.objects.create(
            buyer=buyer,
            support_ticket=support_ticket,
            notification_type=notification_type,
            title=title,
            message=message,
            is_read=False
        )
        
        logger.info(f"✅ Buyer notification created: {title} for buyer #{buyer_id}")
        return notification
        
    except EstateUser.DoesNotExist:
        logger.error(f"❌ Buyer not found: {buyer_id}")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to create buyer notification: {str(e)}")
        return None


def create_admin_notification(title, message, notification_type):
    """
    Create notifications for all admin users
    
    Args:
        title: Notification title
        message: Notification message
        notification_type: Type of notification
    
    Returns:
        List of created notification objects
    """
    notifications = []
    try:
        admins = EstateUser.objects.filter(role='admin')
        
        for admin in admins:
            notification = SellerNotification.objects.create(
                seller=admin,  # Using SellerNotification for admins (reusing table)
                notification_type=notification_type,
                title=title,
                message=message,
                is_read=False
            )
            notifications.append(notification)
        
        logger.info(f"✅ Admin notifications created: {title} for {len(notifications)} admins")
        return notifications
        
    except Exception as e:
        logger.error(f"❌ Failed to create admin notifications: {str(e)}")
        return notifications


# ===========================
# Booking Notification Flows
# ===========================

def notify_booking_received(booking_id):
    """Notify seller when buyer creates a booking"""
    try:
        booking = Booking.objects.select_related('property', 'property__user', 'user').get(booking_id=booking_id)
        seller_id = booking.property.user.user_id
        buyer_name = booking.user.name
        property_title = booking.property.title
        
        return create_seller_notification(
            seller_id=seller_id,
            title="🔔 New Booking Received!",
            message=f"{buyer_name} has placed a booking request for your property '{property_title}'. Please review and confirm.",
            notification_type=NotificationType.BOOKING_RECEIVED,
            property_obj=booking.property,
            booking_obj=booking
        )
    except Exception as e:
        logger.error(f"❌ Booking notification failed: {str(e)}")
        return None


def notify_booking_confirmed(booking_id):
    """Notify buyer and admin when seller confirms booking"""
    try:
        booking = Booking.objects.select_related('property', 'property__user', 'user').get(booking_id=booking_id)
        buyer_id = booking.user.user_id
        property_title = booking.property.title
        seller_name = booking.property.user.name
        
        # Notify buyer
        buyer_notif = create_buyer_notification(
            buyer_id=buyer_id,
            title="✅ Booking Confirmed!",
            message=f"Great news! {seller_name} has confirmed your booking for '{property_title}'. Proceed with payment.",
            notification_type=NotificationType.BOOKING_CONFIRMED
        )
        
        # Notify admins
        admin_notifs = create_admin_notification(
            title="📋 Booking Confirmed",
            message=f"Seller {seller_name} confirmed booking for '{property_title}' by {booking.user.name}.",
            notification_type=NotificationType.BOOKING_CONFIRMED
        )
        
        return {'buyer': buyer_notif, 'admins': admin_notifs}
        
    except Exception as e:
        logger.error(f"❌ Booking confirmation notification failed: {str(e)}")
        return None


def notify_booking_denied(booking_id, reason=""):
    """Notify buyer when seller denies booking"""
    try:
        booking = Booking.objects.select_related('property', 'property__user', 'user').get(booking_id=booking_id)
        buyer_id = booking.user.user_id
        property_title = booking.property.title
        seller_name = booking.property.user.name
        
        message = f"Your booking for '{property_title}' was declined by {seller_name}."
        if reason:
            message += f" Reason: {reason}"
        
        return create_buyer_notification(
            buyer_id=buyer_id,
            title="❌ Booking Declined",
            message=message,
            notification_type=NotificationType.BOOKING_DENIED
        )
    except Exception as e:
        logger.error(f"❌ Booking denial notification failed: {str(e)}")
        return None


def notify_booking_cancelled(booking_id, cancelled_by="buyer"):
    """Notify relevant parties when booking is cancelled"""
    try:
        booking = Booking.objects.select_related('property', 'property__user', 'user').get(booking_id=booking_id)
        property_title = booking.property.title
        
        if cancelled_by == "buyer":
            # Notify seller
            return create_seller_notification(
                seller_id=booking.property.user.user_id,
                title="🚫 Booking Cancelled",
                message=f"{booking.user.name} cancelled their booking for '{property_title}'.",
                notification_type=NotificationType.BOOKING_CANCELLED,
                property_obj=booking.property,
                booking_obj=booking
            )
        else:
            # Notify buyer
            return create_buyer_notification(
                buyer_id=booking.user.user_id,
                title="🚫 Booking Cancelled",
                message=f"Your booking for '{property_title}' has been cancelled by the seller.",
                notification_type=NotificationType.BOOKING_CANCELLED
            )
    except Exception as e:
        logger.error(f"❌ Booking cancellation notification failed: {str(e)}")
        return None


# ===========================
# Payment Notification Flows
# ===========================

def notify_payment_success(booking_id, amount):
    """Notify buyer and seller when payment is successful"""
    try:
        booking = Booking.objects.select_related('property', 'property__user', 'user').get(booking_id=booking_id)
        property_title = booking.property.title
        
        # Notify buyer
        buyer_notif = create_buyer_notification(
            buyer_id=booking.user.user_id,
            title="💰 Payment Successful!",
            message=f"Your payment of ₹{amount:,.0f} for '{property_title}' was successful. Transaction completed!",
            notification_type=NotificationType.PAYMENT_SUCCESS
        )
        
        # Notify seller
        seller_notif = create_seller_notification(
            seller_id=booking.property.user.user_id,
            title="💸 Payment Received!",
            message=f"Payment of ₹{amount:,.0f} received for '{property_title}'. Buyer: {booking.user.name}",
            notification_type=NotificationType.PAYMENT_RECEIVED,
            property_obj=booking.property,
            booking_obj=booking
        )
        
        return {'buyer': buyer_notif, 'seller': seller_notif}
        
    except Exception as e:
        logger.error(f"❌ Payment success notification failed: {str(e)}")
        return None


def notify_payment_failed(booking_id, reason=""):
    """Notify buyer when payment fails"""
    try:
        booking = Booking.objects.select_related('property', 'user').get(booking_id=booking_id)
        property_title = booking.property.title
        
        message = f"Payment failed for '{property_title}'. Please try again."
        if reason:
            message += f" Reason: {reason}"
        
        return create_buyer_notification(
            buyer_id=booking.user.user_id,
            title="❌ Payment Failed",
            message=message,
            notification_type=NotificationType.PAYMENT_FAILED
        )
    except Exception as e:
        logger.error(f"❌ Payment failure notification failed: {str(e)}")
        return None


# ===========================
# Property Notification Flows
# ===========================

def notify_property_added(property_id):
    """Notify admin when seller adds a property"""
    try:
        property_obj = Property.objects.select_related('user').get(property_id=property_id)
        seller_name = property_obj.user.name
        
        return create_admin_notification(
            title="🏠 New Property Listed",
            message=f"{seller_name} added a new property: '{property_obj.title}' in {property_obj.location}.",
            notification_type=NotificationType.PROPERTY_ADDED
        )
    except Exception as e:
        logger.error(f"❌ Property added notification failed: {str(e)}")
        return None


def notify_property_status_changed(property_id, new_status):
    """Notify seller when property status changes"""
    try:
        property_obj = Property.objects.select_related('user').get(property_id=property_id)
        
        return create_seller_notification(
            seller_id=property_obj.user.user_id,
            title="📝 Property Status Updated",
            message=f"Your property '{property_obj.title}' status changed to: {new_status}",
            notification_type=NotificationType.PROPERTY_STATUS_CHANGED,
            property_obj=property_obj
        )
    except Exception as e:
        logger.error(f"❌ Property status notification failed: {str(e)}")
        return None


def notify_property_saved(property_id, buyer_id):
    """Notify seller when buyer saves their property"""
    try:
        property_obj = Property.objects.select_related('user').get(property_id=property_id)
        buyer = EstateUser.objects.get(user_id=buyer_id)
        
        return create_seller_notification(
            seller_id=property_obj.user.user_id,
            title="❤️ Property Saved by Buyer",
            message=f"{buyer.name} saved your property '{property_obj.title}' to their wishlist!",
            notification_type=NotificationType.PROPERTY_SAVED,
            property_obj=property_obj
        )
    except Exception as e:
        logger.error(f"❌ Property saved notification failed: {str(e)}")
        return None


# ===========================
# Support Ticket Notification Flows
# ===========================

def notify_ticket_created(ticket_id):
    """Notify admin when buyer creates a support ticket"""
    try:
        ticket = SupportTicket.objects.select_related('user').get(ticket_id=ticket_id)
        
        return create_admin_notification(
            title="🎫 New Support Ticket",
            message=f"{ticket.user.name} created ticket #{ticket.token_id}: '{ticket.subject}'. Priority: {ticket.priority}",
            notification_type=NotificationType.TICKET_CREATED
        )
    except Exception as e:
        logger.error(f"❌ Ticket created notification failed: {str(e)}")
        return None


def notify_ticket_responded(ticket_id):
    """Notify buyer when admin responds to their ticket"""
    try:
        ticket = SupportTicket.objects.select_related('user').get(ticket_id=ticket_id)
        
        return create_buyer_notification(
            buyer_id=ticket.user.user_id,
            title="💬 Support Ticket Update",
            message=f"You have a new response on your ticket #{ticket.token_id}: '{ticket.subject}'",
            notification_type=NotificationType.TICKET_RESPONDED,
            support_ticket=ticket
        )
    except Exception as e:
        logger.error(f"❌ Ticket response notification failed: {str(e)}")
        return None


def notify_ticket_resolved(ticket_id):
    """Notify buyer when their ticket is resolved"""
    try:
        ticket = SupportTicket.objects.select_related('user').get(ticket_id=ticket_id)
        
        return create_buyer_notification(
            buyer_id=ticket.user.user_id,
            title="✅ Support Ticket Resolved",
            message=f"Your ticket #{ticket.token_id}: '{ticket.subject}' has been marked as resolved.",
            notification_type=NotificationType.TICKET_RESOLVED,
            support_ticket=ticket
        )
    except Exception as e:
        logger.error(f"❌ Ticket resolved notification failed: {str(e)}")
        return None


# ===========================
# Utility Functions
# ===========================

def get_user_notifications(user_id, role, limit=50):
    """
    Get all notifications for a user
    
    Args:
        user_id: User's ID
        role: User's role (buyer/seller/admin)
        limit: Maximum number of notifications to return
    
    Returns:
        QuerySet of notifications
    """
    try:
        if role == 'buyer':
            return BuyerNotification.objects.filter(buyer_id=user_id).order_by('-created_at')[:limit]
        else:  # seller or admin
            return SellerNotification.objects.filter(seller_id=user_id).order_by('-created_at')[:limit]
    except Exception as e:
        logger.error(f"❌ Failed to get notifications: {str(e)}")
        return []


def mark_notification_read(notification_id, role):
    """Mark a notification as read"""
    try:
        if role == 'buyer':
            notification = BuyerNotification.objects.get(notification_id=notification_id)
        else:
            notification = SellerNotification.objects.get(notification_id=notification_id)
        
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        logger.info(f"✅ Notification #{notification_id} marked as read")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to mark notification as read: {str(e)}")
        return False


def mark_all_notifications_read(user_id, role):
    """Mark all unread notifications as read for a user"""
    try:
        if role == 'buyer':
            count = BuyerNotification.objects.filter(buyer_id=user_id, is_read=False).update(
                is_read=True,
                read_at=timezone.now()
            )
        else:
            count = SellerNotification.objects.filter(seller_id=user_id, is_read=False).update(
                is_read=True,
                read_at=timezone.now()
            )
        
        logger.info(f"✅ Marked {count} notifications as read for user #{user_id}")
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to mark all notifications as read: {str(e)}")
        return 0


def get_unread_count(user_id, role):
    """Get count of unread notifications"""
    try:
        if role == 'buyer':
            return BuyerNotification.objects.filter(buyer_id=user_id, is_read=False).count()
        else:
            return SellerNotification.objects.filter(seller_id=user_id, is_read=False).count()
    except Exception as e:
        logger.error(f"❌ Failed to get unread count: {str(e)}")
        return 0


def delete_notification(notification_id, role):
    """Delete a notification"""
    try:
        if role == 'buyer':
            BuyerNotification.objects.filter(notification_id=notification_id).delete()
        else:
            SellerNotification.objects.filter(notification_id=notification_id).delete()
        
        logger.info(f"✅ Notification #{notification_id} deleted")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to delete notification: {str(e)}")
        return False
