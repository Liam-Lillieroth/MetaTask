# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cflows', '0010_add_transition_customization'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflow',
            name='field_config',
            field=models.JSONField(blank=True, default=dict, help_text='Configuration for which standard fields to show/hide/replace'),
        ),
    ]
