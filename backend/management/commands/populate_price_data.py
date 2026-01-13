"""
Django Management Command: Populate PriceDataModel with existing Property data
Usage: python manage.py populate_price_data
"""

from django.core.management.base import BaseCommand
from backend.models import Property, PriceDataModel


class Command(BaseCommand):
    help = 'Populate PriceDataModel with data from existing properties for ML training'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing PriceDataModel data before populating',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting PriceDataModel population...'))
        
        # Clear existing data if requested
        if options['clear']:
            count = PriceDataModel.objects.count()
            PriceDataModel.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing entries'))
        
        # Get all properties
        properties = Property.objects.all()
        total = properties.count()
        
        if total == 0:
            self.stdout.write(self.style.ERROR('No properties found in database'))
            return
        
        self.stdout.write(f'Found {total} properties to process...')
        
        added = 0
        skipped = 0
        errors = 0
        
        for prop in properties:
            try:
                # Validate required fields (bathrooms optional as it may not be in DB yet)
                if not all([prop.location, prop.area_sqft, prop.bedrooms, 
                           prop.property_type, prop.price]):
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(f'Skipped Property #{prop.property_id} - Missing required fields')
                    )
                    continue
                
                # Get bathrooms safely (may not exist in DB)
                bathrooms = getattr(prop, 'bathrooms', 2)  # Default to 2 if not exists
                
                # Check if already exists (avoid duplicates)
                exists = PriceDataModel.objects.filter(
                    location=prop.location,
                    area_sqft=prop.area_sqft,
                    bedrooms=prop.bedrooms,
                    property_type=prop.property_type,
                    actual_price=prop.price
                ).exists()
                
                if exists:
                    skipped += 1
                    continue
                
                # Create training data entry
                PriceDataModel.objects.create(
                    location=prop.location,
                    area_sqft=prop.area_sqft,
                    bedrooms=prop.bedrooms,
                    bathrooms=bathrooms,
                    property_type=prop.property_type,
                    actual_price=prop.price
                )
                
                added += 1
                
                # Progress indicator
                if added % 10 == 0:
                    self.stdout.write(f'Processed {added}/{total}...')
            
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'Error processing Property #{prop.property_id}: {str(e)}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'✅ Successfully added: {added} entries'))
        self.stdout.write(self.style.WARNING(f'⏭️  Skipped (duplicates/incomplete): {skipped}'))
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errors: {errors}'))
        self.stdout.write('='*60)
        
        # Data quality report
        if added > 0:
            self.stdout.write('\n📊 Data Quality Report:')
            
            total_data = PriceDataModel.objects.count()
            self.stdout.write(f'Total training samples: {total_data}')
            
            # Breakdown by location
            from django.db.models import Count
            by_location = PriceDataModel.objects.values('location').annotate(
                count=Count('data_id')
            ).order_by('-count')[:10]
            
            self.stdout.write('\nTop Locations:')
            for item in by_location:
                self.stdout.write(f"  - {item['location']}: {item['count']} samples")
            
            # Breakdown by property type
            by_type = PriceDataModel.objects.values('property_type').annotate(
                count=Count('data_id')
            ).order_by('-count')
            
            self.stdout.write('\nProperty Types:')
            for item in by_type:
                self.stdout.write(f"  - {item['property_type']}: {item['count']} samples")
            
            # Recommendations
            self.stdout.write('\n💡 Recommendations:')
            if total_data < 50:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  Only {total_data} samples available. Add more for better predictions (recommended: 100+)'
                ))
            elif total_data < 100:
                self.stdout.write(self.style.WARNING(
                    f'  ⚡ {total_data} samples available. Good start! Add more for higher accuracy (recommended: 100+)'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ {total_data} samples available. Great! You can now use AI price predictions confidently.'
                ))
        
        self.stdout.write('\n' + self.style.SUCCESS('✅ Population complete!'))
