/**
 * Shared API client: wraps fetch with the JSON API base URL, attaches the
 * bearer token from localStorage when present, and centralizes basic
 * auth-state helpers used by every page (login, chat, dashboards).
 */
window.RraseAPI = (function () {
  const BASE = (window.RRASE_CONFIG && window.RRASE_CONFIG.API_BASE_URL) || "/api/v1";

  function getTokens() {
    try {
      return JSON.parse(localStorage.getItem("rrase_tokens") || "null");
    } catch (e) {
      return null;
    }
  }

  function setTokens(tokens) {
    localStorage.setItem("rrase_tokens", JSON.stringify(tokens));
  }

  function clearTokens() {
    localStorage.removeItem("rrase_tokens");
  }

  function isLoggedIn() {
    return !!getTokens()?.access_token;
  }

  function hasRole(role) {
    const tokens = getTokens();
    return !!tokens && Array.isArray(tokens.roles) && tokens.roles.includes(role);
  }

  async function request(path, { method = "GET", body, auth = true, isForm = false } = {}) {
    const headers = {};
    if (!isForm) headers["Content-Type"] = "application/json";
    if (auth) {
      const tokens = getTokens();
      if (tokens?.access_token) headers["Authorization"] = `Bearer ${tokens.access_token}`;
    }
    const resp = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (resp.status === 204) return null;
    let data = null;
    try {
      data = await resp.json();
    } catch (e) {
      /* empty body */
    }
    if (!resp.ok) {
      const message = (data && (data.detail || data.message)) || `Request failed (${resp.status})`;
      throw new Error(typeof message === "string" ? message : JSON.stringify(message));
    }
    return data;
  }

  async function login(email, password) {
    const data = await request("/auth/login", { method: "POST", body: { email, password }, auth: false });
    setTokens(data);
    return data;
  }

  async function register(email, fullName, password) {
    return request("/auth/register", {
      method: "POST",
      body: { email, full_name: fullName, password },
      auth: false,
    });
  }

  function logout() {
    clearTokens();
  }

  return { BASE, request, login, register, logout, getTokens, isLoggedIn, hasRole };
})();
