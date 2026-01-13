"""
Quick script to add bathrooms column to price_data_model table
Run: python add_bathrooms_to_db.py
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateproject.settings')
django.setup()

from django.db import connection

def add_bathrooms_column():
    """Add bathrooms column to price_data_model table if it doesn't exist"""
    
    with connection.cursor() as cursor:
        try:
            # Check if column exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = 'estate_management_system' 
                AND TABLE_NAME = 'price_data_model' 
                AND COLUMN_NAME = 'bathrooms'
            """)
            
            exists = cursor.fetchone()[0]
            
            if exists == 0:
                print("Adding bathrooms column to price_data_model table...")
                cursor.execute("""
                    ALTER TABLE price_data_model 
                    ADD COLUMN bathrooms INT NOT NULL DEFAULT 2 AFTER bedrooms
                """)
                print("✅ Successfully added bathrooms column!")
            else:
                print("✅ Bathrooms column already exists!")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    add_bathrooms_column()
