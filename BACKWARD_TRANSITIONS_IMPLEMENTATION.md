# Backward Work Item Transitions - Implementation Guide

## Overview

The backward transition feature allows authorized users to move work items back to previously visited steps in their workflow. This is useful for scenarios like:

- Fixing errors that require returning to a previous step
- Quality control rejections that need rework
- Administrative corrections to workflow progress
- Reverting incomplete or incorrect work

## Features Implemented

### 1. **Backward Transition Detection**
- Work items track their history through `WorkItemHistory` records
- System automatically identifies which previous steps are available for backward movement
- Only steps that were actually visited can be returned to (no skipping back to unvisited steps)

### 2. **Permission System**
- **Organization Admins**: Can always move items backward
- **Staff Members**: Can move items backward with staff panel access
- **Work Item Creators**: Can move their own items backward
- **Regular Users**: Cannot move items backward (by default)

### 3. **Safety Mechanisms**
- **Required Comments**: All backward movements require explanation comments
- **Confirmation Dialogs**: Users must confirm backward movements
- **Audit Trail**: All backward movements are recorded in work item history
- **Status Reset**: Items moved back from terminal steps are automatically un-completed

### 4. **User Interface**
- **Move Back Button**: Added to work item detail pages (gray button with undo icon)
- **Dropdown Menu**: Shows all available previous steps
- **Warning Indicators**: Clear indication that this is a backward/destructive action
- **Step Information**: Shows target step details before movement

## Technical Implementation

### Database Changes
No database migrations required - uses existing `WorkItemHistory` model.

### New Model Methods
Added to `WorkItem` model in `/workspaces/mediap/services/cflows/models.py`:

```python
def get_available_backward_steps(self)
def get_backward_transitions(self, user_profile=None)  
def can_move_backward(self, user_profile)
```

### New Views
Added to `/workspaces/mediap/services/cflows/transition_views.py`:

```python
def backward_transition_form(request, work_item_id, step_id)
def move_work_item_back(request, work_item_id, step_id)
```

### New URLs
Added to `/workspaces/mediap/services/cflows/urls.py`:

```python
path('work-items/<int:work_item_id>/move-back/<int:step_id>/', ...)
path('work-items/<int:work_item_id>/move-back/<int:step_id>/form/', ...)
```

### New Template
Created `/workspaces/mediap/templates/cflows/backward_transition_form.html`:
- Warning message about backward movement implications
- Required comment field with explanation
- Step information display
- Confirmation dialog

## Usage Instructions

### For Administrators
1. Navigate to any work item detail page
2. If the item has been moved through multiple steps, a **"Move Back"** button will appear (gray, with undo icon)
3. Click the button to see available previous steps
4. Select the target step to return to
5. Fill out the required comment explaining why you're moving backward
6. Confirm the action

### For Users
- Regular users cannot move items backward unless they are:
  - The original creator of the work item, OR
  - Have staff/admin permissions in the organization

### Workflow Considerations
- **History Tracking**: Every backward movement creates detailed audit records
- **Team Assignment**: Items may be reassigned when moved to steps with different assigned teams
- **Booking Requirements**: If returning to a step that requires booking, new bookings may need to be created
- **Dependencies**: Consider impact on dependent work items when moving backward

## Security and Safety

### Permission Checks
- All backward movement requests verify user permissions
- Organization scoping prevents cross-organization access
- Admin/staff role requirements for most backward movements

### Audit Trail
- Every backward movement is logged in `WorkItemHistory`
- System comments are automatically added to work items
- Required user comments explain the reason for backward movement

### Data Integrity
- Work items maintain data snapshots at each transition
- Completion status is automatically reset when moving back from terminal steps
- All related objects (comments, attachments) remain intact

## Integration with Existing Features

### Works With
- ✅ Existing forward transitions
- ✅ Work item history tracking  
- ✅ Team assignments and booking requirements
- ✅ Permission systems and organization scoping
- ✅ Comment system and activity feeds

### Visual Integration
- **Consistent Styling**: Matches existing CFlows design system
- **Icon Usage**: Uses `fas fa-undo` icon consistently
- **Color Coding**: Gray buttons to indicate caution/administrative action
- **Responsive Design**: Works on mobile and desktop

## Examples

### Example 1: Quality Control Rejection
1. Work item reaches "Quality Check" step
2. QC reviewer finds issues requiring rework
3. Admin user clicks "Move Back" → selects "In Progress" step
4. Provides comment: "Quality issues found - needs rework on specifications"
5. Item moves back, assignee is notified, work continues

### Example 2: Administrative Correction
1. Work item accidentally moved to wrong step
2. Administrator realizes the error
3. Uses "Move Back" to return to correct previous step
4. Provides comment: "Correcting accidental transition error"
5. Workflow continues from correct point

## Future Enhancements

Potential improvements that could be added:

1. **Configurable Permissions**: Allow workflow-specific backward movement rules
2. **Bulk Backward Movement**: Move multiple items back simultaneously  
3. **Conditional Backward Transitions**: Rules-based backward movement availability
4. **Notification System**: Automatic notifications when items are moved backward
5. **Reporting**: Analytics on backward movement patterns

## Troubleshooting

### Common Issues
- **"Move Back" not visible**: User needs admin/staff permissions or must be item creator
- **"No previous steps"**: Work item hasn't moved through multiple steps yet
- **"Comment required"**: All backward movements must include explanation text
- **"Permission denied"**: User lacks required permissions for backward movement

### Checking Permissions
To verify if a user can move items backward:
```python
work_item.can_move_backward(user_profile)
```

To see available backward steps:
```python
work_item.get_available_backward_steps()
```

The backward transition feature is now fully integrated into CFlows and ready for production use!
