"""Playwright E2E smoke test for core Streamlit navigation journey."""

from __future__ import annotations

import os

import pytest

playwright = pytest.importorskip("playwright.sync_api")
Page = playwright.Page
expect = playwright.expect


BASE_URL = os.getenv("E2E_BASE_URL")

pytestmark = pytest.mark.skipif(
    not BASE_URL,
    reason="Set E2E_BASE_URL (for example http://localhost:8501) to run Playwright tests.",
)


def test_can_open_app_and_find_title(page: Page) -> None:
    page.goto(BASE_URL, wait_until="domcontentloaded")
    expect(page.get_by_text("Mall Navigator").first).to_be_visible()


def test_can_open_navigation_tab(page: Page) -> None:
    page.goto(BASE_URL, wait_until="domcontentloaded")
    nav_button = page.get_by_role("button", name="🧭 Navigate")
    nav_button.click()
    expect(page.get_by_text("Indoor Navigation")).to_be_visible()
