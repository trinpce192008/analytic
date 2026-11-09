"""Exercise authorization and storage with simulated SealSkin identities."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from test_dashboard import mod, warden_portal
from patch_sidebar import patch_index

BASE = "/api/warden-portal"
WRITE = {"sec-fetch-site": "same-origin", "x-warden-portal": "1"}


class PortalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        override = patch.object(warden_portal, "DB_PATH", Path(temporary.name) / "portal.sqlite3")
        override.start()
        self.addCleanup(override.stop)
        app = FastAPI()
        app.include_router(warden_portal.router)
        app.include_router(mod.router)

        billing_router = APIRouter(prefix="/api/warden-billing")

        @billing_router.get("/me")
        def billing():
            return {}

        app.include_router(billing_router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def call(self, method, path, who=None, body=None, write=False):
        headers = dict(WRITE) if write else {}
        if who:
            headers["x-test-role"] = who
        return self.client.request(method, BASE + path, json=body, headers=headers)

    def test_upgrade_navigation_follows_installed_billing_route(self):
        for role in ("root", "lecturer"):
            self.assertTrue(self.call("GET", "/nav", role).json()["upgrade"])

        app = FastAPI()
        app.include_router(warden_portal.router)
        with TestClient(app) as client:
            nav = client.get(BASE + "/nav", headers={"x-test-role": "root"})
            self.assertEqual(nav.status_code, 200)
            self.assertFalse(nav.json()["upgrade"])

    def test_shared_dashboard_is_read_only_and_revocable(self):
        root = {"x-test-role": "root"}
        viewer = {"x-test-role": "lecturer"}
        paths = ("/api/warden-analytics", "/api/warden-analytics/app.js",
                 "/api/warden-analytics/data", BASE + "/dashboard")
        # An enabled personal dashboard from v0.10.0 must never grant shared access.
        with warden_portal.database() as db:
            db.execute("INSERT INTO preferences VALUES ('user_dashboard', 1)")
        nav = self.call("GET", "/nav", "lecturer").json()
        self.assertFalse(nav["analytics"])
        for path in paths:
            self.assertEqual(self.client.get(path, headers=viewer).status_code, 403)
        update = {"shared_analytics": True}
        self.assertEqual(self.call("GET", "/settings", "lecturer").status_code, 403)
        self.assertEqual(self.call("PUT", "/settings", "lecturer", update, True).status_code, 403)
        self.assertEqual(self.call("PUT", "/settings", "root", update).status_code, 403)
        self.assertEqual(self.call("PUT", "/settings", "root", update, True).status_code, 200)
        self.assertTrue(self.call("GET", "/nav", "lecturer").json()["analytics"])
        for path in paths:
            self.assertEqual(self.client.get(path, headers=viewer).status_code, 200)
            self.assertEqual(self.client.get(path).status_code, 401)
        self.assertIn('id="dashboard-settings"', self.client.get(paths[0], headers=root).text)
        self.assertNotIn('id="dashboard-settings"', self.client.get(paths[0], headers=viewer).text)
        events = {"events": [{"user": "student", "event": "launch"}], "limited": False}
        with patch.object(mod, "load_events", return_value=events):
            viewer_data = self.client.get(paths[2], headers=viewer)
            admin_data = self.client.get(paths[2], headers=root)
        self.assertEqual(viewer_data.json()["events"], admin_data.json()["events"])
        self.assertEqual(viewer_data.json()["events"][0]["user"], "student")
        self.assertEqual(viewer_data.headers["cache-control"], "no-store")
        self.assertEqual(self.call("PUT", "/settings", "root", {"shared_analytics": False}, True).status_code, 200)
        self.assertFalse(self.call("GET", "/nav", "lecturer").json()["analytics"])
        for path in paths:
            self.assertEqual(self.client.get(path, headers=viewer).status_code, 403)
            self.assertEqual(self.client.get(path, headers=root).status_code, 200)

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
