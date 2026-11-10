"""Exercise owner login against a disposable local database with real Chromium.

Run: python -m scripts.verify_owner_ui --output /tmp/sunmao-owner-qa
The generated password, cookies and database never leave a TemporaryDirectory.
"""
from __future__ import annotations

import argparse
import secrets
import tempfile
import threading
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from sunmao_community.app import create_http_server
from sunmao_community.auth import create_password_hash


def verify(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sunmao-owner-ui-") as root:
        database = Path(root) / "community.sqlite3"
        password = secrets.token_urlsafe(24)
        encoded = create_password_hash(password)
        server = create_http_server(port=0, database_path=database, admin_password_hash=encoded)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_port
        origin = f"http://127.0.0.1:{port}"
        try:
            with sync_playwright() as p:
                errors = []
                profile = str(Path(root) / "browser-profile")
                context = p.chromium.launch_persistent_context(
                    profile, executable_path="/usr/bin/chromium", args=["--no-sandbox"],
                    viewport={"width": 1440, "height": 1000},
                )
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(origin + "/#exchange")
                page.wait_for_function("document.querySelector('#messageFeed').getAttribute('aria-busy') === 'false'")
                page.goto(origin + "/admin/")
                expect(page.locator("#remember")).to_be_checked()
                page.screenshot(path=str(output / "login-desktop.png"), full_page=True)
                page.locator("#password").fill(password)
                page.locator("#loginButton").click()
                expect(page.locator("#dashboardView")).to_be_visible()
                expect(page.locator("#visitorRows .owner-row")).to_have_count(1)
                expect(page.locator("#ownerName")).to_have_text("主理人")
                expect(page.locator("#loginRows")).to_contain_text("密码登录")
                auth_cookie = next(cookie for cookie in context.cookies() if cookie["name"] == "sunmao_admin_session")
                assert 29 * 86400 < auth_cookie["expires"] - time.time() <= 30 * 86400
                assert auth_cookie["httpOnly"] and auth_cookie["sameSite"] == "Strict"
                context.close()

                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
                server = create_http_server(port=port, database_path=database, admin_password_hash=encoded)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                restored = p.chromium.launch_persistent_context(
                    profile, executable_path="/usr/bin/chromium", args=["--no-sandbox"],
                    viewport={"width": 1440, "height": 1000},
                    extra_http_headers={"X-Forwarded-For": "198.51.100.15"},
                )
                browser = restored.browser
                assert browser is not None
                page = restored.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(origin + "/admin/")
                expect(page.locator("#dashboardView")).to_be_visible()
                expect(page.locator("#loginRows")).to_contain_text("自动登录")
                page.screenshot(path=str(output / "owner-dashboard-desktop.png"), full_page=True)

                phone = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True,
                                            user_agent="Mozilla/5.0 (iPhone; Mobile)",
                                            extra_http_headers={"X-Forwarded-For": "203.0.113.22"})
                mobile = phone.new_page()
                mobile.on("pageerror", lambda error: errors.append(str(error)))
                mobile.goto(origin + "/admin/")
                expect(mobile.locator("#loginView")).to_be_visible()
                mobile.locator("#password").fill(password)
                mobile.locator("#loginButton").click()
                expect(mobile.locator("#dashboardView")).to_be_visible()
                mobile.goto(origin + "/#exchange")
                mobile.wait_for_function("document.querySelector('#messageFeed').getAttribute('aria-busy') === 'false'")
                mobile.goto(origin + "/admin/")
                expect(mobile.locator("#visitorRows .owner-row")).to_have_count(1)
                mobile.screenshot(path=str(output / "owner-dashboard-mobile.png"), full_page=True)
                mobile.locator("#excludeOwner").check()
                expect(mobile.locator("#visitorRows .owner-row")).to_have_count(0)
                expect(mobile.locator("#todayVisitors")).to_have_text("0")
                assert mobile.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                mobile.set_viewport_size({"width": 360, "height": 800})
                assert mobile.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                mobile.screenshot(path=str(output / "owner-filter-mobile-360.png"), full_page=True)
                mobile.locator("#logoutButton").click()
                expect(mobile.locator("#loginView")).to_be_visible()
                mobile.reload()
                expect(mobile.locator("#loginView")).to_be_visible()
                page.reload()
                expect(page.locator("#dashboardView")).to_be_visible()
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
    print("PASS: remembered login, restart, network change, two owner devices, filter, logout, 390/360px, no JS errors")
    print(f"Screenshots: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("/tmp/sunmao-owner-qa"))
    verify(parser.parse_args().output)
