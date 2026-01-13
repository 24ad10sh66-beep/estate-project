"""
Fix SupportTicket table - Remove assigned_to_id column if exists and add assigned_to
Run: python fix_support_ticket_table.py
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateproject.settings')
django.setup()

from django.db import connection

def fix_support_ticket_table():
    """Fix support_tickets table schema"""
    
    with connection.cursor() as cursor:
        try:
            print("Checking support_tickets table...")
            
            # Check if assigned_to_id column exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = 'estate_management_system' 
                AND TABLE_NAME = 'support_tickets' 
                AND COLUMN_NAME = 'assigned_to_id'
            """)
            
            has_assigned_to_id = cursor.fetchone()[0]
            
            if has_assigned_to_id > 0:
                print("❌ Found old assigned_to_id column. Dropping it...")
                cursor.execute("""
                    ALTER TABLE support_tickets 
                    DROP FOREIGN KEY IF EXISTS support_tickets_ibfk_2
                """)
                cursor.execute("""
                    ALTER TABLE support_tickets 
                    DROP COLUMN assigned_to_id
                """)
                print("✅ Dropped assigned_to_id column")
            
            # Check if assigned_to column exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = 'estate_management_system' 
                AND TABLE_NAME = 'support_tickets' 
                AND COLUMN_NAME = 'assigned_to'
            """)
            
            has_assigned_to = cursor.fetchone()[0]
            
            if has_assigned_to == 0:
                print("Adding assigned_to column...")
                cursor.execute("""
                    ALTER TABLE support_tickets 
                    ADD COLUMN assigned_to INT NULL 
                    AFTER description
                """)
                
                # Add foreign key constraint
                cursor.execute("""
                    ALTER TABLE support_tickets 
                    ADD CONSTRAINT fk_support_tickets_assigned_to
                    FOREIGN KEY (assigned_to) 
                    REFERENCES users(user_id) 
                    ON DELETE SET NULL
                """)
                print("✅ Added assigned_to column with foreign key")
            else:
                print("✅ assigned_to column already exists")
            
            # Check token_id column
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = 'estate_management_system' 
                AND TABLE_NAME = 'support_tickets' 
                AND COLUMN_NAME = 'token_id'
            """)
            
            has_token_id = cursor.fetchone()[0]
            
            if has_token_id == 0:
                print("Adding token_id column...")
                cursor.execute("""
                    ALTER TABLE support_tickets 
                    ADD COLUMN token_id VARCHAR(50) NULL UNIQUE 
                    AFTER ticket_id
                """)
                print("✅ Added token_id column")
            else:
                print("✅ token_id column already exists")
            
            print("\n" + "="*60)
            print("✅ Support tickets table is now fixed!")
            print("="*60)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    fix_support_ticket_table()
