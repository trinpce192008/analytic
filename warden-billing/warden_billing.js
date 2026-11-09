'use strict';const $=s=>document.getElementById(s),esc=s=>String(s??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),date=t=>t?new Date(t*1000).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'}):'—';let plans={},busy=false;
const labels={pending:'Chờ xác nhận',confirmed:'Đã xác nhận thử nghiệm',active:'VIP đã kích hoạt',expired:'Đã hết hạn · Free',pending_grant:'Chờ cấp quyền VIP',pending_revoke:'Đang chờ thu hồi VIP',pending_cancel:'Đang chờ thu hồi VIP',cancelled:'Đã hủy'};
const planDetails = {
  free: {
    title: 'Bắt đầu với Warden',
    intro: 'Các tiện ích cơ bản dành cho tài khoản miễn phí.',
    period: 'Gói miễn phí',
    features: ['Chạy tối đa 1 ứng dụng cùng lúc', '5 GB dung lượng lưu trữ',
      'Dùng thử VaultWarden trong 30 ngày để lưu trữ và bảo vệ mật khẩu'],
    foot: 'VaultWarden: dùng thử tính năng lưu trữ và bảo vệ mật khẩu trong 30 ngày.',
  },
  demo_5m: {
    title: 'Kiểm tra quyền VIP',
    intro: 'Kiểm tra cấp quyền VIP và tự động thu hồi sau 5 phút.',
    period: 'Trong 5 phút',
    features: ['Kích hoạt VIP sau khi đơn được xác nhận', 'Kiểm tra tự động thu hồi quyền sau 5 phút',
      'Tự động trở về gói Free khi hết hạn'],
    foot: 'Dành cho kiểm tra chức năng cấp và thu hồi quyền VIP.',
  },
  vip_30d: {
    title: 'Không gian làm việc mở rộng',
    intro: 'Mở rộng thời gian sử dụng, lưu trữ và bảo vệ mật khẩu.',
    period: 'Cho 30 ngày sử dụng',
    features: ['Không giới hạn số ứng dụng chạy cùng lúc',
      'Không giới hạn thời lượng mỗi phiên trong tổng hạn mức sử dụng',
      'Tổng 200 giờ sử dụng mỗi tháng', '20 GB dung lượng lưu trữ', 'VaultWarden không giới hạn'],
    foot: 'Giờ sử dụng được cộng dồn khi chạy nhiều ứng dụng cùng lúc.',
  },
};

function planCards(subscription, locked) {
  const current = !locked ? 'free'
    : subscription.state === 'active' && subscription.expires * 1000 > Date.now() ? subscription.plan
    : null;
  return Object.entries({ free: { label: 'Free', amount: 0 }, ...plans }).map(([id, plan]) => {
    const { title, intro, period, features, foot } = planDetails[id];
    const selected = id === current;
    const free = id === 'free';
    const text = selected ? 'Gói đang dùng' : free ? 'Gói miễn phí' : locked ? 'Đang có gói VIP' : 'Nâng cấp';
    return `<section class="plan ${id === 'vip_30d' ? 'featured' : ''} ${selected ? 'current-plan' : ''}">
      <div class="plan-name">${esc(plan.label)}</div>
      <h2>${title}</h2><p class="intro">${intro}</p>
      <button type="button" ${free || locked ? 'disabled' : ''} ${free ? '' : `data-plan="${esc(id)}"`}>${text}</button>
      <div class="price">${Number(plan.amount).toLocaleString('vi-VN')} <small>₫</small></div>
      <p class="period">${period}</p>
      <ul>${features.map(feature => `<li>${esc(feature)}</li>`).join('')}</ul>
      <p class="foot">${foot}</p>
    </section>`;
  }).join('');
}
async function api(path,body){const r=await fetch('/api/warden-billing'+path,{credentials:'same-origin',cache:'no-store',method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Warden-Billing':'1'}:{},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Lỗi HTTP '+r.status);return d}
function orderRow(o,admin=false){return `<tr>${admin?`<td>${esc(o.username)}</td>`:''}<td>${esc(o.id)}</td><td>${esc(plans[o.plan]?.label||o.plan)}</td><td>${esc(labels[o.status]||o.status)}</td>${admin?`<td>${o.status==='pending'?`<button data-confirm="${esc(o.id)}">Giả lập thành công</button>`:'Đã xử lý'}</td>`:`<td>${date(o.created)}</td>`}</tr>`}
async function load(){try{const d=await api('/me');plans=d.plans;const s=d.subscription;const locked=['active','pending_grant','pending_revoke','pending_cancel'].includes(s?.state);$('me').innerHTML=`<p>Tài khoản: <strong>${esc(d.username)}</strong></p><p>Trạng thái: <strong>${s?esc(labels[s.state]||s.state):'Free'}</strong></p>${s?`<p>Hạn VIP: ${date(s.expires)}</p>${s.error?`<p>${esc(s.error)}</p>`:''}`:''}`;if(!d.admin&&locked)$('me').insertAdjacentHTML('beforeend','<button id="warden-cancel-plan" type="button" style="margin-top:10px;background:#b42318">Hủy gói</button>');$('plans').innerHTML=d.admin?'<section><h2>Tài khoản quản trị</h2><p>Dùng tài khoản người dùng riêng để tạo đơn. Admin chỉ xác nhận giao dịch mô phỏng.</p></section>':planCards(s,locked);$('orders').innerHTML=d.orders.map(o=>orderRow(o)).join('')||'<tr><td colspan="4">Chưa có đơn.</td></tr>';$('admin').hidden=!d.admin;if(d.admin){const a=await api('/admin');$('summary').textContent=a.confirmed_test_orders+' đơn thử nghiệm đã xác nhận · Doanh thu thật: chưa kết nối';$('allOrders').innerHTML=a.orders.map(o=>orderRow(o,true)).join('')||'<tr><td colspan="5">Chưa có đơn.</td></tr>';$('subs').innerHTML=a.subscriptions.map(s=>`<p><strong>${esc(s.username)}</strong> · ${esc(labels[s.state]||s.state)} · ${date(s.expires)}${s.error?' · '+esc(s.error):''}</p>`).join('')||'Chưa có gói.';$('logs').textContent=a.events.map(e=>[date(e.at),e.username,e.action,e.order_id,e.detail].filter(Boolean).join(' · ')).join('\n')||'Chưa có sự kiện.'}$('status').textContent='Đã cập nhật · Giờ Việt Nam'}catch(e){$('status').textContent=e.message}}
document.addEventListener('click', async (event) => {
  const button = event.target.closest('button[data-plan],button[data-confirm],#warden-cancel-plan');
  if (!button || button.disabled || busy) return;
  const { plan, confirm } = button.dataset;
  const cancel = button.id === 'warden-cancel-plan';
  if (confirm && !window.confirm('Xác nhận thanh toán thử nghiệm và cấp quyền VIP thật cho tài khoản của đơn này?')) return;
  if (cancel && !window.confirm('Hủy gói hiện tại và trở về Free để thử đăng ký gói khác?')) return;

  busy = true;
  button.disabled = true;
  try {
    if (cancel) await api('/cancel', {});
    else if (plan) await api('/orders', { plan });
    else await api('/admin/orders/' + encodeURIComponent(confirm) + '/confirm', {});
    await load();
  } catch (error) {
    if (cancel) await load();
    $('status').textContent = error.message;
  } finally {
    busy = false;
    button.disabled = false;
  }
});
$('refresh').onclick = () => { if (!busy) load(); };
load();
setInterval(() => { if (!document.hidden && !busy) load(); }, 10000);
