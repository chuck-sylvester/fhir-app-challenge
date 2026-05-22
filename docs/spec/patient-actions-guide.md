# Patient Actions Guide: View, Edit, and Delete from the Patient Table

This guide explains how to implement a row-level action menu on the patient table. When a clinician clicks the ellipsis icon (`fa-ellipsis-vertical`) on any row, a small dropdown menu appears with three options: View, Edit, and Delete. Each option opens a modal or triggers a confirmation before acting on the selected patient.

---

## 1. Overview of the Approach

The full feature involves three layers working together:

| Layer | Responsibility |
|---|---|
| Jinja2 template | Pass the patient ID from each table row into the button's `onclick` |
| JavaScript (`main.js`) | Build and show the dropdown menu, call `htmx.ajax()` for each action |
| HTMX | Load modal partials from the server into `#modal-root` |
| FastAPI routes | Serve the view, edit, and delete-confirm modal partials; handle PUT and DELETE |
| Service layer | `get_patient()` already exists; `update_patient()` is new |
| Jinja2 partials | `view_patient_modal.html`, `edit_patient_modal.html`, `delete_confirm_modal.html` |

The pattern re-uses everything already in place: `#modal-root` in `base.html`, the same HTMX swap pattern used by the create modal, and the same service/router structure.

---

## 2. The Three Actions at a Glance

| Action | Trigger | Server Round-Trips | Outcome |
|---|---|---|---|
| **View** | Menu → View | 1 GET | Read-only modal, close with Cancel |
| **Edit** | Menu → Edit | 1 GET (form), 1 PUT (save) | Pre-filled form modal; save refreshes table |
| **Delete** | Menu → Delete | 1 GET (confirm), 1 DELETE | Confirmation modal; confirm refreshes table |

---

## 3. How the Patient ID Flows from the Template to JavaScript

The patient table is rendered by Jinja2 in `get_patient_table.html`. Each row's ellipsis button is currently calling `patientAction()` with no arguments. To implement the actions, the button needs to pass two things to JavaScript:

1. The **patient resource ID** — so the server knows which patient to act on.
2. The **button element itself** — so JavaScript knows where to position the dropdown menu.

The FHIR resource ID for each patient is `entry.resource.id`.

### Current button (in `get_patient_table.html`):

```html
<button
  class="block rounded-md px-2 py-2 hover:cursor-pointer hover:bg-blue-50"
  onclick="patientAction()"
>
  <i class="fa-solid fa-ellipsis-vertical fa-lg px-2"></i>
</button>
```

### Updated button:

```html
<button
  class="block rounded-md px-2 py-2 hover:cursor-pointer hover:bg-blue-50"
  onclick="patientAction('{{ entry.resource.id }}', this)"
>
  <i class="fa-solid fa-ellipsis-vertical fa-lg px-2"></i>
</button>
```

One change:
- `patientAction()` becomes `patientAction('{{ entry.resource.id }}', this)` — Jinja2 will render the actual patient ID (e.g., `'abc-123'`) into the page at render time; `this` is the button element.

---

## 4. The Action Dropdown Menu

The dropdown is a small floating `<div>` created and positioned by JavaScript when the ellipsis button is clicked. It is not fetched from the server — it is built entirely in the browser. This keeps it instant and avoids an unnecessary server round-trip just to show three buttons.

### Key behaviors the dropdown needs:

- Appear near the clicked button.
- Close when the user clicks anywhere outside it.
- Close when the user presses Escape.
- Only one menu open at a time.
- Each menu option triggers the correct HTMX request and then closes the menu.

### How to trigger HTMX from JavaScript

HTMX normally activates when it finds `hx-*` attributes on elements that were present in the page when it loaded. For dynamically created elements (like a JavaScript-built dropdown), you have two options:

- **Option A**: Call `htmx.process(element)` on the new element so HTMX scans it for `hx-*` attributes.
- **Option B**: Call `htmx.ajax()` directly from JavaScript — no `hx-*` attributes needed on the element at all.

**Option B is simpler and recommended here.** Each menu item calls a small JavaScript function that invokes `htmx.ajax()`. This keeps the dropdown HTML clean and avoids the `htmx.process()` step.

### `htmx.ajax()` signature

```javascript
htmx.ajax(method, url, { target: selector, swap: swapStyle });
```

- `method` — `'GET'`, `'POST'`, `'PUT'`, `'DELETE'`, etc.
- `url` — the URL to request
- `target` — a CSS selector for the element to update (`'#modal-root'`)
- `swap` — how to replace content (`'innerHTML'`)

This is functionally identical to `hx-get="/some/url" hx-target="#modal-root" hx-swap="innerHTML"` on an element, just called from code.

---

## 5. Updated `main.js`

Replace the current stub `patientAction()` with this complete implementation:

```javascript
// ----------------------------------------------------------------
// app/static/js/main.js
// ----------------------------------------------------------------

function patientAction(ptid, btn) {
  closePatientMenu();

  const menu = document.createElement('div');
  menu.id = 'patient-action-menu';
  menu.className = [
    'absolute z-50 bg-white border border-gray-200 rounded-md shadow-lg py-1 w-44',
    'text-sm text-gray-700'
  ].join(' ');

  // Position the menu below and slightly left of the button
  const rect = btn.getBoundingClientRect();
  menu.style.top  = `${rect.bottom + window.scrollY + 4}px`;
  menu.style.left = `${rect.right  + window.scrollX - 176}px`; // 176px = w-44

  menu.innerHTML = `
    <button
      class="flex items-center gap-2 w-full text-left px-4 py-2 hover:bg-gray-100"
      onclick="viewPatient('${ptid}')"
    >
      <i class="fa-regular fa-eye w-4"></i> View
    </button>
    <button
      class="flex items-center gap-2 w-full text-left px-4 py-2 hover:bg-gray-100"
      onclick="editPatient('${ptid}')"
    >
      <i class="fa-regular fa-pen-to-square w-4"></i> Edit
    </button>
    <hr class="my-1 border-gray-200">
    <button
      class="flex items-center gap-2 w-full text-left px-4 py-2 text-red-600 hover:bg-red-50"
      onclick="confirmDeletePatient('${ptid}')"
    >
      <i class="fa-regular fa-trash-can w-4"></i> Delete
    </button>
  `;

  document.body.appendChild(menu);

  // Close the menu when clicking anywhere outside it
  setTimeout(() => {
    document.addEventListener('click', closePatientMenu, { once: true });
  }, 0);
}

function closePatientMenu() {
  const menu = document.getElementById('patient-action-menu');
  if (menu) menu.remove();
}

function viewPatient(ptid) {
  closePatientMenu();
  htmx.ajax('GET', `/Patient/${ptid}/view`, { target: '#modal-root', swap: 'innerHTML' });
}

function editPatient(ptid) {
  closePatientMenu();
  htmx.ajax('GET', `/Patient/${ptid}/edit`, { target: '#modal-root', swap: 'innerHTML' });
}

function confirmDeletePatient(ptid) {
  closePatientMenu();
  htmx.ajax('GET', `/Patient/${ptid}/delete-confirm`, { target: '#modal-root', swap: 'innerHTML' });
}
```

### Why `setTimeout(..., 0)` before adding the outside-click listener?

When the user clicks the ellipsis button, two things happen: the button's `onclick` runs (creating the menu), and then the click event bubbles up through the DOM. If the outside-click listener is added immediately, the same click that opened the menu also triggers the listener and closes it instantly. The `setTimeout(..., 0)` defers the listener registration until after the current click event has fully finished propagating. This is a standard browser pattern for this situation.

### When and how `closePatientMenu()` is called

`closePatientMenu()` removes the floating dropdown div from the DOM. It is called in four distinct situations:

1. **At the start of `patientAction()`** — before building a new menu. If the user clicks a second ellipsis button while a menu is already open, this ensures the old menu is removed before the new one is created. Without this, clicking a second row would leave two menus on the page simultaneously.

2. **By the outside-click listener** — the `setTimeout`-deferred `document.addEventListener('click', closePatientMenu, { once: true })` fires when the user next clicks anywhere on the page. The `{ once: true }` option makes the listener self-removing after it fires once, so it does not accumulate across multiple menu opens.

3. **By `viewPatient()`, `editPatient()`, and `confirmDeletePatient()`** — each of these functions calls `closePatientMenu()` as its first line, before issuing the HTMX request. This closes the dropdown immediately when the user selects an option, so the menu disappears before the modal appears.

4. **By the Escape key handler** — covered in Section 6 below. This handler does not exist yet and must be added to `base.html`.

The function itself is deliberately simple: it looks for the element with `id="patient-action-menu"` and removes it. If no menu is open, `menu` is `null` and the `if (menu)` guard prevents an error. This makes it safe to call defensively from multiple places.

---

## 6. Escape Key to Close the Menu and Modals

> **Implementation status**: This has not been implemented yet. The Escape key currently does nothing. The code in this section must be added to `base.html` before Escape-to-close will work for either the action menu or any of the modals.

### What needs to happen

Pressing Escape should close whatever the user currently has open:
- If the action menu (dropdown) is open, close it.
- If a modal is open (View, Edit, Delete Confirm, or Create Patient), close it.
- If nothing is open, do nothing.

Both the action menu and all modals need to be handled by a single listener. A single listener in one place is easier to maintain than separate listeners scattered across different template files.

### Why the listener belongs in `base.html`, not in `main.js` or a modal partial

There are three possible places to put a `keydown` listener. Understanding why `base.html` is the right choice helps avoid a common mistake:

- **Inside a modal partial** (e.g., in a `<script>` tag in `view_patient_modal.html`): This is wrong. HTMX swaps the modal HTML into `#modal-root` each time a modal opens. If the listener is inside the modal partial, a new listener is registered every time the modal opens. Listeners do not automatically remove themselves when HTMX swaps the element out. After opening and closing the modal several times, there would be multiple active listeners — each one calling `closePatientMenu()` on every Escape keypress, even when no modal is open.

- **In `main.js`** (inside a function): Also wrong for the same accumulation reason if the function is called multiple times, or disconnected from the modal state if the function is only called once during initialization.

- **In `base.html`** (as a `<script>` block just before `</body>`): Correct. `base.html` is the application shell — it loads once and is never swapped out. A `keydown` listener added here runs for the entire lifetime of the page and handles Escape regardless of which modal is currently open.

### How `keydown` events work

`keydown` is a browser event that fires whenever the user presses any key while the browser window is focused. You register a listener on `document` because keyboard events bubble up to the document level regardless of which element has focus.

The event object passed to the handler has a `key` property that contains a string identifying the key that was pressed. For the Escape key, `e.key === 'Escape'`. This is the modern, reliable way to detect it — the older `e.keyCode === 27` approach works but is deprecated.

When the handler fires, it calls both close functions. The order does not matter; both are safe to call even if nothing is currently open.

### The code to add to `base.html`

Add this `<script>` block just before the closing `</body>` tag in `base.html`, after the `<script src="/static/js/main.js"></script>` line. Placing it after `main.js` ensures that `closePatientMenu` is already defined before this code runs.

```html
<script>
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      document.getElementById('modal-root').innerHTML = '';
      closePatientMenu();
    }
  });
</script>
```

After adding this, `base.html`'s closing body section should look like:

```html
     <div id="modal-root"></div>

     <script src="/static/js/main.js"></script>
     <script>
       document.addEventListener('keydown', function(e) {
         if (e.key === 'Escape') {
           document.getElementById('modal-root').innerHTML = '';
           closePatientMenu();
         }
       });
     </script>
    </body>
</html>
```

### What each line does

- `document.addEventListener('keydown', ...)` — registers a listener on the document for all keydown events, for the lifetime of the page.
- `if (e.key === 'Escape')` — filters for only the Escape key; all other keys fall through without action.
- `document.getElementById('modal-root').innerHTML = ''` — clears the modal root div. If a modal is open, this removes its HTML and the modal disappears. If no modal is open, `modal-root` is already empty and setting `innerHTML` to `''` is harmless.
- `closePatientMenu()` — removes the action dropdown if it exists. If no dropdown is open, the `if (menu)` guard inside the function makes this a no-op.

### This single block covers all modals

Because all modals (View, Edit, Delete Confirm, Create Patient) render into `#modal-root`, clearing `modal-root.innerHTML` closes all of them. You do not need to add any Escape handling to individual modal template files.

---

## 7. New FastAPI Routes Required

Three new GET routes and one new PUT route are needed. Add them to `app/routers/patient.py`.

### Route ordering note

FastAPI matches routes in the order they are registered. Literal path segments (`/view`, `/edit`, `/delete-confirm`) are matched before parameter wildcards (`{ptid}`), so these new routes can safely be added after `GET /Patient/{ptid}` without conflict. However, it is still good practice to group related routes together.

### Route summary

```text
GET  /Patient/{ptid}/view           → view_patient_modal.html
GET  /Patient/{ptid}/edit           → edit_patient_modal.html  (pre-filled)
PUT  /Patient/{ptid}                → update patient, refresh table
GET  /Patient/{ptid}/delete-confirm → delete_confirm_modal.html
DELETE /Patient/{ptid}              → already exists (needs response updated)
```

### Route implementations

```python
from datetime import date

@router.get("/Patient/{ptid}/view", response_class=HTMLResponse)
async def get_patient_view(request: Request, ptid: str):
    patient = patient_service.get_patient(ptid)
    context = _patient_to_context(patient)
    context["ptid"] = ptid
    return templates.TemplateResponse(request, "partials/view_patient_modal.html", context)


@router.get("/Patient/{ptid}/edit", response_class=HTMLResponse)
async def get_patient_edit(request: Request, ptid: str):
    patient = patient_service.get_patient(ptid)
    context = _patient_to_context(patient)
    context["ptid"] = ptid
    return templates.TemplateResponse(request, "partials/edit_patient_modal.html", context)


@router.put("/Patient/{ptid}", response_class=HTMLResponse)
async def put_patient(
    request: Request,
    ptid: str,
    first_name:     str = Form(...),
    last_name:      str = Form(...),
    gender:         str = Form(...),
    birth_date:     str = Form(...),
    marital_status: str = Form(""),
    phone:          str = Form(""),
):
    try:
        patient_service.update_patient(ptid, first_name, last_name, gender,
                                       birth_date, marital_status, phone)
    except Exception:
        patient = patient_service.get_patient(ptid)
        context = _patient_to_context(patient)
        context["ptid"] = ptid
        context["error"] = "Failed to update patient. Please try again."
        return templates.TemplateResponse(request, "partials/edit_patient_modal.html", context)

    response = HTMLResponse(content="", status_code=200)
    response.headers["HX-Trigger"] = "patient-updated"
    return response


@router.get("/Patient/{ptid}/delete-confirm", response_class=HTMLResponse)
async def get_patient_delete_confirm(request: Request, ptid: str):
    patient = patient_service.get_patient(ptid)
    name = "this patient"
    if patient.get("name") and patient["name"][0].get("given"):
        given  = patient["name"][0]["given"][0]
        family = patient["name"][0].get("family", "")
        name   = f"{given} {family}".strip()
    return templates.TemplateResponse(
        request,
        "partials/delete_confirm_modal.html",
        {"ptid": ptid, "patient_name": name}
    )
```

### Helper function `_patient_to_context`

Both the view and edit routes need to extract the same fields from a FHIR Patient resource dict. Extract this logic into a private helper in `patient.py` to avoid repeating it:

```python
def _patient_to_context(patient: dict) -> dict:
    """Extract display fields from a FHIR Patient resource dict."""
    first_name = ""
    last_name  = ""
    if patient.get("name"):
        n = patient["name"][0]
        if n.get("given"):
            first_name = n["given"][0]
        last_name = n.get("family", "")

    gender     = patient.get("gender", "")
    birth_date = patient.get("birthDate", "")

    age = None
    if birth_date:
        birth = date.fromisoformat(birth_date)
        today = date.today()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

    phone = ""
    if patient.get("telecom"):
        for t in patient["telecom"]:
            if t.get("system") == "phone":
                phone = t.get("value", "")
                break

    marital_status = ""
    marital_display = ""
    if patient.get("maritalStatus") and patient["maritalStatus"].get("coding"):
        marital_status  = patient["maritalStatus"]["coding"][0].get("code", "")
        marital_display = patient["maritalStatus"].get("text", marital_status)

    last_updated = ""
    if patient.get("meta") and patient["meta"].get("lastUpdated"):
        last_updated = patient["meta"]["lastUpdated"][:10]

    return {
        "first_name":      first_name,
        "last_name":       last_name,
        "gender":          gender,
        "birth_date":      birth_date,
        "age":             age,
        "phone":           phone,
        "marital_status":  marital_status,
        "marital_display": marital_display,
        "last_updated":    last_updated,
    }
```

Place this function above the routes in `patient.py`, after the `templates` declaration. Because it is a module-level function (not a coroutine) and is only called from within the router file, it does not need to be in the service layer.

---

## 8. Service Layer: `update_patient()`

Add this function to `app/services/patient_service.py`. Its structure mirrors `create_patient()`, but uses HTTP `PUT` with the patient ID in the URL.

```python
def update_patient(ptid: str, first_name: str, last_name: str, gender: str,
                   birth_date: str, marital_status: str = "", phone: str = ""):
    updated = {
        "resourceType": "Patient",
        "id": ptid,
        "active": True,
        "name": [{"use": "official", "family": last_name, "given": [first_name]}],
        "gender": gender,
        "birthDate": birth_date,
    }
    if phone:
        updated["telecom"] = [{"system": "phone", "value": phone, "use": "home"}]
    if marital_status:
        display = _MARITAL_DISPLAY.get(marital_status, marital_status)
        updated["maritalStatus"] = {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                "code": marital_status,
                "display": display,
            }],
            "text": display,
        }

    headers = {"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"}
    if settings.fhir_external_api_token:
        headers["Authorization"] = f"Bearer {settings.fhir_external_api_token}"

    output = requests.put(
        f"{settings.fhir_base_url}/Patient/{ptid}",
        json=updated,
        headers=headers
    )
    output.raise_for_status()
    return output.json()
```

### FHIR PUT vs POST

The FHIR server uses HTTP `PUT` for updates and HTTP `POST` for creates. An important difference: a `PUT` request to `/Patient/{id}` must include the `"id"` field in the resource body matching the URL parameter. If the IDs do not match, the FHIR server will reject the request. The `update_patient()` function above includes `"id": ptid` in the dict for this reason.

---

## 9. Updating the Existing DELETE Route

The existing `DELETE /Patient/{ptid}` route tries to render `delete_patient_result.html` which does not exist. Now that there is a `#modal-root` pattern and a table refresh mechanism, update this route to clear the modal and trigger a table refresh:

```python
@router.delete("/Patient/{ptid}", response_class=HTMLResponse)
async def delete_patient(request: Request, ptid: str):
    patient_service.delete_patient(ptid)
    response = HTMLResponse(content="", status_code=200)
    response.headers["HX-Trigger"] = "patient-deleted"
    return response
```

Note: the existing `delete_patient()` service function returns `output.json()`. Some FHIR servers return an `OperationOutcome` body for a DELETE, but others return an empty `204 No Content`. To avoid a JSON decode error on a `204`, you can update the service function to handle that:

```python
def delete_patient(ptid: str):
    base_url = settings.fhir_base_url
    headers = {"Accept": "application/fhir+json"}
    if settings.fhir_external_api_token:
        headers["Authorization"] = f"Bearer {settings.fhir_external_api_token}"
    output = requests.delete(f"{base_url}/Patient/{ptid}", headers=headers)
    if output.content:
        return output.json()
    return {}
```

---

## 10. New Jinja2 Partials

Three new template files are needed in `app/templates/partials/`.

### 10a. `view_patient_modal.html` — Read-Only Patient Detail

This modal displays the patient's key fields in a clean, read-only layout. All variables come from the `_patient_to_context()` helper.

```html
<div class="fixed inset-0 z-50">

  <!-- Backdrop -->
  <div
    class="fixed inset-0 bg-black/40"
    onclick="document.getElementById('modal-root').innerHTML = ''"
  ></div>

  <!-- Centering wrapper -->
  <div class="fixed inset-0 flex items-center justify-center p-4">
    <section
      role="dialog"
      aria-modal="true"
      aria-labelledby="view-patient-title"
      class="relative w-full max-w-lg rounded-lg bg-white shadow-xl"
    >
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h2 id="view-patient-title" class="text-lg font-semibold text-gray-800">
          Patient Record
        </h2>
        <button
          type="button"
          onclick="document.getElementById('modal-root').innerHTML = ''"
          class="text-gray-400 hover:text-gray-600"
          aria-label="Close"
        >
          <i class="fa-solid fa-xmark fa-lg"></i>
        </button>
      </div>

      <!-- Body -->
      <div class="px-6 py-5 space-y-5">

        <!-- Name and ID -->
        <div>
          <p class="text-xl font-semibold text-gray-900">
            {{ first_name }} {{ last_name }}
          </p>
          <p class="text-xs text-gray-400 mt-1">
            FHIR ID: {{ ptid }}
          </p>
        </div>

        <hr class="border-gray-200">

        <!-- Demographics -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Gender</p>
            <p class="mt-1 text-sm text-gray-800 capitalize">{{ gender if gender else "—" }}</p>
          </div>
          <div>
            <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Date of Birth</p>
            <p class="mt-1 text-sm text-gray-800">
              {{ birth_date if birth_date else "—" }}
              {% if age is not none %}<span class="text-gray-400"> (age {{ age }})</span>{% endif %}
            </p>
          </div>
          <div>
            <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Marital Status</p>
            <p class="mt-1 text-sm text-gray-800">{{ marital_display if marital_display else "—" }}</p>
          </div>
          <div>
            <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Phone</p>
            <p class="mt-1 text-sm text-gray-800">{{ phone if phone else "—" }}</p>
          </div>
        </div>

        <hr class="border-gray-200">

        <!-- FHIR Metadata -->
        <div>
          <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Last Updated</p>
          <p class="mt-1 text-sm text-gray-800">{{ last_updated if last_updated else "—" }}</p>
        </div>

      </div>

      <!-- Footer -->
      <div class="px-6 py-4 border-t border-gray-200 flex justify-end">
        <button
          type="button"
          onclick="document.getElementById('modal-root').innerHTML = ''"
          class="rounded-md px-4 py-2 text-sm text-gray-600 hover:bg-gray-100"
        >
          Close
        </button>
      </div>
    </section>
  </div>
</div>
```

### 10b. `edit_patient_modal.html` — Pre-Filled Edit Form

This modal reuses the same field set as `create_patient_modal.html`, but with pre-filled `value` attributes and `hx-put` instead of `hx-post`.

Key differences from the create modal:
- Title is "Edit Patient" instead of "Create Patient".
- Form uses `hx-put="/Patient/{{ ptid }}"` — HTMX's `hx-put` sends an HTTP `PUT` request.
- Every input has a `value="{{ field | default('') }}"` attribute.
- The gender and marital status selects use `{% if ... %}selected{% endif %}` on the matching option.
- No Reset button — resetting a pre-filled edit form to blank would be confusing. Cancel is the escape hatch.
- Save button label is "Save Changes".

```html
<div class="fixed inset-0 z-50">

  <div
    class="fixed inset-0 bg-black/40"
    onclick="document.getElementById('modal-root').innerHTML = ''"
  ></div>

  <div class="fixed inset-0 flex items-center justify-center p-4">
    <section
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-patient-title"
      class="relative w-full max-w-lg rounded-lg bg-white shadow-xl"
    >
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 id="edit-patient-title" class="text-lg font-semibold text-gray-800">
          Edit Patient
        </h2>
      </div>

      <form
        hx-put="/Patient/{{ ptid }}"
        hx-target="#modal-root"
        hx-swap="innerHTML"
      >
        <div class="px-6 py-4 space-y-4">

          {% if error %}
          <div class="rounded-md bg-red-50 border border-red-300 px-4 py-2 text-sm text-red-700">
            {{ error }}
          </div>
          {% endif %}

          <div>
            <label for="edit_first_name" class="block text-sm font-medium text-gray-700">
              First Name <span class="text-red-500">*</span>
            </label>
            <input
              type="text" id="edit_first_name" name="first_name" required
              value="{{ first_name | default('') }}"
              class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
          </div>

          <div>
            <label for="edit_last_name" class="block text-sm font-medium text-gray-700">
              Last Name <span class="text-red-500">*</span>
            </label>
            <input
              type="text" id="edit_last_name" name="last_name" required
              value="{{ last_name | default('') }}"
              class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
          </div>

          <div>
            <label for="edit_gender" class="block text-sm font-medium text-gray-700">
              Gender <span class="text-red-500">*</span>
            </label>
            <select
              id="edit_gender" name="gender" required
              class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">-- Select --</option>
              <option value="male"    {% if gender == 'male'    %}selected{% endif %}>Male</option>
              <option value="female"  {% if gender == 'female'  %}selected{% endif %}>Female</option>
              <option value="other"   {% if gender == 'other'   %}selected{% endif %}>Other</option>
              <option value="unknown" {% if gender == 'unknown' %}selected{% endif %}>Unknown</option>
            </select>
          </div>

          <div>
            <label for="edit_birth_date" class="block text-sm font-medium text-gray-700">
              Date of Birth <span class="text-red-500">*</span>
            </label>
            <input
              type="date" id="edit_birth_date" name="birth_date" required
              value="{{ birth_date | default('') }}"
              class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
          </div>

          <div>
            <label for="edit_marital_status" class="block text-sm font-medium text-gray-700">
              Marital Status
            </label>
            <select
              id="edit_marital_status" name="marital_status"
              class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">-- Select --</option>
              <option value="M" {% if marital_status == 'M' %}selected{% endif %}>Married</option>
              <option value="D" {% if marital_status == 'D' %}selected{% endif %}>Divorced</option>
              <option value="L" {% if marital_status == 'L' %}selected{% endif %}>Legally Separated</option>
              <option value="W" {% if marital_status == 'W' %}selected{% endif %}>Widowed</option>
              <option value="U" {% if marital_status == 'U' %}selected{% endif %}>Never Married</option>
            </select>
          </div>

          <div>
            <label for="edit_phone" class="block text-sm font-medium text-gray-700">
              Phone Number
            </label>
            <input
              type="tel" id="edit_phone" name="phone"
              value="{{ phone | default('') }}"
              class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
          </div>

        </div>

        <div class="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <button
            type="button"
            onclick="document.getElementById('modal-root').innerHTML = ''"
            class="rounded-md px-4 py-2 text-sm text-gray-600 hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Save Changes
          </button>
        </div>
      </form>
    </section>
  </div>
</div>
```

### Why `hx-put` Works for Edit

HTMX supports `hx-put` natively and sends a proper HTTP `PUT` request. The FastAPI route is registered with `@router.put(...)`. The form fields are serialized and sent as a form-encoded body, exactly like `hx-post`. FastAPI reads them with `Form(...)` parameters the same way.

### 10c. `delete_confirm_modal.html` — Confirmation Dialog

This modal is small and focused: it identifies the patient by name and asks for explicit confirmation before deleting. The Confirm Delete button sends the actual `DELETE` request.

```html
<div class="fixed inset-0 z-50">

  <div
    class="fixed inset-0 bg-black/40"
    onclick="document.getElementById('modal-root').innerHTML = ''"
  ></div>

  <div class="fixed inset-0 flex items-center justify-center p-4">
    <section
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="delete-confirm-title"
      class="relative w-full max-w-sm rounded-lg bg-white shadow-xl"
    >
      <div class="px-6 py-5">
        <div class="flex items-start gap-4">
          <div class="flex-shrink-0 rounded-full bg-red-100 p-2">
            <i class="fa-solid fa-triangle-exclamation text-red-600"></i>
          </div>
          <div>
            <h2 id="delete-confirm-title" class="text-base font-semibold text-gray-900">
              Delete Patient
            </h2>
            <p class="mt-1 text-sm text-gray-600">
              Are you sure you want to delete <strong>{{ patient_name }}</strong>?
              This action cannot be undone.
            </p>
          </div>
        </div>
      </div>

      <div class="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
        <button
          type="button"
          onclick="document.getElementById('modal-root').innerHTML = ''"
          class="rounded-md px-4 py-2 text-sm text-gray-600 hover:bg-gray-100"
        >
          Cancel
        </button>
        <button
          type="button"
          hx-delete="/Patient/{{ ptid }}"
          hx-target="#modal-root"
          hx-swap="innerHTML"
          class="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          Confirm Delete
        </button>
      </div>
    </section>
  </div>
</div>
```

The Confirm Delete button uses `hx-delete` directly on the button element (not inside a `<form>`). This is valid HTMX — `hx-*` attributes can go on any element. Because the button is rendered by the server in a Jinja2 template (not dynamically created by JavaScript), HTMX will activate it automatically on page load without needing `htmx.process()`.

---

## 11. Refreshing the Patient Table After Edit or Delete

Just as the Create Patient flow uses `HX-Trigger: patient-created` to refresh the table, the edit and delete flows can use similar triggers.

The server returns:
- `HX-Trigger: patient-updated` after a successful PUT
- `HX-Trigger: patient-deleted` after a successful DELETE

The patient table wrapper in the patient page template needs to listen for all three events. Update the wrapper div that wraps the patient table content area:

```html
<div
  id="patient-table-wrapper"
  hx-get="/Patient/table"
  hx-trigger="patient-created from:body, patient-updated from:body, patient-deleted from:body"
  hx-target="#patient-table-wrapper"
  hx-swap="innerHTML"
>
  <!-- patient table renders here -->
</div>
```

The `from:body` qualifier tells HTMX to listen for the event from anywhere on the page, not just from this element. All three trigger names are comma-separated in the single `hx-trigger` attribute.

---

## 12. Files Changed vs. Files Added

### Files you will modify

| File | Change |
|---|---|
| `app/static/js/main.js` | Replace stub with full dropdown + action functions |
| `app/templates/partials/get_patient_table.html` | Pass `ptid` and `this` to `patientAction()` |
| `app/templates/base.html` | Add `closePatientMenu()` call to the Escape key handler |
| `app/routers/patient.py` | Add `_patient_to_context()` helper, three new GET routes, one new PUT route; update DELETE route response |
| `app/services/patient_service.py` | Add `update_patient()` function; fix `delete_patient()` to handle empty response body |

### Files you will create

| File | Purpose |
|---|---|
| `app/templates/partials/view_patient_modal.html` | Read-only patient detail modal |
| `app/templates/partials/edit_patient_modal.html` | Pre-filled edit form modal |
| `app/templates/partials/delete_confirm_modal.html` | Delete confirmation dialog |

---

## 13. Suggested Implementation Sequence

Each step is independently testable before moving to the next.

**Step 1 — Wire the patient ID into the ellipsis button**

In `get_patient_table.html`, update the `onclick` to pass `'{{ entry.resource.id }}'` and `this`. Open the browser, load the patient table, open the developer console, and click an ellipsis button. You should see `undefined` go away from the alert — the next step replaces it with the real function.

**Step 2 — Update `patientAction()` in `main.js`**

Replace the stub with the full dropdown implementation from Section 5. Test that:
- Clicking the ellipsis shows a dropdown menu with View, Edit, Delete options.
- Clicking outside the menu closes it.
- Pressing Escape closes it.
- The menu does not flash open-and-immediately-close (this is what the `setTimeout` prevents).

**Step 3 — Implement the View modal**

Add the `GET /Patient/{ptid}/view` route and `view_patient_modal.html`. Add `_patient_to_context()` to the router file. Test that clicking View opens a nicely formatted modal with the patient's actual data from the FHIR server. Close with the X button, the backdrop, or Escape.

**Step 4 — Implement the Delete confirmation flow**

Add the `GET /Patient/{ptid}/delete-confirm` route and `delete_confirm_modal.html`. Update the DELETE route response (Section 9). Add `hx-trigger` for `patient-deleted` to the table wrapper. Test the full flow:
1. Click ellipsis → Delete.
2. Confirmation modal appears with the patient's name.
3. Click Cancel — modal closes, patient still in table.
4. Click ellipsis → Delete again → Confirm Delete.
5. Modal closes, table refreshes, patient is gone.

**Step 5 — Implement the Edit modal**

This is the most involved step. Add `update_patient()` to the service layer, add the `GET /Patient/{ptid}/edit` and `PUT /Patient/{ptid}` routes, and create `edit_patient_modal.html`. Add `patient-updated` to the table wrapper trigger. Test:
1. Click ellipsis → Edit.
2. Modal opens with the patient's current data pre-filled.
3. Change a field and click Save Changes.
4. Modal closes, table refreshes, updated data appears.
5. Open the modal again and confirm the change persisted.
6. Test the error path by temporarily breaking the service call.

**Step 6 — Polish**

- Verify the Escape key closes both modals and the action menu.
- Check that `hx-disabled-elt` or the `htmx-request` class can be used on the Save Changes button to prevent double-submission during the PUT.
- Spot-check that the Create Patient modal still works (no regressions).

---

## 14. Important Concepts Summary

| Concept | What to know |
|---|---|
| `htmx.ajax()` | Programmatic HTMX request from JavaScript; avoids needing `htmx.process()` on dynamic elements |
| `htmx.process(el)` | Required if you add `hx-*` attributes to dynamically created elements without using `htmx.ajax()` |
| `hx-put` | HTMX sends HTTP PUT; FastAPI route registered with `@router.put(...)` |
| `hx-delete` | Works directly on a `<button>` element; no `<form>` required |
| `HX-Trigger` header | Server signals the browser to fire a named event; elements with matching `hx-trigger` re-fetch their content |
| `from:body` in `hx-trigger` | Listen for the named event anywhere on the page, not just on this element |
| `_patient_to_context()` | Private router helper — not in the service layer because it only transforms data already fetched from FHIR, rather than making any external calls |
| FHIR PUT requires `"id"` in body | When updating a FHIR resource via PUT, the resource body must include `"id"` matching the URL |
| `role="alertdialog"` | The correct ARIA role for a destructive confirmation dialog (vs `"dialog"` for non-destructive modals) |

---

## 15. Things to Avoid

- Do not pass the full patient resource object through the URL or JavaScript — only the ID. Fetch the full resource from the server when the modal opens.
- Do not create a separate `main.js` function for each patient row. One function handles all rows; the `ptid` argument distinguishes them.
- Do not add `htmx.process()` calls if you use `htmx.ajax()`. They serve the same purpose; using both is redundant.
- Do not use `hx-post` for the edit form — use `hx-put`. Sending a POST to a route registered with `@router.put(...)` will return a `405 Method Not Allowed`.
- Do not omit `"id": ptid` from the update body sent to HAPI FHIR. The FHIR server will reject a PUT that has mismatched IDs between the URL and resource body.
- Do not call `patient_service.get_patient()` from inside `delete_patient()`. The delete service function's only job is to send the DELETE request; the patient name for the confirmation modal is fetched by the `get_patient_delete_confirm` route before the delete happens.
- Do not wire multiple `hx-trigger` event names as separate `hx-trigger` attributes on the same element — they must be comma-separated in one attribute value.
