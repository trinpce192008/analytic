"""Exercise authorization and storage with simulated SealSkin identities."""
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

import test_dashboard
from patch_sidebar import patch_index

BASE = "/api/warden-portal"
WRITE = {"sec-fetch-site": "same-origin", "x-warden-portal": "1"}


async def verify_token(x_test_role: str = Header(default="")):
    if not x_test_role:
        raise HTTPException(401)
    username = "admin" if x_test_role == "root" else x_test_role
    return {"username": username, "is_admin": x_test_role in ("root", "staff")}


test_dashboard.security.verify_token = verify_token
from app import warden_portal


class PortalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        override = patch.object(warden_portal, "DB_PATH", Path(temporary.name) / "portal.sqlite3")
        override.start()
        self.addCleanup(override.stop)
        app = FastAPI()
        app.include_router(warden_portal.router)

        @app.get("/api/warden-billing/me")
        def billing():
            return {}

        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def call(self, method, path, who=None, body=None, write=False):
        headers = dict(WRITE) if write else {}
        if who:
            headers["x-test-role"] = who
        return self.client.request(method, BASE + path, json=body, headers=headers)

    def test_dashboard_switch_blocks_direct_url_and_protects_other_users(self):
        nav = self.call("GET", "/nav", "alice").json()
        self.assertFalse(nav["user_dashboard"])
        self.assertTrue(nav["upgrade"])
        for path in ("/dashboard", "/dashboard/data"):
            self.assertEqual(self.call("GET", path, "alice").status_code, 403)
        update = {"user_dashboard": True}
        self.assertEqual(self.call("PUT", "/settings", "alice", update, True).status_code, 403)
        self.assertEqual(self.call("PUT", "/settings", "root", update).status_code, 403)
        self.assertEqual(self.call("PUT", "/settings", "root", update, True).status_code, 200)
        self.assertTrue(self.call("GET", "/nav", "alice").json()["user_dashboard"])
        now = dt.datetime.now(dt.timezone.utc)
        events = [
            {"user": who, "event": action, "session": who + "-private", "app": app,
             "time": (now - dt.timedelta(minutes=ago)).isoformat()}
            for who, app in (("alice", "Browser"), ("bob", "Private application"))
            for action, ago in (("launch", 10), ("stop", 5))
        ]
        with patch.object(warden_portal, "load_events", return_value={"events": events, "limited": False}):
            payload = self.call("GET", "/dashboard/data", "alice")
        self.assertEqual(payload.json()["apps"], [{"app": "Browser", "launches": 1, "minutes": 5.0}])
        self.assertNotIn("private", payload.text)
        self.assertEqual(self.call("PUT", "/settings", "root", {"user_dashboard": False}, True).status_code, 200)
        self.assertEqual(self.call("GET", "/dashboard/data", "alice").status_code, 403)
        self.assertTrue(self.call("GET", "/nav", "root").json()["admin_analytics"])

    def test_support_visibility_and_replies(self):
        self.assertEqual(self.call("GET", "/tickets").status_code, 401)
        body = {"subject": "Cần hỗ trợ", "message": "Nội dung", "owner": "bob"}
        self.assertEqual(self.call("POST", "/tickets", "alice", body).status_code, 403)
        created = self.call("POST", "/tickets", "alice", body, True)
        self.assertEqual(created.status_code, 201)
        url = "/tickets/" + str(created.json()["id"])
        self.assertEqual(self.call("GET", "/tickets", "bob").json()["tickets"], [])
        self.assertEqual(self.call("GET", url, "bob").status_code, 404)
        admin_list = self.call("GET", "/tickets", "staff").json()
        self.assertEqual(admin_list["tickets"][0]["owner"], "alice")
        self.assertEqual(self.call("POST", url + "/replies", "alice", {"message": "X"}, True).status_code, 403)
        self.assertEqual(self.call("POST", url + "/replies", "staff", {"message": "Đã kiểm tra"}, True).status_code, 201)
        self.assertEqual(self.call("GET", url, "alice").json()["replies"][0]["message"], "Đã kiểm tra")
        self.assertEqual(self.call("GET", "/tickets", "alice").json()["tickets"][0]["answered"], 1)

    def test_sidebar_install_is_idempotent_and_rollback_preserves_existing_code(self):
        original = ('<body><nav id="rail"><div class="rail-links"></div></nav>'
                    '<script src="warden-upgrade.js?v=1"></script>'
                    '<script defer src="/ui/warden-analytics-button.js"></script>'
                    '<script src="/ui/warden-server-visibility.js"></script></body>')
        updated = patch_index(original, "install")
        self.assertEqual(updated, patch_index(updated, "install"))
        self.assertEqual(updated.count("warden-sidebar.js"), 1)
        self.assertIn("WARDEN SUSPENDED SCRIPT", updated)
        self.assertEqual(patch_index(updated, "rollback"), original)
        with self.assertRaises(ValueError):
            patch_index("<body></body>", "install")


if __name__ == "__main__":
    unittest.main()
