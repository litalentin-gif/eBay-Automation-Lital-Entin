"""
BasePage - Parent class for all Page Object classes
===================================================
Contains shared utilities: navigation, screenshots,
waiting, and smart locator factory.
"""

import os
import logging
from datetime import datetime
from playwright.sync_api import Page, expect

from utils.locator_utils import SmartLocator
from utils.retry_utils import retry_on_failure

logger = logging.getLogger(__name__)


class BasePage:
    """All Page Objects inherit from this class."""

    def __init__(self, page: Page):
        self.page = page

    # ── Navigation ────────────────────────────────────────────────

    @retry_on_failure(max_attempts=3, backoff_factor=1.5)
    def navigate(self, url: str):
        logger.info(f"[BasePage] Navigating to: {url}")
        self.page.goto(url, wait_until="domcontentloaded", timeout=30000)

    # ── Smart Locator Factory ─────────────────────────────────────

    def smart(self, locators: list[str], name: str = "element") -> SmartLocator:
        """
        Shorthand to create a SmartLocator.
        Usage: self.smart(["css=...", "xpath=..."], "Search box").find()
        """
        return SmartLocator(self.page, locators, name)

    # ── Screenshots ───────────────────────────────────────────────

    def take_screenshot(self, label: str = "screenshot") -> str:
        """Save a screenshot and return the path."""
        os.makedirs("reports/screenshots", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"reports/screenshots/{label}_{timestamp}.png"
        self.page.screenshot(path=path, full_page=True)
        logger.info(f"[BasePage] 📸 Screenshot saved: {path}")
        return path

    # ── Waiting helpers ───────────────────────────────────────────

    def wait_for_url_contains(self, partial_url: str, timeout: int = 10000):
        self.page.wait_for_url(f"**{partial_url}**", timeout=timeout)

    def wait_for_load(self, timeout: int = 10000):
        self.page.wait_for_load_state("domcontentloaded", timeout=timeout)

    # ── Text / Attribute helpers ──────────────────────────────────

    def get_text(self, locators: list[str], name: str) -> str:
        element = self.smart(locators, name).find()
        return element.inner_text().strip()
