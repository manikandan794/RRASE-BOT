/**
 * Faculty dashboard is intentionally read-only: faculty can see analytics,
 * review unanswered student questions, and browse published FAQs/notices,
 * but content management stays with admin/principal per the RBAC design.
 */
(function () {
  if (!window.RraseDashboard.requireAnyRole(["faculty", "admin", "principal"])) return;

  const { el } = window.RraseDashboard;
  const content = document.getElementById("tabContent");

  async function renderOverview() {
    content.innerHTML = "<h2 class='h5 mb-3'>Overview</h2><div id='ovBox'>Loading...</div>";
    try {
      const data = await window.RraseAPI.request("/analytics/summary");
      const box = document.getElementById("ovBox");
      box.innerHTML = "";
      const stats = [
        ["Total conversations", data.total_conversations],
        ["Total messages", data.total_messages],
        ["Unresolved questions", data.unresolved_unanswered],
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
    } catch (err) {
      content.innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
    }
  }

  async function renderUnanswered() {
    content.innerHTML = "";
    content.appendChild(el("h2", { class: "h5 mb-3", text: "Unanswered Questions" }));
    content.appendChild(el("p", { class: "text-secondary small", text: "Read-only - ask an admin or principal to mark items resolved once the FAQ/knowledge base is updated." }));
    const table = el("table", { class: "table table-sm bg-white" });
    table.innerHTML = "<thead><tr><th>Question</th><th>Times asked</th></tr></thead>";
    const tbody = el("tbody");
    table.appendChild(tbody);
    content.appendChild(table);
    const items = await window.RraseAPI.request("/unanswered-questions");
    items.forEach((item) => {
      tbody.appendChild(el("tr", {}, [el("td", { text: item.question }), el("td", { text: String(item.times_asked) })]));
    });
  }

  async function renderReadOnlyList(endpoint, titleText, fields) {
    content.innerHTML = "";
    content.appendChild(el("h2", { class: "h5 mb-3", text: titleText }));
    const table = el("table", { class: "table table-sm bg-white" });
    table.innerHTML = `<thead><tr>${fields.map((f) => `<th>${f.label}</th>`).join("")}</tr></thead>`;
    const tbody = el("tbody");
    table.appendChild(tbody);
    content.appendChild(table);
    const items = await window.RraseAPI.request(endpoint);
    items.forEach((item) => {
      tbody.appendChild(el("tr", {}, fields.map((f) => el("td", { text: item[f.name] ?? "" }))));
    });
  }

  function showTab(tab) {
    document.querySelectorAll("#tabNav .nav-link").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tab));
    if (tab === "overview") return renderOverview();
    if (tab === "unanswered") return renderUnanswered();
    if (tab === "faqs") return renderReadOnlyList("/faqs", "Published FAQs", [
      { name: "question", label: "Question" }, { name: "answer", label: "Answer" },
    ]);
    if (tab === "notices") return renderReadOnlyList("/notices", "Notices", [
      { name: "title", label: "Title" }, { name: "body", label: "Body" },
    ]);
  }

  document.querySelectorAll("#tabNav .nav-link").forEach((btn) => btn.addEventListener("click", () => showTab(btn.dataset.tab)));
  document.getElementById("logoutBtn").addEventListener("click", () => {
    window.RraseAPI.logout();
    window.location.href = "../login.html";
  });

  showTab("overview");
})();
