'use strict';

const statusMessage = document.getElementById('status');

document.querySelectorAll('button[data-user]').forEach((button) => {
  button.addEventListener('click', async () => {
    const { user, expires } = button.dataset;
    if (!window.confirm(`Hủy gói VIP của ${user} và chuyển tài khoản về Free?`)) return;
    button.disabled = true;
    statusMessage.textContent = 'Đang hủy gói VIP…';
    try {
      const response = await fetch('/api/warden-billing/admin/subscriptions/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Warden-Billing': '1' },
        body: JSON.stringify({ username: user, expires: Number(expires) }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Không thể hủy gói. Hãy thử lại.');
      window.location.reload();
    } catch (error) {
      statusMessage.textContent = error.message;
      button.disabled = false;
    }
  });
});
