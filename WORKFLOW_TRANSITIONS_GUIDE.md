# Workflow Transitions Management Guide

## Overview

Organization staff and administrators can now easily manage workflow transitions without using Django admin. This guide explains how to create, edit, and manage transitions between workflow steps.

## Accessing Transition Management

### From Workflow Detail Page
1. Navigate to **CFlows** → **Workflows**
2. Click on any workflow to view its details
3. Click the **"Manage Transitions"** button (blue button with route icon)

### Available Features

#### 1. Workflow Transitions Manager
- **URL Pattern**: `/cflows/workflows/{workflow_id}/transitions/`
- **Description**: Visual interface showing all workflow steps and their transitions
- **Features**:
  - Visual workflow diagram
  - Add transitions from any step
  - Edit existing transitions
  - Delete transitions
  - Bulk transition creation

#### 2. Individual Transition Management
- **Create Transition**: Add transitions from specific steps to other steps
- **Edit Transition**: Modify transition labels and conditions
- **Delete Transition**: Remove unwanted transitions
- **Bulk Creation**: Create multiple transitions at once using patterns

## Creating Transitions

### Single Transition Creation
1. From the Transitions Manager, click **"Add Transition"** next to any step
2. Select the destination step
3. Add a descriptive label (e.g., "Approve", "Reject", "Send for Review")
4. Optionally add JSON conditions for advanced logic
5. Click **"Create Transition"**

### Bulk Transition Creation
1. Click **"Bulk Create Transitions"** in the Transitions Manager
2. Choose from predefined patterns:
   - **Sequential Flow**: Step 1 → Step 2 → Step 3 → etc.
   - **All to One**: All steps → Final step (e.g., for approval workflows)
   - **One to All**: Initial step → All other steps (e.g., for routing)
   - **Custom**: Manually specify transitions using simple syntax

### Custom Transition Syntax
For custom bulk creation, use this format:
```
Step Name A -> Step Name B : Transition Label
Step Name B -> Step Name C : Process
Step Name C -> Step Name A : Return for Revision
```

## Transition Properties

### Label
- Short descriptive text for the transition button
- Examples: "Approve", "Reject", "Send Back", "Complete", "Review"
- Appears as button text in the work item interface

### Conditions (Advanced)
- Optional JSON conditions for when the transition is available
- Used for advanced workflow logic
- Leave blank for always-available transitions

## Examples

### Simple Approval Workflow
```
Draft -> Under Review : Submit for Review
Under Review -> Approved : Approve
Under Review -> Draft : Send Back for Changes
Approved -> Published : Publish
```

### Complex Review Process
```
New Request -> Initial Review : Begin Review
Initial Review -> Technical Review : Assign Technical Review
Initial Review -> Rejected : Reject Request
Technical Review -> Final Approval : Recommend Approval
Technical Review -> Initial Review : Request Changes
Final Approval -> Completed : Complete
Final Approval -> Technical Review : Request Clarification
```

## User Permissions

### Who Can Manage Transitions
- **Organization Administrators**: Full access to all workflow transitions
- **Organization Staff**: Can manage transitions for workflows in their organization
- **Team Leaders**: Can manage transitions for workflows assigned to their teams

### Access Requirements
- Must be logged in
- Must belong to the organization that owns the workflow
- Must have staff or admin status in the organization

## Visual Features

### Workflow Diagram
- Each step shown as a card
- Outgoing transitions listed under each step
- Hover effects for better interaction
- Color-coded status indicators

### Transition Management
- Add button next to each step
- Quick edit/delete for existing transitions
- Visual feedback for successful operations
- Error handling with clear messages

## Tips for Effective Transition Design

### Best Practices
1. **Use Clear Labels**: Choose intuitive names like "Approve" instead of "Next"
2. **Avoid Loops**: Be careful with transitions that create circular workflows
3. **Plan Terminal Steps**: Ensure workflows have clear end points
4. **Test Thoroughly**: Create test work items to verify transition flow

### Common Patterns
1. **Linear Workflow**: A → B → C → D (sequential steps)
2. **Branching**: A → B or C (conditional routing)
3. **Convergent**: B → D, C → D (multiple paths to same step)
4. **Review Cycles**: A → B → A (back-and-forth review)

## Troubleshooting

### Common Issues
1. **"Transition already exists"**: Each step pair can only have one transition
2. **"Steps from different workflows"**: Can only connect steps within the same workflow
3. **"Cannot transition to itself"**: Self-transitions are not allowed

### Getting Help
- Check the visual diagram to understand current transitions
- Use bulk creation for complex workflows
- Refer to existing transitions as examples
- Contact system administrators for permission issues

## Integration with Work Items

Once transitions are configured:
1. Work items will show available transition buttons
2. Users can click transition buttons to move items between steps
3. Transition labels become button text
4. Conditions determine button availability

This transition management system makes it easy to create sophisticated workflows without technical knowledge or admin access.
