#!/usr/bin/env bash
set -euo pipefail
container="${1:-sealskin}"
action="${2:-install}"
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ "$action" != install && "$action" != rollback ]]; then echo 'Usage: sudo bash install.sh [container] [install|rollback]'; exit 1; fi
if [[ "$action" == rollback ]]; then
 docker exec -i "$container" python3 - <<'PY'
from pathlib import Path
import app
p=Path(app.__file__).parent/'api.py'
s=p.read_text(); start='# BEGIN WARDEN ANALYTICS'; end='# END WARDEN ANALYTICS'
if start in s:
 a=s.index(start); b=s.index(end,a)+len(end)
 p.write_text(s[:a]+s[b:])
print('Warden route removed; original routes preserved.')
PY
 docker restart "$container"
 exit 0
fi
# Inspect installed source without reading or printing any credentials.
appdir="$(docker exec "$container" python3 -c 'import app; from pathlib import Path; print(Path(app.__file__).parent)')"
docker exec -i "$container" python3 - <<'PY'
from pathlib import Path
import ast, app
p=Path(app.__file__).parent
api=(p/'api.py').read_text(); sec=(p/'security.py').read_text()
assert 'api_app = create_app()' in api, 'Unsupported api.py: no api_app = create_app(). No changes made.'
assert 'def verify_admin(' in sec and 'def _web_user(' in sec, 'Unsupported web authentication. No changes made.'
assert (p/'audit.py').is_file(), 'Audit module missing. No changes made.'
from app.settings import settings
assert hasattr(settings,'node_state_path'), 'node_state_path missing. No changes made.'
print('Preflight OK. Installed source supports web authentication and audit logs.')
PY
for f in warden_analytics.py warden_analytics.html warden_analytics.js; do
 test -s "$f"
 docker cp "$f" "$container:$appdir/$f"
done
docker exec "$container" python3 -c 'from app.warden_analytics import router; print("Dashboard module imports successfully.")'
docker exec -i "$container" python3 - <<'PY'
from pathlib import Path
import ast, datetime, app, os
p=Path(app.__file__).parent
f=p/'api.py'; original=f.read_text()
module=(p/'warden_analytics.py').read_text(); ast.parse(module)
marker='# BEGIN WARDEN ANALYTICS'
addition='\n# BEGIN WARDEN ANALYTICS\nfrom .warden_analytics import router as _warden_analytics_router, install_audit_hook as _warden_plan_hook\n_warden_plan_hook()\napi_app.include_router(_warden_analytics_router)\n# END WARDEN ANALYTICS\n'
if marker in original:
 end='# END WARDEN ANALYTICS'
 a=original.index(marker); b=original.index(end,a)+len(end)
 result=original[:a]+addition+original[b:]
 ast.parse(result)
 temp=f.with_suffix('.warden-tmp'); temp.write_text(result); os.replace(temp,f)
else:
 backup=Path('/config/warden-analytics/backups'); backup.mkdir(parents=True,exist_ok=True)
 dest=backup/('api-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.py')
 dest.write_text(original)
 result=original+addition; ast.parse(result)
 temp=f.with_suffix('.warden-tmp'); temp.write_text(result); os.replace(temp,f)
print('Warden Analytics installed. Backup retained under /config/warden-analytics/backups.')
PY
# Restart interrupts running sessions; run during a suitable maintenance window.
docker restart "$container"
echo 'Open your existing Sealskin origin + /api/warden-analytics after signing in as admin.'
echo 'On HTTP 500 or a startup failure: sudo bash install.sh sealskin rollback'
