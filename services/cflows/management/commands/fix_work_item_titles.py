"""
Django management command to fix work item titles from replacement fields
"""

from django.core.management.base import BaseCommand
from services.cflows.models import WorkItem, WorkItemCustomFieldValue


class Command(BaseCommand):
    help = 'Fix work item titles by transferring replacement field values to the title field'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Find work items that have replacement_title data but empty or default titles
        work_items = WorkItem.objects.filter(data__has_key='replacement_title')
        
        updated_count = 0
        
        for work_item in work_items:
            replacement_title_data = work_item.data.get('replacement_title', {})
            custom_field_id = replacement_title_data.get('custom_field_id')
            replacement_value = replacement_title_data.get('value')
            
            if custom_field_id and replacement_value:
                # Check if we should update the title
                # Update if title is empty, or if it's a default/placeholder value
                should_update = (
                    not work_item.title or 
                    work_item.title.strip() == '' or
                    work_item.title in ['New Work Item', 'Work Item', 'Untitled']
                )
                
                if should_update:
                    if dry_run:
                        self.stdout.write(
                            f'WOULD UPDATE: Work Item {work_item.id} '
                            f'title from "{work_item.title}" to "{replacement_value}"'
                        )
                    else:
                        old_title = work_item.title
                        work_item.title = replacement_value
                        work_item.save(update_fields=['title'])
                        
                        self.stdout.write(
                            f'UPDATED: Work Item {work_item.id} '
                            f'title from "{old_title}" to "{replacement_value}"'
                        )
                    
                    updated_count += 1
                else:
                    if dry_run:
                        self.stdout.write(
                            f'SKIP: Work Item {work_item.id} already has proper title: "{work_item.title}"'
                        )
        
        if updated_count > 0:
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'Would update {updated_count} work items')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully updated {updated_count} work items')
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('No work items needed title updates')
            )
