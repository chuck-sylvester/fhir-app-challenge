# Patient Activity Page — Implementation Guide

This guide walks through building the patient activity (clinical detail) page from start
to finish. It is organized into phases and tasks so you can follow along sequentially,
test after each phase, and understand not just *what* to build but *why* each piece is
structured the way it is.

---

## What We Are Building

A full, dedicated browser page scoped to a single patient. The user reaches it by
clicking the ellipsis action menu on any patient row and selecting **Activity**.

| Section | FHIR Resource Type |
|---------|--------------------|
| Demographics header     | `Patient` |
| Vital Signs             | `Observation` (category: vital-signs) |
| Conditions / Diagnoses  | `Condition` |
| Medications             | `MedicationRequest` |
| Allergies               | `AllergyIntolerance` |

**Design decisions:**

- Dedicated page, not a modal — the volume of clinical data needs the full viewport.
- No left nav — removes distraction; a breadcrumb handles navigation back.
- Full browser navigation (`window.location.href`) — not an HTMX swap — because the
  page layout itself changes completely.

---

## Architecture at a Glance

Every new feature in this stack follows the same request lifecycle. Understanding it
once makes every phase below predictable.

```
Browser
  │
  │  GET /Patient/{ptid}/activity
  ▼
FastAPI Router     (app/routers/patient.py)
  │  calls
  ▼
Service Layer      (app/services/patient_service.py)
  │  calls         (HTTP, synchronous requests lib)
  ▼
HAPI FHIR Server   (localhost:8080)
  │  returns JSON bundles
  ▼
Service Layer      returns Python dicts to router
  │
  ▼
FastAPI Router     calls templates.TemplateResponse(...)
  │
  ▼
Jinja2 Engine      renders patient_activity.html with context dict
  │
  ▼
Browser            receives and displays the full HTML page
```

**Separation of concerns:**

| Layer | Responsibility | Should NOT |
|-------|----------------|------------|
| Router   | HTTP routing, assembling context, returning responses | Contain business logic or FHIR calls |
| Service  | FHIR HTTP calls, data shaping | Know about HTTP requests from the browser |
| Template | Rendering HTML from context variables | Contain logic beyond simple display conditionals |

---

## Screen Layout Reference

### Layout A — Stacked Sections (build this first)

```text
┌─────────────────────────────────────────────────────────────────┐
│ ← Patients                                    [App Title]       │
│ Patients > Jane Smith                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Jane Smith                  Female  |  DOB: 1982-04-11 │    │
│  │  Age: 43   |   ID: abc-123-def                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  VITAL SIGNS                                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Date        Measure          Value      Unit           │    │
│  │  2025-03-01  Blood Pressure   118/76     mmHg           │    │
│  │  2025-03-01  Heart Rate       72         /min           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  CONDITIONS                                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Condition               Status     Onset               │    │
│  │  Type 2 Diabetes         Active     2019-06             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  MEDICATIONS / ALLERGIES (same pattern)                         │
└─────────────────────────────────────────────────────────────────┘
```

### Layout B — Tabbed Sections (future enhancement)

```text
┌─────────────────────────────────────────────────────────────────┐
│ ← Patients                                    [App Title]       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Jane Smith    F  |  DOB: 1982-04-11  |  Age: 43        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  [ Vitals ] [ Conditions ] [ Medications ] [ Allergies ]        │
│  ─────────                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  (active tab content rendered here via HTMX on click)   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

Build Layout A first — all sections load at once with no additional HTMX complexity.
Layout B is a natural evolution once Layout A is working.

---

## Phase Checklist

- [ ] **Phase 1** — Create the standalone page template
- [ ] **Phase 2** — Add FHIR service functions
- [ ] **Phase 3** — Add the router endpoint  ← *first testable milestone*
- [ ] **Phase 4** — Wire up the action menu
- [ ] **Phase 5** — Complete the clinical template sections  ← *done*

---

---

# Phase 1: Create the Standalone Page Template

**Goal:** Create `app/templates/patient_activity.html` with a full HTML skeleton —
breadcrumb, demographics header, and placeholder comments for each clinical section.
The page will not be reachable from the browser until Phase 3, but you can build and
refine the template structure independently.

---

## Task 1.1 — Create the template file

Create a new file: **`app/templates/patient_activity.html`**

This is a **standalone** template — do not use `{% extends "base.html" %}`. The activity
page intentionally omits the left nav, so it manages its own complete HTML document.
This means duplicating the `<head>` dependencies (Tailwind, HTMX, FontAwesome, main.css).
That duplication is acceptable for this implementation. A natural future refinement is a
shared `clinical_base.html` that both this page and any future full-page clinical views
can extend.

Add the following skeleton:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ first_name }} {{ last_name }} — Activity</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
  <link rel="stylesheet" href="https://kit.fontawesome.com/124182fb50.css">
  <link rel="stylesheet" href="/static/css/main.css">
</head>
<body class="bg-gray-100 text-gray-900">

  <!-- Breadcrumb
       href="/" returns to the app root, which loads the full shell with the left nav.
       Do NOT use href="/Patient/table" — that route returns an HTML fragment, not a
       full page. Navigating to it directly renders a bare table with no layout. -->
  <header class="bg-white border-b border-gray-300 px-8 py-3 flex items-center gap-2 text-sm text-gray-600">
    <a href="/" class="hover:text-blue-700">
      <i class="fa-regular fa-users"></i> Patients
    </a>
    <span>/</span>
    <span class="text-gray-900 font-medium">{{ first_name }} {{ last_name }}</span>
  </header>

  <main class="max-w-5xl mx-auto px-8 py-6">

    <!-- Task 1.2: Demographics header goes here -->

    <!-- Phase 5: Clinical sections go here -->

  </main>
</body>
</html>
```

---

## Task 1.2 — Add the demographics header

Replace the `<!-- Task 1.2 -->` comment with the following block inside `<main>`:

```html
<div class="bg-white rounded-lg border border-gray-300 px-6 py-4 mb-6">
  <h1 class="text-xl font-semibold text-gray-900">{{ first_name }} {{ last_name }}</h1>
  <p class="text-sm text-gray-500 mt-1">
    {{ gender | title if gender else "—" }}
    &nbsp;|&nbsp;
    DOB: {{ birth_date if birth_date else "—" }}
    &nbsp;|&nbsp;
    Age: {{ age if age else "—" }}
    &nbsp;|&nbsp;
    ID: {{ ptid }}
  </p>
</div>
```

**Where do these variables come from?**
The router (Phase 3) calls the existing `_patient_to_context(patient)` helper in
`patient.py`. That function already extracts `first_name`, `last_name`, `gender`,
`birth_date`, and `age` from a FHIR Patient resource. It is reused here — no new
extraction logic needed. The `ptid` value is passed separately by the router.

---

---

# Phase 2: Add FHIR Service Functions

**Goal:** Add four new functions to **`app/services/patient_service.py`**, one per
FHIR resource type. Each function follows the same pattern as the existing service
functions: build headers, build params, make a GET request, return the JSON.

Add these functions after the existing `get_patient()` function and before `_MARITAL_DISPLAY`.

---

## Task 2.1 — Add get_vitals()

```python
def get_vitals(ptid: str) -> dict:
    headers = {"Accept": "application/fhir+json"}
    if settings.fhir_external_api_token:
        headers["Authorization"] = f"Bearer {settings.fhir_external_api_token}"
    params = {
        "patient": ptid,
        "category": "vital-signs",
        "_sort": "-date",
        "_count": 20,
    }
    output = requests.get(f"{settings.fhir_base_url}/Observation", headers=headers, params=params)
    output.raise_for_status()
    return output.json()
```

**FHIR notes:**
- `category=vital-signs` filters to only vital sign observations, excluding lab results
  and other observation types.
- `_sort=-date` returns the most recent readings first (the `-` prefix means descending).
- The FHIR `Observation` resource uses `effectiveDateTime` for the recorded date and
  `valueQuantity` for single-value measurements (heart rate, weight, etc.). Blood pressure
  is a special case — it uses a `component` array instead. See Appendix A for the full
  resource structure.

---

## Task 2.2 — Add get_conditions()

```python
def get_conditions(ptid: str) -> dict:
    headers = {"Accept": "application/fhir+json"}
    if settings.fhir_external_api_token:
        headers["Authorization"] = f"Bearer {settings.fhir_external_api_token}"
    params = {
        "patient": ptid,
        "_sort": "-recorded-date",
        "_count": 20,
    }
    output = requests.get(f"{settings.fhir_base_url}/Condition", headers=headers, params=params)
    output.raise_for_status()
    return output.json()
```

**FHIR notes:**
- Each `Condition` has a `clinicalStatus` (active, resolved, etc.) and a `code` that
  identifies the diagnosis. Use `code.text` first for display — it is the human-readable
  label. Fall back to `code.coding[0].display` if `text` is absent.
- The onset date may appear as `onsetDateTime` (a string) or `onsetPeriod.start`
  (a period with start/end). Check for both in the template.

---

## Task 2.3 — Add get_medications()

```python
def get_medications(ptid: str) -> dict:
    headers = {"Accept": "application/fhir+json"}
    if settings.fhir_external_api_token:
        headers["Authorization"] = f"Bearer {settings.fhir_external_api_token}"
    params = {
        "patient": ptid,
        "_sort": "-authoredon",
        "_count": 20,
    }
    output = requests.get(f"{settings.fhir_base_url}/MedicationRequest", headers=headers, params=params)
    output.raise_for_status()
    return output.json()
```

**FHIR notes:**
- The sort key is `authoredon` (no hyphen) — this is the exact FHIR R4 search parameter
  name for `MedicationRequest`. Using `authored-on` (with a hyphen) will be silently
  ignored or cause an error depending on the HAPI version.
- The medication name is in `medicationCodeableConcept.text` or
  `medicationCodeableConcept.coding[0].display`.
- Dosage instructions are in `dosageInstruction[0].text`.

---

## Task 2.4 — Add get_allergies()

```python
def get_allergies(ptid: str) -> dict:
    headers = {"Accept": "application/fhir+json"}
    if settings.fhir_external_api_token:
        headers["Authorization"] = f"Bearer {settings.fhir_external_api_token}"
    params = {
        "patient": ptid,
        "_count": 20,
    }
    output = requests.get(f"{settings.fhir_base_url}/AllergyIntolerance", headers=headers, params=params)
    output.raise_for_status()
    return output.json()
```

**FHIR notes:**
- The allergen name is in `code.text` or `code.coding[0].display`.
- Reaction details (substance, manifestation, severity) are in the `reaction` array.
- `criticality` (`low`, `high`, `unable-to-assess`) and `clinicalStatus` are separate fields.

---

## A Note on `patient=` vs. `subject=`

All four functions above use `patient={ptid}` to scope results to a specific patient.
This is the correct and most common form for HAPI FHIR and Synthea-generated data.

If a resource type returns empty or unexpected results despite the patient having data,
try the alternative reference form: `subject=Patient/{ptid}`. Some FHIR servers store
the patient link as a full reference string (`"Patient/abc-123"`) and the `subject=`
parameter searches that field directly. For the four resources in this guide,
`patient={ptid}` is the right starting point.

---

---

# Phase 3: Add the Router Endpoint

**Goal:** Register `GET /Patient/{ptid}/activity` in **`app/routers/patient.py`**,
call all five service functions, and return the rendered template. After this phase
you have a testable page.

---

## Task 3.1 — Insert the route in the correct position

**Route ordering matters.** FastAPI registers routes in the order they are defined.
A route like `GET /Patient/new` must appear before `GET /Patient/{ptid}`, or the
string `"new"` is captured as a patient ID and routed to the wrong handler. The same
principle applies to every named sub-route under `/Patient/`.

Note: FastAPI's `{ptid}` captures only a single path segment and does not consume
slashes, so `/Patient/{ptid}` cannot accidentally match `/Patient/abc/activity` as a
single ID. The ordering concern is specifically about bare literal routes like
`/Patient/new` that share the same prefix level as `{ptid}`.

Place the new route in the **"Action-menu modal routes"** block, alongside `/view`,
`/edit`, and `/delete-confirm` — all of which are already above the `/{ptid}` wildcard:

```python
# --- Action-menu modal routes (must be registered before /{ptid} wildcard) ---

@router.get("/Patient/{ptid}/activity", response_class=HTMLResponse)  # <-- add here
async def get_patient_activity(request: Request, ptid: str):
    ...

@router.get("/Patient/{ptid}/view", response_class=HTMLResponse)
...
```

---

## Task 3.2 — Write the endpoint handler

Add the following function body. Each clinical service call is wrapped in its own
`try/except` so that one failed FHIR call does not crash the entire page.

```python
@router.get("/Patient/{ptid}/activity", response_class=HTMLResponse)
async def get_patient_activity(request: Request, ptid: str):
    patient = patient_service.get_patient(ptid)
    context = _patient_to_context(patient)
    context["ptid"] = ptid

    try:
        context["vitals"] = patient_service.get_vitals(ptid)
    except Exception:
        context["vitals"] = {"entry": [], "_error": True}

    try:
        context["conditions"] = patient_service.get_conditions(ptid)
    except Exception:
        context["conditions"] = {"entry": [], "_error": True}

    try:
        context["medications"] = patient_service.get_medications(ptid)
    except Exception:
        context["medications"] = {"entry": [], "_error": True}

    try:
        context["allergies"] = patient_service.get_allergies(ptid)
    except Exception:
        context["allergies"] = {"entry": [], "_error": True}

    return templates.TemplateResponse(request, "patient_activity.html", context)
```

**Why the `_error` flag?**
An empty result (`{"entry": []}`) and a failed call both result in no rows being
displayed — but they have different clinical meanings. "No conditions on record" means
the patient genuinely has no recorded conditions. "Unable to load conditions" means the
data may exist but could not be retrieved. A clinician should not draw clinical
conclusions from an error state. The `_error` flag lets the template show the right
message in each case (see Phase 5).

---

## ✓ Milestone: Test the Page in the Browser

Before wiring up the action menu, test the page directly:

1. Ensure your dev server is running: `uvicorn app.main:app --reload --port 8000`
2. Find a real patient ID from your FHIR server (check the patient table in the app or
   look at the URL when viewing a patient).
3. Navigate directly to: `http://localhost:8000/Patient/{real-patient-id}/activity`

**Expected result:** The page loads with the breadcrumb, the demographics header
populated with the patient's name, DOB, and age, and placeholder comments where the
clinical sections will go. Each section's context variable (`vitals`, `conditions`, etc.)
is available in the template even if not yet rendered.

If you see a 500 error, check the FastAPI console for the traceback — the most common
cause at this stage is a route ordering issue or a template variable name mismatch.

---

---

# Phase 4: Wire Up the Action Menu

**Goal:** Replace the placeholder `alert()` in **`app/static/js/main.js`** with real
navigation to the activity page.

---

## Task 4.1 — Add an activityPatient() function

In `main.js`, add a new function alongside the existing `viewPatient()`, `editPatient()`,
and `confirmDeletePatient()` functions:

```javascript
function activityPatient(ptid) {
  closePatientMenu();
  window.location.href = `/Patient/${ptid}/activity`;
}
```

**Why `window.location.href` and not `htmx.ajax()`?**
The existing modal actions (View, Edit, Delete) use `htmx.ajax()` because they load
content into `#modal-root` without leaving the current page. The Activity page is
different — it has a completely different layout (no left nav, its own breadcrumb).
A full browser navigation is the right tool here. The browser back button will then
return the user to the patient list naturally.

---

## Task 4.2 — Update the Activity button onclick

In `main.js`, find the Activity button inside the `menu.innerHTML` template string in
`patientAction()`. It currently shows:

```javascript
onclick="alert('Note: Patient Activity to be implemented in week 2.')"
```

Replace it with:

```javascript
onclick="activityPatient('${ptid}')"
```

The updated button block should look like:

```javascript
<button
  class="flex items-center gap-2 w-full text-left px-4 py-2 hover:bg-gray-100"
  onclick="activityPatient('${ptid}')"
>
  <i class="fa-regular fa-clock w-4"></i> Activity
</button>
```

---

---

# Phase 5: Complete the Template Clinical Sections

**Goal:** Replace the `<!-- Phase 5: Clinical sections go here -->` comment in
`patient_activity.html` with working HTML tables for each FHIR resource type.

**Error vs. empty state pattern** — use this structure for every section. The `_error`
flag set by the router (Phase 3) distinguishes a failed FHIR call from a genuinely
empty result:

```html
{% if section_name.get("_error") %}
  <p class="text-sm text-red-600">Unable to load [section]. Please try again.</p>
{% else %}
  {% for entry in section_name.get("entry", []) %}
    ... table rows ...
  {% else %}
    <p class="text-sm text-gray-500">No [section] on record.</p>
  {% endfor %}
{% endif %}
```

---

## Task 5.1 — Add the Vital Signs section

Observations have two value shapes: single-value (`valueQuantity`) and multi-component
(blood pressure uses `component`). The template handles both cases with an `if/elif`:

```html
<section class="mb-8">
  <h2 class="text-base font-semibold text-gray-700 mb-2">
    <i class="fa-regular fa-heart-pulse"></i>&nbsp; Vital Signs
  </h2>
  <table class="w-full text-sm border border-gray-300 rounded bg-white">
    <thead class="bg-gray-50 text-gray-600">
      <tr>
        <th class="px-4 py-2 border-b text-left">Date</th>
        <th class="px-4 py-2 border-b text-left">Observation</th>
        <th class="px-4 py-2 border-b text-left">Value</th>
        <th class="px-4 py-2 border-b text-left">Unit</th>
      </tr>
    </thead>
    <tbody>
      {% if vitals.get("_error") %}
      <tr>
        <td colspan="4" class="px-4 py-2 text-red-600">Unable to load vital signs. Please try again.</td>
      </tr>
      {% else %}
      {% for entry in vitals.get("entry", []) %}
      {% set obs = entry.resource %}
      <tr class="border-b border-gray-200 hover:bg-yellow-50">
        <td class="px-4 py-2">{{ obs.effectiveDateTime[:10] if obs.effectiveDateTime else "—" }}</td>
        <td class="px-4 py-2">{{ obs.code.coding[0].display if obs.code.coding else "—" }}</td>
        <td class="px-4 py-2">
          {% if obs.valueQuantity is defined %}
            {{ obs.valueQuantity.value }}
          {% elif obs.component is defined %}
            {{ obs.component[0].valueQuantity.value }}/{{ obs.component[1].valueQuantity.value }}
          {% else %}
            —
          {% endif %}
        </td>
        <td class="px-4 py-2">
          {% if obs.valueQuantity is defined %}
            {{ obs.valueQuantity.unit }}
          {% elif obs.component is defined %}
            mmHg
          {% else %}
            —
          {% endif %}
        </td>
      </tr>
      {% else %}
      <tr>
        <td colspan="4" class="px-4 py-2 text-gray-500">No vital signs on record.</td>
      </tr>
      {% endfor %}
      {% endif %}
    </tbody>
  </table>
</section>
```

---

## Task 5.2 — Add the Conditions section

```html
<section class="mb-8">
  <h2 class="text-base font-semibold text-gray-700 mb-2">
    <i class="fa-regular fa-stethoscope"></i>&nbsp; Conditions
  </h2>
  <table class="w-full text-sm border border-gray-300 rounded bg-white">
    <thead class="bg-gray-50 text-gray-600">
      <tr>
        <th class="px-4 py-2 border-b text-left">Condition</th>
        <th class="px-4 py-2 border-b text-left">Status</th>
        <th class="px-4 py-2 border-b text-left">Onset</th>
      </tr>
    </thead>
    <tbody>
      {% if conditions.get("_error") %}
      <tr>
        <td colspan="3" class="px-4 py-2 text-red-600">Unable to load conditions. Please try again.</td>
      </tr>
      {% else %}
      {% for entry in conditions.get("entry", []) %}
      {% set cond = entry.resource %}
      <tr class="border-b border-gray-200 hover:bg-yellow-50">
        <td class="px-4 py-2">
          {{ cond.code.text if cond.code.text else
             (cond.code.coding[0].display if cond.code.coding else "—") }}
        </td>
        <td class="px-4 py-2">
          {{ cond.clinicalStatus.coding[0].code | title
             if cond.clinicalStatus and cond.clinicalStatus.coding else "—" }}
        </td>
        <td class="px-4 py-2">
          {% if cond.onsetDateTime is defined %}
            {{ cond.onsetDateTime[:10] }}
          {% elif cond.onsetPeriod is defined %}
            {{ cond.onsetPeriod.start[:10] }}
          {% else %}
            —
          {% endif %}
        </td>
      </tr>
      {% else %}
      <tr>
        <td colspan="3" class="px-4 py-2 text-gray-500">No conditions on record.</td>
      </tr>
      {% endfor %}
      {% endif %}
    </tbody>
  </table>
</section>
```

---

## Task 5.3 — Add the Medications section

```html
<section class="mb-8">
  <h2 class="text-base font-semibold text-gray-700 mb-2">
    <i class="fa-regular fa-pills"></i>&nbsp; Medications
  </h2>
  <table class="w-full text-sm border border-gray-300 rounded bg-white">
    <thead class="bg-gray-50 text-gray-600">
      <tr>
        <th class="px-4 py-2 border-b text-left">Medication</th>
        <th class="px-4 py-2 border-b text-left">Status</th>
        <th class="px-4 py-2 border-b text-left">Authored</th>
        <th class="px-4 py-2 border-b text-left">Instructions</th>
      </tr>
    </thead>
    <tbody>
      {% if medications.get("_error") %}
      <tr>
        <td colspan="4" class="px-4 py-2 text-red-600">Unable to load medications. Please try again.</td>
      </tr>
      {% else %}
      {% for entry in medications.get("entry", []) %}
      {% set med = entry.resource %}
      <tr class="border-b border-gray-200 hover:bg-yellow-50">
        <td class="px-4 py-2">
          {% if med.medicationCodeableConcept is defined %}
            {{ med.medicationCodeableConcept.text if med.medicationCodeableConcept.text else
               (med.medicationCodeableConcept.coding[0].display
                if med.medicationCodeableConcept.coding else "—") }}
          {% else %}
            —
          {% endif %}
        </td>
        <td class="px-4 py-2">{{ med.status | title if med.status else "—" }}</td>
        <td class="px-4 py-2">{{ med.authoredOn[:10] if med.authoredOn is defined else "—" }}</td>
        <td class="px-4 py-2">
          {{ med.dosageInstruction[0].text
             if med.dosageInstruction is defined and med.dosageInstruction else "—" }}
        </td>
      </tr>
      {% else %}
      <tr>
        <td colspan="4" class="px-4 py-2 text-gray-500">No medications on record.</td>
      </tr>
      {% endfor %}
      {% endif %}
    </tbody>
  </table>
</section>
```

---

## Task 5.4 — Add the Allergies section

```html
<section class="mb-8">
  <h2 class="text-base font-semibold text-gray-700 mb-2">
    <i class="fa-regular fa-triangle-exclamation"></i>&nbsp; Allergies
  </h2>
  <table class="w-full text-sm border border-gray-300 rounded bg-white">
    <thead class="bg-gray-50 text-gray-600">
      <tr>
        <th class="px-4 py-2 border-b text-left">Substance</th>
        <th class="px-4 py-2 border-b text-left">Status</th>
        <th class="px-4 py-2 border-b text-left">Criticality</th>
        <th class="px-4 py-2 border-b text-left">Reaction</th>
      </tr>
    </thead>
    <tbody>
      {% if allergies.get("_error") %}
      <tr>
        <td colspan="4" class="px-4 py-2 text-red-600">Unable to load allergies. Please try again.</td>
      </tr>
      {% else %}
      {% for entry in allergies.get("entry", []) %}
      {% set allergy = entry.resource %}
      <tr class="border-b border-gray-200 hover:bg-yellow-50">
        <td class="px-4 py-2">
          {{ allergy.code.text if allergy.code.text else
             (allergy.code.coding[0].display if allergy.code.coding else "—") }}
        </td>
        <td class="px-4 py-2">
          {{ allergy.clinicalStatus.coding[0].code | title
             if allergy.clinicalStatus and allergy.clinicalStatus.coding else "—" }}
        </td>
        <td class="px-4 py-2">{{ allergy.criticality | title if allergy.criticality else "—" }}</td>
        <td class="px-4 py-2">
          {% if allergy.reaction is defined and allergy.reaction %}
            {{ allergy.reaction[0].manifestation[0].text
               if allergy.reaction[0].manifestation else "—" }}
          {% else %}
            —
          {% endif %}
        </td>
      </tr>
      {% else %}
      <tr>
        <td colspan="4" class="px-4 py-2 text-gray-500">No allergies on record.</td>
      </tr>
      {% endfor %}
      {% endif %}
    </tbody>
  </table>
</section>
```

---

## ✓ Final End-to-End Test

1. Start the app and navigate to the patient list.
2. Click the ellipsis on any patient row.
3. Select **Activity** from the menu.
4. Verify the activity page loads with:
   - The patient's name in the breadcrumb and demographics header
   - Correct DOB and calculated age
   - Vital signs, conditions, medications, and allergies populated from the FHIR server
   - "No [x] on record." for any sections with no data
5. Click **← Patients** in the breadcrumb and verify you return to the main app shell.
6. Verify the browser back button also returns you to the patient list.

---

> **Future Refinement — Move FHIR parsing out of templates**
>
> The template sections above put FHIR-specific extraction logic directly in Jinja2:
> checking for `valueQuantity` vs `component`, accessing `coding[0].display`, slicing
> date strings, and so on. This is appropriate for a first implementation and keeps the
> router and service simple.
>
> As the app matures, consider shaping data in the service or router before it reaches
> the template. Instead of passing raw FHIR Bundles, pass lists of pre-shaped dicts:
>
> ```python
> {"date": "2025-03-01", "label": "Blood Pressure", "value": "118/76", "unit": "mmHg"}
> ```
>
> The template then only needs `{{ row.label }}` — it no longer needs to understand FHIR
> structure. This makes templates easier to read, easier to test, and more resilient when
> FHIR data shapes vary between servers.

---

---

# Appendix A: FHIR Resource Structures

These JSON examples show the shape of each FHIR resource as returned by HAPI FHIR /
Synthea. Use these as a reference when building templates or debugging unexpected output.

### What is a FHIR Bundle?

All FHIR search results are wrapped in a Bundle. The actual resource data is always
one level deep inside `entry[n].resource`:

```json
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 3,
  "entry": [
    {
      "fullUrl": "http://localhost:8080/fhir/Observation/456",
      "resource": {
        "resourceType": "Observation",
        "..."  : "..."
      }
    }
  ]
}
```

In templates: `{% for entry in vitals.get("entry", []) %}` → `entry.resource` is the
observation.

---

### Patient (demographics)

```json
{
  "resourceType": "Patient",
  "id": "abc-123",
  "name": [
    { "use": "official", "family": "Smith", "given": ["Jane", "Marie"] }
  ],
  "gender": "female",
  "birthDate": "1982-04-11",
  "telecom": [
    { "system": "phone", "value": "555-867-5309", "use": "home" }
  ],
  "address": [
    { "line": ["123 Main St"], "city": "Springfield", "state": "IL" }
  ]
}
```

---

### Observation (vital signs — single value)

```json
{
  "resourceType": "Observation",
  "status": "final",
  "category": [{ "coding": [{ "code": "vital-signs" }] }],
  "code": {
    "coding": [{ "system": "http://loinc.org", "code": "8867-4", "display": "Heart rate" }]
  },
  "effectiveDateTime": "2025-03-01T09:15:00Z",
  "valueQuantity": { "value": 72, "unit": "/min" }
}
```

### Observation (blood pressure — component array)

Blood pressure is the main exception to the single-value pattern. It uses `component`
instead of `valueQuantity`:

```json
{
  "code": { "coding": [{ "code": "55284-4", "display": "Blood pressure panel" }] },
  "effectiveDateTime": "2025-03-01T09:15:00Z",
  "component": [
    {
      "code": { "coding": [{ "code": "8480-6", "display": "Systolic" }] },
      "valueQuantity": { "value": 118, "unit": "mmHg" }
    },
    {
      "code": { "coding": [{ "code": "8462-4", "display": "Diastolic" }] },
      "valueQuantity": { "value": 76, "unit": "mmHg" }
    }
  ]
}
```

---

### Condition

```json
{
  "resourceType": "Condition",
  "clinicalStatus": { "coding": [{ "code": "active" }] },
  "code": {
    "coding": [{ "system": "http://snomed.info/sct", "code": "73211009",
                 "display": "Diabetes mellitus type 2" }],
    "text": "Type 2 Diabetes"
  },
  "onsetDateTime": "2019-06-15",
  "recordedDate": "2019-06-20"
}
```

Use `code.text` first — it is the human-readable label. Fall back to
`code.coding[0].display` if absent.

---

### MedicationRequest

```json
{
  "resourceType": "MedicationRequest",
  "status": "active",
  "medicationCodeableConcept": {
    "coding": [{ "display": "Metformin 500 MG Oral Tablet" }],
    "text": "Metformin 500 mg"
  },
  "authoredOn": "2019-07-15",
  "dosageInstruction": [
    { "text": "Take 1 tablet twice daily with meals" }
  ]
}
```

---

### AllergyIntolerance

```json
{
  "resourceType": "AllergyIntolerance",
  "clinicalStatus": { "coding": [{ "code": "active" }] },
  "code": { "text": "Penicillin" },
  "criticality": "high",
  "reaction": [
    {
      "manifestation": [{ "text": "Rash" }],
      "severity": "moderate"
    }
  ]
}
```

---

### LOINC Codes for Common Vital Signs

LOINC is the standard coding system for clinical observations. These are the codes
HAPI FHIR / Synthea typically uses:

| LOINC Code | Observation |
|------------|-------------|
| `8867-4`   | Heart rate |
| `9279-1`   | Respiratory rate |
| `8310-5`   | Body temperature |
| `55284-4`  | Blood pressure panel (parent — has `component` children) |
| `8480-6`   | Systolic blood pressure (component) |
| `8462-4`   | Diastolic blood pressure (component) |
| `29463-7`  | Body weight |
| `8302-2`   | Body height |
| `39156-5`  | BMI |
| `59408-5`  | Oxygen saturation (pulse ox) |

---

---

# Appendix B: Jinja2 Quick Reference

### Context variables

Whatever keys you pass in the router's context dict become variables in the template.
`context["vitals"] = {...}` → `{{ vitals }}` in the template.

### for / else

Jinja2's `{% for %}` block supports an `{% else %}` clause that renders when the
iterable is empty — always use it for FHIR result sets:

```html
{% for entry in conditions.get("entry", []) %}
  <tr>...</tr>
{% else %}
  <tr><td>No conditions on record.</td></tr>
{% endfor %}
```

### Safe nested access

FHIR resources are deeply nested and many fields are optional. Use defensive access:

```html
{{ entry.resource.valueQuantity.value | default("—") }}
{{ entry.resource.code.coding[0].display if entry.resource.code.coding else "—" }}
```

### `is defined` vs. truthiness

- `{% if x %}` — falsy for `None`, `""`, `0`, `[]`, `{}`
- `{% if x is defined %}` — falsy only when the variable does not exist at all in context

For FHIR dict keys accessed via dot notation in Jinja2, prefer `if x is defined` when
checking for the presence of an optional field.

### The `| title` filter

Jinja2's built-in `| title` filter title-cases a string. `"active" | title` → `"Active"`.
Useful for FHIR status codes, which are always lowercase in the spec.

### Dates

FHIR `dateTime` values look like `"2025-03-01T09:15:00Z"`. Slice the first 10 characters
to get a display-friendly date: `obs.effectiveDateTime[:10]` → `"2025-03-01"`.

---

---

# Appendix C: Common Pitfalls & Tips

### FHIR data is always optional

The FHIR spec marks many fields as optional (cardinality `0..1` or `0..*`). Even fields
that seem logically required — like a patient's name or a condition's onset date — may be
absent in real data. Build templates defensively from the start.

### Synthea-generated data vs. real data

HAPI FHIR loaded with Synthea patients usually has well-formed, complete data. When you
connect to a real clinical FHIR server, expect gaps, nulls, and unexpected field
combinations. Defensive Jinja2 access pays off later.

### The `_patient_to_context()` helper already exists

`patient.py` already has `_patient_to_context(patient)` which extracts `first_name`,
`last_name`, `gender`, `birth_date`, `age`, `phone`, `marital_status`, and `last_updated`
from a FHIR Patient dict. Reuse it in the activity page router — no new extraction logic
is needed for the demographics header.

### Test routes directly before wiring the UI

After Phase 3, visit the page directly in the browser with a real patient ID:
`http://localhost:8000/Patient/{real-patient-id}/activity`

This lets you develop and debug the template completely independently of the action menu.
Find a real ID by checking the patient table URL or viewing a patient's JSON output.

### FHIR server CORS and auth

CORS only restricts browser-to-server calls. Your service layer uses the `requests`
library server-to-server, so CORS headers on HAPI are irrelevant for this architecture.

The `fhir_external_api_token` is only needed for the Medblocks-hosted external server.
When running locally against Docker HAPI, the token is empty and the
`if settings.fhir_external_api_token` guard correctly skips the Authorization header.

### `authoredon` — no hyphen

The FHIR R4 search parameter for `MedicationRequest` authored date is `authoredon`
(no hyphen). Using `authored-on` will be silently ignored or return an error depending
on the HAPI server version. This is a known gotcha that does not produce an obvious error.
