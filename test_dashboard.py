"""Unit tests with simulated SealSkin authentication; no live-server claims."""
import importlib.util, sys, tempfile, types, unittest, json
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
ROOT=Path(__file__).parent
pkg=types.ModuleType('app');pkg.__path__=[str(ROOT)];sys.modules['app']=pkg
security=types.ModuleType('app.security')
async def verify_admin(x_test_role: str=Header(default='')):
    if not x_test_role: raise HTTPException(401)
    if x_test_role=='user': raise HTTPException(403)
    return {'username':'admin' if x_test_role=='root' else 'other_admin','is_admin':True}
audit=types.ModuleType('app.audit'); audit.record=lambda *a,**k:None; sys.modules['app.audit']=audit
security.verify_admin=verify_admin;sys.modules['app.security']=security
settings=types.ModuleType('app.settings');settings.settings=types.SimpleNamespace(node_state_path='/unused');sys.modules['app.settings']=settings
spec=importlib.util.spec_from_file_location('app.warden_analytics',ROOT/'warden_analytics.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
app=FastAPI();app.include_router(mod.router);client=TestClient(app)
class Tests(unittest.TestCase):
 def test_access(self):
    for path in ['/api/warden-analytics','/api/warden-analytics/data','/api/warden-analytics/app.js']:
      self.assertEqual(client.get(path).status_code,401)
      self.assertEqual(client.get(path,headers={'x-test-role':'user'}).status_code,403)
      self.assertEqual(client.get(path,headers={'x-test-role':'other_admin'}).status_code,403)
      self.assertEqual(client.get(path,headers={'x-test-role':'root'}).status_code,200)
 def test_malformed_dedup_cross_day(self):
    with tempfile.TemporaryDirectory() as d:
      first={'event':'launch','session':'s1','time':'2026-10-21T23:59:00+00:00','user':'test'}
      end={**first,'event':'stop','time':'2026-10-22T00:01:00+00:00'}
      Path(d,'2026-10-21.log').write_text(json.dumps(first)+'\n'+json.dumps(first)+'\nBAD\n'+json.dumps({'event':'launch','time':0})+'\n')
      Path(d,'2026-10-22.log').write_text(json.dumps(end)+'\n')
      result=mod.load_events(d)
      self.assertEqual(len(result['events']),2); self.assertEqual(result['skipped'],2)
      self.assertEqual(result['events'][0]['event'],'launch')
      self.assertTrue(mod.load_events(d,1)['limited'])
 def test_sanitized_events(self):
    with tempfile.TemporaryDirectory() as d:
      Path(d,'2026-10-21.log').write_text(json.dumps({'event':'launch','time':'2026-10-21T00:00:00Z','access_token':'secret','plan':'free'})+'\n')
      e=mod.load_events(d)['events'][0]
      self.assertNotIn('access_token',e); self.assertEqual(e['plan'],'free')
 def test_plan_hook(self):
    um=types.ModuleType('app.user_manager')
    um.groups_of=lambda user:['warden_vip']
    um.get_effective_settings=lambda user:{}
    sys.modules['app.user_manager']=um
    captured=[];audit.record=lambda event,user='',**fields:captured.append(fields)
    mod.install_audit_hook();first=audit.record;mod.install_audit_hook()
    self.assertIs(first,audit.record)
    audit.record('launch','u');self.assertEqual(captured[-1]['plan'],'vip')
    um.groups_of=lambda user:[]
    audit.record('launch','u');self.assertEqual(captured[-1]['plan'],'unknown')
 def test_billing_readonly(self):
    import sqlite3
    with tempfile.TemporaryDirectory() as d:
      path=Path(d,'billing.sqlite3')
      self.assertNotIn('orders',mod.billing_summary(path))
      self.assertFalse(path.exists())
      c=sqlite3.connect(path)
      c.executescript("CREATE TABLE orders(id,username,plan,status,created,confirmed,is_test); CREATE TABLE billing_events(at,action); INSERT INTO orders VALUES('d','u','demo','pending',1,NULL,1);")
      c.commit();c.close()
      before=path.read_bytes();r=mod.billing_summary(path)
      self.assertEqual(r['orders'][0]['is_test'],1)
      self.assertIsNone(r['real_revenue']);self.assertEqual(path.read_bytes(),before)
 def test_quota_uses_sealskin_counters_and_omits_admin_and_secrets(self):
    um=types.ModuleType('app.user_manager')
    um.USER_DATA={'vip':{'username':'vip','private_key':'NEVER_RETURN'},'weekly':{'username':'weekly'},'free':{'username':'free'},'manager':{'is_admin':True}}
    um.get_effective_settings=lambda name:{'allowance_hours':10,'allowance_period':'week' if name=='weekly' else 'month','admin':name=='manager'}
    um.groups_of=lambda name:['warden_free'] if name=='free' else ['warden_vip']
    quota=types.ModuleType('app.quota'); quota.used_hours=lambda name,period:8.5 if period=='month' else 2
    saved_um=sys.modules.get('app.user_manager');saved_q=sys.modules.get('app.quota')
    sys.modules['app.user_manager']=um;sys.modules['app.quota']=quota
    pkg.user_manager=um;pkg.quota=quota
    try:
      result=mod.account_summary()
      self.assertEqual(result['admin_users'],['admin','manager'])
      users={u['user']:u for u in result['vip_quota']['users']}
      self.assertEqual(set(users),{'vip','weekly'})
      self.assertEqual(users['vip']['used_hours'],8.5)
      self.assertEqual(users['weekly']['used_hours'],2)
      self.assertEqual(users['weekly']['month_used_hours'],8.5)
      self.assertNotIn('NEVER_RETURN',json.dumps(result))
      response=client.get('/api/warden-analytics/data',headers={'x-test-role':'root'}).json()
      self.assertEqual(response['admin_users'],['admin','manager'])
    finally:
      if saved_um:sys.modules['app.user_manager']=saved_um
      else:sys.modules.pop('app.user_manager',None)
      if saved_q:sys.modules['app.quota']=saved_q
      else:sys.modules.pop('app.quota',None)
      for attr in ('user_manager','quota'):
        if hasattr(pkg,attr):delattr(pkg,attr)
 def test_no_store(self):
    r=client.get('/api/warden-analytics/data',headers={'x-test-role':'root'})
    self.assertEqual(r.headers['cache-control'],'no-store')
if __name__=='__main__': unittest.main()
