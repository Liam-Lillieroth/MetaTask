# Manual migration to clean up after moving models to core

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('cflows', '0001_initial'),
        ('core', '0003_migrate_data_from_cflows'),
    ]

    operations = [
        # Update foreign key references to point to core models
        migrations.AlterField(
            model_name='workflow',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflows',
                to='core.organization'
            ),
        ),
        migrations.AlterField(
            model_name='workflowstep',
            name='assigned_team',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='workflow_steps',
                to='core.team'
            ),
        ),
        migrations.AlterField(
            model_name='workitem',
            name='created_by',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='created_work_items',
                to='core.userprofile'
            ),
        ),
        migrations.AlterField(
            model_name='workitem',
            name='current_assignee',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_work_items',
                to='core.userprofile'
            ),
        ),
        migrations.AlterField(
            model_name='workitemhistory',
            name='changed_by',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='work_item_changes',
                to='core.userprofile'
            ),
        ),
        migrations.AlterField(
            model_name='teambooking',
            name='team',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='bookings',
                to='core.team'
            ),
        ),
        migrations.AlterField(
            model_name='teambooking',
            name='job_type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='core.jobtype'
            ),
        ),
        migrations.AlterField(
            model_name='teambooking',
            name='booked_by',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='created_bookings',
                to='core.userprofile'
            ),
        ),
        migrations.AlterField(
            model_name='teambooking',
            name='completed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='completed_bookings',
                to='core.userprofile'
            ),
        ),
        migrations.AlterField(
            model_name='teambooking',
            name='assigned_members',
            field=models.ManyToManyField(
                blank=True,
                related_name='team_bookings',
                to='core.userprofile'
            ),
        ),
        
        # Drop the old tables that have been moved to core
        migrations.RunSQL(
            "DROP TABLE IF EXISTS cflows_organization CASCADE;",
            migrations.RunSQL.noop
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS cflows_userprofile CASCADE;", 
            migrations.RunSQL.noop
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS cflows_team CASCADE;",
            migrations.RunSQL.noop
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS cflows_jobtype CASCADE;",
            migrations.RunSQL.noop
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS cflows_calendarevent CASCADE;",
            migrations.RunSQL.noop
        ),
    ]
