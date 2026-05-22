# Refactor Patient Activity

**Goal:** refactor from a dedicated page to a partial that extends patient.

### Plan

1. Move `app/templates/activity.html` to `app/templates/partials/view_patient_activity.html`
2. Rework `view_patient_activity.html` as a partial
3. Update patient pop-up actions menu (JavaScript) route
4. Create route: /Patient/etc...
