"""Single-node, simulated billing for SealSkin. No bank or payment provider."""
import asyncio, contextlib, json, logging, os, sqlite3, time, uuid
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from . import user_manager as um
from .security import verify_token
from .settings import settings
log=logging.getLogger(__name__)
BASE=Path(__file__).parent
ROOT=Path('/config/warden-billing')
FREE='warden_free'; VIP='warden_vip'
PLANS={'demo_5m':{'label':'VIP thử nghiệm · 5 phút','seconds':300,'amount':0},'vip_30d':{'label':'VIP thử nghiệm · 30 ngày','seconds':2592000,'amount':49000}}
router=APIRouter(prefix='/api/warden-billing')
HEAD={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"}
def db():
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    c=sqlite3.connect(ROOT/'billing.sqlite3',timeout=10);c.row_factory=sqlite3.Row
    os.chmod(ROOT/'billing.sqlite3',0o600)
    c.executescript('''CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,username TEXT NOT NULL,plan TEXT NOT NULL,status TEXT NOT NULL,created REAL NOT NULL,confirmed REAL,confirmed_by TEXT,is_test INTEGER NOT NULL DEFAULT 1); CREATE TABLE IF NOT EXISTS subscriptions(username TEXT PRIMARY KEY,expires REAL NOT NULL,state TEXT NOT NULL,error TEXT NOT NULL DEFAULT ''); CREATE TABLE IF NOT EXISTS billing_events(id INTEGER PRIMARY KEY,at REAL,username TEXT,action TEXT,order_id TEXT,detail TEXT);''')
    return c
@contextlib.contextmanager
def connection():
    c=db()
    try:
        with c: yield c
    finally: c.close()
def event(c,user,action,oid='',detail=''):
    c.execute('INSERT INTO billing_events(at,username,action,order_id,detail) VALUES(?,?,?,?,?)',(time.time(),user,action,oid,detail))
def ensure_groups():
    for name in (FREE,VIP):
        g=um.GROUP_DATA.get(name)
        if not g: raise ValueError('Chưa tạo nhóm '+name+' trong Sealskin.')
        if g.get('settings',{}).get('admin'): raise ValueError('Nhóm '+name+' đang có quyền Administrator; hãy tắt quyền này.')
def account(name):
    u=um.get_user(name)
    if not u: raise ValueError('Tài khoản không còn tồn tại.')
    if u.get('is_admin') or um.get_effective_settings(name).get('admin'): raise ValueError('Không nâng cấp hoặc đổi nhóm tài khoản quản trị.')
    if (u.get('settings') or {}).get('approved') is False: raise ValueError('Tài khoản đang chờ phê duyệt trong Sealskin.')
    return u
async def signed(user=Depends(verify_token)):
    return user
async def root(user=Depends(signed)):
    if user.get('username')!='admin' or not user.get('is_admin'): raise HTTPException(403,'Chỉ admin tích hợp được quản lý thanh toán thử nghiệm.')
    return user
async def write_guard(req:Request,user=Depends(signed)):
    if req.headers.get('X-Warden-Billing')!='1': raise HTTPException(403,'Thiếu header xác nhận nguồn yêu cầu.')
    if req.headers.get('Sec-Fetch-Site')!='same-origin': raise HTTPException(403,'Chỉ chấp nhận thao tác từ trang cùng origin.')
    return user
def change_group(name,target):
    ensure_groups();u=account(name);s=dict(u.get('settings') or {})
    groups=list(s.get('groups') or ([s['group']] if s.get('group') and s['group']!='default' else []))
    desired=[g for g in groups if g not in (FREE,VIP)]+[target]
    # Refuse provider-assigned plan groups: their membership cannot be removed locally.
    provider=set(um.groups_of(name))-set(groups)
    if provider & {FREE,VIP}: raise ValueError('Nhóm gói được gán bởi IdP; cần bỏ mapping Free/VIP trong IdP trước.')
    if groups==desired: return
    s.update(groups=desired,group=desired[0])
    um.update_user_settings(name,s)
    actual=(um.get_user(name).get('settings') or {}).get('groups',[])
    if set(actual)!=set(desired): raise ValueError('Đọc lại nhóm không khớp; chờ thử lại.')
def reconcile():
    now=time.time()
    with connection() as c:
        subscriptions=c.execute('SELECT * FROM subscriptions').fetchall()
        for s in subscriptions:
            target=VIP if s['expires']>now else FREE
            state='active' if target==VIP else 'expired'
            try:
                change_group(s['username'],target)
                if s['state']!=state:
                    event(c,s['username'],'vip_activated' if target==VIP else 'vip_expired')
                c.execute('UPDATE subscriptions SET state=?,error=? WHERE username=?',(state,'',s['username']))
            except Exception as exc:
                message=str(exc)[:300]
                if message!=s['error']: event(c,s['username'],'sync_failed',detail=message)
                c.execute('UPDATE subscriptions SET state=?,error=? WHERE username=?',('pending_grant' if target==VIP else 'pending_revoke',message,s['username']))
async def worker():
    while True:
        try: reconcile()
        except Exception: log.exception('Warden billing reconciliation failed')
        await asyncio.sleep(15)
def install(app):
    """Preserve SealSkin's original lifespan and run an independent expiry worker."""
    original=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(a):
        async with original(a):
            with connection(): pass
            task=asyncio.create_task(worker())
            try: yield
            finally:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError): await task
    app.router.lifespan_context=lifespan
    app.include_router(router)
@router.get('',response_class=HTMLResponse)
async def page():
    return HTMLResponse((BASE/'warden_billing.html').read_text(),headers=HEAD)
@router.get('/app.js')
async def js():
    return Response((BASE/'warden_billing.js').read_text(),media_type='text/javascript',headers=HEAD)
@router.get('/me')
async def me(user=Depends(signed)):
    name=user['username']
    with connection() as c:
        sub=c.execute('SELECT * FROM subscriptions WHERE username=?',(name,)).fetchone()
        orders=c.execute('SELECT * FROM orders WHERE username=? ORDER BY created DESC LIMIT 50',(name,)).fetchall()
    return {'username':name,'admin':name=='admin' and bool(user.get('is_admin')),'plans':PLANS,'subscription':dict(sub) if sub else None,'orders':[dict(o) for o in orders],'is_test':True}
@router.post('/orders')
async def create(req:Request,user=Depends(write_guard)):
    try:
        body=await req.json();p=body.get('plan');ensure_groups();account(user['username'])
        if p not in PLANS: raise ValueError('Gói không hợp lệ.')
        with connection() as c:
            c.execute('BEGIN IMMEDIATE')
            existing=c.execute("SELECT id FROM orders WHERE username=? AND status='pending'",(user['username'],)).fetchone()
            if existing:return {'id':existing['id'],'existing':True}
            oid='DEMO-'+uuid.uuid4().hex[:16].upper()
            c.execute('INSERT INTO orders(id,username,plan,status,created) VALUES(?,?,?,?,?)',(oid,user['username'],p,'pending',time.time()))
            event(c,user['username'],'order_created',oid)
        return {'id':oid}
    except (ValueError,AttributeError) as e: raise HTTPException(400,str(e))
@router.get('/admin')
async def admin_data(user=Depends(root)):
    with connection() as c:
        orders=[dict(o) for o in c.execute('SELECT * FROM orders ORDER BY created DESC LIMIT 200')]
        subs=[dict(s) for s in c.execute('SELECT * FROM subscriptions')]
        logs=[dict(e) for e in c.execute('SELECT * FROM billing_events ORDER BY id DESC LIMIT 100')]
        count=c.execute("SELECT COUNT(*) FROM orders WHERE status='confirmed'").fetchone()[0]
    return {'orders':orders,'subscriptions':subs,'events':logs,'confirmed_test_orders':count,'real_revenue':None}
@router.post('/admin/orders/{oid}/confirm')
async def confirm(oid:str,user=Depends(root),guard=Depends(write_guard)):
    try:
        ensure_groups()
        with connection() as c:
            c.execute('BEGIN IMMEDIATE')
            o=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
            if not o:raise HTTPException(404,'Không tìm thấy đơn.')
            if o['status']=='confirmed':return {'status':'already_confirmed'}
            if o['status']!='pending':raise HTTPException(409,'Đơn không ở trạng thái chờ.')
            account(o['username']);old=c.execute('SELECT expires FROM subscriptions WHERE username=?',(o['username'],)).fetchone()
            expiry=max(time.time(),old['expires'] if old else 0)+PLANS[o['plan']]['seconds']
            c.execute("UPDATE orders SET status='confirmed',confirmed=?,confirmed_by=? WHERE id=?",(time.time(),user['username'],oid))
            c.execute("INSERT INTO subscriptions(username,expires,state) VALUES(?,?,'pending_grant') ON CONFLICT(username) DO UPDATE SET expires=excluded.expires,state='pending_grant',error=''",(o['username'],expiry))
            event(c,o['username'],'test_payment_confirmed',oid)
        reconcile()
        return {'status':'confirmed','expires':expiry}
    except ValueError as e:raise HTTPException(400,str(e))
