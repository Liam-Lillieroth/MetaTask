# Fix organization references after moving Organization to core

from django.db import migrations

def fix_organization_references(apps, schema_editor):
    """
    Update organization_id references in CFlows tables to point to core organizations
    """
    from django.db import connection
    
    cursor = connection.cursor()
    
    # Map old organization IDs to new ones
    cursor.execute("""
        SELECT old_org.id as old_id, core_org.id as new_id 
        FROM cflows_organization old_org 
        JOIN core_organization core_org ON old_org.name = core_org.name
    """)
    org_mapping = dict(cursor.fetchall())
    print(f"Organization mapping: {org_mapping}")
    
    # Update workflow table
    for old_id, new_id in org_mapping.items():
        cursor.execute("""
            UPDATE cflows_workflow 
            SET organization_id = %s 
            WHERE organization_id = %s
        """, [new_id, old_id])
        print(f"Updated workflow organization references from {old_id} to {new_id}")

def reverse_fix_organization_references(apps, schema_editor):
    """
    Reverse the organization reference fixes
    """
    pass  # We don't need to reverse this

class Migration(migrations.Migration):

    dependencies = [
        ('cflows', '0002_alter_jobtype_unique_together_and_more'),
        ('core', '0003_migrate_data_from_cflows'),
    ]

    operations = [
        migrations.RunPython(fix_organization_references, reverse_fix_organization_references),
    ]
