#!/usr/bin/env python
"""
Update Sold Properties Script - Comprehensive Property Status Fix
==================================================================

This script finds all properties with completed/confirmed bookings and transactions,
and marks them as 'Sold' in the database. This fixes the bug where properties remain
as 'Available' even after being purchased.

Features:
- Finds all properties with completed transactions (payment_status='completed' or 'success')
- Finds all properties with confirmed bookings (status='confirmed' or 'completed')
- Updates property status to 'Sold'
- Sends notifications to sellers about sold properties
- Creates comprehensive logs
- Shows before/after statistics
- Safe to run multiple times (idempotent)

Usage:
    python update_sold_properties.py
"""

import os
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateproject.settings')
django.setup()

from backend.models import Property, Booking, Transaction, EstateUser, Log
from backend import notification_service
from django.db.models import Q

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")

def print_section(text):
    """Print formatted section"""
    print("\n" + "-"*80)
    print(f"  {text}")
    print("-"*80)

def get_sold_properties_by_transactions():
    """
    Find properties with completed/successful transactions.
    These properties should definitely be marked as 'Sold'.
    """
    # Get all completed/successful transactions
    completed_transactions = Transaction.objects.filter(
        Q(payment_status='completed') | Q(payment_status='success')
    ).select_related('booking', 'booking__property')
    
    # Extract unique properties
    sold_property_ids = set()
    for txn in completed_transactions:
        if txn.booking and txn.booking.property:
            sold_property_ids.add(txn.booking.property.property_id)
    
    return Property.objects.filter(property_id__in=sold_property_ids)

def get_sold_properties_by_bookings():
    """
    Find properties with confirmed/completed bookings.
    These properties should be marked as 'Sold'.
    """
    confirmed_bookings = Booking.objects.filter(
        Q(status='confirmed') | Q(status='completed')
    ).select_related('property')
    
    # Extract unique properties
    sold_property_ids = set()
    for booking in confirmed_bookings:
        if booking.property:
            sold_property_ids.add(booking.property.property_id)
    
    return Property.objects.filter(property_id__in=sold_property_ids)

def get_statistics():
    """Get current property statistics"""
    total_properties = Property.objects.count()
    available_properties = Property.objects.filter(status='Available').count()
    sold_properties = Property.objects.filter(status='Sold').count()
    pending_properties = Property.objects.filter(status='Pending').count()
    
    # Properties with completed transactions
    completed_txns = Transaction.objects.filter(
        Q(payment_status='completed') | Q(payment_status='success')
    ).select_related('booking', 'booking__property')
    
    properties_with_completed_txns = set()
    for txn in completed_txns:
        if txn.booking and txn.booking.property:
            properties_with_completed_txns.add(txn.booking.property.property_id)
    
    # Properties with confirmed bookings
    confirmed_bookings = Booking.objects.filter(
        Q(status='confirmed') | Q(status='completed')
    ).select_related('property')
    
    properties_with_confirmed_bookings = set()
    for booking in confirmed_bookings:
        if booking.property:
            properties_with_confirmed_bookings.add(booking.property.property_id)
    
    # Properties that should be sold but aren't
    should_be_sold = properties_with_completed_txns | properties_with_confirmed_bookings
    actually_sold = set(Property.objects.filter(status='Sold').values_list('property_id', flat=True))
    needs_update = should_be_sold - actually_sold
    
    return {
        'total': total_properties,
        'available': available_properties,
        'sold': sold_properties,
        'pending': pending_properties,
        'should_be_sold_count': len(should_be_sold),
        'needs_update_count': len(needs_update),
        'needs_update_ids': list(needs_update)
    }

def update_sold_properties(send_notifications=True, create_logs=True):
    """
    Main function to update all sold properties.
    
    Args:
        send_notifications (bool): Whether to send notifications to sellers
        create_logs (bool): Whether to create activity logs
    
    Returns:
        dict: Summary of updates
    """
    print_header("🔄 PROPERTY STATUS UPDATE SCRIPT")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get statistics BEFORE update
    print_section("📊 CURRENT DATABASE STATUS (BEFORE UPDATE)")
    stats_before = get_statistics()
    
    print(f"📦 Total Properties: {stats_before['total']}")
    print(f"✅ Available: {stats_before['available']}")
    print(f"🔴 Sold: {stats_before['sold']}")
    print(f"⏳ Pending: {stats_before['pending']}")
    print(f"\n🔍 Properties with completed transactions/bookings: {stats_before['should_be_sold_count']}")
    print(f"⚠️  Properties that NEED status update: {stats_before['needs_update_count']}")
    
    if stats_before['needs_update_count'] == 0:
        print("\n✅ All properties already have correct status! No updates needed.")
        return {
            'success': True,
            'message': 'No updates needed - all properties already correct',
            'updated_count': 0,
            'stats_before': stats_before,
            'stats_after': stats_before
        }
    
    # Get properties that need to be marked as sold
    print_section("🔍 IDENTIFYING PROPERTIES TO UPDATE")
    
    properties_by_transactions = get_sold_properties_by_transactions()
    properties_by_bookings = get_sold_properties_by_bookings()
    
    # Combine both lists (union)
    all_sold_property_ids = set(properties_by_transactions.values_list('property_id', flat=True)) | \
                            set(properties_by_bookings.values_list('property_id', flat=True))
    
    properties_to_update = Property.objects.filter(
        property_id__in=all_sold_property_ids
    ).exclude(status='Sold').select_related('user')
    
    print(f"Found {properties_to_update.count()} properties to update:\n")
    
    # Update each property
    print_section("🔄 UPDATING PROPERTIES")
    updated_count = 0
    notification_count = 0
    log_count = 0
    
    for prop in properties_to_update:
        print(f"\n🏠 Property ID: {prop.property_id}")
        print(f"   Title: {prop.title}")
        print(f"   Owner: {prop.user.name if prop.user else 'Unknown'}")
        print(f"   Current Status: {prop.status}")
        
        # Get related booking and transaction info
        confirmed_booking = Booking.objects.filter(
            property=prop,
            status__in=['confirmed', 'completed']
        ).select_related('user').first()
        
        completed_transaction = None
        if confirmed_booking:
            completed_transaction = Transaction.objects.filter(
                booking=confirmed_booking,
                payment_status__in=['completed', 'success']
            ).first()
        
        # Update status
        old_status = prop.status
        prop.status = 'Sold'
        prop.save()
        updated_count += 1
        
        print(f"   ✅ Updated Status: {old_status} → Sold")
        
        # Send notification to seller
        if send_notifications and prop.user:
            try:
                buyer_name = confirmed_booking.user.name if confirmed_booking and confirmed_booking.user else "Unknown Buyer"
                amount = completed_transaction.amount if completed_transaction else "N/A"
                
                notification_message = f"""
🎉 Property Status Updated to SOLD! 🎉

Your property "{prop.title}" has been marked as SOLD in the system.

Property Details:
- Property ID: {prop.property_id}
- Title: {prop.title}
- Location: {prop.location}
- Price: ₹{prop.price}

Sale Details:
- Buyer: {buyer_name}
- Amount: ₹{amount}
- Status: Sold & Confirmed

This is a system update to reflect the completed transaction.
                """.strip()
                
                notification_service.create_seller_notification(
                    seller_id=prop.user.user_id,
                    title=f'🎉 Property Sold: {prop.title}',
                    message=notification_message,
                    notification_type=notification_service.NotificationType.PAYMENT_RECEIVED,
                    property_obj=prop,
                    booking_obj=confirmed_booking
                )
                notification_count += 1
                print(f"   📧 Notification sent to seller")
            except Exception as e:
                print(f"   ⚠️  Failed to send notification: {str(e)}")
        
        # Create activity log
        if create_logs and prop.user:
            try:
                Log.objects.create(
                    user=prop.user,
                    action=f"Property status updated to SOLD: {prop.title} (Property ID: {prop.property_id}) - System Update"
                )
                log_count += 1
                print(f"   📝 Activity log created")
            except Exception as e:
                print(f"   ⚠️  Failed to create log: {str(e)}")
    
    # Get statistics AFTER update
    print_section("📊 FINAL DATABASE STATUS (AFTER UPDATE)")
    stats_after = get_statistics()
    
    print(f"📦 Total Properties: {stats_after['total']}")
    print(f"✅ Available: {stats_after['available']} (was {stats_before['available']})")
    print(f"🔴 Sold: {stats_after['sold']} (was {stats_before['sold']})")
    print(f"⏳ Pending: {stats_after['pending']} (was {stats_before['pending']})")
    
    # Summary
    print_header("✅ UPDATE COMPLETE")
    print(f"🔄 Properties Updated: {updated_count}")
    print(f"📧 Notifications Sent: {notification_count}")
    print(f"📝 Activity Logs Created: {log_count}")
    print(f"\n📈 Status Change:")
    print(f"   Available: {stats_before['available']} → {stats_after['available']} (Change: {stats_after['available'] - stats_before['available']})")
    print(f"   Sold: {stats_before['sold']} → {stats_after['sold']} (Change: +{stats_after['sold'] - stats_before['sold']})")
    print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    return {
        'success': True,
        'message': f'Successfully updated {updated_count} properties',
        'updated_count': updated_count,
        'notification_count': notification_count,
        'log_count': log_count,
        'stats_before': stats_before,
        'stats_after': stats_after
    }

if __name__ == '__main__':
    try:
        result = update_sold_properties(
            send_notifications=True,  # Set to False if you don't want to spam sellers
            create_logs=True          # Set to False if you don't want logs
        )
        
        if result['success']:
            print("\n🎉 SUCCESS! All sold properties have been updated.\n")
        else:
            print("\n⚠️  Script completed with warnings. Check the output above.\n")
            
    except Exception as e:
        print(f"\n❌ ERROR: Script failed with exception:")
        print(f"   {str(e)}\n")
        import traceback
        traceback.print_exc()
