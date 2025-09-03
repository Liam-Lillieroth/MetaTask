# Generated migration to move data from CFlows to Core models

from django.db import migrations, models
import uuid

def migrate_data_from_cflows(apps, schema_editor):
    """
    Move data from CFlows models to Core models
    """
    # Get old CFlows models
    CFlowsOrganization = apps.get_model('cflows', 'Organization')
    CFlowsUserProfile = apps.get_model('cflows', 'UserProfile')  
    CFlowsTeam = apps.get_model('cflows', 'Team')
    CFlowsJobType = apps.get_model('cflows', 'JobType')
    CFlowsCalendarEvent = apps.get_model('cflows', 'CalendarEvent')
    
    # Get new Core models
    CoreOrganization = apps.get_model('core', 'Organization')
    CoreUserProfile = apps.get_model('core', 'UserProfile')
    CoreTeam = apps.get_model('core', 'Team')  
    CoreJobType = apps.get_model('core', 'JobType')
    CoreCalendarEvent = apps.get_model('core', 'CalendarEvent')
    
    # Migrate Organizations
    org_mapping = {}
    for old_org in CFlowsOrganization.objects.all():
        new_org, created = CoreOrganization.objects.get_or_create(
            name=old_org.name,
            defaults={
                'description': old_org.description,
                'is_active': old_org.is_active,
                'created_at': old_org.created_at,
                'updated_at': old_org.updated_at,
            }
        )
        org_mapping[old_org.id] = new_org.id
        print(f"Migrated organization: {old_org.name}")
    
    # Migrate UserProfiles
    profile_mapping = {}
    for old_profile in CFlowsUserProfile.objects.all():
        new_profile, created = CoreUserProfile.objects.get_or_create(
            user_id=old_profile.user_id,
            organization_id=org_mapping[old_profile.organization_id],
            defaults={
                'title': getattr(old_profile, 'title', ''),
                'department': '',  # New field, not in old model
                'location': getattr(old_profile, 'location', ''),
                'timezone': getattr(old_profile, 'timezone', 'UTC'),
                'bio': getattr(old_profile, 'bio', ''),
                'phone': '',  # New field, not in old model
                'mobile': '',  # New field, not in old model
                'is_organization_admin': getattr(old_profile, 'is_organization_admin', False),
                'has_staff_panel_access': getattr(old_profile, 'has_staff_panel_access', False),
                'email_notifications': True,  # New field with default
                'desktop_notifications': True,  # New field with default
                'is_active': True,  # New field with default
                'created_at': old_profile.created_at,
                'updated_at': old_profile.updated_at,
            }
        )
        profile_mapping[old_profile.id] = new_profile.id
        print(f"Migrated user profile: {old_profile.user}")
    
    # Migrate JobTypes
    jobtype_mapping = {}
    for old_jobtype in CFlowsJobType.objects.all():
        new_jobtype, created = CoreJobType.objects.get_or_create(
            name=old_jobtype.name,
            organization_id=org_mapping[old_jobtype.organization_id],
            defaults={
                'description': old_jobtype.description,
                'default_duration_hours': old_jobtype.default_duration_hours,
                'color': old_jobtype.color,
                'is_active': old_jobtype.is_active,
                'created_at': old_jobtype.created_at,
            }
        )
        jobtype_mapping[old_jobtype.id] = new_jobtype.id
        print(f"Migrated job type: {old_jobtype.name}")
    
    # Migrate Teams
    team_mapping = {}
    for old_team in CFlowsTeam.objects.all():
        new_team, created = CoreTeam.objects.get_or_create(
            name=old_team.name,
            organization_id=org_mapping[old_team.organization_id],
            defaults={
                'description': old_team.description,
                'is_active': old_team.is_active,
                'created_at': old_team.created_at,
                'updated_at': old_team.updated_at,
            }
        )
        team_mapping[old_team.id] = new_team.id
        
        # Migrate team members
        for old_member in old_team.members.all():
            if old_member.id in profile_mapping:
                new_profile = CoreUserProfile.objects.get(id=profile_mapping[old_member.id])
                new_team.members.add(new_profile)
        
        print(f"Migrated team: {old_team.name}")
    
    # Migrate CalendarEvents
    for old_event in CFlowsCalendarEvent.objects.all():
        new_event, created = CoreCalendarEvent.objects.get_or_create(
            title=old_event.title,
            start_time=old_event.start_time,
            end_time=old_event.end_time,
            organization_id=org_mapping[old_event.organization_id],
            defaults={
                'uuid': old_event.uuid,
                'event_type': old_event.event_type,
                'description': old_event.description,
                'location': getattr(old_event, 'location', ''),
                'is_all_day': old_event.is_all_day,
                'timezone': getattr(old_event, 'timezone', 'UTC'),
                'created_by_id': profile_mapping.get(old_event.created_by_id),
                'related_team_id': team_mapping.get(old_event.related_team_id) if old_event.related_team_id else None,
                'content_type': getattr(old_event, 'content_type', ''),
                'object_id': getattr(old_event, 'object_id', ''),
                'color': old_event.color,
                'is_recurring': getattr(old_event, 'is_recurring', False),
                'recurrence_pattern': getattr(old_event, 'recurrence_pattern', {}),
                'is_cancelled': getattr(old_event, 'is_cancelled', False),
                'created_at': old_event.created_at,
                'updated_at': old_event.updated_at,
            }
        )
        
        # Migrate invitees
        for old_invitee in old_event.invitees.all():
            if old_invitee.id in profile_mapping:
                new_profile = CoreUserProfile.objects.get(id=profile_mapping[old_invitee.id])
                new_event.invitees.add(new_profile)
        
        print(f"Migrated calendar event: {old_event.title}")

def reverse_migrate_data_from_cflows(apps, schema_editor):
    """
    Reverse migration - delete the migrated data from Core models
    """
    CoreOrganization = apps.get_model('core', 'Organization')
    CoreUserProfile = apps.get_model('core', 'UserProfile')
    CoreTeam = apps.get_model('core', 'Team')
    CoreJobType = apps.get_model('core', 'JobType')
    CoreCalendarEvent = apps.get_model('core', 'CalendarEvent')
    
    # Delete in reverse order to avoid foreign key constraints
    CoreCalendarEvent.objects.all().delete()
    CoreTeam.objects.all().delete()
    CoreJobType.objects.all().delete()
    CoreUserProfile.objects.all().delete()
    CoreOrganization.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_organization_userprofile_team_jobtype_calendarevent_and_more'),
        ('cflows', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_data_from_cflows, reverse_migrate_data_from_cflows),
    ]
