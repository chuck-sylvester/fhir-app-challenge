# Patient Activity Page — Build Guide

This document covers how to build the patient activity (clinical detail) page for the FHIR App Challenge project. It is written as a learning reference, so each section explains not just *what* to do but *why* it works the way it does
across FastAPI, Jinja2, HTMX, and the FHIR R4 specification.

---

## 1. Feature Overview

The patient activity page is a full, dedicated browser page scoped to a single patient. It replaces the current application shell (left nav + main content area) with a focused clinical view. The user reaches it by clicking the
ellipsis action menu on any patient row and selecting "Activity."

**What the page shows:**

| Section | FHIR Resource Type |
|---------|--------------------|
| Demographics header     | `Patient` |
| Vital Signs             | `Observation` (category: vital-signs) |
| Conditions / Diagnoses  | `Condition` |
| Medications             | `MedicationRequest` |
| Allergies               | `AllergyIntolerance` |
| Procedures *(optional)* | `Procedure` |

**Design decisions already made:**

- Dedicated page, not a modal — the volume of clinical data needs the full viewport.
- No left nav — removes distraction; a breadcrumb handles navigation back.
- Full browser navigation (`window.location.href`) — not an HTMX swap — because the page layout itself changes completely.

---

## 2. Architecture Recap

Understanding the request lifecycle is the foundation for building any new feature in this stack.

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

### Key principle: separation of concerns

| Layer | Responsibility | Should NOT |
|-------|----------------|------------|
| Router   | HTTP routing, assembling context, returning responses | Contain business logic or FHIR calls |
| Service  | FHIR HTTP calls, data shaping | Know about HTTP requests/responses from the browser |
| Template | Rendering HTML from context variables | Contain logic beyond simple display conditionals |

---

## 3. Screen Layout Concepts

### Layout A — Stacked Sections (simplest to build first)

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
│  │  2025-03-01  Body Weight      68.5       kg             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  CONDITIONS                                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Condition               Status     Onset               │    │
│  │  Type 2 Diabetes         Active     2019-06             │    │
│  │  Essential Hypertension  Active     2017-11             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  MEDICATIONS                                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Medication         Status    Authored                  │    │
│  │  Metformin 500 mg   Active    2019-07-15                │    │
│  │  Lisinopril 10 mg   Active    2017-12-01                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ALLERGIES                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Substance     Reaction       Severity                  │    │
│  │  Penicillin    Rash           Moderate                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Layout B — Tabbed Sections (progressive enhancement)

```text
┌─────────────────────────────────────────────────────────────────┐
│ ← Patients                                    [App Title]       │
│ Patients > Jane Smith                                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Jane Smith    F  |  DOB: 1982-04-11  |  Age: 43        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  [ Vitals ] [ Conditions ] [ Medications ] [ Allergies ]        │
│  ─────────                                                      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  (active tab content rendered here via HTMX)            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

Layout A is recommended to start — all sections load at once, no additional HTMX complexity. Layout B is a natural evolution once Layout A is working.

---

## 4. Task Checklist

Work in this order. Each task produces a testable result before the next one begins.

- [ ] **Task 1** — Create `app/templates/patient_activity.html` (standalone, no left nav)
- [ ] **Task 2** — Add service functions for each clinical FHIR resource type
- [ ] **Task 3** — Add `GET /Patient/{ptid}/activity` route in `patient.py`
- [ ] **Task 4** — Wire up the action menu in `main.js` to navigate to the activity page
- [ ] **Task 5** — Fill in each template section with real FHIR data

**Milestone after Task 3:** visit `http://localhost:8000/Patient/{any-real-id}/activity` directly in the browser — the page should load with demographics even before the action menu is wired up. This lets you develop the template independently.

---

## 5. FastAPI — Router & Endpoint

### Route ordering rule

FastAPI registers routes in the order they are defined. Because `{ptid}` is a wildcard path segment, any route that shares the `/Patient/` prefix with a literal segment **must be defined before** the wildcard route. Your existing code already demonstrates this — `/view`, `/edit`, and `/delete-confirm` all appear above `GET /Patient/{ptid}`.

```python
# CORRECT — specific routes first
@router.get("/Patient/{ptid}/activity")   # <-- new route here
@router.get("/Patient/{ptid}/view")
@router.get("/Patient/{ptid}/edit")
@router.get("/Patient/{ptid}/delete-confirm")
@router.get("/Patient/{ptid}")            # <-- wildcard last
```

Note: FastAPI's `{ptid}` captures a single path segment and does not consume slashes, so `/Patient/{ptid}` would not accidentally swallow `/Patient/abc/activity` as a single ID. The real risk is simpler: a literal route like `GET /Patient/new` must appear before `GET /Patient/{ptid}`, or the string `"new"` will be captured as a patient ID and routed to the wrong handler. The same principle applies to `/activity` and all other named sub-routes.

### Endpoint pattern

```python
@router.get("/Patient/{ptid}/activity", response_class=HTMLResponse)
async def get_patient_activity(request: Request, ptid: str):
    patient  = patient_service.get_patient(ptid)
    vitals   = patient_service.get_vitals(ptid)
    conditions  = patient_service.get_conditions(ptid)
    medications = patient_service.get_medications(ptid)
    allergies   = patient_service.get_allergies(ptid)

    context = _patient_to_context(patient)
    context["ptid"] = ptid
    context["vitals"]      = vitals
    context["conditions"]  = conditions
    context["medications"] = medications
    context["allergies"]   = allergies

    return templates.TemplateResponse(request, "patient_activity.html", context)
```

**Why all calls are made in the router, not in the template or service:**  
The router is the orchestration layer. It knows which data the page needs. Each service function does one thing — the router composes them.

**Why `response_class=HTMLResponse`:**  
FastAPI defaults to JSON responses. Declaring `HTMLResponse` sets the `Content-Type: text/html` header and tells FastAPI not to serialize the return value as JSON.

---

## 6. Service Layer — Fetching FHIR Clinical Data

### General pattern

Every new service function follows the same shape:

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

### FHIR search parameters for each resource

| Function | FHIR Endpoint | Key Search Params |
|----------|---------------|-------------------|
| `get_vitals(ptid)`      | `/Observation` | `patient={ptid}`, `category=vital-signs`, `_sort=-date` |
| `get_conditions(ptid)`  | `/Condition`   | `patient={ptid}`, `_sort=-recorded-date` |
| `get_medications(ptid)` | `/MedicationRequest`  | `patient={ptid}`, `_sort=-authoredon` |
| `get_allergies(ptid)`   | `/AllergyIntolerance` | `patient={ptid}` |
| `get_procedures(ptid)`  | `/Procedure`   | `patient={ptid}`, `_sort=-date`, `_count=20` |

### Why `_sort` matters

FHIR servers return resources in an unspecified order by default. Sorting by `-date` (descending) puts the most recent records first, which is what a clinician expects. The `-` prefix means descending. Not all FHIR servers support all sort parameters — HAPI FHIR supports these for the resources above.

### Why `_count` matters

Without `_count`, HAPI FHIR returns its default page size (usually 20). For vitals this is fine. For conditions or medications on a long-term patient, you may want to increase it or implement pagination later. Start with `_count=20`
and adjust.

### Error handling

`output.raise_for_status()` raises a `requests.HTTPError` if the FHIR server returns a 4xx or 5xx. For the activity page, a missing resource type (e.g., no allergy records) will return a valid FHIR Bundle with zero entries — not an
error. Only unreachable server or auth failures produce HTTP errors.

Consider wrapping each call in the router with a try/except so that one failed resource type does not break the entire page:

```python
try:
    vitals = patient_service.get_vitals(ptid)
except Exception:
    vitals = {"entry": [], "_error": True}
```

Passing `_error: True` in the fallback dict lets the template distinguish between a failed call and a genuine empty result — and show a different message to the user. These two states have different clinical meanings:

- **"No vital signs on record"** — the FHIR server responded successfully with zero entries. The patient may genuinely have no vitals recorded.
- **"Unable to load vital signs"** — the call failed. The data may exist but could not be retrieved. A clinician should not act on the assumption that the record is empty.

In the template, check for the flag:

```html
{% if vitals.get("_error") %}
  <p class="text-red-600 text-sm">Unable to load vital signs. Please try again.</p>
{% else %}
  {% for entry in vitals.get("entry", []) %}
    ...
  {% else %}
    <p class="text-gray-500 text-sm">No vital signs on record.</p>
  {% endfor %}
{% endif %}
```

---

## 7. Jinja2 — Standalone Page Template

### Standalone vs. extending base.html

`base.html` provides the left nav shell. The activity page does not want that, so do **not** use `{% extends "base.html" %}`. Instead write a complete HTML document from scratch.

The tradeoff is that the `<head>` dependencies (Tailwind, HTMX, FontAwesome, favicon, `main.css`) are duplicated between `base.html` and the activity page. This is acceptable for a v1 learning implementation. A natural future refinement is a shared `clinical_base.html` that provides the `<head>` block and a minimal body wrapper, which both the activity page and any future full-page clinical views can extend.

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

  <!-- Breadcrumb -->
  <!-- href="/" returns to the app root, which loads the full shell with the left nav.
       Do NOT use href="/Patient/table" — that route returns a partial HTML fragment,
       not a full page, so navigating to it directly would render a bare table with no layout. -->
  <header class="bg-white border-b border-gray-300 px-8 py-3 flex items-center gap-2 text-sm text-gray-600">
    <a href="/" class="hover:text-blue-700">
      <i class="fa-regular fa-users"></i> Patients
    </a>
    <span>/</span>
    <span class="text-gray-900 font-medium">{{ first_name }} {{ last_name }}</span>
  </header>

  <main class="max-w-5xl mx-auto px-8 py-6">

    <!-- Demographics Header -->
    <!-- Clinical Sections -->

  </main>
</body>
</html>
```

### Accessing context variables in the template

Whatever keys you pass in the context dict from the router become variables in the template. If the router passes `context["vitals"] = {...}`, then in the template you write `{{ vitals }}` or iterate with `{% for entry in vitals.get("entry", []) %}`.

### The for/else pattern

Jinja2's `{% for %}` block supports an `{% else %}` clause that renders when the iterable is empty. Always use it for FHIR result sets:

```html
{% for entry in conditions.get("entry", []) %}
  <tr>
    <td>{{ entry.resource.code.coding[0].display if entry.resource.code.coding else "—" }}</td>
  </tr>
{% else %}
  <tr>
    <td colspan="3" class="text-gray-500 px-4 py-2">No conditions on record.</td>
  </tr>
{% endfor %}
```

### Safe nested access

FHIR resources are deeply nested. A field may be absent entirely. Use Jinja2's
`if` and the `default` filter defensively:

```html
{{ entry.resource.valueQuantity.value | default("—") }}
{{ entry.resource.code.coding[0].display if entry.resource.code.coding else "—" }}
```

Do not assume any field is always present, even ones that seem required by the spec — real-world FHIR data is often incomplete.

---

## 8. HTMX — Navigation vs. Dynamic Swaps

### When to use full browser navigation

The activity page uses a full page load, not an HTMX swap. Use `window.location.href` when:

- The target page has a **different layout** (no left nav in this case)
- The target page has its own URL that should appear in the browser address bar
- The user should be able to use the browser back button to return

```javascript
// In main.js, inside patientAction() for the "Activity" option:
window.location.href = `/Patient/${ptid}/activity`;
```

### When to use HTMX swaps

HTMX is the right tool when you want to **replace part of the current page** without a full reload. Your existing modals (view, edit, delete) work this way: the modal content is fetched and injected into `#modal-root`, leaving the rest of the page untouched.

Inside the activity page itself, you may later use HTMX for tab switching (Layout B): clicking a tab fetches only the content for that tab and swaps it into the content area, avoiding a full page reload.

### HTMX attribute quick reference

| Attribute | Purpose |
|-----------|---------|
| `hx-get="/some/url"`      | Fetch URL on trigger event |
| `hx-trigger="click"`      | What user action fires the request |
| `hx-target="#element-id"` | Which element in the DOM to update |
| `hx-swap="innerHTML"`     | Replace the target's inner content |
| `hx-swap="outerHTML"`     | Replace the target element itself |
| `hx-select="#element-id"` | Extract a subset of the response to swap |
| `hx-push-url="true"`      | Update the browser address bar URL |
| `hx-indicator="#spinner"` | Show/hide a loading indicator |

---

## 9. FHIR Resources Reference

### What is a FHIR Bundle?

When you search for resources (e.g., `GET /Observation?patient=123`), the FHIR server returns a **Bundle** — a wrapper object that contains zero or more matching resources. Every FHIR search result has this shape:

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
        ...
      }
    }
  ]
}
```

In your templates, `results.get("entry", [])` iterates over the `entry` array. The actual resource data is always one level deeper: `entry.resource`.

### Patient resource (demographics)

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

### Observation resource (vital signs)

```json
{
  "resourceType": "Observation",
  "status": "final",
  "category": [
    { "coding": [{ "code": "vital-signs" }] }
  ],
  "code": {
    "coding": [{ "system": "http://loinc.org", "code": "8867-4", "display": "Heart rate" }]
  },
  "effectiveDateTime": "2025-03-01T09:15:00Z",
  "valueQuantity": { "value": 72, "unit": "/min" }
}
```

Blood pressure is a special case — it uses `component` instead of `valueQuantity`:

```json
{
  "code": { "coding": [{ "display": "Blood pressure panel" }] },
  "component": [
    { "code": { "coding": [{ "display": "Systolic" }] }, "valueQuantity": { "value": 118, "unit": "mmHg" } },
    { "code": { "coding": [{ "display": "Diastolic" }] }, "valueQuantity": { "value": 76, "unit": "mmHg" } }
  ]
}
```

In your template, check for `entry.resource.component` to handle blood pressure separately from single-value observations.

### Condition resource

```json
{
  "resourceType": "Condition",
  "clinicalStatus": {
    "coding": [{ "code": "active" }]
  },
  "code": {
    "coding": [{ "system": "http://snomed.info/sct", "code": "73211009", "display": "Diabetes mellitus type 2" }],
    "text": "Type 2 Diabetes"
  },
  "onsetDateTime": "2019-06-15",
  "recordedDate": "2019-06-20"
}
```

Use `code.text` first for display — it is the human-readable label. Fall back to `code.coding[0].display` if `text` is absent.

### MedicationRequest resource

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

### AllergyIntolerance resource

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

### LOINC codes for common vital signs

LOINC is the standard coding system for clinical observations. If you want to filter or label vitals by type, these are the codes HAPI/Synthea typically uses:

| LOINC Code | Observation |
|------------|-------------|
| `8867-4`   | Heart rate |
| `9279-1`   | Respiratory rate |
| `8310-5`   | Body temperature |
| `8480-6`   | Systolic blood pressure |
| `8462-4`   | Diastolic blood pressure |
| `55284-4`  | Blood pressure panel (parent) |
| `29463-7`  | Body weight |
| `8302-2`   | Body height |
| `39156-5`  | BMI |
| `59408-5`  | Oxygen saturation (pulse ox) |

---

## 10. Rendering FHIR Data in Templates

### Demographics header snippet

```html
<div class="bg-white rounded-lg border border-gray-300 px-6 py-4 mb-6 flex items-center gap-6">
  <div>
    <h1 class="text-xl font-semibold">{{ first_name }} {{ last_name }}</h1>
    <p class="text-sm text-gray-500">
      {{ gender | title if gender else "—" }}
      &nbsp;|&nbsp;
      DOB: {{ birth_date if birth_date else "—" }}
      &nbsp;|&nbsp;
      Age: {{ age if age else "—" }}
    </p>
  </div>
</div>
```

### Vital signs table snippet

```html
<section class="mb-8">
  <h2 class="text-base font-semibold text-gray-700 mb-2">Vital Signs</h2>
  <table class="w-full text-sm border border-gray-300 rounded">
    <thead class="bg-gray-50 text-gray-600">
      <tr>
        <th class="px-4 py-2 border-b text-left">Date</th>
        <th class="px-4 py-2 border-b text-left">Observation</th>
        <th class="px-4 py-2 border-b text-left">Value</th>
        <th class="px-4 py-2 border-b text-left">Unit</th>
      </tr>
    </thead>
    <tbody>
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
        <td class="px-4 py-2">{{ obs.valueQuantity.unit if obs.valueQuantity is defined else "mmHg" }}</td>
      </tr>
      {% else %}
      <tr>
        <td colspan="4" class="px-4 py-2 text-gray-500">No vital signs on record.</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</section>
```

> **Future Refinement — Move FHIR parsing out of templates**
>
> The template snippets in this section put FHIR-specific extraction logic directly in Jinja2: checking for `valueQuantity` vs `component`, accessing `coding[0].display`, slicing date strings, and so on. This is fine for a first learning implementation and keeps the router and service simple.
>
> As the app matures, consider shaping the data in the service or router before it reaches the template. Instead of passing a raw FHIR Bundle, pass a list of pre-shaped display dicts:
>
> ```python
> {"date": "2025-03-01", "label": "Blood Pressure", "value": "118/76", "unit": "mmHg"}
> ```
>
> The template then only needs `{{ row.label }}` — it no longer needs to understand FHIR structure. This makes templates easier to read, easier to test, and easier to change when the FHIR data shape varies between servers.

### Conditions table snippet

```html
<section class="mb-8">
  <h2 class="text-base font-semibold text-gray-700 mb-2">Conditions</h2>
  <table class="w-full text-sm border border-gray-300 rounded">
    <thead class="bg-gray-50 text-gray-600">
      <tr>
        <th class="px-4 py-2 border-b text-left">Condition</th>
        <th class="px-4 py-2 border-b text-left">Status</th>
        <th class="px-4 py-2 border-b text-left">Onset</th>
      </tr>
    </thead>
    <tbody>
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
          {{ cond.onsetDateTime[:10] if cond.onsetDateTime is defined else
             (cond.onsetPeriod.start[:10] if cond.onsetPeriod is defined else "—") }}
        </td>
      </tr>
      {% else %}
      <tr>
        <td colspan="3" class="px-4 py-2 text-gray-500">No conditions on record.</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</section>
```

---

## 11. Common Pitfalls & Tips

### FHIR data is always optional

The FHIR spec marks many fields as optional (cardinality `0..1` or `0..*`). Even fields that seem logically required — like a patient's name or a condition's onset date — may be absent in real data. Always use defensive access in templates (`if x is defined`, `| default("—")`, `x if x else "—"`).

### Synthea-generated data vs. real data

If your HAPI server is loaded with Synthea-generated synthetic patients, the data is usually well-formed and complete. When you eventually connect to a real clinical FHIR server, expect gaps, nulls, and unexpected field combinations.
Building defensively from the start pays off later.

### `is defined` vs. checking for truthiness in Jinja2

In Jinja2, `{% if x %}` is falsy for `None`, `""`, `0`, `[]`, and `{}`. `{% if x is defined %}` is only falsy when the variable doesn't exist at all in the context. For FHIR dict keys, `entry.resource.valueQuantity` will raise a Jinja2 error if accessed on a resource that doesn't have it — use `entry.resource.get("valueQuantity")` in a filter or test for it with `if "valueQuantity" in entry.resource`.

### The `_patient_to_context()` helper already exists

The router already has `_patient_to_context(patient)` which extracts `first_name`, `last_name`, `gender`, `birth_date`, `age`, `phone`, `marital_status`, and `last_updated` from a Patient dict. Reuse it for the activity page demographics header — no need to duplicate that logic.

### Test routes directly before wiring the UI

After adding a new route, visit it directly in the browser:  
`http://localhost:8000/Patient/{real-patient-id}/activity`

This lets you develop and debug the template completely independently of the action menu wiring. Add a hardcoded patient ID to the URL if needed.

### FHIR server CORS and auth

When calling the FHIR server from Python (server-to-server), CORS does not apply. CORS only restricts browser-to-server calls. Your service layer uses the `requests` library server-side, so CORS headers on HAPI are irrelevant for this architecture.

The `fhir_external_api_token` from settings is only needed for the Medblocks-hosted external server — when running locally against Docker HAPI, that token is typically empty and the `if settings.fhir_external_api_token` guard correctly skips the Authorization header.

### FHIR search: `patient=` vs. `subject=`

The search params in Section 6 use `patient={ptid}` to scope results to a specific patient. This is the correct and most common form for HAPI FHIR and Synthea-generated data — `patient` is a convenience search parameter defined on most clinical resource types.

If you encounter a resource type that returns unexpected or empty results despite the patient having data, try the alternative reference form:

```
subject=Patient/{ptid}
```

Some FHIR servers store the patient link as `subject.reference` (a full reference string like `"Patient/abc-123"`) rather than a plain ID, and the `subject=` parameter searches that field directly. For the resources in this guide (`Observation`, `Condition`, `MedicationRequest`, `AllergyIntolerance`), `patient={ptid}` is the right starting point. If you expand to resources like `Procedure` or `DiagnosticReport`, verify which parameter your server responds to.

### Dates from FHIR are ISO 8601 strings

FHIR `dateTime` values look like `"2025-03-01T09:15:00Z"` or `"2025-03-01"`. Slice the first 10 characters to get a display-friendly date: `obs.effectiveDateTime[:10]`. The `age` Jinja2 filter you already have in the router handles full date-to-age conversion.

### The `title` Jinja2 filter

Jinja2 has a built-in `| title` filter that title-cases a string. `"active" | title` produces `"Active"`. Useful for FHIR status codes which are always lowercase in the spec.
