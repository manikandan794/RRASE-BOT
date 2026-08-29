(function () {
  if (!window.RraseDashboard.requireAnyRole(["principal", "admin"])) return;

  const { renderCrudSection, el } = window.RraseDashboard;
  const content = document.getElementById("tabContent");

  const CRUD_TABS = {
    college_info: {
      endpoint: "/college-info", idField: "key", title: "College Info",
      fields: [
        { name: "key", label: "Key" }, { name: "label", label: "Label" },
        { name: "value", label: "Value" }, { name: "source", label: "Source" },
      ],
    },
    departments: {
      endpoint: "/departments", idField: "id", title: "Departments",
      fields: [
        { name: "name", label: "Name" }, { name: "short_code", label: "Short code" },
        { name: "hod_name", label: "HOD" }, { name: "description", label: "Description" },
      ],
    },
    faculty: {
      endpoint: "/faculty", idField: "id", title: "Faculty",
      fields: [
        { name: "full_name", label: "Full name" }, { name: "designation", label: "Designation" },
        { name: "department_id", label: "Department ID" }, { name: "email", label: "Email" },
        { name: "phone", label: "Phone" },
      ],
    },
    courses: {
      endpoint: "/courses", idField: "id", title: "Courses",
      fields: [
        { name: "name", label: "Name" }, { name: "level", label: "Level" },
        { name: "department_id", label: "Department ID" },
        { name: "duration_years", label: "Duration (yrs)", type: "number" },
        { name: "intake", label: "Intake", type: "number" },
      ],
    },
    faqs: {
      endpoint: "/faqs", idField: "id", title: "FAQs",
      fields: [
        { name: "question", label: "Question" }, { name: "answer", label: "Answer" },
        { name: "category", label: "Category" },
      ],
    },
    notices: {
      endpoint: "/notices", idField: "id", title: "Notices",
      fields: [{ name: "title", label: "Title" }, { name: "body", label: "Body" }],
    },
    events: {
      endpoint: "/events", idField: "id", title: "Events",
      fields: [
        { name: "title", label: "Title" }, { name: "location", label: "Location" },
        { name: "starts_at", label: "Starts at", type: "datetime" },
        { name: "description", label: "Description" },
      ],
    },
    facilities: {
      endpoint: "/facilities", idField: "id", title: "Facilities",
      fields: [
        { name: "name", label: "Name" }, { name: "category", label: "Category" },
        { name: "description", label: "Description" },
      ],
    },
    contacts: {
      endpoint: "/contacts", idField: "id", title: "Contacts",
      fields: [
        { name: "label", label: "Label" }, { name: "phone", label: "Phone" },
        { name: "email", label: "Email" }, { name: "address", label: "Address" },
      ],
    },
  };

  async function renderOverview() {
    content.innerHTML = "<h2 class='h5 mb-3'>Overview</h2><div id='ovBox'>Loading...</div>";
    try {
      const data = await window.RraseAPI.request("/analytics/summary");
      const box = document.getElementById("ovBox");
      box.innerHTML = "";
      const stats = [
        ["Total users", data.total_users], ["Conversations", data.total_conversations],
        ["Messages", data.total_messages], ["Unresolved questions", data.unresolved_unanswered],
        ["Knowledge chunks", `${data.embedded_knowledge_chunks}/${data.total_knowledge_chunks} embedded`],
        ["Avg. feedback rating", data.average_feedback_rating?.toFixed(2) ?? "No feedback yet"],
      ];
      const row = el("div", { class: "row g-3" });
      stats.forEach(([label, value]) => {
        row.appendChild(el("div", { class: "col-md-4" }, [
          el("div", { class: "rrase-card p-3" }, [
            el("div", { class: "text-secondary small", text: label }),
            el("div", { class: "fs-4 fw-bold", text: String(value) }),
          ]),
        ]));
      });
      box.appendChild(row);

      const sourceBox = el("div", { class: "mt-4" });
      sourceBox.appendChild(el("h3", { class: "h6", text: "Answers by source" }));
      Object.entries(data.messages_by_source).forEach(([k, v]) => {
        sourceBox.appendChild(el("div", { class: "small", text: `${k}: ${v}` }));
      });
      box.appendChild(sourceBox);
    } catch (err) {
      content.innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
    }
  }

  async function renderDocuments() {
    content.innerHTML = "";
    content.appendChild(el("h2", { class: "h5 mb-3", text: "Uploaded Documents (PDF)" }));
    const errorBox = el("div", { class: "alert alert-danger d-none" });
    content.appendChild(errorBox);

    const form = el("form", { class: "d-flex gap-2 mb-3" });
    const fileInput = el("input", { type: "file", accept: "application/pdf", class: "form-control" });
    const uploadBtn = el("button", { class: "btn btn-primary", type: "submit", text: "Upload" });
    form.appendChild(fileInput);
    form.appendChild(uploadBtn);
    content.appendChild(form);

    const table = el("table", { class: "table table-sm bg-white" });
    table.innerHTML = "<thead><tr><th>Filename</th><th>Status</th><th>Pages</th><th>Error</th><th></th></tr></thead>";
    const tbody = el("tbody");
    table.appendChild(tbody);
    content.appendChild(table);

    async function loadDocs() {
      tbody.innerHTML = "";
      const docs = await window.RraseAPI.request("/documents");
      docs.forEach((doc) => {
        const tr = el("tr", {}, [
          el("td", { text: doc.filename }), el("td", { text: doc.status }),
          el("td", { text: doc.extracted_pages ?? "" }), el("td", { text: doc.error ?? "" }),
        ]);
        const delBtn = el("button", { class: "btn btn-sm btn-outline-danger", text: "Delete" });
        delBtn.addEventListener("click", async () => {
          await window.RraseAPI.request(`/documents/${doc.id}`, { method: "DELETE" });
          loadDocs();
        });
        const td = el("td");
        td.appendChild(delBtn);
        tr.appendChild(td);
        tbody.appendChild(tr);
      });
    }

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      errorBox.classList.add("d-none");
      const file = fileInput.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append("file", file);
      try {
        await window.RraseAPI.request("/documents/upload", { method: "POST", body: formData, isForm: true });
        fileInput.value = "";
        loadDocs();
      } catch (err) {
        errorBox.textContent = err.message;
        errorBox.classList.remove("d-none");
      }
    });

    loadDocs();
  }

  async function renderWebsiteKnowledge() {
    content.innerHTML = "";
    content.appendChild(el("h2", { class: "h5 mb-3", text: "Official Website Knowledge Import" }));
    const errorBox = el("div", { class: "alert alert-danger d-none" });
    content.appendChild(errorBox);

    const importBtn = el("button", { class: "btn btn-primary mb-3", text: "Import from official website" });
    content.appendChild(importBtn);

    const list = el("div", { id: "pendingList" });
    content.appendChild(list);

    async function loadPending() {
      list.innerHTML = "Loading...";
      const pending = await window.RraseAPI.request("/knowledge/website/pending");
      list.innerHTML = "";
      if (pending.length === 0) {
        list.appendChild(el("p", { class: "text-secondary small", text: "No pages awaiting review." }));
      }
      pending.forEach((page) => {
        const card = el("div", { class: "rrase-card p-3 mb-2" });
        card.appendChild(el("div", { class: "fw-bold", text: page.title || page.page_url }));
        card.appendChild(el("div", { class: "small text-secondary mb-2", text: page.page_url }));
        const textarea = el("textarea", { class: "form-control mb-2", rows: "5" });
        textarea.value = page.raw_text;
        card.appendChild(textarea);
        const approveBtn = el("button", { class: "btn btn-sm btn-success me-2", text: "Approve into knowledge base" });
        const rejectBtn = el("button", { class: "btn btn-sm btn-outline-danger", text: "Reject" });
        approveBtn.addEventListener("click", async () => {
          await window.RraseAPI.request(`/knowledge/website/${page.id}/review`, {
            method: "POST", body: { approve: true, edited_text: textarea.value },
          });
          loadPending();
        });
        rejectBtn.addEventListener("click", async () => {
          await window.RraseAPI.request(`/knowledge/website/${page.id}/review`, {
            method: "POST", body: { approve: false },
          });
          loadPending();
        });
        card.appendChild(approveBtn);
        card.appendChild(rejectBtn);
        list.appendChild(card);
      });
    }

    importBtn.addEventListener("click", async () => {
      errorBox.classList.add("d-none");
      importBtn.disabled = true;
      importBtn.textContent = "Importing...";
      try {
        await window.RraseAPI.request("/knowledge/website/import", { method: "POST" });
        await loadPending();
      } catch (err) {
        errorBox.textContent = err.message;
        errorBox.classList.remove("d-none");
      } finally {
        importBtn.disabled = false;
        importBtn.textContent = "Import from official website";
      }
    });

    loadPending();
  }

  async function renderUnanswered() {
    content.innerHTML = "";
    content.appendChild(el("h2", { class: "h5 mb-3", text: "Unanswered Questions" }));
    const table = el("table", { class: "table table-sm bg-white" });
    table.innerHTML = "<thead><tr><th>Question</th><th>Times asked</th><th></th></tr></thead>";
    const tbody = el("tbody");
    table.appendChild(tbody);
    content.appendChild(table);

    async function load() {
      tbody.innerHTML = "";
      const items = await window.RraseAPI.request("/unanswered-questions");
      items.forEach((item) => {
        const resolveBtn = el("button", { class: "btn btn-sm btn-outline-success", text: "Mark resolved" });
        resolveBtn.addEventListener("click", async () => {
          await window.RraseAPI.request(`/unanswered-questions/${item.id}/resolve`, { method: "POST" });
          load();
        });
        const td = el("td");
        td.appendChild(resolveBtn);
        tbody.appendChild(el("tr", {}, [
          el("td", { text: item.question }), el("td", { text: String(item.times_asked) }), td,
        ]));
      });
    }
    load();
  }


  async function renderAudit() {
    content.innerHTML = "";
    content.appendChild(el("h2", { class: "h5 mb-3", text: "Audit Log" }));
    const table = el("table", { class: "table table-sm bg-white" });
    table.innerHTML = "<thead><tr><th>Action</th><th>Target</th><th>Actor</th><th>Details</th></tr></thead>";
    const tbody = el("tbody");
    table.appendChild(tbody);
    content.appendChild(table);
    const logs = await window.RraseAPI.request("/audit-logs");
    logs.forEach((log) => {
      tbody.appendChild(el("tr", {}, [
        el("td", { text: log.action }), el("td", { text: log.target ?? "" }),
        el("td", { text: log.actor_id ?? "" }), el("td", { text: log.details ?? "" }),
      ]));
    });
  }

  function showTab(tab) {
    document.querySelectorAll("#tabNav .nav-link").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tab);
    });
    if (tab === "overview") return renderOverview();
    if (tab === "documents") return renderDocuments();
    if (tab === "website") return renderWebsiteKnowledge();
    if (tab === "unanswered") return renderUnanswered();
    if (tab === "audit") return renderAudit();
    if (CRUD_TABS[tab]) return renderCrudSection(content, CRUD_TABS[tab]);
  }

  document.querySelectorAll("#tabNav .nav-link").forEach((btn) => {
    btn.addEventListener("click", () => showTab(btn.dataset.tab));
  });
  document.getElementById("logoutBtn").addEventListener("click", () => {
    window.RraseAPI.logout();
    window.location.href = "../login.html";
  });

  showTab("overview");
})();
