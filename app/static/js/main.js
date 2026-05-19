// ----------------------------------------------------------------
// app/static/js/main.js
// ----------------------------------------------------------------

// Holds a reference to the outside-click handler so closePatientMenu()
// can explicitly remove it when the menu is closed by any means (e.g. Escape),
// preventing a stale listener from closing the next menu that opens.
let _menuClickHandler = null;

// Tracks the table row that is currently associated with an open action menu
// so its highlight can be cleared when the menu closes.
let _activeRow = null;

function patientAction(ptid, btn) {
  closePatientMenu();

  _activeRow = btn.closest('tr');
  if (_activeRow) {
    _activeRow.style.backgroundColor = 'rgb(239 246 255)'; // blue-50
    _activeRow.style.borderLeft = '3px solid rgb(59 130 246)'; // blue-500 accent
  }

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

    <button
      class="flex items-center gap-2 w-full text-left px-4 py-2 hover:bg-gray-100"
      onclick="alert('Note: Patient Activity to be implemented in week 2.')"
    >
      <i class="fa-regular fa-clock w-4"></i> Activity
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

  // Register a named outside-click handler so it can be explicitly removed
  // if the menu is closed by a non-click means (e.g. Escape key).
  _menuClickHandler = function() {
    closePatientMenu();
  };

  setTimeout(() => {
    document.addEventListener('click', _menuClickHandler);
  }, 0);
}

function closePatientMenu() {
  const menu = document.getElementById('patient-action-menu');
  if (menu) menu.remove();
  if (_menuClickHandler) {
    document.removeEventListener('click', _menuClickHandler);
    _menuClickHandler = null;
  }
  if (_activeRow) {
    _activeRow.style.backgroundColor = '';
    _activeRow.style.borderLeft = '';
    _activeRow = null;
  }
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