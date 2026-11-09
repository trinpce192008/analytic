(() => {
  const base = "/api/warden-portal";
  const byId = id => document.getElementById(id);
  const status = byId("portal-status");
  const show = message => { status.textContent = message; };
  const formatDate = value => new Date(value).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });

  async function api(path, method = "GET", payload) {
    const response = await fetch(base + path, {
      method,
      cache: "no-store",
      ...(payload === undefined ? {} : {
        headers: { "Content-Type": "application/json", "X-Warden-Portal": "1" },
        body: JSON.stringify(payload),
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw Error(typeof data.detail === "string" ? data.detail : "Yêu cầu không hợp lệ hoặc chưa thực hiện được.");
    }
    return data;
  }

  async function submit(form, event, work) {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    if (button.disabled) return;
    button.disabled = true;
    try { await work(); }
    catch (error) { show(error.message); }
    finally { button.disabled = false; }
  }

  async function setupSettings() {
    const form = byId("dashboard-settings");
    const checkbox = form.elements.user_dashboard;
    form.addEventListener("submit", event => submit(form, event, async () => {
      const result = await api("/settings", "PUT", { user_dashboard: checkbox.checked });
      checkbox.checked = result.user_dashboard;
      show(result.user_dashboard ? "Đã bật dashboard cá nhân." : "Đã tắt dashboard cá nhân.");
    }));
    checkbox.checked = (await api("/settings")).user_dashboard;
    form.hidden = false;
  }

  async function showUsage() {
    const result = await api("/dashboard/data");
    byId("usage-period").textContent = "30 ngày gần nhất · " + result.from + " → " + result.to;
    if (result.limited) show("Nhật ký vượt giới hạn đọc nên số liệu có thể chưa đầy đủ.");
    const rows = result.apps.map(app => {
      const row = document.createElement("tr");
      for (const value of [app.app, app.launches, app.minutes]) {
        const cell = row.insertCell();
        cell.textContent = typeof value === "number" ? value.toLocaleString("vi-VN") : value;
      }
      return row;
    });
    if (!rows.length && !result.limited) show("Chưa có hoạt động được ghi nhận trong kỳ.");
    byId("usage-apps").replaceChildren(...rows);
    byId("usage-table").hidden = !rows.length;
  }

  function setupSupport() {
    let offset = 0, admin = false, selected = null;
    let listRequest = 0, detailRequest = 0;
    const detail = byId("ticket-detail");
    const replyForm = byId("ticket-reply");
    const createForm = byId("ticket-create");
    const prev = byId("ticket-prev");
    const next = byId("ticket-next");

    async function list() {
      const generation = ++listRequest;
      const result = await api("/tickets?offset=" + offset);
      if (generation !== listRequest) return;
      admin = result.admin;
      byId("ticket-compose").hidden = admin;
      byId("ticket-list-title").textContent = admin ? "Tất cả yêu cầu hỗ trợ" : "Yêu cầu của tôi";
      const rows = result.tickets.map(ticket => {
        const row = document.createElement("li");
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "#" + ticket.id + " · " + ticket.subject;
        button.onclick = () => open(ticket.id).catch(error => show(error.message));
        const meta = document.createElement("span");
        meta.className = "meta";
        meta.textContent = [
          ...(admin ? [ticket.owner] : []),
          formatDate(ticket.created),
          ticket.answered ? "Đã phản hồi" : "Chờ phản hồi",
        ].join(" · ");
        row.append(button, meta);
        return row;
      });
      const target = byId("ticket-list");
      target.replaceChildren(...rows);
      if (!rows.length) target.textContent = "Chưa có yêu cầu hỗ trợ.";
      prev.hidden = offset === 0;
      next.hidden = !result.more;
    }

    async function open(id) {
      const generation = ++detailRequest;
      if (selected !== id) replyForm.reset();
      selected = id;
      detail.hidden = true;
      const { ticket, replies } = await api("/tickets/" + id);
      if (generation !== detailRequest) return;
      byId("ticket-subject").textContent = "#" + ticket.id + " · " + ticket.subject;
      byId("ticket-meta").textContent = (admin ? ticket.owner + " · " : "") + formatDate(ticket.created);
      byId("ticket-message").textContent = ticket.message;
      const container = byId("ticket-replies");
      container.replaceChildren();
      if (!replies.length) container.textContent = "Chưa có phản hồi.";
      for (const reply of replies) {
        const label = document.createElement("p");
        label.className = "meta";
        label.textContent = "Quản trị viên · " + formatDate(reply.created);
        const message = document.createElement("p");
        message.className = "message";
        message.textContent = reply.message;
        container.append(label, message);
      }
      replyForm.hidden = !admin;
      detail.hidden = false;
    }

    createForm.onsubmit = event => submit(createForm, event, async () => {
      const data = Object.fromEntries(new FormData(createForm));
      const { id } = await api("/tickets", "POST", data);
      createForm.reset();
      show("Đã gửi yêu cầu #" + id + ".");
      offset = 0;
      await list();
      await open(id);
    });
    replyForm.onsubmit = event => submit(replyForm, event, async () => {
      const id = selected;
      await api("/tickets/" + id + "/replies", "POST", Object.fromEntries(new FormData(replyForm)));
      show("Đã gửi phản hồi cho yêu cầu #" + id + ".");
      if (selected === id) {
        replyForm.reset();
        await open(id);
      }
      await list();
    });
    byId("ticket-reload").onclick = async () => {
      try {
        await list();
        if (selected !== null) await open(selected);
      } catch (error) { show(error.message); }
    };
    prev.onclick = () => { offset = Math.max(0, offset - 50); list().catch(error => show(error.message)); };
    next.onclick = () => { offset += 50; list().catch(error => show(error.message)); };
    return list();
  }

  const page = document.body.dataset.wardenPage;
  const init = byId("dashboard-settings") ? setupSettings
    : page === "support" ? setupSupport : showUsage;
  init().catch(error => show(error.message));
})();
