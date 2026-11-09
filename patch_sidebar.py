"""Apply or remove Warden's sidebar integration in SealSkin's local UI."""
import os
import re
import sys
import tempfile
from pathlib import Path

START = "<!-- BEGIN WARDEN SIDEBAR -->"
END = "<!-- END WARDEN SIDEBAR -->"
BLOCK = (
    START + '\n<link rel="stylesheet" href="/ui/warden-sidebar.css?v=1">'
    '\n<script src="/ui/warden-sidebar.js?v=2" defer></script>\n' + END + '\n'
)
MANAGED = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.S)
LEGACY = re.compile(
    r"""<script\b[^>]*\bsrc\s*=\s*["'](?:/ui/|\./)?warden-(?:upgrade|analytics-button)\.js(?:\?[^"'<>]*)?["'][^>]*>\s*</script\s*>""",
    re.I,
)
SUSPENDED = re.compile(r"<!-- WARDEN SUSPENDED SCRIPT\n(.*?)\n-->", re.S)


def patch_index(html, action):
    if action == "rollback":
        return SUSPENDED.sub(lambda match: match[1], MANAGED.sub("", html))
    if not re.search(r'''\bid=["']rail["']''', html) or not re.search(
        r'''\bclass=["'][^"']*\brail-links\b''', html
    ):
        raise ValueError("Unsupported SealSkin sidebar: #rail .rail-links missing.")
    if html.lower().count("</body>") != 1:
        raise ValueError("Unsupported SealSkin index.html: expected a single closing body tag.")
    # Restore first so a second install produces identical markup.
    html = patch_index(html, "rollback")
    html = LEGACY.sub(lambda match: "<!-- WARDEN SUSPENDED SCRIPT\n" + match[0] + "\n-->", html)
    return re.sub(r"</body>", lambda _: BLOCK + "</body>", html, count=1, flags=re.I)


def main(action):
    from app.settings import settings

    path = Path(settings.ui_path) / "index.html"
    original = path.read_text()
    updated = patch_index(original, action)
    if action == "check" or original == updated:
        return
    mode = path.stat().st_mode & 0o777
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temp:
        name = Path(temp.name)
        try:
            temp.write(updated)
            temp.flush()
            name.chmod(mode)
            os.replace(name, path)
        finally:
            name.unlink(missing_ok=True)


if __name__ == "__main__":
    main(sys.argv[1])
