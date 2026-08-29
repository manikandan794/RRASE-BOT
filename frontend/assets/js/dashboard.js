/**
 * Shared dashboard helpers: route guarding by role, and a generic
 * CRUD-table renderer so every "management" tab (Departments, Faculty,
 * Courses, FAQs, Notices, Events, Facilities, Contacts, College Info)
 * shares one implementation instead of eight near-duplicates.
 */
window.RraseDashboard = (function () {
  function requireAnyRole(roles) {
    if (!window.RraseAPI.isLoggedIn() || !roles.some((r) => window.RraseAPI.hasRole(r))) {
      window.location.href = "../login.html";
      return false;
    }
    return true;
  }

  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else node.setAttribute(k, v);
    });
    children.forEach((c) => node.appendChild(c));
    return node;
  }

  /**
   * config: { endpoint, idField, title, fields: [{name,label,type}] }
   * Renders a table + an add/edit form into `container`.
   */
  function renderCrudSection(container, config) {
    container.innerHTML = "";
    const heading = el("h2", { class: "h5 mb-3", text: config.title });
    const errorBox = el("div", { class: "alert alert-danger d-none" });
    const table = el("table", { class: "table table-sm table-hover bg-white" });
    const thead = el("thead");
    const headRow = el("tr");
    config.fields.forEach((f) => headRow.appendChild(el("th", { text: f.label })));
    headRow.appendChild(el("th", { text: "Actions" }));
    thead.appendChild(headRow);
    const tbody = el("tbody");
    table.appendChild(thead);
    table.appendChild(tbody);

    const form = el("form", { class: "row g-2 mt-3 mb-4" });
    const inputs = {};
    config.fields.forEach((f) => {
      const col = el("div", { class: "col-md-3" });
      const input = el("input", {
        class: "form-control form-control-sm",
        placeholder: f.label,
        type: f.type === "number" ? "number" : f.type === "datetime" ? "datetime-local" : "text",
      });
      inputs[f.name] = input;
      col.appendChild(input);
      form.appendChild(col);
    });
    const submitCol = el("div", { class: "col-md-3" });
    const submitBtn = el("button", { class: "btn btn-sm btn-primary w-100", type: "submit", text: "Add" });
    submitCol.appendChild(submitBtn);
    form.appendChild(submitCol);

    let editingId = null;

    function showError(message) {
      errorBox.textContent = message;
      errorBox.classList.remove("d-none");
    }

    function collectPayload() {
      const payload = {};
      config.fields.forEach((f) => {
        let value = inputs[f.name].value;
        if (f.type === "number") value = value === "" ? null : Number(value);
        if (f.type === "boolean") value = inputs[f.name].checked;
        if (f.type === "datetime" && value) value = new Date(value).toISOString();
        payload[f.name] = value === "" ? null : value;
      });
      return payload;
    }

    async function loadRows() {
      tbody.innerHTML = "";
      try {
        const rows = await window.RraseAPI.request(config.endpoint);
        rows.forEach((row) => {
          const tr = el("tr");
          config.fields.forEach((f) => tr.appendChild(el("td", { text: row[f.name] ?? "" })));
          const actionsTd = el("td");
          const editBtn = el("button", { class: "btn btn-sm btn-outline-secondary me-1", text: "Edit" });
          const delBtn = el("button", { class: "btn btn-sm btn-outline-danger", text: "Delete" });
          editBtn.addEventListener("click", () => {
            editingId = row[config.idField];
            config.fields.forEach((f) => (inputs[f.name].value = row[f.name] ?? ""));
            submitBtn.textContent = "Save changes";
          });
          delBtn.addEventListener("click", async () => {
            if (!confirm("Delete this item?")) return;
            try {
              await window.RraseAPI.request(`${config.endpoint}/${row[config.idField]}`, { method: "DELETE" });
              loadRows();
            } catch (err) {
              showError(err.message);
            }
          });
          actionsTd.appendChild(editBtn);
          actionsTd.appendChild(delBtn);
          tr.appendChild(actionsTd);
          tbody.appendChild(tr);
        });
      } catch (err) {
        showError(err.message);
      }
    }

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      errorBox.classList.add("d-none");
      try {
        const payload = collectPayload();
        if (editingId !== null) {
          await window.RraseAPI.request(`${config.endpoint}/${editingId}`, { method: "PUT", body: payload });
          editingId = null;
          submitBtn.textContent = "Add";
        } else {
          await window.RraseAPI.request(config.endpoint, { method: "POST", body: payload });
        }
        config.fields.forEach((f) => (inputs[f.name].value = ""));
        loadRows();
      } catch (err) {
        showError(err.message);
      }
    });

    container.appendChild(heading);
    container.appendChild(errorBox);
    container.appendChild(form);
    container.appendChild(table);
    loadRows();
  }

  return { requireAnyRole, renderCrudSection, el };
})();
