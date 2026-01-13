# Generated migration to add missing category and priority fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0016_add_token_and_notifications'),
    ]

    operations = [
        migrations.AddField(
            model_name='supportticket',
            name='category',
            field=models.CharField(default='general', max_length=50),
        ),
        migrations.AddField(
            model_name='supportticket',
            name='priority',
            field=models.CharField(default='medium', max_length=20),
        ),
        migrations.AddField(
            model_name='supportticket',
            name='assigned_to_id',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='supportticket',
            name='resolved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
