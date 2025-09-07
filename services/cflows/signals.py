"""
Django signals to automatically sync CFlows team bookings with scheduling service
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver, Signal

from .models import TeamBooking
from .scheduling_integration import CFlowsSchedulingIntegration


# Custom signal for scheduling booking status changes
booking_status_changed = Signal()


@receiver(post_save, sender=TeamBooking)
def sync_team_booking_on_save(sender, instance, created, **kwargs):
    """Sync team booking with scheduling service when saved"""
    if created:
        # Create new scheduling booking
        CFlowsSchedulingIntegration.create_scheduling_booking(instance)
    else:
        # Update existing scheduling booking
        CFlowsSchedulingIntegration.update_scheduling_booking(instance)


@receiver(post_delete, sender=TeamBooking)
def sync_team_booking_on_delete(sender, instance, **kwargs):
    """Remove corresponding scheduling booking when team booking is deleted"""
    CFlowsSchedulingIntegration.delete_scheduling_booking(instance)


@receiver(booking_status_changed)
def handle_scheduling_booking_completion(sender, booking, event, **kwargs):
    """Handle completion of scheduling bookings by updating corresponding CFlows team booking"""
    if event == 'completed' and booking.source_service == 'cflows':
        CFlowsSchedulingIntegration.handle_scheduling_booking_completion(booking)
