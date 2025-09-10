# Generated manually to fix owner_team nullable issue

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cflows", "0014_workflow_allowed_edit_teams_and_more"),
        ("core", "0009_add_sub_teams"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workflow",
            name="owner_team",
            field=models.ForeignKey(
                help_text="The team that owns and manages this workflow",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="owned_workflows",
                to="core.team",
            ),
        ),
    ]
