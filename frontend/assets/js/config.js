/**
 * Frontend configuration.
 *
 * During local development the backend runs on a different port than the
 * static frontend, so the API base URL is configurable here in one place.
 * When deployed under the college subdomain behind Nginx, this should be
 * changed to a relative path ("/api/v1") once Nginx proxies /api to FastAPI.
 */
window.RRASE_CONFIG = {
  API_BASE_URL: "https://rrase-bot.onrender.com/api/v1",
};
