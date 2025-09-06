import django.dispatch

# Signal sent when a booking status changes
booking_status_changed = django.dispatch.Signal()

# Signal sent when a new booking is created
booking_created = django.dispatch.Signal()

# Signal sent when a booking is cancelled
booking_cancelled = django.dispatch.Signal()

# Signal sent when a resource is updated
resource_updated = django.dispatch.Signal()
