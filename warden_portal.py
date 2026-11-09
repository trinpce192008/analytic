"""Warden sidebar capabilities, shared analytics access and support inbox."""
import datetime as dt
import os
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field, StrictBool

from .security import verify_token
from .warden_analytics import HEADERS, analytics_access, can_manage_analytics, root_only

PREFIX = "/api/warden-portal"
router = APIRouter(prefix=PREFIX)
BASE = Path(__file__).parent
DB_PATH = Path("/config/warden-analytics/portal.sqlite3")


@contextmanager
def database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.close(os.open(DB_PATH, os.O_CREAT | os.O_RDWR, 0o600))
    with closing(sqlite3.connect(DB_PATH, timeout=5)) as db:
        db.row_factory = sqlite3.Row
        db.executescript("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY, value INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY, owner TEXT NOT NULL,
                subject TEXT NOT NULL, message TEXT NOT NULL, created TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ticket_owner ON tickets(owner, id);
            CREATE TABLE IF NOT EXISTS replies (
                id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL REFERENCES tickets(id),
                author TEXT NOT NULL, message TEXT NOT NULL, created TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS reply_ticket ON replies(ticket_id, id);
        """)
        with db:
            yield db


def shared_analytics_enabled():
    with database() as db:
        setting = db.execute(
            "SELECT value FROM preferences WHERE key = 'shared_analytics'"
        ).fetchone()
        return bool(setting and setting["value"] == 1)


def response(data, status=200):
    return JSONResponse(data, status_code=status, headers=HEADERS)


def write_guard(request: Request):
    if (
        request.headers.get("sec-fetch-site") != "same-origin"
        or request.headers.get("x-warden-portal") != "1"
    ):
        raise HTTPException(403, "Chỉ chấp nhận thao tác từ giao diện Warden.")


class Preferences(BaseModel):
    shared_analytics: StrictBool


class TicketInput(BaseModel):
    subject: str = Field(max_length=120)
    message: str = Field(max_length=4000)


class ReplyInput(BaseModel):
    message: str = Field(max_length=4000)


def required_text(value):
    clean = value.strip()
    if not clean:
        raise HTTPException(422, "Vui lòng nhập nội dung.")
    return clean


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


@router.get("/nav")
def navigation(request: Request, user=Depends(verify_token)):
    return response({
        "analytics": can_manage_analytics(user) or shared_analytics_enabled(),
        "upgrade": any(
            getattr(route, "path", None) == "/api/warden-billing/me"
            for route in request.app.routes
        ),
    })


@router.get("/settings")
def read_preferences(user=Depends(root_only)):
    return response({"shared_analytics": shared_analytics_enabled()})


@router.put("/settings", dependencies=[Depends(write_guard)])
def update_preferences(body: Preferences, user=Depends(root_only)):
    with database() as db:
        db.execute(
            "INSERT INTO preferences VALUES ('shared_analytics', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (int(body.shared_analytics),),
        )
    return response({"shared_analytics": body.shared_analytics})


@router.get("/support", response_class=HTMLResponse)
def support(user=Depends(verify_token)):
    return HTMLResponse((BASE / "warden_support.html").read_text(), headers=HEADERS)


@router.get("/app.js")
def javascript():
    return Response(
        (BASE / "warden_portal.js").read_text(),
        media_type="text/javascript",
        headers=HEADERS,
    )


@router.get("/tickets")
def tickets(offset: int = Query(0, ge=0), user=Depends(verify_token)):
    admin = bool(user.get("is_admin"))
    where, args = ("", ()) if admin else ("WHERE t.owner = ?", (user["username"],))
    with database() as db:
        rows = db.execute(
            "SELECT t.id, t.owner, t.subject, t.created, "
            "EXISTS(SELECT 1 FROM replies WHERE ticket_id = t.id) AS answered "
            f"FROM tickets t {where} ORDER BY t.id DESC LIMIT 51 OFFSET ?",
            (*args, offset),
        ).fetchall()
    return response({
        "admin": admin,
        "tickets": [dict(row) for row in rows[:50]],
        "more": len(rows) > 50,
    })


@router.post("/tickets", dependencies=[Depends(write_guard)])
def create_ticket(body: TicketInput, user=Depends(verify_token)):
    subject, message = required_text(body.subject), required_text(body.message)
    with database() as db:
        ticket = db.execute(
            "INSERT INTO tickets(owner, subject, message, created) VALUES (?, ?, ?, ?)",
            (user["username"], subject, message, timestamp()),
        )
        ticket_id = ticket.lastrowid
    return response({"id": ticket_id}, status=201)


@router.get("/tickets/{ticket_id}")
def ticket_detail(ticket_id: int, user=Depends(verify_token)):
    admin = bool(user.get("is_admin"))
    with database() as db:
        ticket = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if not ticket or (not admin and ticket["owner"] != user["username"]):
            raise HTTPException(404, "Không tìm thấy yêu cầu hỗ trợ.")
        replies = db.execute(
            "SELECT author, message, created FROM replies WHERE ticket_id = ? ORDER BY id",
            (ticket_id,),
        ).fetchall()
    return response({"ticket": dict(ticket), "replies": [dict(row) for row in replies]})


@router.post("/tickets/{ticket_id}/replies", dependencies=[Depends(write_guard)])
def reply(ticket_id: int, body: ReplyInput, user=Depends(verify_token)):
    if not user.get("is_admin"):
        raise HTTPException(403, "Chỉ quản trị viên được phản hồi yêu cầu.")
    message = required_text(body.message)
    with database() as db:
        if not db.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone():
            raise HTTPException(404, "Không tìm thấy yêu cầu hỗ trợ.")
        db.execute(
            "INSERT INTO replies(ticket_id, author, message, created) VALUES (?, ?, ?, ?)",
            (ticket_id, user["username"], message, timestamp()),
        )
    return response({"saved": True}, status=201)


@router.get("/dashboard")
def dashboard_redirect(user=Depends(analytics_access)):
    return RedirectResponse("/api/warden-analytics", headers=HEADERS)
