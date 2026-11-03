"""Real browser/FastAPI/PostgreSQL checks in a disposable test-database schema.

Run with the backend Python environment after installing Playwright separately:
  backend/.venv/bin/python -m pip install playwright==1.64.1
  backend/.venv/bin/python -m playwright install chromium
  backend/.venv/bin/python scripts/test-frontend-integration.py

TEST_DATABASE_URL is read from the environment or the ignored root .env. The
runner never migrates, seeds, or deletes tables in the application schema.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from splitbill.seed import seed_database
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def free_port(port: int) -> None:
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", port))


def wait_for_server(url: str, process: subprocess.Popen, timeout: int = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("A test server exited before becoming ready")
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except (URLError, TimeoutError):
            time.sleep(0.2)
            continue
        time.sleep(0.2)
    raise RuntimeError("A test server did not become ready before the timeout")


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


async def browser_checks(
    api_url: str, web_url: str, engine, screenshot_dir: Path
) -> None:
    from playwright.async_api import Error as PlaywrightError
    from playwright.async_api import async_playwright, expect

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        context = await browser.new_context(viewport={"width": 1440, "height": 1000})
        page = await context.new_page()
        console_errors: list[str] = []
        page.on("pageerror", lambda error: console_errors.append(str(error)))
        api_requests: list = []
        page.on(
            "request",
            lambda request: (
                api_requests.append(request)
                if request.url.startswith(api_url)
                else None
            ),
        )
        try:
            await page.goto(web_url)
            entry = page.get_by_role("heading", name="คุณคือใคร?", exact=True)
            exit_profile = page.get_by_role("button", name="เปลี่ยนผู้ใช้", exact=True)
            group = page.get_by_label("กลุ่ม", exact=True)
            form = page.get_by_test_id("expense-form")
            ledger = page.get_by_role("region", name="ยอดสุทธิของสมาชิก", exact=True)
            rows = page.get_by_test_id("expense-row")

            async def choose_user(name: str) -> None:
                await expect(entry).to_be_visible()
                await page.get_by_role("button", name=name, exact=True).click()
                await expect(
                    page.get_by_role("banner").get_by_text(name, exact=True)
                ).to_be_visible()

            async def leave_profile() -> None:
                await exit_profile.click()
                discard = page.get_by_role(
                    "button", name="ทิ้งร่างและเปลี่ยนผู้ใช้", exact=True
                )
                await expect(entry.or_(discard)).to_be_visible()
                if await discard.is_visible():
                    await discard.click()
                await expect(entry).to_be_visible()
                await expect(entry).to_be_focused()
                await expect(form).to_have_count(0)
                await expect(group).to_have_count(0)

            async def switch_user(name: str, group_id: str) -> None:
                if await exit_profile.is_visible():
                    await leave_profile()
                await choose_user(name)
                await expect(group).to_have_value(group_id)
                await expect(form).to_be_visible()
                await expect(ledger).to_be_visible()

            async def fill_expense(
                description: str, amount: str, payer: str = "alice"
            ) -> None:
                await form.get_by_label("รายละเอียด", exact=True).fill(description)
                await form.get_by_label("จำนวนเงิน (บาท)", exact=True).fill(amount)
                await form.get_by_label("จ่ายโดย", exact=False).select_option(payer)

            async def save() -> None:
                async with page.expect_response(
                    lambda response: (
                        response.request.method == "POST"
                        and response.url.endswith("/expenses")
                    )
                ) as response_info:
                    await form.get_by_role(
                        "button", name="บันทึกค่าใช้จ่าย", exact=True
                    ).click()
                response = await response_info.value
                assert response.status in (200, 201), "Expense POST did not succeed"

            def sql_count(description: str) -> int:
                with engine.connect() as connection:
                    return connection.execute(
                        text(
                            "SELECT count(*) FROM expenses WHERE description = :description"
                        ),
                        {"description": description},
                    ).scalar_one()

            await expect(entry).to_be_visible()
            await expect(group).to_have_count(0)
            for name in ("alice", "bob", "carol", "dan"):
                await expect(
                    page.get_by_role("button", name=name, exact=True)
                ).to_be_visible()
            await page.evaluate(
                "new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
            )
            assert not api_requests, "The entry view selected a user or read API data"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            for width, height, name in [(1440, 1000, "desktop"), (390, 844, "mobile")]:
                await page.set_viewport_size({"width": width, "height": height})
                await page.evaluate("document.fonts.ready")
                await page.locator(".brand-mark").evaluate("image => image.decode()")
                assert await page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth"
                ), f"Entry view horizontal overflow at {width}px"
                await page.screenshot(
                    path=str(screenshot_dir / f"frontend-entry-{name}.png"),
                    full_page=True,
                )
            for width in (375, 768, 1024):
                await page.set_viewport_size({"width": width, "height": 1024})
                assert await page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth"
                ), f"Entry view horizontal overflow at {width}px"
            await page.set_viewport_size({"width": 1440, "height": 1000})
            carol_profile = page.get_by_role("button", name="carol", exact=True)
            await carol_profile.focus()
            await carol_profile.press("Enter")
            await expect(group).to_have_value("1")
            await expect(ledger).to_contain_text("carol")
            await expect(group.locator('option[value="2"]')).to_have_count(0)
            await page.reload()
            await expect(ledger).to_contain_text("carol")
            await expect(
                page.get_by_role("banner").get_by_text("carol", exact=True)
            ).to_be_visible()
            assert (
                await page.evaluate("sessionStorage.getItem('splitbill.user.v1')")
                == "carol"
            ), "Reload did not retain the selected tab profile"
            other_tab = await context.new_page()
            try:
                await other_tab.goto(web_url)
                await expect(
                    other_tab.get_by_role("heading", name="คุณคือใคร?", exact=True)
                ).to_be_visible()
            finally:
                await other_tab.close()
            await leave_profile()
            assert (
                await page.evaluate("sessionStorage.getItem('splitbill.user.v1')")
                is None
            ), "Profile exit retained the selected user"
            print(
                "PASS entry chooser, no preselection/API reads, keyboard, tab-local reload and exit focus"
            )

            await switch_user("alice", "1")
            await fill_expense("ร่างที่ยังไม่บันทึก", "100.00", "bob")
            await form.get_by_role("radio", name="กำหนดจำนวนเอง", exact=True).check()
            for member, share in [
                ("alice", "10.00"),
                ("bob", "20.00"),
                ("carol", "70.00"),
            ]:
                await form.get_by_label(f"จำนวนของ {member}", exact=False).fill(share)
            await exit_profile.click()
            back_to_draft = page.get_by_role("button", name="กลับไปแก้บิล", exact=True)
            await expect(back_to_draft).to_be_focused()
            await back_to_draft.press("Enter")
            await expect(exit_profile).to_be_focused()
            await expect(form.get_by_label("รายละเอียด", exact=True)).to_have_value(
                "ร่างที่ยังไม่บันทึก"
            )
            await expect(form.get_by_label("จำนวนเงิน (บาท)", exact=True)).to_have_value(
                "100.00"
            )
            await expect(form.get_by_label("จ่ายโดย", exact=False)).to_have_value("bob")
            await expect(
                form.get_by_role("radio", name="กำหนดจำนวนเอง", exact=True)
            ).to_be_checked()
            for member, share in [
                ("alice", "10.00"),
                ("bob", "20.00"),
                ("carol", "70.00"),
            ]:
                await expect(
                    form.get_by_label(f"จำนวนของ {member}", exact=False)
                ).to_have_value(share)
            assert sql_count("ร่างที่ยังไม่บันทึก") == 0
            await leave_profile()
            await expect(form).to_have_count(0)
            await switch_user("alice", "1")
            await expect(form.get_by_label("รายละเอียด", exact=True)).to_have_value("")
            await expect(form.get_by_label("จำนวนเงิน (บาท)", exact=True)).to_have_value(
                ""
            )
            print(
                "PASS unsaved draft cancellation preserves values; explicit exit discards the draft"
            )

            await leave_profile()
            await switch_user("alice", "1")
            await expect(group.locator('option[value="1"]')).to_have_count(1)
            await expect(group.locator('option[value="2"]')).to_have_count(0)
            await expect(rows).to_have_count(0)
            await expect(ledger).to_contain_text("alice")
            await expect(ledger).to_contain_text("carol")
            await switch_user("bob", "1")
            await expect(group.locator('option[value="1"]')).to_have_count(1)
            await expect(group.locator('option[value="2"]')).to_have_count(1)
            await switch_user("dan", "2")
            await expect(group.locator('option[value="1"]')).to_have_count(0)
            await expect(group.locator('option[value="2"]')).to_have_count(1)
            await expect(ledger).to_contain_text("dan")
            await expect(ledger).not_to_contain_text("alice")
            await switch_user("alice", "1")
            print("PASS user/group membership and clean context switching")

            # Payer and first participant deliberately differ: the list owns rounding.
            await fill_expense("มื้อเย็นทดสอบ", "100.00", "bob")
            await expect(page.get_by_test_id("preview-alice")).to_contain_text("33.34")
            await expect(page.get_by_test_id("preview-bob")).to_contain_text("33.33")
            await expect(page.get_by_test_id("preview-carol")).to_contain_text("33.33")
            await save()
            await expect(rows).to_have_count(1)
            await expect(ledger).to_contain_text("66.67")
            await expect(ledger).to_contain_text("33.34")
            assert sql_count("มื้อเย็นทดสอบ") == 1
            await expect(
                page.get_by_role("button", name="ลบ มื้อเย็นทดสอบ", exact=True)
            ).to_have_count(0)
            print("PASS equal split preview, real POST, balances, payer-only control")

            await fill_expense("เศษสตางค์ทดสอบ", "0.30")
            await form.get_by_role("radio", name="กำหนดจำนวนเอง", exact=True).check()
            await form.get_by_label("จำนวนของ alice", exact=False).fill("0.10")
            await form.get_by_label("จำนวนของ bob", exact=False).fill("0.19")
            await form.get_by_label("จำนวนของ carol", exact=False).fill("0.00")
            await expect(
                form.get_by_role("button", name="บันทึกค่าใช้จ่าย", exact=True)
            ).to_be_disabled()
            await form.get_by_label("จำนวนของ bob", exact=False).fill("0.20")
            await save()
            await expect(rows).to_have_count(2)
            await expect(rows.first).to_contain_text("เศษสตางค์ทดสอบ")
            with engine.connect() as connection:
                value = connection.execute(
                    text(
                        "SELECT amount FROM expenses WHERE description = 'เศษสตางค์ทดสอบ'"
                    )
                ).scalar_one()
                assert str(value) == "0.30", (
                    "Exact decimal amount changed in PostgreSQL"
                )
            print(
                "PASS exact allocation, zero share, mismatch disabled, newest-first list"
            )

            # The backend really commits this request; only its first response is lost.
            posted: list[tuple[str, str]] = []
            lost_once = False
            post_committed = asyncio.Event()
            post_release = asyncio.Event()

            async def lose_first_response(route) -> None:
                nonlocal lost_once
                request = route.request
                if request.method != "POST":
                    await route.continue_()
                    return
                posted.append(
                    (
                        request.headers.get("idempotency-key", ""),
                        request.post_data or "",
                    )
                )
                if not lost_once:
                    lost_once = True
                    response = await route.fetch()
                    assert response.status == 201, (
                        "Lost-response request did not commit"
                    )
                    post_committed.set()
                    await post_release.wait()
                    await route.abort("failed")
                else:
                    await route.continue_()

            await page.route(f"{api_url}/groups/1/expenses", lose_first_response)
            await fill_expense("ส่งซ้ำหลังเน็ตหลุด", "100.00")
            await form.get_by_role("radio", name="หารเท่ากัน", exact=True).check()
            await form.get_by_role("button", name="บันทึกค่าใช้จ่าย", exact=True).click()
            await asyncio.wait_for(post_committed.wait(), timeout=20)
            await expect(exit_profile).to_be_disabled()
            post_release.set()
            retry = page.get_by_role("button", name="ลองส่งรายการเดิมอีกครั้ง", exact=True)
            await expect(retry).to_be_visible()
            await expect(retry).to_be_enabled()
            await expect(exit_profile).to_be_disabled()
            assert sql_count("ส่งซ้ำหลังเน็ตหลุด") == 1
            frozen_pending = await page.evaluate(
                "sessionStorage.getItem('splitbill.pending.v1')"
            )
            await page.evaluate("""() => {
                sessionStorage.setItem('splitbill.user.v1', 'dan');
                sessionStorage.setItem('splitbill.test.fail-profile-write', '1');
            }""")
            await page.add_init_script("""(() => {
                window.__failProfileWrite = sessionStorage.getItem(
                    'splitbill.test.fail-profile-write') === '1';
                const original = Storage.prototype.setItem;
                Storage.prototype.setItem = function(key, value) {
                    if (key === 'splitbill.user.v1' && window.__failProfileWrite)
                        throw new DOMException('Simulated profile storage failure', 'QuotaExceededError');
                    return original.call(this, key, value);
                };
            })();""")
            reload_requests = len(api_requests)
            await page.reload()
            await expect(retry).to_be_visible()
            await expect(retry).to_be_enabled()
            await expect(group).to_have_value("1")
            await expect(ledger).to_contain_text("alice")
            await expect(
                page.get_by_role("banner").get_by_text("alice", exact=True)
            ).to_be_visible()
            await expect(exit_profile).to_be_disabled()
            await expect(
                page.get_by_role("button", name="ตรวจรายการแล้ว เริ่มบิลใหม่", exact=True)
            ).to_have_count(0)
            assert (
                await page.evaluate("sessionStorage.getItem('splitbill.pending.v1')")
                == frozen_pending
            ), "Profile storage failure lost the unresolved request"
            assert all(
                request.headers.get("x-user") != "dan"
                for request in api_requests[reload_requests:]
                if request.method != "OPTIONS"
            ), "A saved profile overrode the unresolved expense owner during reload"
            async with page.expect_response(
                lambda response: (
                    response.request.method == "POST"
                    and response.url.endswith("/expenses")
                )
            ) as retry_info:
                await retry.click()
            assert (await retry_info.value).status == 200, (
                "Retry did not replay the original"
            )
            await expect(retry).to_be_enabled()
            await expect(exit_profile).to_be_disabled()
            assert (
                await page.evaluate("sessionStorage.getItem('splitbill.pending.v1')")
                == frozen_pending
            ), "A replay cleared pending before its owner was persisted"
            assert sql_count("ส่งซ้ำหลังเน็ตหลุด") == 1
            await page.evaluate("""() => {
                window.__failProfileWrite = false;
                sessionStorage.removeItem('splitbill.test.fail-profile-write');
            }""")
            async with page.expect_response(
                lambda response: (
                    response.request.method == "POST"
                    and response.url.endswith("/expenses")
                )
            ) as recovered_retry_info:
                await retry.click()
            assert (await recovered_retry_info.value).status == 200
            await expect(rows).to_have_count(3)
            await expect(exit_profile).to_be_enabled()
            assert (
                await page.evaluate("sessionStorage.getItem('splitbill.pending.v1')")
                is None
            ), "The confirmed request was not cleared after storage recovered"
            await expect(form.get_by_label("รายละเอียด", exact=True)).to_have_value("")
            await expect(
                form.get_by_role("button", name="บันทึกค่าใช้จ่าย", exact=True)
            ).to_be_disabled()
            assert (
                len(posted) == 3
                and all(attempt == posted[0] for attempt in posted)
                and posted[0][0]
            ), "A retry changed the original key or frozen request body"
            assert sql_count("ส่งซ้ำหลังเน็ตหลุด") == 1
            await page.unroute(f"{api_url}/groups/1/expenses", lose_first_response)
            await page.reload()
            await expect(group).to_have_value("1")
            await expect(ledger).to_contain_text("alice")
            await expect(
                page.get_by_role("banner").get_by_text("alice", exact=True)
            ).to_be_visible()
            await expect(ledger).not_to_contain_text("dan")
            await expect(exit_profile).to_be_enabled()
            print(
                "PASS real committed request + simulated response loss, locked exit, owner restore and same-key replay"
            )
            print(
                "PASS profile storage failure retains the frozen pending request until same-key recovery"
            )

            await switch_user("bob", "1")
            delete_button = page.get_by_role("button", name="ลบ มื้อเย็นทดสอบ", exact=True)
            await delete_button.click()
            cancel = page.get_by_role("button", name="ยกเลิก", exact=True)
            await expect(cancel).to_be_focused()
            await cancel.press("Enter")
            await expect(delete_button).to_be_focused()
            await delete_button.press("Enter")
            await expect(cancel).to_be_focused()
            await page.keyboard.press("Tab")
            await expect(
                page.get_by_role("button", name="ยืนยันลบ", exact=True)
            ).to_be_focused()
            delete_committed = asyncio.Event()
            delete_release = asyncio.Event()

            async def hold_delete_response(route) -> None:
                if route.request.method != "DELETE":
                    await route.continue_()
                    return
                response = await route.fetch()
                assert response.status == 204, "Held payer deletion did not commit"
                delete_committed.set()
                await delete_release.wait()
                await route.fulfill(response=response)

            await page.route(f"{api_url}/groups/1/expenses/*", hold_delete_response)
            async with page.expect_response(
                lambda response: response.request.method == "DELETE"
            ) as deletion_info:
                await page.keyboard.press("Enter")
                await asyncio.wait_for(delete_committed.wait(), timeout=20)
                await expect(exit_profile).to_be_disabled()
                delete_release.set()
            assert (await deletion_info.value).status == 204
            await expect(rows).to_have_count(2)
            await expect(exit_profile).to_be_enabled()
            await page.unroute(f"{api_url}/groups/1/expenses/*", hold_delete_response)
            await expect(rows.filter(has_text="มื้อเย็นทดสอบ")).to_have_count(0)
            await expect(ledger).to_contain_text("66.86")
            await expect(ledger).to_contain_text("-33.53")
            await expect(ledger).to_contain_text("-33.33")
            with engine.connect() as connection:
                assert (
                    connection.execute(
                        text(
                            "SELECT deleted FROM expenses WHERE description = 'มื้อเย็นทดสอบ'"
                        )
                    ).scalar_one()
                    is True
                )
            print(
                "PASS real payer deletion, locked profile exit, retained PostgreSQL row and refreshed list"
            )

            # Independent HTTP assertions distinguish a hidden UI control from authorization.
            request = context.request
            denied = await request.get(
                f"{api_url}/groups/2/balances", headers={"X-User": "alice"}
            )
            assert denied.status == 404, "Group access was not enforced by the API"
            listing = await request.get(
                f"{api_url}/groups/1/expenses", headers={"X-User": "alice"}
            )
            active = await listing.json()
            own_expense = next(
                item for item in active if item["description"] == "ส่งซ้ำหลังเน็ตหลุด"
            )
            denied_delete = await request.delete(
                f"{api_url}/groups/1/expenses/{own_expense['id']}",
                headers={"X-User": "bob"},
            )
            assert denied_delete.status == 403, "The API accepted a nonpayer deletion"
            balances = await request.get(
                f"{api_url}/groups/1/balances", headers={"X-User": "bob"}
            )
            values = await balances.json()
            from decimal import Decimal

            assert sum(map(Decimal, values.values())) == Decimal("0.00")
            print("PASS real API authorization and zero-sum balances after deletion")

            # Freeze an actual old manual-refresh snapshot, then create a new bill.
            # Its newer refresh must win after the old HTTP responses arrive last.
            old_ready = asyncio.Event()
            old_release = asyncio.Event()
            old_finished = asyncio.Event()
            held: set[str] = set()
            old_payloads: dict = {}
            completed_old = 0

            async def hold_old_snapshot(route) -> None:
                nonlocal completed_old
                request_url = route.request.url
                if route.request.method != "GET" or request_url in held:
                    await route.continue_()
                    return
                held.add(request_url)
                response = await route.fetch()
                old_payloads[request_url] = await response.json()
                if len(old_payloads) == 2:
                    old_ready.set()
                await old_release.wait()
                await route.fulfill(response=response)
                completed_old += 1
                if completed_old == 2:
                    old_finished.set()

            for endpoint in ("expenses", "balances"):
                await page.route(f"{api_url}/groups/1/{endpoint}", hold_old_snapshot)
            await page.get_by_role("button", name="รีเฟรชรายการ", exact=True).click()
            await asyncio.wait_for(old_ready.wait(), timeout=20)
            assert len(old_payloads[f"{api_url}/groups/1/expenses"]) == 2
            await fill_expense("รายการหลังรีเฟรชช้า", "60.00", "bob")
            await form.get_by_role("radio", name="หารเท่ากัน", exact=True).check()
            await save()
            await expect(rows).to_have_count(3)
            await expect(rows.first).to_contain_text("รายการหลังรีเฟรชช้า")
            await expect(ledger).to_contain_text("46.86")
            await expect(ledger).to_contain_text("6.47")
            await expect(ledger).to_contain_text("-53.33")
            async with (
                page.expect_response(
                    lambda response: (
                        response.request.method == "GET"
                        and response.url.endswith("/expenses")
                    )
                ) as old_expenses_info,
                page.expect_response(
                    lambda response: response.url.endswith("/balances")
                ) as old_balances_info,
            ):
                old_release.set()
                await asyncio.wait_for(old_finished.wait(), timeout=20)
            assert len(await (await old_expenses_info.value).json()) == 2
            await (await old_balances_info.value).json()
            # Allow both completed fetches to settle and React to paint their result.
            await page.evaluate(
                "new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
            )
            await expect(rows).to_have_count(3)
            await expect(rows.first).to_contain_text("รายการหลังรีเฟรชช้า")
            await expect(ledger).to_contain_text("46.86")
            await expect(ledger).to_contain_text("6.47")
            await expect(ledger).to_contain_text("-53.33")
            for endpoint in ("expenses", "balances"):
                await page.unroute(f"{api_url}/groups/1/{endpoint}", hold_old_snapshot)
            print("PASS delayed old snapshot cannot undo a successful create/refresh")

            # A delayed response from the previous user/group must not replace the new one.
            delayed = asyncio.Event()
            release = asyncio.Event()
            finished = asyncio.Event()

            async def delayed_balance(route) -> None:
                try:
                    response = await route.fetch()
                    delayed.set()
                    await release.wait()
                    await route.fulfill(response=response)
                except PlaywrightError:
                    # Switching users may abort the old browser request, which is correct.
                    print("Old context request was aborted during user switching")
                finally:
                    finished.set()

            await page.route(f"{api_url}/groups/1/balances", delayed_balance)
            await switch_user("dan", "2")
            await leave_profile()
            await choose_user("alice")
            await asyncio.wait_for(delayed.wait(), timeout=20)
            await switch_user("dan", "2")
            release.set()
            await asyncio.wait_for(finished.wait(), timeout=20)
            await expect(group).to_have_value("2")
            await expect(ledger).to_contain_text("dan")
            await expect(ledger).not_to_contain_text("alice")
            await expect(rows).to_have_count(0)
            await page.unroute(f"{api_url}/groups/1/balances", delayed_balance)
            print("PASS delayed old-group response cannot overwrite a new user context")

            # Capture realistic example data through the same real API. These are
            # disposable fixtures in this runner's schema, never application rows.
            await switch_user("alice", "1")
            listing = await request.get(
                f"{api_url}/groups/1/expenses", headers={"X-User": "alice"}
            )
            for expense in await listing.json():
                removed = await request.delete(
                    f"{api_url}/groups/1/expenses/{expense['id']}",
                    headers={"X-User": expense["paid_by"]},
                )
                assert removed.status == 204
            for description, amount, payer in [
                ("มื้อเย็นที่เชียงใหม่", "1000.00", "alice"),
                ("กาแฟระหว่างทาง", "240.00", "bob"),
                ("ค่ารถกลับที่พัก", "180.00", "carol"),
            ]:
                created = await request.post(
                    f"{api_url}/groups/1/expenses",
                    headers={"X-User": "alice", "Idempotency-Key": uuid4().hex},
                    data={
                        "description": description,
                        "paid_by": payer,
                        "amount": amount,
                        "split": {
                            "type": "equal",
                            "members": ["alice", "bob", "carol"],
                        },
                    },
                )
                assert created.status == 201
            await page.get_by_role("button", name="รีเฟรชรายการ", exact=True).click()
            await expect(rows).to_have_count(3)
            await expect(rows.first).to_contain_text("ค่ารถกลับที่พัก")
            await expect(ledger).to_contain_text("526.66")
            await fill_expense("มื้อถัดไป", "100.00")
            await form.get_by_role("radio", name="หารเท่ากัน", exact=True).check()
            await expect(page.get_by_test_id("preview-alice")).to_contain_text("33.34")
            carol = form.get_by_role("checkbox", name="carol", exact=True)
            await carol.focus()
            await carol.press("Space")
            await expect(carol).not_to_be_checked()
            await expect(page.get_by_test_id("preview-alice")).to_contain_text("50.00")
            await carol.press("Space")
            await expect(carol).to_be_checked()
            equal = form.get_by_role("radio", name="หารเท่ากัน", exact=True)
            exact = form.get_by_role("radio", name="กำหนดจำนวนเอง", exact=True)
            await equal.focus()
            await equal.press("ArrowRight")
            await expect(exact).to_be_checked()
            await expect(
                form.get_by_label("จำนวนของ alice", exact=False)
            ).to_be_visible()
            await exact.press("ArrowLeft")
            await expect(equal).to_be_checked()
            await expect(page.get_by_test_id("preview-alice")).to_contain_text("33.34")
            print(
                "PASS keyboard checkboxes, radio arrows, delete cancellation/focus and confirmation"
            )
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            for width, height, name in [(1440, 1000, "desktop"), (390, 844, "mobile")]:
                await page.set_viewport_size({"width": width, "height": height})
                await page.get_by_role(
                    "heading", name="Chiang Mai trip", exact=True
                ).click()
                await page.evaluate("""async () => {
                    await document.fonts.ready;
                    await Promise.all(document.getAnimations()
                        .filter(animation => Number.isFinite(animation.effect?.getTiming().iterations ?? 1))
                        .map(animation => animation.finished.catch(() => {})));
                }""")
                await page.locator(".brand-mark").evaluate("image => image.decode()")
                assert await page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth"
                ), f"Horizontal overflow at {width}px"
                await page.screenshot(
                    path=str(screenshot_dir / f"frontend-{name}.png"), full_page=True
                )
            for width in (375, 768, 1024):
                await page.set_viewport_size({"width": width, "height": 1024})
                assert await page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth"
                ), f"Horizontal overflow at {width}px"
            await page.emulate_media(reduced_motion="reduce")
            await expect(form.get_by_label("รายละเอียด", exact=True)).to_be_visible()
            assert not console_errors, (
                "The browser reported an uncaught JavaScript exception"
            )
            print(
                "PASS 375/390/768/1024/1440px overflow checks, reduced motion, no uncaught browser errors"
            )
            print(
                f"Screenshots: {screenshot_dir} / frontend[-entry]-desktop.png, frontend[-entry]-mobile.png"
            )
        except (AssertionError, PlaywrightError, TimeoutError) as error:
            failure_dir = Path(tempfile.mkdtemp(prefix="splitbill-frontend-failure-"))
            try:
                await page.screenshot(
                    path=str(failure_dir / "failure.png"), full_page=True, timeout=5000
                )
                (failure_dir / "failure.html").write_text(await page.content())
                print(f"Failure screenshot and HTML: {failure_dir}", file=sys.stderr)
            except PlaywrightError:
                print(
                    "Failure screenshot unavailable because the browser closed",
                    file=sys.stderr,
                )
            print(f"Browser check failed: {error}", file=sys.stderr)
            raise
        finally:
            await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", type=int, default=8059)
    parser.add_argument("--web-port", type=int, default=3001)
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Use a build made with this test API URL",
    )
    parser.add_argument("--screenshot-dir", type=Path, default=ROOT / "design-system")
    args = parser.parse_args()
    free_port(args.api_port)
    free_port(args.web_port)
    values = dotenv_values(ROOT / ".env")
    raw_url = os.environ.get("TEST_DATABASE_URL") or values.get("TEST_DATABASE_URL")
    if not raw_url:
        raise RuntimeError(
            "Set TEST_DATABASE_URL to a dedicated PostgreSQL 16 test database"
        )
    test_url = make_url(raw_url)
    app_url = values.get("DATABASE_URL")
    if app_url and make_url(app_url).set(password=None) == test_url.set(password=None):
        raise RuntimeError(
            "TEST_DATABASE_URL must use a database separate from the root .env application database"
        )
    admin = create_engine(test_url)
    schema = f"splitbill_browser_{uuid4().hex}"
    scoped = test_url.update_query_dict({"options": f"-csearch_path={schema}"})
    engine = create_engine(scoped)
    processes: list[subprocess.Popen] = []
    api_url = f"http://127.0.0.1:{args.api_port}"
    web_url = f"http://127.0.0.1:{args.web_port}"
    web_env = os.environ | {
        "NEXT_PUBLIC_API_URL": api_url,
        "NEXT_TELEMETRY_DISABLED": "1",
    }
    for name in ("DATABASE_URL", "TEST_DATABASE_URL"):
        web_env.pop(name, None)
    api_env = os.environ | {
        "DATABASE_URL": scoped.render_as_string(hide_password=False),
        "CORS_ORIGINS": f"{web_url},http://localhost:{args.web_port}",
    }
    schema_created = False
    try:
        with admin.begin() as connection:
            version = int(
                connection.exec_driver_sql("SHOW server_version_num").scalar_one()
            )
            if not 160000 <= version < 170000:
                raise RuntimeError("Browser integration requires PostgreSQL 16")
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            schema_created = True
        config = Config(str(BACKEND / "alembic.ini"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        with Session(engine) as session, session.begin():
            seed_database(session)
        with tempfile.TemporaryFile(mode="w+") as log:
            if not args.skip_build:
                subprocess.run(
                    ["npm", "run", "build"],
                    cwd=ROOT / "frontend",
                    env=web_env,
                    check=True,
                )
            for cmd, cwd, env in [
                (
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "splitbill.app:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(args.api_port),
                    ],
                    BACKEND,
                    api_env,
                ),
                (
                    [
                        "npm",
                        "run",
                        "start",
                        "--",
                        "--hostname",
                        "127.0.0.1",
                        "--port",
                        str(args.web_port),
                    ],
                    ROOT / "frontend",
                    web_env,
                ),
            ]:
                processes.append(
                    subprocess.Popen(
                        cmd,
                        cwd=cwd,
                        env=env,
                        stdout=log,
                        stderr=log,
                        start_new_session=True,
                    )
                )
            wait_for_server(f"{api_url}/openapi.json", processes[0])
            wait_for_server(web_url, processes[1])
            asyncio.run(browser_checks(api_url, web_url, engine, args.screenshot_dir))
    finally:
        for process in reversed(processes):
            stop(process)
        engine.dispose()
        if schema_created:
            with admin.begin() as connection:
                connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        admin.dispose()


if __name__ == "__main__":
    # Secrets stay in the child environment, never command-line arguments or output.
    # A failing check still produces a nonzero exit status for CI.
    try:
        main()
    except ImportError as error:
        print(f"FAIL missing test-tooling module: {error.name}", file=sys.stderr)
        raise SystemExit(1) from None
    except OSError as error:
        print(
            f"FAIL {type(error).__name__}: {error.errno} {error.strerror}",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    except Exception as error:  # noqa: BLE001 - do not expose credentials in connection tracebacks
        print(
            f"FAIL {type(error).__name__}: {error}"
            if isinstance(error, AssertionError)
            else f"FAIL {type(error).__name__}; verify test database, Playwright and local server setup",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
