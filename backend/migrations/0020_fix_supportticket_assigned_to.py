# Generated migration to fix assigned_to field in SupportTicket model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0019_remove_supportticket_assigned_to_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='supportticket',
            name='assigned_to',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_tickets',
                to='backend.estateuser'
            ),
        ),
    ]
