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
if [[ "$action" != install && "$action" != restore-ui ]]; then
 echo 'Usage: install.sh [container] [install|restore-ui|rollback]' >&2
 exit 1
fi
appdir="$(docker exec "$container" python3 -c 'import app; from pathlib import Path; print(Path(app.__file__).parent)')"
docker exec -i "$container" python3 - <<'PY'
import app,inspect
from pathlib import Path
import yaml
from app import user_manager as u
from app.security import verify_token
from app.routers import admin
from app.settings import settings
s=(Path(app.__file__).parent/'api.py').read_text()
assert 'api_app = create_app()' in s,'Unsupported api.py'
assert 'req.settings.model_dump()' in inspect.getsource(admin.update_user),'Unsupported user update'
assert hasattr(u,'groups_of') and hasattr(u,'get_effective_settings'),'Unsupported groups API'
# The running API populates GROUP_DATA at startup. This separate Python
# process checks the persisted definitions without initializing the API.
groups_dir = Path(settings.groups_base_path)
for name in ('warden_free', 'warden_vip'):
 group_file = groups_dir / name
 assert group_file.is_file(), 'Create group ' + name + ' in Sealskin before installation'
 group_settings = yaml.safe_load(group_file.read_text(encoding='utf-8'))
 assert isinstance(group_settings, dict), 'Invalid settings for group ' + name
 assert not group_settings.get('admin'), 'Disable Administrator on ' + name
print('Preflight OK')
PY
for f in warden_billing.html warden_billing.js warden_billing.py warden_admin_subscriptions.js; do
 test -s "$f"
done
if [[ "$action" == restore-ui ]]; then
 docker exec -i -u 0 "$container" python3 - <<'PY'
from pathlib import Path
import app, shutil, time

appdir = Path(app.__file__).parent
backup = Path('/config/warden-billing/backups') / f'restore-ui-{time.time_ns()}'
backup.mkdir(parents=True, mode=0o700)
for name in ('warden_billing.html', 'warden_billing.js'):
    path = appdir / name
    if path.is_file():
        shutil.copy2(path, backup / name)
print(f'Payment UI backup: {backup}')
PY
fi
for f in warden_billing.html warden_billing.js; do
 if [[ "$action" == restore-ui ]] || ! docker exec "$container" test -e "$appdir/$f"; then
  docker cp "$f" "$container:$appdir/$f"
 fi
done
for f in warden_billing.py warden_admin_subscriptions.js; do
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
