/**
 * Shared frontend behavior for Phase 1:
 *  - Highlights the active nav link
 *  - Performs a REAL call to GET /api/v1/health and reflects the actual
 *    backend/database status. No fake/hard-coded "connected" state.
 */
(function () {
  function highlightActiveNav() {
    const path = window.location.pathname.split("/").pop() || "index.html";
    document.querySelectorAll(".rrase-navbar .nav-link").forEach((link) => {
      const href = link.getAttribute("href");
      if (href === path) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      }
    });
  }

  async function checkBackendHealth() {
    const indicator = document.getElementById("rrase-status-indicator");
    const label = document.getElementById("rrase-status-label");
    if (!indicator || !label) return;

    const base = (window.RRASE_CONFIG && window.RRASE_CONFIG.API_BASE_URL) || "";

    try {
      const response = await fetch(`${base}/health`, { method: "GET" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();

      const dbLabel = data.database ? "database connected" : "database unavailable";
      if (data.status === "ok") {
        indicator.className = "rrase-status-dot rrase-status-ok";
        label.textContent = `Backend online (${dbLabel})`;
      } else {
        indicator.className = "rrase-status-dot rrase-status-down";
        label.textContent = `Backend running, ${dbLabel}`;
      }
    } catch (err) {
      indicator.className = "rrase-status-dot rrase-status-down";
      label.textContent = "Backend unreachable - is uvicorn running?";
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    highlightActiveNav();
    checkBackendHealth();
  });
})();
