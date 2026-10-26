#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
container="${1:-sealskin}"
action="${2:-install}"
if [[ "$action" == rollback ]]; then
 docker exec -i "$container" python3 - <<'PY'
import app
from pathlib import Path
p=Path(app.__file__).parent/'api.py';s=p.read_text();a='# BEGIN WARDEN BILLING';b='# END WARDEN BILLING'
if a in s:s=s[:s.index(a)]+s[s.index(b)+len(b):];p.write_text(s)
print('Billing removed. Database retained; existing VIP rights must be reviewed manually.')
PY
 docker restart "$container"
 exit 0
fi
[[ "$action" == install ]] || exit 1
appdir="$(docker exec "$container" python3 -c 'import app; from pathlib import Path; print(Path(app.__file__).parent)')"
docker exec -i "$container" python3 - <<'PY'
import app,inspect
from pathlib import Path
from app import user_manager as u
from app.security import verify_token
from app.routers import admin
s=(Path(app.__file__).parent/'api.py').read_text()
assert 'api_app = create_app()' in s,'Unsupported api.py'
assert 'req.settings.model_dump()' in inspect.getsource(admin.update_user),'Unsupported user update'
assert hasattr(u,'groups_of') and hasattr(u,'get_effective_settings'),'Unsupported groups API'
for n in ('warden_free','warden_vip'):
 g=u.GROUP_DATA.get(n)
 assert g is not None, 'Create group '+n+' in Sealskin before installation'
 assert not g.get('settings',{}).get('admin'), 'Disable Administrator on '+n
print('Preflight OK')
PY
for f in warden_billing.py warden_billing.html warden_billing.js; do
 test -s "$f"
 docker cp "$f" "$container:$appdir/$f"
done
docker exec "$container" python3 -c 'from app.warden_billing import router; print("Billing module imports OK")'
docker exec -i "$container" python3 - <<'PY'
import app,ast,datetime,os
from pathlib import Path
p=Path(app.__file__).parent/'api.py';s=p.read_text()
marker='# BEGIN WARDEN BILLING'
if marker not in s:
 root=Path('/config/warden-billing/backups');root.mkdir(parents=True,exist_ok=True,mode=0o700)
 (root/('api-'+datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')+'.py')).write_text(s)
 s+='\n# BEGIN WARDEN BILLING\nfrom .warden_billing import install as _install_warden_billing\n_install_warden_billing(api_app)\n# END WARDEN BILLING\n'
 ast.parse(s);tmp=p.with_suffix('.billing-tmp');tmp.write_text(s);os.replace(tmp,p)
print('Installed. Restarting SealSkin.')
PY
docker restart "$container"
echo 'Open existing SealSkin origin + /api/warden-billing after sign-in.'
