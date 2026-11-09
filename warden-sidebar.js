(() => {
  const links = [
    ["warden-analytics-button", "Dashboard Analytics", "fa-chart-bar", "/api/warden-analytics", "analytics"],
    ["warden-upgrade-button", "Nâng cấp gói", "fa-arrow-circle-up", "/api/warden-billing", "upgrade"],
    ["warden-support-button", "Hỗ trợ", "fa-life-ring", "/api/warden-portal/support", "support"],
  ];
  let sidebar;
  let allowed = {};
  let refreshing = false;
  let startupRetries = 10;
  let retryTimer;

  function render() {
    sidebar = document.querySelector("#rail .rail-links");
    if (!sidebar) return;
    for (const [id, label, icon, href, permission] of links) {
      let link = document.getElementById(id);
      if (!allowed[permission]) {
        link?.remove();
        continue;
      }
      if (!link || link.tagName !== "A") {
        link?.remove();
        link = document.createElement("a");
        link.id = id;
      }
      if (link.parentElement !== sidebar || !link.classList.contains("warden-rail-link")) {
        link.className = "warden-rail-link";
        link.removeAttribute("style");
        link.href = href;
        link.title = label;
        const glyph = document.createElement("i");
        glyph.className = "fas " + icon;
        glyph.setAttribute("aria-hidden", "true");
        const text = document.createElement("span");
        text.textContent = label;
        link.replaceChildren(glyph, text);
        sidebar.append(link);
      }
    }
  }

  async function refresh() {
    if (refreshing) return;
    clearTimeout(retryTimer);
    refreshing = true;
    try {
      const response = await fetch("/api/warden-portal/nav", {
        cache: "no-store",
        credentials: "same-origin",
      });
      allowed = response.ok ? { ...(await response.json()), support: true } : {};
      if (response.ok) startupRetries = 0;
    } catch {
      allowed = {};
    } finally {
      refreshing = false;
    }
    render();
    if (startupRetries > 0) {
      startupRetries--;
      retryTimer = setTimeout(refresh, 1000);
    }
  }

  new MutationObserver((records) => {
    const current = document.querySelector("#rail .rail-links");
    if (current !== sidebar || records.some(({ target }) => target === sidebar)) render();
  }).observe(document.body, { childList: true, subtree: true });
  refresh();
  window.addEventListener("pageshow", refresh);
  window.addEventListener("focus", refresh);
  setInterval(refresh, 15000);
})();
