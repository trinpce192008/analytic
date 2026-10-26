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
 def confirm(self,oid):return client.post('/api/warden-billing/admin/orders/'+oid+'/confirm',json={},headers=headers('admin'))
 def test_lifecycle(self):
  oid=self.order();self.assertEqual(self.order(),oid)
  self.assertEqual(self.confirm(oid).status_code,200)
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
  oid=self.order();original=u.update_user_settings
  def fail(*args):raise ValueError('simulated failure')
  u.update_user_settings=fail
  try:self.confirm(oid)
  finally:u.update_user_settings=original
  with b.connection() as c:
   s=c.execute('SELECT * FROM subscriptions').fetchone();self.assertEqual(s['state'],'pending_grant');expiry=s['expires']
  b.reconcile()
  with b.connection() as c:
   s=c.execute('SELECT * FROM subscriptions').fetchone();self.assertEqual(s['state'],'active');self.assertEqual(s['expires'],expiry)
 def test_renew(self):
  self.confirm(self.order())
  with b.connection() as c:old=c.execute('SELECT expires FROM subscriptions').fetchone()[0]
  self.confirm(self.order())
  with b.connection() as c:self.assertAlmostEqual(c.execute('SELECT expires FROM subscriptions').fetchone()[0],old+300)
if __name__=='__main__':unittest.main()
