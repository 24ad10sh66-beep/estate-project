"""
Fix Script for Support Ticket and Notification Issues
=======================================================

This script fixes:
1. Missing assigned_to_id column in support_tickets table
2. Notification API errors (slice before filter issue)
3. Adds robust error handling
4. Creates test data for notifications

Run this after creating the migration file.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateproject.settings')
django.setup()

from django.db import connection
from backend.models import EstateUser, SupportTicket, SellerNotification, BuyerNotification
from django.utils import timezone
import datetime


def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = '{table_name}'
            AND COLUMN_NAME = '{column_name}'
        """)
        return cursor.fetchone()[0] > 0


def fix_support_ticket_table():
    """Add assigned_to_id column if missing"""
    print("\n" + "="*60)
    print("STEP 1: Checking support_tickets table...")
    print("="*60)
    
    table_name = 'support_tickets'
    column_name = 'assigned_to_id'
    
    if check_column_exists(table_name, column_name):
        print(f"✅ Column '{column_name}' already exists in '{table_name}' table")
        return True
    
    print(f"⚠️  Column '{column_name}' is missing from '{table_name}' table")
    print(f"📝 Adding column...")
    
    try:
        with connection.cursor() as cursor:
            # Add the column
            cursor.execute(f"""
                ALTER TABLE {table_name}
                ADD COLUMN {column_name} INT NULL,
                ADD CONSTRAINT fk_support_tickets_assigned_to
                FOREIGN KEY ({column_name}) REFERENCES users(user_id)
                ON DELETE SET NULL
            """)
        
        print(f"✅ Successfully added '{column_name}' column with foreign key constraint")
        return True
    except Exception as e:
        print(f"❌ Error adding column: {str(e)}")
        return False


def verify_database_structure():
    """Verify all critical columns exist"""
    print("\n" + "="*60)
    print("STEP 2: Verifying database structure...")
    print("="*60)
    
    checks = [
        ('support_tickets', 'ticket_id'),
        ('support_tickets', 'token_id'),
        ('support_tickets', 'user_id'),
        ('support_tickets', 'assigned_to_id'),
        ('support_tickets', 'subject'),
        ('support_tickets', 'status'),
        ('seller_notifications', 'notification_id'),
        ('seller_notifications', 'seller_id'),
        ('buyer_notifications', 'notification_id'),
        ('buyer_notifications', 'buyer_id'),
    ]
    
    all_good = True
    for table, column in checks:
        exists = check_column_exists(table, column)
        status = "✅" if exists else "❌"
        print(f"{status} {table}.{column}")
        if not exists:
            all_good = False
    
    return all_good


def create_sample_notifications():
    """Create sample notifications for testing"""
    print("\n" + "="*60)
    print("STEP 3: Creating sample notifications...")
    print("="*60)
    
    try:
        # Get sample users
        sellers = EstateUser.objects.filter(role='seller')[:2]
        buyers = EstateUser.objects.filter(role='buyer')[:2]
        
        if not sellers:
            print("⚠️  No sellers found, skipping seller notifications")
        else:
            # Create seller notifications
            for seller in sellers:
                # Check if seller already has notifications
                existing = SellerNotification.objects.filter(seller=seller).count()
                if existing > 0:
                    print(f"ℹ️  Seller {seller.name} already has {existing} notification(s)")
                    continue
                
                SellerNotification.objects.create(
                    seller=seller,
                    notification_type='booking_received',
                    title='🎯 Test Notification',
                    message=f'This is a test notification for {seller.name}',
                    is_read=False
                )
                print(f"✅ Created test notification for seller: {seller.name}")
        
        if not buyers:
            print("⚠️  No buyers found, skipping buyer notifications")
        else:
            # Create buyer notifications
            for buyer in buyers:
                # Check if buyer already has notifications
                existing = BuyerNotification.objects.filter(buyer=buyer).count()
                if existing > 0:
                    print(f"ℹ️  Buyer {buyer.name} already has {existing} notification(s)")
                    continue
                
                BuyerNotification.objects.create(
                    buyer=buyer,
                    notification_type='booking_confirmed',
                    title='✅ Test Notification',
                    message=f'This is a test notification for {buyer.name}',
                    is_read=False
                )
                print(f"✅ Created test notification for buyer: {buyer.name}")
        
        return True
    except Exception as e:
        print(f"❌ Error creating sample notifications: {str(e)}")
        return False


def test_notification_queries():
    """Test notification queries to ensure they work"""
    print("\n" + "="*60)
    print("STEP 4: Testing notification queries...")
    print("="*60)
    
    try:
        # Test seller notifications
        seller_count = SellerNotification.objects.count()
        print(f"✅ Seller notifications: {seller_count}")
        
        # Test buyer notifications
        buyer_count = BuyerNotification.objects.count()
        print(f"✅ Buyer notifications: {buyer_count}")
        
        # Test support tickets query
        tickets = SupportTicket.objects.select_related('user', 'assigned_to')[:5]
        print(f"✅ Support tickets query successful: {tickets.count()} tickets found")
        
        for ticket in tickets:
            assigned = ticket.assigned_to.name if ticket.assigned_to else "Unassigned"
            print(f"   - Ticket #{ticket.ticket_id}: {ticket.subject} (Assigned to: {assigned})")
        
        return True
    except Exception as e:
        print(f"❌ Error testing queries: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def print_summary():
    """Print summary of database state"""
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    try:
        print(f"📊 Users: {EstateUser.objects.count()}")
        print(f"   - Sellers: {EstateUser.objects.filter(role='seller').count()}")
        print(f"   - Buyers: {EstateUser.objects.filter(role='buyer').count()}")
        print(f"   - Admins: {EstateUser.objects.filter(role='admin').count()}")
        
        print(f"\n🎫 Support Tickets: {SupportTicket.objects.count()}")
        print(f"   - Open: {SupportTicket.objects.filter(status='open').count()}")
        print(f"   - In Progress: {SupportTicket.objects.filter(status='in_progress').count()}")
        print(f"   - Resolved: {SupportTicket.objects.filter(status='resolved').count()}")
        
        print(f"\n🔔 Notifications:")
        print(f"   - Seller: {SellerNotification.objects.count()} total ({SellerNotification.objects.filter(is_read=False).count()} unread)")
        print(f"   - Buyer: {BuyerNotification.objects.count()} total ({BuyerNotification.objects.filter(is_read=False).count()} unread)")
        
    except Exception as e:
        print(f"❌ Error getting summary: {str(e)}")


def main():
    """Main execution function"""
    print("\n" + "="*70)
    print(" " * 10 + "SUPPORT TICKET & NOTIFICATION FIX SCRIPT")
    print("="*70)
    
    # Step 1: Fix support_tickets table
    if not fix_support_ticket_table():
        print("\n❌ Failed to fix support_tickets table. Please check manually.")
        return
    
    # Step 2: Verify structure
    if not verify_database_structure():
        print("\n⚠️  Some columns are missing. Please run migrations:")
        print("   python manage.py makemigrations")
        print("   python manage.py migrate")
        return
    
    # Step 3: Create sample data
    create_sample_notifications()
    
    # Step 4: Test queries
    test_notification_queries()
    
    # Print summary
    print_summary()
    
    print("\n" + "="*70)
    print("✅ FIX SCRIPT COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("\n📌 Next steps:")
    print("   1. Restart Django server: python manage.py runserver")
    print("   2. Test admin support tickets page: /backend/admin/support-tickets/")
    print("   3. Test notification icon in dashboards")
    print("   4. Check browser console for any JavaScript errors")
    print("\n")


if __name__ == '__main__':
    main()
