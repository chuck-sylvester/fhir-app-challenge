# Adding Email and Veteran Status to Patient Records

**Goal:** Add two new data elements — Email Address and Veteran Status — to the Create, Edit, View, and Activity screens. Veteran Status also appears as a badge in the patient list table.

---

## Before You Begin

### Files you will touch

| File | Role |
|---|---|
| `app/services/patient_service.py` | FHIR HTTP calls and data extraction |
| `app/routers/patient.py` | FastAPI route handlers and form parameters |
| `app/templates/partials/create_patient_modal.html` | Create form |
| `app/templates/partials/edit_patient_modal.html` | Edit form (pre-filled) |
| `app/templates/partials/view_patient_modal.html` | Read-only view |
| `app/templates/partials/view_patient_activity.html` | Activity page demographics |
| `app/templates/partials/get_patient_table.html` | Patient list table |

### The pattern every new field follows

Every field travels this path in both directions:

```
FHIR Server JSON
    ↕  patient_service.py  (read: extract from JSON / write: build JSON)
    ↕  patient.py router   (bind Form parameter, pass to service, add to context)
    ↕  Jinja2 templates    (render value / capture input)
```

Understanding this pipeline is the key takeaway. Each part of the guide below reinforces it with a new field.

---

## Core Concepts: Three Objects, Three Roles

Before touching any code, it helps to have a clear mental model of the three distinct data representations the app uses and why each one exists. Confusion here is the most common source of bugs when adding new fields.

---

### The `results` object — a FHIR Bundle for the patient list

`results` appears only in `get_patient_table.html`. It is the raw JSON response that HAPI FHIR returns when you search for patients — a **FHIR Bundle**, which is a container resource that wraps a collection of other resources.

Here is an abridged example of what that JSON looks like:

```json
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 3,
  "entry": [
    {
      "resource": {
        "resourceType": "Patient",
        "id": "abc-123",
        "name": [{ "family": "Lovelace", "given": ["Ada"] }],
        "gender": "female",
        "birthDate": "1815-12-10"
      }
    },
    {
      "resource": { ... }
    }
  ]
}
```

The template accesses it with `results.get("entry", [])` and then reads each `entry.resource` directly. There is **no helper function** between `results` and the template — the table only displays a handful of fields, so Jinja2 navigates the FHIR structure directly inline (e.g., `entry.resource.name[0].family`).

`results` is **never used** by the Create, View, Edit, or Activity routes. It is exclusively the data source for the list table.

---

### `_patient_to_context` — translating one FHIR Patient into flat template variables

When you open the View modal, Edit modal, or Activity page, the route needs to work with a **single** Patient resource rather than a list. The raw FHIR JSON for one patient looks like this:

```json
{
  "resourceType": "Patient",
  "id": "abc-123",
  "name": [
    { "use": "official", "family": "Lovelace", "given": ["Ada"] }
  ],
  "gender": "female",
  "birthDate": "1815-12-10",
  "telecom": [
    { "system": "phone", "value": "555-1234", "use": "home" },
    { "system": "email", "value": "ada@example.com", "use": "home" }
  ],
  "maritalStatus": {
    "coding": [{ "code": "U" }],
    "text": "Never Married"
  }
}
```

FHIR's structure is deeply nested by design — it is built for clinical interoperability, not for rendering HTML. Passing this raw dict to a Jinja2 template would produce verbose, fragile expressions everywhere:

```html
<!-- Without helper — brittle and repetitive in every template -->
{{ patient.name[0].given[0] if patient.name and patient.name[0].given else "—" }}
```

`_patient_to_context` in `app/routers/patient.py` solves this by **translating the FHIR structure into a flat dict of simple variables** before the template ever sees them:

```python
# Inside _patient_to_context — this is what the translation looks like
first_name = patient["name"][0]["given"][0]   # navigates nested FHIR structure
last_name  = patient["name"][0]["family"]     # once, in one place

# Returns a plain dict the template can use cleanly
return {
    "first_name": first_name,
    "last_name":  last_name,
    "phone":      phone,
    "email":      email,
    ...
}
```

The template then receives clean, flat variables:

```html
<!-- With helper — readable in every template -->
{{ first_name }} {{ last_name }}
{{ email if email else "—" }}
```

This helper is called by four routes — `/view`, `/edit`, `/delete-confirm`, and `/activity` — so the parsing logic lives in exactly one place. When you add a new field like `email`, you add the extraction logic once in `_patient_to_context` and all four templates immediately have access to it.

**`_patient_to_context` is a read-direction helper only.** It transforms data coming *from* the FHIR server *to* the templates. It does not write anything.

---

### `create_patient` and `update_patient` — the reverse direction

When a user submits the Create or Edit form, the browser sends flat HTTP form fields:

```
POST /Patient
first_name=Ada&last_name=Lovelace&gender=female&birth_date=1815-12-10&phone=555-1234&email=ada%40example.com
```

FastAPI's route handler receives these as plain Python strings. The strings are then passed to `patient_service.create_patient()` or `patient_service.update_patient()`, whose job is the **inverse of `_patient_to_context`**: assemble those flat strings into the nested FHIR JSON structure the server expects.

```python
def create_patient(first_name, last_name, gender, birth_date,
                   marital_status, phone, email):

    # Build the nested FHIR Patient resource from flat strings
    new_patient = {
        "resourceType": "Patient",
        "name": [{"use": "official", "family": last_name, "given": [first_name]}],
        "gender": gender,
        "birthDate": birth_date,
    }

    # telecom is an array — build it from the individual fields
    telecom = []
    if phone:
        telecom.append({"system": "phone", "value": phone, "use": "home"})
    if email:
        telecom.append({"system": "email", "value": email, "use": "home"})
    if telecom:
        new_patient["telecom"] = telecom

    # POST the assembled resource to HAPI FHIR
    requests.post(f"{settings.fhir_base_url}/Patient", json=new_patient, ...)
```

The FHIR server assigns the resource an `id` and stores it. On the next page load, the table route calls `get_patient("table")` which fetches the list from FHIR again, and the new patient appears.

---

### How the three fit together

```
┌─────────────────────────────────────────────────────────┐
│                     FHIR Server                         │
│  Stores canonical Patient resources as nested JSON      │
└────────────┬────────────────────────────┬───────────────┘
             │  GET /Patient (Bundle)     │  GET /Patient/{id}
             ▼                            ▼
    ┌─────────────────┐        ┌──────────────────────────┐
    │    results      │        │   _patient_to_context()  │
    │  (raw Bundle)   │        │   flat dict of strings   │
    │  used as-is in  │        │   used by View / Edit /  │
    │  list table     │        │   Activity templates     │
    └────────┬────────┘        └────────────┬─────────────┘
             │                              │
             ▼                              ▼
    get_patient_table.html      view / edit / activity templates
             ▲                              ▲
             │         form submit          │
             │  ──────────────────────►     │
             │                    create_patient()
             │                    update_patient()
             │                    (flat strings → nested FHIR JSON)
             │                              │
             └──────────────────────────────┘
                   triggers table refresh
                   via HX-Trigger header
```

When you add a new field to this app, the change always touches all three roles:
1. **`_patient_to_context`** — extract the value from FHIR JSON so templates can display it
2. **`create_patient` / `update_patient`** — write the value into FHIR JSON so it persists
3. **Templates** — show the value (View/Activity) or capture it (Create/Edit)

The router is the coordinator: it calls the service, builds the context, and sends both directions.

---

## Part 1 — Email Address

### 1.1  How FHIR stores contact information

FHIR uses a `telecom` array on the Patient resource. Each entry has a `system` (the type of contact), a `value` (the actual address or number), and an optional `use` (home, work, etc.).

```json
"telecom": [
  { "system": "phone", "value": "555-867-5309", "use": "home" },
  { "system": "email", "value": "ada.lovelace@example.com", "use": "home" }
]
```

Your app already reads and writes `phone` using exactly this structure. Email follows the identical pattern — only the `system` value changes from `"phone"` to `"email"`.

---

### Step 1.1 — Router: Extract email in `_patient_to_context`

**File:** `app/routers/patient.py`

The `_patient_to_context` helper in `patient.py` already loops through `telecom` to find the phone number. Add a second pass (or extend the existing loop) to find the email entry.

**Locate this existing block** (around line 54 in `patient.py`):

```python
phone = ""
if patient.get("telecom"):
    for t in patient["telecom"]:
        if t.get("system") == "phone":
            phone = t.get("value", "")
            break
```

**Replace it with:**

```python
phone = ""
email = ""
if patient.get("telecom"):
    for t in patient["telecom"]:
        if t.get("system") == "phone" and not phone:
            phone = t.get("value", "")
        elif t.get("system") == "email" and not email:
            email = t.get("value", "")
```

> **Why one loop instead of two?**  
> The `telecom` array can hold many entries. A single loop reads it once and extracts both values. The `and not phone` / `and not email` guards ensure we take only the first of each type — matching the pattern already used for phone.

**Add `email` to the return dict** at the bottom of `_patient_to_context`:

```python
return {
    "first_name":      first_name,
    "last_name":       last_name,
    "gender":          gender,
    "birth_date":      birth_date,
    "age":             age,
    "phone":           phone,
    "email":           email,          # ← add this line
    "marital_status":  marital_status,
    "marital_display": marital_display,
    "last_updated":    last_updated,
}
```

---

### Step 1.2 — Service: Write email in `create_patient` and `update_patient`

**File:** `app/services/patient_service.py`

Both functions build a FHIR Patient resource from scratch. The current phone handling is:

```python
if phone:
    new_patient["telecom"] = [{"system": "phone", "value": phone, "use": "home"}]
```

**Replace the phone block in both `create_patient` and `update_patient` with:**

```python
telecom = []
if phone:
    telecom.append({"system": "phone", "value": phone, "use": "home"})
if email:
    telecom.append({"system": "email", "value": email, "use": "home"})
if telecom:
    new_patient["telecom"] = telecom
```

> **Why the list approach?**  
> FHIR's `telecom` is an array by design — a patient can have multiple contact methods. Building a list and assigning it once is cleaner than conditionally overwriting the key.

Also **add `email` to both function signatures**:

```python
def create_patient(first_name: str, last_name: str, gender: str,
                   birth_date: str, marital_status: str, phone: str = "",
                   email: str = ""):
```

```python
def update_patient(ptid: str, first_name: str, last_name: str, gender: str,
                   birth_date: str, marital_status: str = "", phone: str = "",
                   email: str = ""):
```

---

### Step 1.3 — Router: Add `email` form parameter

**File:** `app/routers/patient.py`

Both the `POST /Patient` and `PUT /Patient/{ptid}` handlers accept form fields. Add `email` to each.

**In `post_patient`**, add after the `phone` parameter:

```python
email: str = Form(""),
```

Pass it through to the service call:

```python
patient_service.create_patient(
    first_name, last_name, gender, birth_date, marital_status, phone, email
)
```

**In `put_patient`**, same change — add after `phone`:

```python
email: str = Form(""),
```

And update the service call:

```python
patient_service.update_patient(
    ptid, first_name, last_name, gender, birth_date, marital_status, phone, email
)
```

> **FastAPI form binding:** `Form("")` sets the default to an empty string, so the field is optional — the form submits successfully whether or not the user fills in an email.

---

### Step 1.4 — Template: Create Patient modal

**File:** `app/templates/partials/create_patient_modal.html`

Add this block **after the Phone field** and before the closing `</div>` of the form body:

```html
<!-- Email (optional) -->
<div>
  <label for="email" class="block text-sm font-medium text-gray-700">
    Email Address
  </label>
  <input
    type="email"
    id="email"
    name="email"
    autocomplete="email"
    class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
  >
</div>
```

> **`type="email"`** gives you browser-native format validation for free — no JavaScript needed. The browser will reject clearly invalid values (missing `@`, etc.) before the form even submits.

---

### Step 1.5 — Template: Edit Patient modal

**File:** `app/templates/partials/edit_patient_modal.html`

The Edit modal pre-fills fields using the context values. Add after the Phone field:

```html
<!-- Email -->
<div>
  <label for="edit_email" class="block text-sm font-medium text-gray-700">
    Email Address
  </label>
  <input
    type="email"
    id="edit_email"
    name="email"
    value="{{ email | default('') }}"
    autocomplete="email"
    class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
  >
</div>
```

> **`| default('')`** is a Jinja2 filter that prevents an `undefined` error if `email` is missing from the context for any reason.

---

### Step 1.6 — Template: View Patient modal

**File:** `app/templates/partials/view_patient_modal.html`

The view modal uses a 2-column grid for demographics. Add Email alongside Phone. Locate the Phone block:

```html
<div>
  <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Phone</p>
  <p class="mt-1 text-sm text-gray-800">{{ phone if phone else "—" }}</p>
</div>
```

**Add immediately after it** (inside the same `grid grid-cols-2` div):

```html
<div>
  <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Email</p>
  <p class="mt-1 text-sm text-gray-800">{{ email if email else "—" }}</p>
</div>
```

---

### Step 1.7 — Template: Patient Activity page

**File:** `app/templates/partials/view_patient_activity.html`

The demographics row uses the custom `.demographics-box` CSS class. Add an Email box after the Phone box:

```html
<div class="demographics-box">
  <span class="text-sm">Email</span><br>
  <span class="text-sm font-semibold">{{ email if email else "-" }}</span>
</div>
```

---

### Step 1.8 — Validate: Email round-trip

Follow these steps to confirm the full stack is working.

1. **Create** — Open Create Patient, fill in all fields including an email address, save.
2. **Inspect the raw FHIR resource** — Open your browser's DevTools (Network tab). Click the action menu ellipsis on the new patient row, choose View. The request to `/Patient/{ptid}/view` returns JSON in the network response. Alternatively, navigate directly to `http://localhost:8080/fhir/Patient/{ptid}` in your browser to see the raw FHIR JSON. Confirm the `telecom` array contains both the phone and email entries with the correct `system` values.
3. **View modal** — Confirm the email appears in the View modal.
4. **Edit** — Open Edit, change the email, save. Re-open View and confirm the updated value.
5. **Activity page** — Open Activity from the action menu and confirm email appears in the demographics row.
6. **Empty email** — Create a patient with no email. Confirm all views show `—` and no errors occur.

---

## Part 2 — Veteran Status

### 2.1  How FHIR stores extensions

FHIR R4's Patient resource has no built-in `veteranStatus` field. Non-standard data is stored in the `extension` array. Each extension entry has a `url` (a unique identifier for the extension type) and a typed value.

The **US Core** implementation guide defines a standard extension for this:

```json
"extension": [
  {
    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-veteran-status",
    "valueBoolean": true
  }
]
```

Using the official US Core URL matters for interoperability — any FHIR-aware system that understands US Core will recognize this extension and know exactly what it means.

> **Key vocabulary:** The `valueBoolean` key is a FHIR data type convention. Extensions can hold many types (`valueString`, `valueCode`, `valueDateTime`, etc.). Boolean is the right choice here because veteran status is a yes/no fact.

**The extension URL constant** — define this once at the top of `patient_service.py` so it never gets mistyped:

```python
_VETERAN_STATUS_URL = (
    "http://hl7.org/fhir/us/core/StructureDefinition/us-core-veteran-status"
)
```

---

### Step 2.1 — Router: Extract veteran_status in `_patient_to_context`

**File:** `app/routers/patient.py` (inside `_patient_to_context`)

Add after the `marital_display` block:

```python
veteran_status = False
for ext in patient.get("extension", []):
    if ext.get("url") == patient_service._VETERAN_STATUS_URL:
        veteran_status = ext.get("valueBoolean", False)
        break
```

Add `veteran_status` to the return dict:

```python
return {
    ...
    "veteran_status":  veteran_status,   # ← add this line
    ...
}
```

> **Why `False` as default?** An absent extension and an explicit `valueBoolean: false` are semantically equivalent — the patient is not flagged as a veteran. Defaulting to `False` means templates never receive `None` and don't need an extra guard.

---

### Step 2.2 — Service: Write veteran_status in `create_patient` and `update_patient`

**File:** `app/services/patient_service.py`

Add the `_VETERAN_STATUS_URL` constant near the top of the file, before `create_patient`:

```python
_VETERAN_STATUS_URL = (
    "http://hl7.org/fhir/us/core/StructureDefinition/us-core-veteran-status"
)
```

**Add `veteran_status` to both function signatures:**

```python
def create_patient(first_name: str, last_name: str, gender: str,
                   birth_date: str, marital_status: str, phone: str = "",
                   email: str = "", veteran_status: bool = False):
```

```python
def update_patient(ptid: str, first_name: str, last_name: str, gender: str,
                   birth_date: str, marital_status: str = "", phone: str = "",
                   email: str = "", veteran_status: bool = False):
```

**Write the extension** in both functions, after the `maritalStatus` block:

```python
if veteran_status:
    new_patient["extension"] = [
        {
            "url": _VETERAN_STATUS_URL,
            "valueBoolean": True,
        }
    ]
```

> **Why only write the extension when `True`?** FHIR resources should be as lean as possible. An absent extension means "not set" which is equivalent to `false` for a boolean flag. Writing `valueBoolean: false` explicitly is valid but unnecessary.

---

### Step 2.3 — Router: Add `veteran_status` form parameter

**File:** `app/routers/patient.py`

**Important — how HTML checkboxes work with forms:**  
An HTML checkbox only submits its value when it is *checked*. When unchecked, the field is absent from the form data entirely. FastAPI's `Form(default="")` handles this: a missing field uses the default. We accept the value as a string and convert it to a boolean.

**In `post_patient`**, add after `email`:

```python
veteran_status: str = Form(""),
```

Pass it to the service — convert the string to bool at the call site:

```python
patient_service.create_patient(
    first_name, last_name, gender, birth_date, marital_status,
    phone, email, veteran_status=(veteran_status == "true")
)
```

**In `put_patient`**, same pattern:

```python
veteran_status: str = Form(""),
```

```python
patient_service.update_patient(
    ptid, first_name, last_name, gender, birth_date, marital_status,
    phone, email, veteran_status=(veteran_status == "true")
)
```

> **Why `str` not `bool`?** FastAPI's `Form(False)` with type `bool` does not parse checkbox strings reliably across browsers. Accepting `str` and comparing to `"true"` is the idiomatic and safe approach for HTML form checkboxes.

---

### Step 2.4 — Template: Create Patient modal

**File:** `app/templates/partials/create_patient_modal.html`

Add after the Email field:

```html
<!-- Veteran Status -->
<div class="flex items-center gap-3">
  <input
    type="checkbox"
    id="veteran_status"
    name="veteran_status"
    value="true"
    class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
  >
  <label for="veteran_status" class="text-sm font-medium text-gray-700">
    Veteran Status
  </label>
</div>
```

> The `value="true"` attribute means the form submits `veteran_status=true` when checked. When unchecked, the field is omitted and FastAPI receives the default `""`, which evaluates to `False` in the router.

---

### Step 2.5 — Template: Edit Patient modal

**File:** `app/templates/partials/edit_patient_modal.html`

The edit form must pre-fill the checkbox state from the context. The Jinja2 `checked` attribute trick:

```html
<!-- Veteran Status -->
<div class="flex items-center gap-3">
  <input
    type="checkbox"
    id="edit_veteran_status"
    name="veteran_status"
    value="true"
    {% if veteran_status %}checked{% endif %}
    class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
  >
  <label for="edit_veteran_status" class="text-sm font-medium text-gray-700">
    Veteran Status
  </label>
</div>
```

> **`{% if veteran_status %}checked{% endif %}`** — Jinja2 evaluates `veteran_status` as a Python bool. When `True`, it renders the word `checked` into the HTML attribute list, which the browser interprets as the checkbox being pre-selected.

---

### Step 2.6 — Template: View Patient modal

**File:** `app/templates/partials/view_patient_modal.html`

Add a Veteran Status row to the demographics grid (inside the `grid grid-cols-2` div), after the Email entry:

```html
<div>
  <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Veteran Status</p>
  <p class="mt-1 text-sm text-gray-800">
    {% if veteran_status %}
      <span class="inline-flex items-center gap-1 text-green-700 font-medium">
        <i class="fa-solid fa-shield-halved fa-sm"></i> Yes
      </span>
    {% else %}
      —
    {% endif %}
  </p>
</div>
```

---

### Step 2.7 — Template: Patient Activity page demographics

**File:** `app/templates/partials/view_patient_activity.html`

Two changes here: move the Patient ID to a subheading under the patient name, and add Email and Veteran Status as demographics boxes.

**1. Move FHIR ID under the patient name.** Locate the `<h1>` for the patient name and add a subheading immediately after it:

```html
<h1 class="text-xl font-semibold text-gray-900 pt-2">{{ first_name }} {{ last_name }}</h1>
<p class="text-xs text-gray-400 mt-0.5 mb-2 font-mono">ID: {{ ptid }}</p>
```

**2. Remove the existing "Patient ID" demographics box** — find and delete this block:

```html
<div class="demographics-box">
  <span class="text-sm">Patient ID</span><br>
  <span class="text-sm font-semibold">{{ ptid }}</span>
</div>
```

**3. Add Email and Veteran Status demographics boxes** (after the Phone box):

```html
<div class="demographics-box">
  <span class="text-sm">Email</span><br>
  <span class="text-sm font-semibold">{{ email if email else "-" }}</span>
</div>

<div class="demographics-box">
  <span class="text-sm">Veteran Status</span><br>
  <span class="text-sm font-semibold">
    {% if veteran_status %}
      <span class="text-green-700"><i class="fa-solid fa-shield-halved fa-sm"></i> Yes</span>
    {% else %}
      -
    {% endif %}
  </span>
</div>
```

---

### Step 2.8 — Template: Patient list table

**File:** `app/templates/partials/get_patient_table.html`

Add a Veteran column header in `<thead>` after the Last Updated header:

```html
<th class="px-4 py-2 border-b border-gray-300">Veteran</th>
```

Add the corresponding data cell in `<tbody>` after the Last Updated cell:

```html
<td class="px-4 py-2 text-center">
  {% set ext_list = entry.resource.get("extension", []) %}
  {% set is_veteran = namespace(value=false) %}
  {% for ext in ext_list %}
    {% if ext.get("url") == "http://hl7.org/fhir/us/core/StructureDefinition/us-core-veteran-status" %}
      {% set is_veteran.value = ext.get("valueBoolean", false) %}
    {% endif %}
  {% endfor %}
  {% if is_veteran.value %}
    <span class="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700 ring-1 ring-green-600/20">
      <i class="fa-solid fa-shield-halved fa-xs"></i> Vet
    </span>
  {% endif %}
</td>
```

> **Why repeat the URL in the template instead of using a variable?**  
> Jinja2 templates don't have access to Python module-level constants unless you explicitly pass them in the context. For a one-off lookup like this, the inline URL is acceptable. If you find yourself needing it in more than two templates, pass it from the router as a context value (e.g., `"veteran_url": patient_service._VETERAN_STATUS_URL`).
>
> **`namespace(value=false)`** is a Jinja2 pattern for mutable loop variables. Jinja2's scoping rules prevent a plain `{% set %}` inside a `{% for %}` from being visible outside the loop. `namespace` works around this.

---

### Step 2.9 — Validate: Veteran Status round-trip

1. **Create with Veteran = checked** — Create a patient, check the Veteran Status box, save.
2. **Inspect FHIR JSON** — Navigate to `http://localhost:8080/fhir/Patient/{ptid}`. Confirm the response body contains:
   ```json
   "extension": [
     {
       "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-veteran-status",
       "valueBoolean": true
     }
   ]
   ```
3. **Patient table** — The patient row should show the `Vet` badge in the Veteran column.
4. **View modal** — Open View and confirm Veteran Status shows the shield icon and "Yes".
5. **Edit — uncheck** — Open Edit, uncheck Veteran Status, save. Reload the patient from FHIR. Confirm the `extension` array is absent from the JSON (or the value is `false`).
6. **Create without checking** — Create another patient without checking the box. Confirm no extension is written, the table shows no badge, and all views show `—` or `-`.

---

## Summary checklist

Use this to track progress as you implement each step.

### Part 1 — Email
- [ ] `_patient_to_context`: extract `email` from `telecom`
- [ ] `create_patient`: accept `email` param, write to `telecom`
- [ ] `update_patient`: accept `email` param, write to `telecom`
- [ ] `post_patient` route: add `email: str = Form("")`, pass to service
- [ ] `put_patient` route: add `email: str = Form("")`, pass to service
- [ ] `create_patient_modal.html`: add email `<input type="email">`
- [ ] `edit_patient_modal.html`: add email input with `value="{{ email | default('') }}"`
- [ ] `view_patient_modal.html`: add email display field
- [ ] `view_patient_activity.html`: add email demographics box
- [ ] Validate round-trip (create → FHIR JSON → view → edit → activity)

### Part 2 — Veteran Status
- [ ] `patient_service.py`: add `_VETERAN_STATUS_URL` constant
- [ ] `_patient_to_context`: extract `veteran_status` from `extension`
- [ ] `create_patient`: accept `veteran_status` param, write extension
- [ ] `update_patient`: accept `veteran_status` param, write extension
- [ ] `post_patient` route: add `veteran_status: str = Form("")`, convert to bool
- [ ] `put_patient` route: add `veteran_status: str = Form("")`, convert to bool
- [ ] `create_patient_modal.html`: add checkbox
- [ ] `edit_patient_modal.html`: add checkbox with `{% if veteran_status %}checked{% endif %}`
- [ ] `view_patient_modal.html`: add veteran status display
- [ ] `view_patient_activity.html`: move FHIR ID to subheading, add veteran + email boxes, remove old Patient ID box
- [ ] `get_patient_table.html`: add Veteran column header and badge cell
- [ ] Validate round-trip (create checked → FHIR JSON → table badge → view → edit uncheck → verify)
