'use strict';const $=s=>document.getElementById(s),esc=s=>String(s??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),date=t=>t?new Date(t*1000).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'}):'—';let plans={},busy=false;
const labels={pending:'Chờ xác nhận',confirmed:'Đã xác nhận thử nghiệm',active:'VIP đã kích hoạt',expired:'Đã hết hạn · Free',pending_grant:'Chờ cấp quyền VIP',pending_revoke:'Hết hạn · chờ thu hồi VIP',pending_cancel:'Đang chờ thu hồi VIP',cancelled:'Đã hủy · Free'};
async function api(path,body){const r=await fetch('/api/warden-billing'+path,{credentials:'same-origin',cache:'no-store',method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Warden-Billing':'1'}:{},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Lỗi HTTP '+r.status);return d}
function orderRow(o,admin=false){return `<tr>${admin?`<td>${esc(o.username)}</td>`:''}<td>${esc(o.id)}</td><td>${esc(plans[o.plan]?.label||o.plan)}</td><td>${esc(labels[o.status]||o.status)}</td>${admin?`<td>${o.status==='pending'?`<button data-confirm="${esc(o.id)}">Giả lập thành công</button>`:'Đã xử lý'}</td>`:`<td>${date(o.created)}</td>`}</tr>`}
function subscriptionRow(s) {
  const canCancel = ['active', 'pending_grant'].includes(s.state) && s.expires > Date.now() / 1000;
  const cancel = canCancel
    ? ` <button data-cancel="${esc(s.username)}" data-expires="${esc(s.expires)}">Hủy gói VIP</button>`
    : '';
  return `<p><strong>${esc(s.username)}</strong> · ${esc(labels[s.state] || s.state)} · ${date(s.expires)}${s.error ? ' · ' + esc(s.error) : ''}${cancel}</p>`;
}
async function load(message = 'Đã cập nhật · Giờ Việt Nam'){try{const d=await api('/me');plans=d.plans;const s=d.subscription;$('me').innerHTML=`<p>Tài khoản: <strong>${esc(d.username)}</strong></p><p>Trạng thái: <strong>${s?esc(labels[s.state]||s.state):'Chưa có gói do Billing quản lý'}</strong></p>${s?`<p>${['pending_cancel','cancelled'].includes(s.state)?'Thời điểm hủy':'Hạn VIP'}: ${date(s.expires)}</p>${s.error?`<p>${esc(s.error)}</p>`:''}`:''}`;$('plans').innerHTML=d.admin?'<section><h2>Tài khoản quản trị</h2><p>Dùng tài khoản người dùng riêng để tạo đơn. Admin có thể xác nhận đơn và hủy gói VIP do Warden quản lý.</p></section>':Object.entries(plans).map(([id,p])=>`<section><h2>${esc(p.label)}</h2><p>${p.amount.toLocaleString('vi-VN')} đ · giá minh họa</p><button data-plan="${esc(id)}">Nâng cấp thử nghiệm</button></section>`).join('');$('orders').innerHTML=d.orders.map(o=>orderRow(o)).join('')||'<tr><td colspan="4">Chưa có đơn.</td></tr>';$('admin').hidden=!d.admin;if(d.admin){const a=await api('/admin');$('summary').textContent=a.confirmed_test_orders+' đơn thử nghiệm đã xác nhận · Doanh thu thật: chưa kết nối';$('allOrders').innerHTML=a.orders.map(o=>orderRow(o,true)).join('')||'<tr><td colspan="5">Chưa có đơn.</td></tr>';$('subs').innerHTML=a.subscriptions.map(subscriptionRow).join('')||'Chưa có gói.';$('logs').textContent=a.events.map(e=>[date(e.at),e.username,e.action,e.order_id,e.detail].filter(Boolean).join(' · ')).join('\n')||'Chưa có sự kiện.'}$('status').textContent=message}catch(e){$('status').textContent=e.message}}
document.addEventListener('click', async (event) => {
  const button = event.target.closest('button[data-plan],button[data-confirm],button[data-cancel]');
  if (!button || busy) return;
  const { plan, confirm, cancel, expires } = button.dataset;
  if (confirm && !window.confirm('Xác nhận thanh toán thử nghiệm và cấp quyền VIP thật cho tài khoản của đơn này?')) return;
  if (cancel && !window.confirm(`Hủy gói VIP của ${cancel} và chuyển tài khoản về Free?`)) return;

  busy = true;
  button.disabled = true;
  try {
    if (cancel) {
      const result = await api('/admin/subscriptions/cancel', { username: cancel, expires: Number(expires) });
      await load(result.status === 'cancelled'
        ? 'Đã hủy gói VIP và chuyển tài khoản về Free.'
        : 'Đã ghi yêu cầu hủy. Hệ thống sẽ thử lại việc thu hồi VIP.');
    } else {
      if (plan) await api('/orders', { plan });
      else await api('/admin/orders/' + encodeURIComponent(confirm) + '/confirm', {});
      await load();
    }
  } catch (error) {
    $('status').textContent = error.message;
  } finally {
    busy = false;
    button.disabled = false;
  }
});
$('refresh').onclick = () => { if (!busy) load(); };
load();
setInterval(() => { if (!document.hidden && !busy) load(); }, 10000);
