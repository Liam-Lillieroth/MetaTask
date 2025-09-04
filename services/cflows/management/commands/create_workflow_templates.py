from django.core.management.base import BaseCommand
from django.utils import timezone
from services.cflows.models import WorkflowTemplate
import json


class Command(BaseCommand):
    help = 'Create sample workflow templates for various business processes'

    def handle(self, *args, **options):
        self.stdout.write("Creating workflow templates...")
        
        # Car Dealership Template
        car_dealership_template = {
            "name": "Vehicle Processing Workflow",
            "description": "Complete vehicle processing from acquisition to sale",
            "category": "Automotive",
            "is_public": True,
            "template_data": {
                "steps": [
                    {
                        "id": "intake",
                        "name": "Vehicle Intake",
                        "description": "Initial vehicle intake and documentation",
                        "order": 1,
                        "requires_booking": False,
                        "estimated_duration_hours": 0.5,
                        "is_terminal": False
                    },
                    {
                        "id": "inspect",
                        "name": "Test & Inspect",
                        "description": "Complete vehicle testing and inspection",
                        "order": 2,
                        "requires_booking": True,
                        "estimated_duration_hours": 2.0,
                        "is_terminal": False
                    },
                    {
                        "id": "assess",
                        "name": "Repair Assessment",
                        "description": "Assess required repairs",
                        "order": 3,
                        "requires_booking": False,
                        "estimated_duration_hours": 1.0,
                        "is_terminal": False
                    },
                    {
                        "id": "mechanical",
                        "name": "Mechanical Repairs",
                        "description": "Complete mechanical repairs",
                        "order": 4,
                        "requires_booking": True,
                        "estimated_duration_hours": 4.0,
                        "is_terminal": False
                    },
                    {
                        "id": "bodywork",
                        "name": "Body Work",
                        "description": "Complete body work and painting",
                        "order": 5,
                        "requires_booking": True,
                        "estimated_duration_hours": 6.0,
                        "is_terminal": False
                    },
                    {
                        "id": "final_inspect",
                        "name": "Final Inspection",
                        "description": "Final quality inspection",
                        "order": 6,
                        "requires_booking": True,
                        "estimated_duration_hours": 1.5,
                        "is_terminal": False
                    },
                    {
                        "id": "detailing",
                        "name": "Detailing",
                        "description": "Complete vehicle detailing",
                        "order": 7,
                        "requires_booking": True,
                        "estimated_duration_hours": 3.0,
                        "is_terminal": False
                    },
                    {
                        "id": "photography",
                        "name": "Photography",
                        "description": "Professional vehicle photography",
                        "order": 8,
                        "requires_booking": True,
                        "estimated_duration_hours": 1.0,
                        "is_terminal": False
                    },
                    {
                        "id": "listing",
                        "name": "Listing Created",
                        "description": "Vehicle listed for sale",
                        "order": 9,
                        "requires_booking": False,
                        "estimated_duration_hours": 0.5,
                        "is_terminal": False
                    },
                    {
                        "id": "sold",
                        "name": "Sold",
                        "description": "Vehicle sold to customer",
                        "order": 10,
                        "requires_booking": False,
                        "estimated_duration_hours": 0,
                        "is_terminal": True
                    }
                ],
                "transitions": [
                    {"from_step_id": "intake", "to_step_id": "inspect", "label": "Ready for Inspection"},
                    {"from_step_id": "inspect", "to_step_id": "assess", "label": "Needs Repair"},
                    {"from_step_id": "inspect", "to_step_id": "final_inspect", "label": "No Repairs Needed"},
                    {"from_step_id": "assess", "to_step_id": "mechanical", "label": "Mechanical Issues"},
                    {"from_step_id": "assess", "to_step_id": "bodywork", "label": "Body Issues"},
                    {"from_step_id": "assess", "to_step_id": "final_inspect", "label": "Minor Issues Only"},
                    {"from_step_id": "mechanical", "to_step_id": "final_inspect", "label": "Repairs Complete"},
                    {"from_step_id": "bodywork", "to_step_id": "final_inspect", "label": "Body Work Complete"},
                    {"from_step_id": "final_inspect", "to_step_id": "detailing", "label": "Passed"},
                    {"from_step_id": "final_inspect", "to_step_id": "assess", "label": "Failed - Needs More Work"},
                    {"from_step_id": "detailing", "to_step_id": "photography", "label": "Ready for Photos"},
                    {"from_step_id": "photography", "to_step_id": "listing", "label": "Photos Complete"},
                    {"from_step_id": "listing", "to_step_id": "sold", "label": "Customer Purchase"}
                ]
            }
        }
        
        # Service Request Template
        service_request_template = {
            "name": "Service Request Workflow",
            "description": "Client service delivery from request to completion",
            "category": "Service",
            "is_public": True,
            "template_data": {
                "steps": [
                    {
                        "id": "submitted",
                        "name": "Submitted",
                        "description": "Service request submitted by client",
                        "order": 1,
                        "requires_booking": False,
                        "is_terminal": False
                    },
                    {
                        "id": "review",
                        "name": "Review",
                        "description": "Initial review and assessment",
                        "order": 2,
                        "requires_booking": False,
                        "estimated_duration_hours": 1.0,
                        "is_terminal": False
                    },
                    {
                        "id": "approved",
                        "name": "Approved",
                        "description": "Service request approved",
                        "order": 3,
                        "requires_booking": False,
                        "is_terminal": False
                    },
                    {
                        "id": "in_progress",
                        "name": "In Progress",
                        "description": "Service work in progress",
                        "order": 4,
                        "requires_booking": True,
                        "estimated_duration_hours": 4.0,
                        "is_terminal": False
                    },
                    {
                        "id": "qa",
                        "name": "Quality Assurance",
                        "description": "Quality check and testing",
                        "order": 5,
                        "requires_booking": True,
                        "estimated_duration_hours": 1.0,
                        "is_terminal": False
                    },
                    {
                        "id": "delivered",
                        "name": "Delivered",
                        "description": "Service delivered to client",
                        "order": 6,
                        "requires_booking": False,
                        "is_terminal": True
                    }
                ],
                "transitions": [
                    {"from_step_id": "submitted", "to_step_id": "review", "label": "Start Review"},
                    {"from_step_id": "review", "to_step_id": "approved", "label": "Approve"},
                    {"from_step_id": "review", "to_step_id": "submitted", "label": "Request Changes"},
                    {"from_step_id": "approved", "to_step_id": "in_progress", "label": "Begin Work"},
                    {"from_step_id": "in_progress", "to_step_id": "qa", "label": "Ready for QA"},
                    {"from_step_id": "qa", "to_step_id": "delivered", "label": "Passed QA"},
                    {"from_step_id": "qa", "to_step_id": "in_progress", "label": "Failed QA"}
                ]
            }
        }
        
        # Manufacturing Template
        manufacturing_template = {
            "name": "Product Manufacturing",
            "description": "Product manufacturing from order to shipment",
            "category": "Manufacturing",
            "is_public": True,
            "template_data": {
                "steps": [
                    {
                        "id": "order",
                        "name": "Order Received",
                        "description": "Manufacturing order received",
                        "order": 1,
                        "requires_booking": False,
                        "is_terminal": False
                    },
                    {
                        "id": "design",
                        "name": "Design",
                        "description": "Product design and specifications",
                        "order": 2,
                        "requires_booking": True,
                        "estimated_duration_hours": 8.0,
                        "is_terminal": False
                    },
                    {
                        "id": "production",
                        "name": "Production",
                        "description": "Manufacturing and production",
                        "order": 3,
                        "requires_booking": True,
                        "estimated_duration_hours": 16.0,
                        "is_terminal": False
                    },
                    {
                        "id": "assembly",
                        "name": "Assembly",
                        "description": "Product assembly",
                        "order": 4,
                        "requires_booking": True,
                        "estimated_duration_hours": 4.0,
                        "is_terminal": False
                    },
                    {
                        "id": "qc",
                        "name": "Quality Control",
                        "description": "Quality control testing",
                        "order": 5,
                        "requires_booking": True,
                        "estimated_duration_hours": 2.0,
                        "is_terminal": False
                    },
                    {
                        "id": "package",
                        "name": "Packaging",
                        "description": "Product packaging",
                        "order": 6,
                        "requires_booking": True,
                        "estimated_duration_hours": 1.0,
                        "is_terminal": False
                    },
                    {
                        "id": "ship",
                        "name": "Shipped",
                        "description": "Product shipped to customer",
                        "order": 7,
                        "requires_booking": False,
                        "is_terminal": True
                    }
                ],
                "transitions": [
                    {"from_step_id": "order", "to_step_id": "design", "label": "Start Design"},
                    {"from_step_id": "design", "to_step_id": "production", "label": "Design Approved"},
                    {"from_step_id": "design", "to_step_id": "order", "label": "Design Rejected"},
                    {"from_step_id": "production", "to_step_id": "assembly", "label": "Production Complete"},
                    {"from_step_id": "assembly", "to_step_id": "qc", "label": "Assembly Complete"},
                    {"from_step_id": "qc", "to_step_id": "package", "label": "QC Passed"},
                    {"from_step_id": "qc", "to_step_id": "production", "label": "QC Failed"},
                    {"from_step_id": "package", "to_step_id": "ship", "label": "Ready to Ship"}
                ]
            }
        }
        
        # Project Delivery Template
        project_template = {
            "name": "Project Delivery",
            "description": "Client project from initiation to completion",
            "category": "Project Management",
            "is_public": True,
            "template_data": {
                "steps": [
                    {
                        "id": "proposal",
                        "name": "Proposal",
                        "description": "Initial project proposal",
                        "order": 1,
                        "requires_booking": False,
                        "is_terminal": False
                    },
                    {
                        "id": "planning",
                        "name": "Planning",
                        "description": "Project planning and scoping",
                        "order": 2,
                        "requires_booking": True,
                        "estimated_duration_hours": 8.0,
                        "is_terminal": False
                    },
                    {
                        "id": "execute",
                        "name": "Execution",
                        "description": "Project execution phase",
                        "order": 3,
                        "requires_booking": True,
                        "estimated_duration_hours": 40.0,
                        "is_terminal": False
                    },
                    {
                        "id": "review",
                        "name": "Review",
                        "description": "Project review and testing",
                        "order": 4,
                        "requires_booking": True,
                        "estimated_duration_hours": 8.0,
                        "is_terminal": False
                    },
                    {
                        "id": "delivered",
                        "name": "Delivered",
                        "description": "Project delivered to client",
                        "order": 5,
                        "requires_booking": False,
                        "is_terminal": True
                    }
                ],
                "transitions": [
                    {"from_step_id": "proposal", "to_step_id": "planning", "label": "Approved"},
                    {"from_step_id": "planning", "to_step_id": "execute", "label": "Plan Approved"},
                    {"from_step_id": "planning", "to_step_id": "proposal", "label": "Needs Revision"},
                    {"from_step_id": "execute", "to_step_id": "review", "label": "Ready for Review"},
                    {"from_step_id": "review", "to_step_id": "delivered", "label": "Approved"},
                    {"from_step_id": "review", "to_step_id": "execute", "label": "Needs Changes"}
                ]
            }
        }
        
        templates = [
            car_dealership_template,
            service_request_template,
            manufacturing_template,
            project_template
        ]
        
        created_count = 0
        for template_data in templates:
            template, created = WorkflowTemplate.objects.get_or_create(
                name=template_data["name"],
                category=template_data["category"],
                defaults=template_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"✓ Created template: {template.name} ({template.category})")
            else:
                self.stdout.write(f"✓ Template already exists: {template.name}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Successfully created {created_count} workflow templates!\n\n'
                f'Available templates:\n'
                f'• Vehicle Processing Workflow (Automotive)\n'
                f'• Service Request Workflow (Service)\n'
                f'• Product Manufacturing (Manufacturing)\n'
                f'• Project Delivery (Project Management)\n\n'
                f'These templates are now available when creating new workflows.\n'
            )
        )
