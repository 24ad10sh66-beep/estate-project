import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateproject.settings')
django.setup()

from backend.models import Property

props = Property.objects.all()
print(f'📊 Property Status Analysis:')
print(f'   Total properties: {props.count()}')
print(f'   Available: {Property.objects.filter(status="Available").count()}')
print(f'\n📋 Status breakdown:')
for status in Property.objects.values_list('status', flat=True).distinct():
    count = Property.objects.filter(status=status).count()
    print(f'   - "{status}": {count}')

print(f'\n🏠 First 10 properties:')
for prop in Property.objects.all()[:10]:
    print(f'   - ID:{prop.property_id}, Title:"{prop.title}", Status:"{prop.status}"')
