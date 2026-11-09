(() => {
  const sidebar = document.querySelector("#rail .rail-links");
  if (!sidebar) return;

  const links = [
    ["warden-analytics-button", "Dashboard Analytics", "fa-chart-bar", "/api/warden-analytics", "admin_analytics"],
    ["warden-personal-button", "Dashboard cá nhân", "fa-chart-bar", "/api/warden-portal/dashboard", "user_dashboard"],
    ["warden-upgrade-button", "Nâng cấp gói", "fa-arrow-circle-up", "/api/warden-billing", "upgrade"],
    ["warden-support-button", "Hỗ trợ", "fa-life-ring", "/api/warden-portal/support", "support"],
  ];
  let refreshing = false;

  async function refresh() {
    if (refreshing) return;
    refreshing = true;
    try {
      const response = await fetch("/api/warden-portal/nav", { cache: "no-store" });
      const allowed = response.ok ? { ...(await response.json()), support: true } : {};
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
    } catch {
      for (const [id] of links) document.getElementById(id)?.remove();
    } finally {
      refreshing = false;
    }
  }

  refresh();
  window.addEventListener("pageshow", refresh);
  window.addEventListener("focus", refresh);
  setInterval(refresh, 15000);
})();
