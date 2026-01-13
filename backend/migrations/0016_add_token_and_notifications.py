# Generated manually for BuyerNotification only (token_id already exists)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0015_sellernotification'),
    ]

    operations = [
        migrations.CreateModel(
            name='BuyerNotification',
            fields=[
                ('notification_id', models.AutoField(primary_key=True, serialize=False)),
                ('notification_type', models.CharField(default='ticket_resolved', max_length=50)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('buyer', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='buyer_notifications', to='backend.estateuser')),
                ('support_ticket', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='buyer_notifications', to='backend.supportticket')),
            ],
            options={
                'db_table': 'buyer_notifications',
                'ordering': ['-created_at'],
            },
        ),
    ]
