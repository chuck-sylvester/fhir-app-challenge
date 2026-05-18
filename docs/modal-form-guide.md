# Modal Form Patterns for FastAPI, Jinja2, and HTMX

This guide explains how modal dialogs work in web applications and how to implement them cleanly in this project using FastAPI, Jinja2 templates, and HTMX. It is written for the upcoming "Create Patient" feature, where a clinician can open a modal form from either the lefthand navigation or the patient page header, enter basic patient demographics, and save a new FHIR `Patient` resource.

## 1. What a Modal Is

A modal is a temporary interface layer that appears above the current page and asks the user to complete or dismiss a focused task.

Common modal examples:

- Create a new record
- Edit a small set of fields
- Confirm a destructive action
- Show a focused detail view
- Ask for required input before continuing

A modal usually has three visual parts:

- **Overlay**: a dimmed backdrop covering the page
- **Dialog panel**: the visible box containing the form or message
- **Actions**: buttons such as Cancel, Reset, Save, or Delete

For this project, the modal should be used for a bounded task: creating one new patient with a small set of fields.

## 2. When a Modal Is a Good Choice

A modal is a good fit when the user needs to complete a short task without losing their current page context.

The "Create Patient" workflow fits this pattern well:

- The user is already on the patient list or in the main app shell.
- The form is short.
- The user should return to the patient list after saving or canceling.
- The create action is related to the current page but does not need a full page transition.

A modal becomes a weaker choice when the form is long, multi-step, highly complex, or needs a lot of supporting context. In those cases, a dedicated page is usually better.

## 3. Standard Modal Behavior

A familiar create-record modal should usually support:

- Open from one or more buttons or links.
- Close with a Cancel button.
- Close after a successful Save.
- Reset form fields without closing.
- Prevent accidental background interaction while open.
- Show validation errors inside the modal.
- Keep the user on the same screen after completion.
- Refresh or update the relevant page content after saving.

For this patient-create modal, the expected actions are:

- **Cancel**: close the modal without saving.
- **Reset**: clear or restore the form values while keeping the modal open.
- **Save**: submit the form to FastAPI, create the FHIR `Patient`, then close the modal and refresh the patient table or show a success state.

## 4. Accessibility Basics

Modals have some accessibility responsibilities because they interrupt the normal page flow.

Important modal accessibility practices:

- Use `role="dialog"` or `role="alertdialog"` on the modal panel.
- Add `aria-modal="true"`.
- Label the modal with `aria-labelledby`.
- Move keyboard focus into the modal when it opens.
- Return focus to the triggering button when it closes.
- Allow `Escape` to close the modal, unless there is a strong reason not to.
- Keep keyboard tab focus inside the modal while it is open.

HTMX does not automatically handle all focus-management behavior. For an early learning implementation, it is reasonable to start with a simple modal and then improve focus handling as a follow-up.

## 5. The HTMX Mental Model

HTMX lets the browser ask the server for HTML fragments and place those fragments into the current page.

Instead of writing a large amount of client-side JavaScript, the pattern is:

1. User clicks "Create Patient".
2. Browser sends an HTMX request to FastAPI.
3. FastAPI returns a Jinja2-rendered modal partial.
4. HTMX inserts the modal HTML into a placeholder element.
5. User fills out the form.
6. Form submits via HTMX to FastAPI.
7. FastAPI creates the FHIR resource.
8. FastAPI returns either updated HTML, a success response, or an instruction to refresh part of the page.

This is a strong fit for FastAPI + Jinja2 because the server remains responsible for routing, validation, and rendering.

## 6. Recommended Project Pattern

For this app, the cleanest modal pattern is:

- Keep the main page shell in `base.html`.
- Add an empty modal target near the end of the body.
- Load modal content into that target with HTMX.
- Keep modal markup in a dedicated Jinja2 partial.
- Submit the modal form with HTMX.
- Return validation errors as the same modal partial.
- On success, close the modal and refresh the patient table.

Suggested template structure:

```text
app/templates/
  base.html
  patient.html
  partials/
    get_patient_table.html
    create_patient_modal.html
```

Suggested routes:

```text
GET  /Patient/new       -> returns create_patient_modal.html
POST /Patient           -> validates input and creates the FHIR Patient
GET  /Patient/table     -> returns refreshed patient table
```

The existing `POST /Patient` route already exists, but it currently creates a hard-coded patient and references a missing template. For the real modal workflow, that route should accept submitted form fields from the request.

### What Each Route Does — and Does Not Do

A common source of confusion is knowing exactly what each route is responsible for. Here is a precise breakdown for the three routes involved in the create-patient workflow.

**`GET /Patient/new`**
- **Purpose:** Deliver the empty create-patient form to the browser as an HTML fragment.
- **Does:** Render `create_patient_modal.html` via Jinja2 and return it.
- **Does NOT:** Call any service function. Make any FHIR request. Fetch or create any data.
- **Context:** An empty dict `{}` is all that is needed — the template requires no data from the server to display a blank form.
- **Common mistake:** Calling `patient_service.create_patient()` inside this route. The GET route only *delivers the form*. It creates nothing. The service call belongs in the POST route.

**`POST /Patient`**
- **Purpose:** Receive the submitted form data, validate it, create the FHIR Patient, and return an HTML response.
- **Does:** Read `Form(...)` parameters from the request body, build a FHIR `Patient` dict, call the service, and return either a success response or the modal with errors.
- **Does NOT:** Render a blank form. Duplicate the GET route logic.

**`GET /Patient/table`**
- **Purpose:** Fetch the current patient list from the FHIR server and render it as an HTML table fragment.
- **Used for:** The initial patient table load and the post-save table refresh.
- **Does NOT:** Need to know anything about the modal. It simply returns the table every time it is called.

## 7. Modal Placeholder in the Base Template

Most HTMX modal implementations need a stable empty element where modal HTML can be inserted.

Conceptually, `base.html` would contain something like this near the end of `<body>`:

```html
<div id="modal-root"></div>
```

When the user clicks Create Patient, HTMX loads the modal partial into `#modal-root`.

Example trigger:

```html
<button
  type="button"
  hx-get="/Patient/new"
  hx-target="#modal-root"
  hx-swap="innerHTML"
>
  Create Patient
</button>
```

The same pattern can be used from both places:

- Lefthand navigation "Create Patient"
- Patient page header "+ Create Patient" button

Both triggers can call the same `GET /Patient/new` route.

## 8. Modal Partial Shape

The modal partial should include the overlay, the dialog panel, the form, and the buttons.

Conceptual structure:

```html
<div class="fixed inset-0 z-50">
  <div class="fixed inset-0 bg-black/40"></div>

  <div class="fixed inset-0 flex items-center justify-center p-4">
    <section
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-patient-title"
      class="w-full max-w-lg rounded-md bg-white shadow-xl"
    >
      <header>
        <h2 id="create-patient-title">Create Patient</h2>
      </header>

      <form hx-post="/Patient" hx-target="#modal-root" hx-swap="innerHTML">
        <!-- form fields -->

        <footer>
          <button type="button">Cancel</button>
          <button type="reset">Reset</button>
          <button type="submit">Save</button>
        </footer>
      </form>
    </section>
  </div>
</div>
```

This is only a learning sketch, not final production markup.

### A More Complete Starting Example

The following is closer to what `create_patient_modal.html` should actually contain. It uses Tailwind classes consistent with the rest of the app and wires up all three buttons correctly. Use this as a starting point, not a finished product — styling details can be adjusted as you go.

```html
<!-- Overlay: covers the full screen and dims the background -->
<div class="fixed inset-0 z-50">

  <!-- Backdrop: dimmed layer, click closes the modal -->
  <div
    class="fixed inset-0 bg-black/40"
    onclick="document.getElementById('modal-root').innerHTML = ''"
  ></div>

  <!-- Centering wrapper -->
  <div class="fixed inset-0 flex items-center justify-center p-4">

    <!-- Dialog panel -->
    <section
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-patient-title"
      class="relative w-full max-w-lg rounded-lg bg-white shadow-xl"
    >
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 id="create-patient-title" class="text-lg font-semibold text-gray-800">
          Create Patient
        </h2>
      </div>

      <!-- Form: hx-post sends the data, hx-target replaces modal content -->
      <form
        hx-post="/Patient"
        hx-target="#modal-root"
        hx-swap="innerHTML"
      >
        <div class="px-6 py-4 space-y-4">

          <!-- First Name -->
          <div>
            <label for="first_name" class="block text-sm font-medium text-gray-700">
              First Name <span class="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="first_name"
              name="first_name"
              required
              class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
          </div>

          <!-- Last Name -->
          <div>
            <label for="last_name" class="block text-sm font-medium text-gray-700">
              Last Name <span class="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="last_name"
              name="last_name"
              required
              class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
          </div>

          <!-- Gender -->
          <div>
            <label for="gender" class="block text-sm font-medium text-gray-700">
              Gender <span class="text-red-500">*</span>
            </label>
            <select
              id="gender"
              name="gender"
              required
              class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">-- Select --</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
              <option value="unknown">Unknown</option>
            </select>
          </div>

          <!-- Birthdate -->
          <div>
            <label for="birth_date" class="block text-sm font-medium text-gray-700">
              Date of Birth <span class="text-red-500">*</span>
            </label>
            <input
              type="date"
              id="birth_date"
              name="birth_date"
              required
              class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
          </div>

          <!-- Phone (optional) -->
          <div>
            <label for="phone" class="block text-sm font-medium text-gray-700">
              Phone Number
            </label>
            <input
              type="tel"
              id="phone"
              name="phone"
              class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
          </div>

        </div>

        <!-- Footer: action buttons -->
        <div class="px-6 py-4 border-t border-gray-200 flex items-center justify-between">

          <!-- Left: Cancel and Reset -->
          <div class="flex gap-2">
            <button
              type="button"
              onclick="document.getElementById('modal-root').innerHTML = ''"
              class="rounded-md px-4 py-2 text-sm text-gray-600 hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="reset"
              class="rounded-md px-4 py-2 text-sm text-gray-600 hover:bg-gray-100"
            >
              Reset
            </button>
          </div>

          <!-- Right: Save -->
          <button
            type="submit"
            class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Save Patient
          </button>

        </div>
      </form>
    </section>
  </div>
</div>
```

Key points about this example:
- The `name` attributes on each input (`first_name`, `last_name`, `gender`, `birth_date`, `phone`) must exactly match the parameter names in the FastAPI POST route.
- `required` on an input gives browser-level validation before the form is even submitted.
- Cancel and Reset both leave the modal open or clear it locally — neither sends a server request.
- Only the `type="submit"` button triggers the `hx-post` defined on the `<form>`.

### A Note on the Native `<dialog>` Element

HTML5 provides a native `<dialog>` element that handles two modal responsibilities automatically: focus trapping (keyboard Tab stays inside the dialog) and Escape-to-close. It also exposes a `.showModal()` / `.close()` JavaScript API.

This guide uses a `<div>`-based approach because it gives full control over Tailwind styling and integrates more naturally with HTMX's innerHTML swap pattern. However, it is worth knowing the native element exists. A future refactor could adopt `<dialog>` to gain built-in accessibility behavior with less custom code.

### HTMX Attribute Inheritance

HTMX attributes are inherited by child elements. When `hx-post`, `hx-target`, and `hx-swap` are set on the `<form>` element, every button inside the form that triggers a request will use those same values unless it overrides them individually. This means:

- The Save (`type="submit"`) button inherits the form's `hx-post` and `hx-target` automatically.
- The Cancel button should have `type="button"` to prevent it from triggering form submission.
- The Reset button should have `type="reset"` to use the browser's native field-clearing behavior.

Understanding this inheritance prevents a common mistake of wiring `hx-*` attributes onto individual buttons when the form-level declaration already covers the submit path.

## 9. Closing the Modal

There are a few common ways to close an HTMX modal.

### Option A: Clear the Modal Root

The Cancel button can clear `#modal-root`.

Example concept:

```html
<button
  type="button"
  onclick="document.getElementById('modal-root').innerHTML = ''"
>
  Cancel
</button>
```

This is simple and easy to understand. It uses a tiny amount of JavaScript for a purely local UI action. This is an intentional exception in an otherwise HTMX-driven page — closing a modal is a client-only concern with no server state involved, so a small inline script is appropriate and does not undermine the overall server-driven approach.

### Option B: Ask the Server for an Empty Response

Cancel can call a route that returns an empty response.

Example concept:

```html
<button
  type="button"
  hx-get="/modal/empty"
  hx-target="#modal-root"
  hx-swap="innerHTML"
>
  Cancel
</button>
```

This keeps behavior server-driven but adds a route just to close the modal. For this project, that is probably unnecessary.

### Option C: Use HTMX Events

After a successful save, the server can respond with headers that trigger browser-side behavior.

For example, FastAPI can return an `HX-Trigger` header such as:

```text
patient-created
```

Then frontend code can listen for that event, clear the modal, and refresh the table.

This is a good pattern once the project has several modal workflows.

For the first implementation, Option A is the easiest to learn and debug.

### Option D: Overlay Click-to-Close

A common UX expectation is that clicking the dimmed backdrop closes the modal. This can be added to the overlay `<div>` with an inline click handler:

```html
<div
  class="fixed inset-0 bg-black/40"
  onclick="document.getElementById('modal-root').innerHTML = ''"
></div>
```

The key detail is that this must be on the backdrop element, not the dialog panel. Clicks on the dialog panel itself should not propagate to the backdrop and close the modal. This is handled automatically because the dialog panel is a sibling of the backdrop, not a child of it, so clicks on the panel do not reach the backdrop's handler.

This is a nice UX improvement and can be added alongside Option A for the Cancel button with minimal extra code.

## 10. Reset Button Behavior

The Reset button should usually be:

```html
<button type="reset">Reset</button>
```

This tells the browser to restore the form fields to their original values.

For an empty create form, that means the fields return to blank/default values.

Good defaults for the patient modal might be:

- First name: blank
- Last name: blank
- Gender: blank or "unknown"
- Birthdate: blank
- Phone: blank

## 11. Save Button Behavior

The Save button should submit the form to the server.

With HTMX:

```html
<form
  hx-post="/Patient"
  hx-target="#modal-root"
  hx-swap="innerHTML"
>
```

FastAPI receives the form values, validates them, builds a FHIR `Patient` resource, posts it to the FHIR server, and then returns a response.

There are two good success-response patterns.

### Pattern 1: Return a Success Message in the Modal

After saving, the modal stays open briefly and shows "Patient created."

Pros:

- Very easy to understand.
- Good for early learning.
- No special event wiring required.

Cons:

- The user may still need to close the modal manually.
- The patient table may not refresh automatically.

### Pattern 2: Close Modal and Refresh Patient Table

After saving, the modal closes and the patient table refreshes.

Pros:

- Better user experience.
- Feels like a polished create workflow.

Cons:

- Requires slightly more HTMX coordination.

There are two concrete mechanisms to achieve this. Both are worth understanding.

#### Mechanism A: `HX-Trigger` Response Header

FastAPI returns a custom event name in the `HX-Trigger` response header after a successful save. A wrapper `<div>` around the patient table listens for that event and re-fetches the table.

FastAPI side:
```python
from fastapi.responses import HTMLResponse

response = HTMLResponse(content="", status_code=200)
response.headers["HX-Trigger"] = "patient-created"
return response
```

Template side — wrap the patient table in a div that listens for the event:
```html
<div
  id="patient-table-wrapper"
  hx-get="/Patient/table"
  hx-trigger="patient-created from:body"
  hx-target="#patient-table-wrapper"
  hx-swap="innerHTML"
>
  <!-- patient table renders here -->
</div>
```

The modal root is cleared separately (via the Cancel/close mechanism or an empty response). The `from:body` qualifier tells HTMX to listen for the event anywhere on the page, not just on this element.

#### Mechanism B: `hx-swap-oob` (Out-of-Band Swap)

HTMX allows a single response to update multiple targets. The primary response goes to the element specified by `hx-target` (in this case `#modal-root`, which clears the modal), and additional elements in the response marked `hx-swap-oob="true"` are swapped into matching elements elsewhere on the page.

FastAPI returns:
```html
<!-- empty string → clears #modal-root (closes the modal) -->
<div id="patient-table-wrapper" hx-swap-oob="true">
  <!-- rendered table HTML here -->
</div>
```

HTMX processes the OOB element independently and places it into the existing `#patient-table-wrapper` on the page without a second request.

**Which to use:** `HX-Trigger` is cleaner when the table wrapper is always present on the page and you want the refresh to feel independent of the save response. `hx-swap-oob` is more self-contained — the server controls exactly what updates in a single round trip. Either works; `HX-Trigger` is generally more maintainable as the app grows.

A practical first version could show a success state in the modal. A polished second version could close the modal and refresh the table using either mechanism above.

## 12. Validation Strategy

The modal should validate at two layers:

- Browser-level validation for simple field requirements.
- Server-side validation in FastAPI before creating the FHIR resource.

Recommended form fields:

| UI Label | FHIR Field | Suggested Input |
|---|---|---|
| First Name | `Patient.name[0].given[0]` | text |
| Last Name | `Patient.name[0].family` | text |
| Gender | `Patient.gender` | select |
| Birthdate | `Patient.birthDate` | date |
| Phone Number | `Patient.telecom[]` | tel |

Recommended required fields for the first version:

- First Name
- Last Name
- Gender
- Birthdate

Phone number can be optional unless the project requires it.

FHIR allows `gender` values from a specific value set:

- `male`
- `female`
- `other`
- `unknown`

The form should submit those lowercase FHIR values even if the visible labels are title case. In an HTML `<select>`, the `value` attribute on each `<option>` is what gets submitted — not the display text. Make sure the `value` attributes match the FHIR strings exactly:

```html
<select name="gender">
  <option value="">-- Select --</option>
  <option value="male">Male</option>
  <option value="female">Female</option>
  <option value="other">Other</option>
  <option value="unknown">Unknown</option>
</select>
```

## 13. About `meta.lastUpdated`

In FHIR, `meta.lastUpdated` is usually managed by the FHIR server, not by the client application.

For a HAPI FHIR server, when the app creates a `Patient`, the server should assign or update metadata such as:

```json
{
  "meta": {
    "versionId": "1",
    "lastUpdated": "2026-05-17T..."
  }
}
```

Best practice is not to send `meta.lastUpdated` from the create form. Instead:

1. Submit the new `Patient` resource without `meta.lastUpdated`.
2. Let the FHIR server create the resource.
3. Read the server response.
4. Display the returned `meta.lastUpdated` in the patient table.

This matches normal FHIR server behavior and avoids pretending the client controls server-managed metadata.

## 14. Building the FHIR Patient Resource

The submitted form can become a FHIR `Patient` resource like this:

```json
{
  "resourceType": "Patient",
  "active": true,
  "name": [
    {
      "use": "official",
      "family": "Smith",
      "given": ["Jordan"]
    }
  ],
  "gender": "female",
  "birthDate": "1987-04-12",
  "telecom": [
    {
      "system": "phone",
      "value": "555-123-4567",
      "use": "home"
    }
  ]
}
```

The app should only include `telecom` if the user supplies a phone number.

## 15. FastAPI Form Handling

FastAPI can read submitted form values using `Form`.

> **Dependency required:** FastAPI's `Form` parameter type requires the `python-multipart` package. If it is not installed, the server returns a `400 Bad Request` with no obvious explanation. Verify it is in `requirements.txt` and installed in the virtual environment:
> ```bash
> pip install python-multipart
> ```

Conceptual route shape:

```python
from fastapi import Form, Request

@router.post("/Patient")
async def post_patient(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: str = Form(...),
    birth_date: str = Form(...),
    phone: str = Form(""),
):
    ...
```

The names in the HTML form must match the parameter names:

```html
<input name="first_name">
<input name="last_name">
<select name="gender">
<input name="birth_date" type="date">
<input name="phone" type="tel">
```

For a learning implementation, it is fine to start with simple `Form` parameters. Later, this could be refactored into a Pydantic model or a small form object.

### What `Form(...)` and `Form("")` Mean

This syntax belongs to **FastAPI** (and the underlying **Pydantic** library it builds on). It is not Python standard syntax, not HTMX, and not Jinja2. You import `Form` from FastAPI:

```python
from fastapi import Form
```

The parentheses contain the **default value** for that parameter. FastAPI uses the default value to decide whether the field is required or optional:

| Syntax | Meaning |
|---|---|
| `Form(...)` | Required. If the submitted form does not include this field, FastAPI immediately returns a `422 Unprocessable Entity` error before your function body runs. |
| `Form("")` | Optional. If the field is missing or empty, the parameter receives an empty string as its value. Your function always runs. |

The `...` (three dots) is Python's built-in **Ellipsis** object — a real Python value, like `None` or `True`. On its own it has no special meaning. FastAPI and Pydantic adopted it by convention as a sentinel that means "no default exists, this is required." You will see the same `...` used in Pydantic model field definitions for the same reason.

In plain terms:
- `first_name: str = Form(...)` → "first_name must be present in the submitted form or FastAPI will reject the request"
- `phone: str = Form("")` → "phone is optional; if absent, treat it as an empty string"

This is entirely a server-side concern. HTMX, the browser, and Jinja2 have no awareness of it — they just send and receive HTTP requests and HTML.

## 15a. Connecting HTML Form Names to FastAPI Parameters

This is the most important wiring detail to understand. When the browser submits a form, it sends each field as a key-value pair where the key is the `name` attribute of the input. FastAPI reads those keys and matches them to function parameter names.

The connection is direct and must be exact — spelling, case, and underscores all matter.

Here is the complete picture, showing both sides at once:

**HTML form fields** (`create_patient_modal.html`):
```html
<input type="text"  name="first_name"  ...>
<input type="text"  name="last_name"   ...>
<select             name="gender"      ...>
<input type="date"  name="birth_date"  ...>
<input type="tel"   name="phone"       ...>
```

**FastAPI route parameters** (`patient.py`):
```python
@router.post("/Patient", response_class=HTMLResponse)
async def post_patient(
    request: Request,
    first_name: str = Form(...),   # ← matches name="first_name"
    last_name:  str = Form(...),   # ← matches name="last_name"
    gender:     str = Form(...),   # ← matches name="gender"
    birth_date: str = Form(...),   # ← matches name="birth_date"
    phone:      str = Form(""),    # ← matches name="phone", default empty = optional
):
```

`Form(...)` means the field is required — FastAPI returns a `422 Unprocessable Entity` if it is missing. `Form("")` means the field is optional with a default of empty string.

**What happens if the names don't match?**

If the HTML has `name="firstName"` but FastAPI expects `first_name`, FastAPI will not find the value. Required fields will raise a `422` error. Optional fields will silently use their default. Neither gives a helpful error message, so verifying the name alignment early is worth the effort.

**How to verify the connection is working**

A quick way to confirm form data is reaching FastAPI correctly is to temporarily add a print statement at the top of the POST route:

```python
async def post_patient(request: Request, first_name: str = Form(...), ...):
    print(f"Received: {first_name=}, {last_name=}, {gender=}")
```

The values will appear in the uvicorn terminal output. Once confirmed, remove the print.

## 16. Error Handling

The modal should handle errors without dumping the user onto a new page.

Common errors:

- Required field missing
- Invalid gender value
- Invalid date
- FHIR server unavailable
- FHIR server rejects the resource

With HTMX, the route can return the same modal partial with:

- The previously entered values
- An error summary
- Field-level messages where useful

This makes the modal feel stable: the user corrects the issue and tries again without losing their input.

## 17. Suggested Implementation Sequence

When you are ready to implement, a good learning-friendly sequence would be:

1. Add a `#modal-root` placeholder to `base.html`.
2. Add a `GET /Patient/new` route that renders an empty modal partial.
3. Wire the sidebar and patient header Create Patient buttons to load that route with HTMX.
4. Create `partials/create_patient_modal.html`.
5. Add the form fields and Cancel, Reset, Save buttons.
6. Update `POST /Patient` to read form data instead of creating a hard-coded patient.
7. Build the FHIR `Patient` resource from submitted form values.
8. Return validation errors back into the modal.
9. On successful save, refresh the patient table.
10. Add small UX improvements: loading state, disabled Save while submitting, focus behavior, and Escape-to-close.

### Step-by-Step Detail

**Step 1 — Add `#modal-root` to `base.html`**

Near the closing `</body>` tag, add an empty div. This is the injection point for all modal content:

```html
<div id="modal-root"></div>
```

It should be outside the main layout divs so it can overlay everything cleanly. Nothing else needs to go in it — HTMX will fill it when the user opens a modal.

**Step 2 — Add `GET /Patient/new` in `patient.py`**

Place this route *after* `GET /Patient/table` and *before* `GET /Patient/{ptid}`. The order matters — literal path segments must be registered before path parameters or they will be captured by the `{ptid}` wildcard.

```python
@router.get("/Patient/new", response_class=HTMLResponse)
async def get_patient_new(request: Request):
    return templates.TemplateResponse(
        request,
        "partials/create_patient_modal.html",
        {}
    )
```

Note: no service call, no data fetching — just rendering the empty form template.

**Step 3 — Wire the trigger buttons**

Both the sidebar link and the patient page header button should call the same route. Replace the existing placeholder `<a>` tags with HTMX-enabled buttons or anchors:

```html
<button
  type="button"
  hx-get="/Patient/new"
  hx-target="#modal-root"
  hx-swap="innerHTML"
  class="..."
>
  + Create Patient
</button>
```

After this step you can verify: clicking the button should send a `GET /Patient/new` request (visible in the uvicorn log) even before the template exists.

**Step 4 — Create `create_patient_modal.html`**

Create the file at `app/templates/partials/create_patient_modal.html`. Start with a minimal structure to verify the modal appears before adding all fields:

```html
<div class="fixed inset-0 z-50 flex items-center justify-center">
  <div class="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg">
    <h2 class="text-lg font-semibold mb-4">Create Patient</h2>
    <p>Form coming soon.</p>
    <button
      type="button"
      onclick="document.getElementById('modal-root').innerHTML = ''"
      class="mt-4 px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded"
    >
      Close
    </button>
  </div>
</div>
```

Test this before adding any form fields. At this point clicking "Create Patient" should show the modal panel over the page, and "Close" should dismiss it.

**Step 5 — Add form fields and buttons**

Replace the placeholder content with the full form from Section 8. Verify:
- The modal opens and the form renders.
- Cancel closes the modal.
- Reset clears the fields.
- The browser enforces `required` fields before allowing submit.
- The submit button sends a POST (visible in the uvicorn log as a `422` or `500` until Step 6 is done).

**Step 6 — Update `POST /Patient` to read form data**

Replace the existing hard-coded `patient_service.create_patient()` call with `Form` parameters:

```python
from fastapi import Form

@router.post("/Patient", response_class=HTMLResponse)
async def post_patient(
    request: Request,
    first_name: str = Form(...),
    last_name:  str = Form(...),
    gender:     str = Form(...),
    birth_date: str = Form(...),
    phone:      str = Form(""),
):
    data = patient_service.create_patient(first_name, last_name, gender, birth_date, phone)
    return templates.TemplateResponse(
        request,
        "partials/create_patient_modal.html",
        {"success": True}
    )
```

At this step, add a temporary `print` statement to verify form values are arriving before touching the service.

**Step 7 — Update `patient_service.create_patient()`**

Change the function signature to accept parameters instead of using hard-coded values, and build the FHIR dict from them:

```python
def create_patient(first_name: str, last_name: str, gender: str,
                   birth_date: str, phone: str = ""):
    new_patient = {
        "resourceType": "Patient",
        "active": True,
        "name": [{"use": "official", "family": last_name, "given": [first_name]}],
        "gender": gender,
        "birthDate": birth_date,
    }
    if phone:
        new_patient["telecom"] = [{"system": "phone", "value": phone, "use": "home"}]

    headers = {"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"}
    if settings.fhir_external_api_token:
        headers["Authorization"] = f"Bearer {settings.fhir_external_api_token}"

    output = requests.post(f"{settings.fhir_base_url}/Patient", json=new_patient, headers=headers)
    return output.json()
```

**Step 8 — Return validation errors into the modal**

Two files need to change for error handling: `app/routers/patient.py` and `app/templates/partials/create_patient_modal.html`. The service file (`patient_service.py`) does not need changes — it simply returns whatever the FHIR server responds with, and the router decides what to do with that response.

*File 1: `app/routers/patient.py`*

The POST route needs two return statements — one for failure, one for success. When the FHIR server cannot create a patient, it returns a resource with `"resourceType": "OperationOutcome"` instead of `"resourceType": "Patient"`. That is the signal to take the error path.

```python
@router.post("/Patient", response_class=HTMLResponse)
async def post_patient(
    request: Request,
    first_name: str = Form(...),
    last_name:  str = Form(...),
    gender:     str = Form(...),
    birth_date: str = Form(...),
    phone:      str = Form(""),
):
    result = patient_service.create_patient(first_name, last_name, gender, birth_date, phone)

    # FHIR servers return OperationOutcome when something goes wrong
    if result.get("resourceType") == "OperationOutcome":
        # Error path — re-render the modal with the error message and the
        # user's previously entered values so they do not have to retype them
        return templates.TemplateResponse(
            request,
            "partials/create_patient_modal.html",
            {
                "error": "Could not create patient. Please check your entries and try again.",
                "first_name": first_name,
                "last_name":  last_name,
                "gender":     gender,
                "birth_date": birth_date,
                "phone":      phone,
            }
        )

    # Success path — clear the modal and signal the patient table to refresh
    response = HTMLResponse(content="", status_code=200)
    response.headers["HX-Trigger"] = "patient-created"
    return response
```

*File 2: `app/templates/partials/create_patient_modal.html`*

Two changes are needed in the template:

**Change A — Add the error block.** Place it at the top of the form body, above the first input field. When `GET /Patient/new` renders the modal, `error` is not in the context so this block is silently skipped. When the POST route re-renders the modal after a failure, `error` is present and the red message appears.

```html
<form hx-post="/Patient" hx-target="#modal-root" hx-swap="innerHTML">
  <div class="px-6 py-4 space-y-4">

    <!-- Error block: only renders when the POST route passes an 'error' value -->
    {% if error %}
    <div class="rounded-md bg-red-50 border border-red-300 px-4 py-3 text-sm text-red-700">
      {{ error }}
    </div>
    {% endif %}

    <!-- First Name field follows here -->
```

**Change B — Pre-fill every input field.** Add a `value` attribute to each input using Jinja2. The `default('')` filter ensures the field renders as blank on first open (when the variable is not in the context) and shows the previously entered value after a failed submit.

```html
<input type="text" name="first_name"
       value="{{ first_name | default('') }}" ...>

<input type="text" name="last_name"
       value="{{ last_name | default('') }}" ...>

<input type="date" name="birth_date"
       value="{{ birth_date | default('') }}" ...>

<input type="tel" name="phone"
       value="{{ phone | default('') }}" ...>
```

The `<select>` for gender requires a different approach — you mark the matching option as `selected` rather than using a `value` attribute on the element itself:

```html
<select name="gender" ...>
  <option value="">-- Select --</option>
  <option value="male"    {% if gender == 'male'    %}selected{% endif %}>Male</option>
  <option value="female"  {% if gender == 'female'  %}selected{% endif %}>Female</option>
  <option value="other"   {% if gender == 'other'   %}selected{% endif %}>Other</option>
  <option value="unknown" {% if gender == 'unknown' %}selected{% endif %}>Unknown</option>
</select>
```

**Step 9 — Refresh the patient table on success**

After a successful save, the POST route should clear the modal and trigger a table refresh. The simplest approach using `HX-Trigger`:

```python
from fastapi.responses import HTMLResponse as FastAPIHTMLResponse

response = FastAPIHTMLResponse(content="", status_code=200)
response.headers["HX-Trigger"] = "patient-created"
return response
```

Wrap the patient table on the patient page in a div that listens for this event:

```html
<div
  id="patient-table-wrapper"
  hx-get="/Patient/table"
  hx-trigger="patient-created from:body"
  hx-target="#patient-table-wrapper"
  hx-swap="innerHTML"
>
  <!-- table content -->
</div>
```

**Step 10 — Loading and polish**

Add `hx-disabled-elt` to the form to prevent double-submission:

```html
<form hx-post="/Patient" hx-disabled-elt="find button[type='submit']" ...>
```

The Save button will be automatically disabled while the POST request is in flight.

**Escape-to-close details:**

Pressing ESC while the modal is open should close it — identical to clicking Cancel or the backdrop. No data is saved and the modal disappears.

This behavior is not automatic with a `<div>`-based modal. The browser only handles ESC natively for the HTML `<dialog>` element. With divs, it must be wired manually with a JavaScript `keydown` event listener.

The correct place to add this is **`base.html`**, not `create_patient_modal.html`. A `document`-level listener in `base.html` is always present regardless of which page is loaded and handles ESC for any modal added to the app in the future. Adding the listener inside the modal partial is risky — a new listener is registered every time the modal opens and they accumulate if not cleaned up.

Add the following `<script>` block to `base.html` just before the closing `</body>` tag:

```html
<script>
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      document.getElementById('modal-root').innerHTML = '';
    }
  });
</script>
```

This is the complete implementation. ESC key handling is a local browser UI concern with no server interaction, so plain JavaScript is the right tool. If no modal is open, clearing an already-empty `#modal-root` div is harmless.

**Loading state details:** While an HTMX request is in flight, HTMX adds the CSS class `htmx-request` to the element that triggered the request. This can be used to show a spinner or visually disable the Save button:

```css
/* In a <style> block or stylesheet */
button[type="submit"].htmx-request {
  opacity: 0.5;
  cursor: wait;
}
```

Alternatively, use the `hx-disabled-elt` attribute on the form to disable specific elements during the request:

```html
<form hx-post="/Patient" hx-disabled-elt="find button[type='submit']" ...>
```

This prevents double-submission without requiring any custom JavaScript.

This order keeps each step testable and avoids mixing too many ideas at once.

## 18. Recommended First Version for This Project

For the first complete version, aim for:

- Sidebar Create Patient opens modal.
- Patient page "+ Create Patient" opens the same modal.
- Modal includes First Name, Last Name, Gender, Birthdate, Phone Number.
- Cancel closes the modal.
- Reset clears the form.
- Save creates the FHIR `Patient`.
- Validation errors appear in the modal.
- Successful save closes the modal and refreshes the patient table if the table is visible.

One practical compromise: if the user opens the modal from a page where the patient table is not currently loaded, the app can still create the patient and show a success message. Later, navigation behavior can be refined.

## 19. UI and UX Guidance

The modal should feel like part of the existing app:

- Use the same Tailwind visual language as the patient page.
- Keep the dialog width moderate, around `max-w-lg`.
- Use clear labels, not placeholders as labels.
- Put required fields first.
- Use a select for gender.
- Use native `type="date"` for birthdate.
- Use native `type="tel"` for phone.
- Place Cancel and Reset on the left or secondary side.
- Place Save on the right as the primary action.
- Do not make the modal too tall for smaller screens.

Suggested action order:

```text
Cancel    Reset                         Save Patient
```

This visually separates "leave/clear" actions from the primary save action.

## 20. Things to Avoid

Avoid these early implementation traps:

- Do not create separate modal code for the sidebar and the patient page button.
- Do not send `meta.lastUpdated` from the form; let HAPI FHIR manage it.
- Do not return raw JSON to the modal after save unless the goal is debugging.
- Do not replace the whole page when only the modal or patient table needs updating.
- Do not make the Create Patient form depend on JavaScript-heavy state management.
- Do not hide validation errors after failed submit.
- Do not leave the existing hard-coded patient creation behavior in place once the form is wired.
- Do not omit the leading slash in a route decorator. `@router.get("Patient/new")` registers a relative path that will never match; it must be `@router.get("/Patient/new")`.
- Do not call a service function from `GET /Patient/new`. That route only renders the empty form. The service call belongs in `POST /Patient`. Calling `patient_service.create_patient()` from the GET route would create a new patient every time a user opens the modal — before they have entered any data.

## 21. Open Design Decisions

Before implementation, it would be useful to decide:

- Should phone number be required or optional?
- Should the modal close immediately after save, or briefly show a success message?
- Should the patient table automatically load on the Patient page before any button is clicked?
- Should the app create only minimal demographic records, or include identifiers such as MRN?
- Should the initial implementation include client-side focus trapping and Escape-to-close behavior, or should that be a follow-up?

## 22. Suggested Learning Goal

The best learning outcome for this feature is not just "make a modal." It is to understand the flow of responsibility:

- **Browser**: displays modal, handles native form behavior, sends HTMX requests.
- **HTMX**: swaps server-rendered HTML fragments into the page.
- **FastAPI router**: receives requests, validates form inputs, chooses responses.
- **Service layer**: builds and sends FHIR requests.
- **FHIR server**: stores the `Patient` and controls resource metadata.
- **Jinja2 templates**: render the modal, errors, success states, and patient table.

Once this pattern is clear, the same approach can be reused for editing patients, deleting patients, viewing patient details, or adding related resources.
