import sys,types,importlib.util,tempfile,unittest,time
from pathlib import Path
from fastapi import FastAPI,Request,HTTPException
from fastapi.testclient import TestClient
base=Path(__file__).parent
pkg=types.ModuleType('app');pkg.__path__=[str(base)];sys.modules['app']=pkg
u=types.ModuleType('app.user_manager');u.GROUP_DATA={n:{'settings':{'admin':False}} for n in ['warden_free','warden_vip','study']}
records={}
u.get_user=lambda n:records.get(n)
u.get_effective_settings=lambda n:{'admin':n=='admin'}
u.groups_of=lambda n:records[n]['settings'].get('groups',[])
def update(n,s):records[n]['settings']=s.copy()
u.update_user_settings=update;sys.modules['app.user_manager']=u
sec=types.ModuleType('app.security')
async def verify(request:Request):
 n=request.headers.get('test-user')
 if not n:raise HTTPException(401)
 return {'username':n,'is_admin':n=='admin'}
sec.verify_token=verify;sys.modules['app.security']=sec
st=types.ModuleType('app.settings');st.settings=types.SimpleNamespace();sys.modules['app.settings']=st
spec=importlib.util.spec_from_file_location('app.warden_billing',base/'warden_billing.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
a=FastAPI();a.include_router(b.router);client=TestClient(a)
def headers(n='student'):return {'test-user':n,'X-Warden-Billing':'1','Sec-Fetch-Site':'same-origin'}
class TestBilling(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();b.ROOT=Path(self.tmp.name)
  records.clear();records.update({'student':{'username':'student','is_admin':False,'settings':{'groups':['warden_free','study'],'group':'warden_free','harden_container':True,'session_limit':2}},'admin':{'username':'admin','is_admin':True}})
 def tearDown(self):self.tmp.cleanup()
 def order(self):
  r=client.post('/api/warden-billing/orders',json={'plan':'demo_5m'},headers=headers());self.assertEqual(r.status_code,200,r.text);return r.json()['id']
 def legacy_order(self,plan='demo_5m'):
  with b.connection() as c:
   oid=f"LEGACY-{c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]}"
   c.execute("INSERT INTO orders(id,username,plan,status,created) VALUES(?,'student',?,'pending',?)",(oid,plan,time.time()))
  return oid
 def confirm(self,oid):return client.post('/api/warden-billing/admin/orders/'+oid+'/confirm',json={},headers=headers('admin'))
 def subscription(self):
  with b.connection() as c:
   return dict(c.execute('SELECT * FROM subscriptions WHERE username=?',('student',)).fetchone())
 def cancel(self,expires,request_headers=None):
  return client.post('/api/warden-billing/admin/subscriptions/cancel',
                     json={'username':'student','expires':expires},
                     headers=headers('admin') if request_headers is None else request_headers)
 def test_lifecycle(self):
  oid=self.order()
  self.assertEqual(self.confirm(oid).json(),{'status':'already_confirmed'})
  duplicate=client.post('/api/warden-billing/orders',json={'plan':'demo_5m'},headers=headers())
  self.assertEqual(duplicate.status_code,409)
  s=records['student']['settings'];self.assertEqual(s['groups'],['study','warden_vip']);self.assertTrue(s['harden_container']);self.assertEqual(s['session_limit'],2)
  with b.connection() as c: expiry=c.execute('SELECT expires FROM subscriptions').fetchone()[0]
  self.confirm(oid)
  with b.connection() as c:self.assertEqual(c.execute('SELECT expires FROM subscriptions').fetchone()[0],expiry)
  with b.connection() as c:c.execute('UPDATE subscriptions SET expires=?',(time.time()-1,))
  b.reconcile();self.assertEqual(records['student']['settings']['groups'],['study','warden_free'])
 def test_auth_csrf(self):
  self.assertEqual(client.get('/api/warden-billing/me').status_code,401)
  self.assertEqual(client.get('/api/warden-billing/admin',headers=headers()).status_code,403)
  self.assertEqual(client.post('/api/warden-billing/orders',json={'plan':'demo_5m'},headers={'test-user':'student'}).status_code,403)
  oid=self.order();self.assertEqual(client.post('/api/warden-billing/admin/orders/'+oid+'/confirm',json={},headers=headers()).status_code,403)
 def test_retry_no_extension(self):
  original=u.update_user_settings
  def fail(*args):raise ValueError('simulated failure')
  u.update_user_settings=fail
  try:
   self.order()
   self.assertEqual(client.post('/api/warden-billing/orders',json={'plan':'demo_5m'},headers=headers()).status_code,409)
  finally:u.update_user_settings=original
  with b.connection() as c:
   s=c.execute('SELECT * FROM subscriptions').fetchone();self.assertEqual(s['state'],'pending_grant');expiry=s['expires']
  b.reconcile()
  with b.connection() as c:
   s=c.execute('SELECT * FROM subscriptions').fetchone();self.assertEqual(s['state'],'active');self.assertEqual(s['expires'],expiry)
 def test_renew(self):
  self.order()
  with b.connection() as c:old=c.execute('SELECT expires FROM subscriptions').fetchone()[0]
  self.confirm(self.legacy_order())
  with b.connection() as c:self.assertAlmostEqual(c.execute('SELECT expires FROM subscriptions').fetchone()[0],old+300)
 def test_auto_confirm_reuses_matching_legacy_order_and_retires_other_test_orders(self):
  pending=self.legacy_order('vip_30d')
  other=self.legacy_order()
  response=client.post('/api/warden-billing/orders',json={'plan':'vip_30d'},headers=headers())
  self.assertEqual(response.status_code,200)
  self.assertEqual(response.json()['id'],pending)
  self.assertIn('warden_vip',records['student']['settings']['groups'])
  with b.connection() as c:
   self.assertEqual(tuple(c.execute("SELECT status,confirmed_by,is_test FROM orders WHERE id=?",(pending,)).fetchone()),
                    ('confirmed','system',1))
   self.assertEqual(c.execute("SELECT status FROM orders WHERE id=?",(other,)).fetchone()[0],'cancelled')
 def test_cancel_preserves_order_and_other_settings(self):
  oid=self.order()
  self.confirm(oid)
  expires=self.subscription()['expires']
  self.assertEqual(self.cancel(expires,headers()).status_code,403)
  self.assertEqual(self.cancel(expires,{'test-user':'admin'}).status_code,403)
  self.assertEqual(self.cancel(expires-1).status_code,409)
  self.assertEqual(self.cancel(expires).json(),{'status':'cancelled'})
  self.assertEqual(self.cancel(expires).json(),{'status':'cancelled'})
  b.reconcile()
  self.assertEqual(self.subscription()['state'],'cancelled')
  settings=records['student']['settings']
  self.assertEqual(settings['groups'],['study','warden_free'])
  self.assertTrue(settings['harden_container'])
  with b.connection() as c:
   self.assertEqual(c.execute('SELECT status FROM orders WHERE id=?',(oid,)).fetchone()[0],'confirmed')
   self.assertEqual(c.execute("SELECT detail FROM billing_events WHERE action='vip_cancel_requested'").fetchall()[0][0],'admin')
   self.assertEqual(c.execute("SELECT COUNT(*) FROM billing_events WHERE action='vip_cancelled'").fetchone()[0],1)
  self.confirm(self.order())
  self.assertEqual(self.subscription()['state'],'active')
  self.assertEqual(self.cancel(expires).status_code,409)

 def test_cancel_retries_a_failed_downgrade(self):
  self.confirm(self.order())
  expires=self.subscription()['expires']
  original=u.update_user_settings
  def fail(*args):raise ValueError('simulated failure')
  u.update_user_settings=fail
  try:self.assertEqual(self.cancel(expires).json(),{'status':'pending_cancel'})
  finally:u.update_user_settings=original
  self.assertEqual(records['student']['settings']['groups'],['study','warden_vip'])
  b.reconcile()
  self.assertEqual(self.subscription()['state'],'cancelled')
  self.assertEqual(records['student']['settings']['groups'],['study','warden_free'])
 def test_subscription_management_is_separate_and_admin_only(self):
  self.confirm(self.order())
  url='/api/warden-billing/admin/subscriptions'
  for path in (url,url+'.js'):
   self.assertEqual(client.get(path).status_code,401)
   self.assertEqual(client.get(path,headers=headers()).status_code,403)
   self.assertEqual(client.get(path,headers=headers('admin')).status_code,200)
  self.assertIn('Hủy gói VIP',client.get(url,headers=headers('admin')).text)
  self.cancel(self.subscription()['expires'])
  page=client.get(url,headers=headers('admin')).text
  self.assertIn('Đã hủy · Free',page)
  self.assertNotIn('data-user=',page)
  for suffix,file in (('', 'warden_billing.html'),('/app.js','warden_billing.js')):
   self.assertEqual(client.get('/api/warden-billing'+suffix).content,(base/file).read_bytes())

 def test_self_cancel_is_account_scoped_and_preserves_confirmed_orders(self):
  url='/api/warden-billing'
  confirmed=self.order()
  self.confirm(confirmed)
  pending=self.legacy_order()
  self.assertEqual(client.post(url+'/cancel',json={}).status_code,401)
  self.assertEqual(client.post(url+'/cancel',headers={'test-user':'student'},json={}).status_code,403)
  self.assertEqual(client.post(url+'/cancel',headers=headers('admin'),json={}).status_code,400)
  before=client.get(url+'/me',headers=headers()).json()
  self.assertEqual(before['subscription']['plan'],'demo_5m')
  self.assertEqual(before['plans']['vip_30d']['amount'],429000)
  self.assertEqual(client.post(url+'/cancel',headers=headers(),json={'username':'admin'}).json(),{'status':'cancelled'})
  after=client.get(url+'/me',headers=headers()).json()
  self.assertEqual(after['subscription']['state'],'expired')
  self.assertEqual({order['id']:order['status'] for order in after['orders']},
                   {confirmed:'confirmed',pending:'cancelled'})
  self.assertEqual(records['student']['settings']['groups'],['study','warden_free'])
  self.assertNotEqual(self.order(),pending)

 def test_self_cancel_blocks_new_orders_until_free_is_applied(self):
  self.confirm(self.order())
  url='/api/warden-billing'
  original=u.update_user_settings
  def fail(*args):raise ValueError('simulated failure')
  u.update_user_settings=fail
  try:
   self.assertEqual(client.post(url+'/cancel',headers=headers(),json={}).status_code,409)
   self.assertEqual(client.get(url+'/me',headers=headers()).json()['subscription']['state'],'pending_revoke')
   self.assertEqual(client.post(url+'/orders',headers=headers(),json={'plan':'demo_5m'}).status_code,409)
  finally:u.update_user_settings=original
  b.reconcile()
  self.assertEqual(client.get(url+'/me',headers=headers()).json()['subscription']['state'],'expired')
  self.order()
if __name__=='__main__':unittest.main()
