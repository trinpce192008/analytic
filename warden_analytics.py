"""Warden node-local analytics. Read-only; uses SealSkin's own authentication."""
import datetime as dt
import json
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from .security import verify_admin
from .settings import settings
router = APIRouter(prefix='/api/warden-analytics')
BASE = Path(__file__).parent
async def root_only(user=Depends(verify_admin)):
    if user.get('username') != 'admin':
        raise HTTPException(403, 'Warden Analytics is restricted to the built-in admin.')
    return user
HEADERS = {'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin','Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"}
@router.get('', response_class=HTMLResponse)
async def page(user=Depends(root_only)):
    return HTMLResponse((BASE/'warden_analytics.html').read_text(), headers=HEADERS)
@router.get('/app.js')
async def script(user=Depends(root_only)):
    return Response((BASE/'warden_analytics.js').read_text(), media_type='text/javascript', headers=HEADERS)
def load_events(directory, max_bytes=32*1024*1024):
    events=[]; skipped=0; used=0; seen=set(); limited=False
    for path in sorted(Path(directory).glob('????-??-??.log'), reverse=True):
        with path.open(encoding='utf-8',errors='replace') as handle:
            for line in handle:
                used+=len(line.encode())
                if used>max_bytes:
                    limited=True; break
                try:
                    e=json.loads(line)
                    if not isinstance(e,dict) or not isinstance(e.get('event'),str): raise ValueError()
                    t=dt.datetime.fromisoformat(e['time'].replace('Z','+00:00'))
                    if t.tzinfo is None: raise ValueError()
                    key=json.dumps(e,sort_keys=True)
                    if key in seen: continue
                    seen.add(key); events.append({k:e[k] for k in ('time','event','user','session','app','admin','plan','plan_source') if k in e})
                except (ValueError,KeyError,TypeError,AttributeError): skipped+=1
        if limited: break
    return {'events':sorted(events,key=lambda e:e['time']), 'skipped':skipped,'limited':limited}
@router.get('/data')
async def data(user=Depends(root_only)):
    import asyncio
    result=await asyncio.to_thread(load_events,os.path.join(settings.node_state_path,'audit'))
    from . import audit
    result.update(billing=await asyncio.to_thread(billing_summary), plan_tracking=bool(getattr(audit.record, '_warden_plan_hook', False)), source='Sealskin · node hiện tại', fetched_at=dt.datetime.now(dt.timezone.utc).isoformat())
    return Response(json.dumps(result),media_type='application/json',headers=HEADERS)

# Capture the plan at launch; never infer historical membership from today's group.
def install_audit_hook():
    from . import audit, user_manager as um
    if getattr(audit.record, '_warden_plan_hook', False):
        return
    original = audit.record
    def record(event, user='', **fields):
        if event == 'launch':
            try:
                groups = set(um.groups_of(user))
                fields['plan'] = 'vip' if groups & {'warden_vip', 'VIP'} else 'free' if groups & {'warden_free', 'Free'} else 'unknown'
                fields['plan_source'] = 'group_at_launch'
                if um.get_effective_settings(user).get('admin'):
                    fields['admin'] = True
            except Exception:
                fields['plan'] = 'unknown'
        return original(event, user, **fields)
    record._warden_plan_hook = True
    audit.record = record

def billing_summary(path=None):
    """Read billing analytics without changing any orders or inferring real revenue."""
    import sqlite3
    path = Path(path or '/config/warden-billing/billing.sqlite3')
    if not path.is_file():
        return {'status': 'Chưa cài module thanh toán mô phỏng'}
    try:
        with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=2) as conn:
            conn.row_factory = sqlite3.Row
            orders = [dict(row) for row in conn.execute(
                'SELECT id,username,plan,status,created,confirmed,is_test FROM orders ORDER BY created')]
            events = [dict(row) for row in conn.execute(
                "SELECT at,action FROM billing_events WHERE action IN ('vip_activated','vip_expired','sync_failed') ORDER BY at")]
        return {'status':'Đã kết nối module thanh toán mô phỏng','orders':orders,
                'events':events,'real_revenue':None}
    except sqlite3.Error:
        return {'status':'Không đọc được nguồn thanh toán thử nghiệm'}
