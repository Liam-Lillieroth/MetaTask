from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Organization, UserProfile, Team, JobType
from services.cflows.models import WorkflowTemplate, Workflow, WorkflowStep, WorkflowTransition
import json


class Command(BaseCommand):
    help = 'Set up sample CFlows workflow templates and data'

    def handle(self, *args, **options):
        self.stdout.write('Setting up CFlows sample data...')
        
        with transaction.atomic():
            # Create sample workflow templates
            self.create_workflow_templates()
            
            # Create sample workflows if there are organizations
            organizations = Organization.objects.all()[:3]  # Limit to first 3 orgs
            for org in organizations:
                self.create_sample_workflows(org)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up CFlows sample data!')
        )
    
    def create_workflow_templates(self):
        """Create sample workflow templates"""
        templates_data = [
            {
                'name': 'Vehicle Processing Workflow',
                'category': 'Automotive',
                'description': 'Complete vehicle lifecycle from acquisition to sale',
                'template_data': {
                    'steps': [
                        {
                            'id': 'intake',
                            'name': 'Vehicle Intake',
                            'description': 'Initial vehicle assessment and documentation',
                            'order': 1,
                            'requires_booking': True,
                            'estimated_duration_hours': 1.0,
                            'data_schema': {
                                'vin': {'type': 'string', 'required': True},
                                'mileage': {'type': 'number', 'required': True},
                                'condition': {'type': 'select', 'options': ['Excellent', 'Good', 'Fair', 'Poor']}
                            }
                        },
                        {
                            'id': 'inspection',
                            'name': 'Test & Inspect',
                            'description': 'Comprehensive mechanical and cosmetic inspection',
                            'order': 2,
                            'requires_booking': True,
                            'estimated_duration_hours': 2.5,
                            'data_schema': {
                                'mechanical_issues': {'type': 'text'},
                                'cosmetic_issues': {'type': 'text'},
                                'estimated_repair_cost': {'type': 'number'}
                            }
                        },
                        {
                            'id': 'repair',
                            'name': 'Repair',
                            'description': 'Address identified mechanical and cosmetic issues',
                            'order': 3,
                            'requires_booking': True,
                            'estimated_duration_hours': 8.0,
                            'data_schema': {
                                'repairs_completed': {'type': 'text'},
                                'parts_used': {'type': 'text'},
                                'actual_cost': {'type': 'number'}
                            }
                        },
                        {
                            'id': 'detail',
                            'name': 'Detail & Clean',
                            'description': 'Professional cleaning and detailing',
                            'order': 4,
                            'requires_booking': True,
                            'estimated_duration_hours': 3.0,
                        },
                        {
                            'id': 'photography',
                            'name': 'Photography',
                            'description': 'Professional vehicle photography for listing',
                            'order': 5,
                            'requires_booking': True,
                            'estimated_duration_hours': 1.0,
                        },
                        {
                            'id': 'listing',
                            'name': 'Create Listing',
                            'description': 'Create online listing with photos and details',
                            'order': 6,
                            'estimated_duration_hours': 0.5,
                            'data_schema': {
                                'listing_price': {'type': 'number', 'required': True},
                                'listing_platforms': {'type': 'multiselect', 'options': ['AutoTrader', 'Cars.com', 'CarGurus', 'Facebook']}
                            }
                        },
                        {
                            'id': 'sold',
                            'name': 'Vehicle Sold',
                            'description': 'Vehicle has been sold to customer',
                            'order': 7,
                            'is_terminal': True,
                            'data_schema': {
                                'sale_price': {'type': 'number', 'required': True},
                                'customer_info': {'type': 'text'},
                                'payment_method': {'type': 'select', 'options': ['Cash', 'Finance', 'Trade']}
                            }
                        }
                    ],
                    'transitions': [
                        {'from_step_id': 'intake', 'to_step_id': 'inspection', 'label': 'Ready for Inspection'},
                        {'from_step_id': 'inspection', 'to_step_id': 'repair', 'label': 'Needs Repair'},
                        {'from_step_id': 'inspection', 'to_step_id': 'detail', 'label': 'Skip Repair'},
                        {'from_step_id': 'repair', 'to_step_id': 'detail', 'label': 'Repairs Complete'},
                        {'from_step_id': 'detail', 'to_step_id': 'photography', 'label': 'Ready for Photos'},
                        {'from_step_id': 'photography', 'to_step_id': 'listing', 'label': 'Photos Complete'},
                        {'from_step_id': 'listing', 'to_step_id': 'sold', 'label': 'Vehicle Sold'},
                    ]
                }
            },
            {
                'name': 'Service Request Workflow',
                'category': 'Service Management',
                'description': 'Client service delivery from request to completion',
                'template_data': {
                    'steps': [
                        {
                            'id': 'submitted',
                            'name': 'Request Submitted',
                            'description': 'Initial service request received',
                            'order': 1,
                            'data_schema': {
                                'client_name': {'type': 'string', 'required': True},
                                'service_type': {'type': 'select', 'options': ['Consultation', 'Implementation', 'Support', 'Training']},
                                'urgency': {'type': 'select', 'options': ['Low', 'Medium', 'High', 'Critical']}
                            }
                        },
                        {
                            'id': 'review',
                            'name': 'Initial Review',
                            'description': 'Review and assess the service request',
                            'order': 2,
                            'requires_booking': True,
                            'estimated_duration_hours': 1.0,
                        },
                        {
                            'id': 'approved',
                            'name': 'Approved',
                            'description': 'Service request approved and ready for work',
                            'order': 3,
                            'data_schema': {
                                'approved_budget': {'type': 'number'},
                                'estimated_completion': {'type': 'date'}
                            }
                        },
                        {
                            'id': 'in_progress',
                            'name': 'In Progress',
                            'description': 'Service work is being performed',
                            'order': 4,
                            'requires_booking': True,
                            'estimated_duration_hours': 4.0,
                        },
                        {
                            'id': 'qa',
                            'name': 'Quality Assurance',
                            'description': 'Review and test completed work',
                            'order': 5,
                            'requires_booking': True,
                            'estimated_duration_hours': 1.0,
                        },
                        {
                            'id': 'delivered',
                            'name': 'Delivered',
                            'description': 'Service completed and delivered to client',
                            'order': 6,
                            'is_terminal': True,
                            'data_schema': {
                                'client_satisfaction': {'type': 'select', 'options': ['Very Satisfied', 'Satisfied', 'Neutral', 'Dissatisfied']},
                                'delivery_notes': {'type': 'text'}
                            }
                        }
                    ],
                    'transitions': [
                        {'from_step_id': 'submitted', 'to_step_id': 'review', 'label': 'Begin Review'},
                        {'from_step_id': 'review', 'to_step_id': 'approved', 'label': 'Approve'},
                        {'from_step_id': 'review', 'to_step_id': 'submitted', 'label': 'Request More Info'},
                        {'from_step_id': 'approved', 'to_step_id': 'in_progress', 'label': 'Start Work'},
                        {'from_step_id': 'in_progress', 'to_step_id': 'qa', 'label': 'Ready for QA'},
                        {'from_step_id': 'qa', 'to_step_id': 'delivered', 'label': 'Approve & Deliver'},
                        {'from_step_id': 'qa', 'to_step_id': 'in_progress', 'label': 'Needs Revision'},
                    ]
                }
            },
            {
                'name': 'Project Delivery Workflow',
                'category': 'Project Management',
                'description': 'Client project from initiation to completion',
                'template_data': {
                    'steps': [
                        {
                            'id': 'proposal',
                            'name': 'Proposal',
                            'description': 'Initial project proposal and scoping',
                            'order': 1,
                            'estimated_duration_hours': 2.0,
                        },
                        {
                            'id': 'planning',
                            'name': 'Planning',
                            'description': 'Detailed project planning and resource allocation',
                            'order': 2,
                            'requires_booking': True,
                            'estimated_duration_hours': 4.0,
                        },
                        {
                            'id': 'execution',
                            'name': 'Execution',
                            'description': 'Project implementation and development',
                            'order': 3,
                            'requires_booking': True,
                            'estimated_duration_hours': 40.0,
                        },
                        {
                            'id': 'review',
                            'name': 'Review',
                            'description': 'Project review and quality check',
                            'order': 4,
                            'requires_booking': True,
                            'estimated_duration_hours': 3.0,
                        },
                        {
                            'id': 'delivered',
                            'name': 'Delivered',
                            'description': 'Project completed and delivered to client',
                            'order': 5,
                            'is_terminal': True,
                        }
                    ],
                    'transitions': [
                        {'from_step_id': 'proposal', 'to_step_id': 'planning', 'label': 'Proposal Accepted'},
                        {'from_step_id': 'planning', 'to_step_id': 'execution', 'label': 'Begin Execution'},
                        {'from_step_id': 'execution', 'to_step_id': 'review', 'label': 'Ready for Review'},
                        {'from_step_id': 'review', 'to_step_id': 'delivered', 'label': 'Approve & Deliver'},
                        {'from_step_id': 'review', 'to_step_id': 'execution', 'label': 'Needs Revision'},
                    ]
                }
            }
        ]
        
        for template_data in templates_data:
            template, created = WorkflowTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults={
                    'category': template_data['category'],
                    'description': template_data['description'],
                    'is_public': True,
                    'template_data': template_data['template_data'],
                    'usage_count': 0
                }
            )
            if created:
                self.stdout.write(f'  Created template: {template.name}')

    def create_sample_workflows(self, organization):
        """Create sample workflows for an organization"""
        # Create a simple demo workflow
        workflow, created = Workflow.objects.get_or_create(
            organization=organization,
            name='Demo Content Review',
            defaults={
                'description': 'Simple content review and approval workflow',
                'is_active': True,
                'auto_assign': True,
            }
        )
        
        if created:
            # Create workflow steps
            steps_data = [
                {
                    'name': 'Draft',
                    'description': 'Initial content draft creation',
                    'order': 1,
                    'estimated_duration_hours': 2.0,
                },
                {
                    'name': 'Review',
                    'description': 'Content review and feedback',
                    'order': 2,
                    'requires_booking': True,
                    'estimated_duration_hours': 1.0,
                },
                {
                    'name': 'Approved',
                    'description': 'Content approved and ready for publication',
                    'order': 3,
                    'is_terminal': True,
                },
            ]
            
            step_objects = []
            for step_data in steps_data:
                step = WorkflowStep.objects.create(
                    workflow=workflow,
                    **step_data
                )
                step_objects.append(step)
            
            # Create transitions
            transitions_data = [
                {'from': 0, 'to': 1, 'label': 'Submit for Review'},
                {'from': 1, 'to': 2, 'label': 'Approve'},
                {'from': 1, 'to': 0, 'label': 'Request Revisions'},
            ]
            
            for trans_data in transitions_data:
                WorkflowTransition.objects.create(
                    from_step=step_objects[trans_data['from']],
                    to_step=step_objects[trans_data['to']],
                    label=trans_data['label']
                )
            
            self.stdout.write(f'  Created workflow for {organization.name}: {workflow.name}')
