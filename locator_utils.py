"""
Locator Utility - Smart Locator with Fallback
============================================
Each element has multiple locators. If the primary fails,
we automatically try the next one — tests stay clean.
"""

import logging
import os
from datetime import datetime
from typing import Optional
from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class SmartLocator:
    """
    Wraps multiple locator strategies for a single element.
    Tries each in order; logs which succeeded/failed.
    If all fail → takes a screenshot and raises.
    """

    def __init__(self, page: Page, locators: list[str], element_name: str = "element"):
        """
        Args:
            page: Playwright Page object
            locators: list of CSS/XPath selectors (primary first, fallbacks after)
            element_name: human-readable name for logging
        """
        self.page = page
        self.locators = locators
        self.element_name = element_name

    def find(self, timeout: int = 5000) -> Locator:
        """
        Try each locator in order. Returns the first one that is visible.
        Raises ValueError if all fail.
        """
        attempts = len(self.locators)
        for i, selector in enumerate(self.locators):
            locator_num = i + 1
            try:
                logger.info(
                    f"[SmartLocator] '{self.element_name}' — "
                    f"attempt {locator_num}/{attempts} using: {selector}"
                )
                loc = self.page.locator(selector).first
                loc.wait_for(state="visible", timeout=timeout)
                logger.info(
                    f"[SmartLocator] ✅ '{self.element_name}' found "
                    f"on attempt {locator_num} with: {selector}"
                )
                return loc

            except PlaywrightTimeoutError:
                logger.warning(
                    f"[SmartLocator] ❌ '{self.element_name}' "
                    f"attempt {locator_num} FAILED with: {selector}"
                )

        # All locators failed — screenshot + raise
        self._take_failure_screenshot()
        raise ValueError(
            f"[SmartLocator] All {attempts} locators failed for '{self.element_name}'. "
            f"Tried: {self.locators}"
        )

    def find_all(self, timeout: int = 5000) -> list[Locator]:
        """
        Like find(), but returns ALL matching elements using the first working locator.
        """
        for i, selector in enumerate(self.locators):
            try:
                self.page.locator(selector).first.wait_for(state="visible", timeout=timeout)
                all_elements = self.page.locator(selector).all()
                logger.info(
                    f"[SmartLocator] ✅ '{self.element_name}' found {len(all_elements)} elements "
                    f"on attempt {i+1} with: {selector}"
                )
                return all_elements
            except PlaywrightTimeoutError:
                logger.warning(
                    f"[SmartLocator] ❌ '{self.element_name}' attempt {i+1} FAILED"
                )

        self._take_failure_screenshot()
        return []  # return empty list (don't crash on find_all)

    def _take_failure_screenshot(self):
        """Save a screenshot when all locators fail."""
        try:
            os.makedirs("reports/screenshots", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"reports/screenshots/FAIL_{self.element_name}_{timestamp}.png"
            self.page.screenshot(path=path)
            logger.error(f"[SmartLocator] 📸 Failure screenshot saved: {path}")
        except Exception as e:
            logger.error(f"[SmartLocator] Could not take screenshot: {e}")
