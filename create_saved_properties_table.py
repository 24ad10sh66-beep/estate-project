#!/usr/bin/env python
"""
Script to create saved_properties table manually
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateproject.settings')
django.setup()

from django.db import connection

def create_saved_properties_table():
    with connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables 
            WHERE table_schema = 'estate_management_system' 
            AND table_name = 'saved_properties'
        """)
        
        exists = cursor.fetchone()[0]
        
        if exists:
            print("✓ Table 'saved_properties' already exists!")
            return
        
        print("Creating 'saved_properties' table...")
        
        # Create table
        cursor.execute("""
            CREATE TABLE `saved_properties` (
                `saved_id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
                `saved_at` datetime(6) NOT NULL,
                `notes` longtext NULL,
                `property_id` integer NULL,
                `user_id` integer NULL,
                CONSTRAINT `saved_properties_user_id_property_id_dd6425be_uniq` UNIQUE (`user_id`, `property_id`),
                CONSTRAINT `saved_properties_property_id_824cd525_fk_properties_property_id` 
                    FOREIGN KEY (`property_id`) REFERENCES `properties` (`property_id`),
                CONSTRAINT `saved_properties_user_id_449a50d5_fk_users_user_id` 
                    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
            )
        """)
        
        print("✓ Table 'saved_properties' created successfully!")
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX `saved_properties_property_id_824cd525` 
            ON `saved_properties` (`property_id`)
        """)
        
        cursor.execute("""
            CREATE INDEX `saved_properties_user_id_449a50d5` 
            ON `saved_properties` (`user_id`)
        """)
        
        print("✓ Indexes created successfully!")
        print("\n✅ All done! You can now use the Save Property feature!")

if __name__ == '__main__':
    try:
        create_saved_properties_table()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
