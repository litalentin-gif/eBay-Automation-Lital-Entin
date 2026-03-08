"""
SearchPage - eBay Search Page Object
=====================================
Handles: search bar, price filter, result collection, pagination.
Core function: search_items_by_name_under_price()
"""

import logging
import re
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage
from utils.retry_utils import retry_on_failure

logger = logging.getLogger(__name__)


class SearchPage(BasePage):
    """Page Object for eBay search results page."""

    # ── Locators (primary + fallback for each element) ─────────────

    SEARCH_BOX = [
        "input#gh-ac",                         # primary: ID
        "input[aria-label='Search for anything']",  # fallback: aria-label
    ]

    SEARCH_BUTTON = [
        "button#gh-btn",                        # primary
        "button[type='submit'][aria-label='Search']",  # fallback
    ]

    MIN_PRICE_INPUT = [
        "input[aria-label='Minimum Value in $']",  # primary
        "input[placeholder='Min']",               # fallback
    ]

    MAX_PRICE_INPUT = [
        "input[aria-label='Maximum Value in $']",  # primary
        "input[placeholder='Max']",               # fallback
    ]

    PRICE_FILTER_SUBMIT = [
        "button[aria-label='Submit price range']",  # primary
        "//button[contains(@class,'x-price-filter__submit')]",  # fallback xpath
    ]

    # Item cards on results page
    ITEM_TITLES = [
        "//ul[contains(@class,'srp-results')]//li[contains(@class,'s-item')]"
        "//a[contains(@class,'s-item__link')]",   # primary xpath
        "a.s-item__link",                         # fallback css
    ]

    ITEM_PRICE = [
        ".s-item__price",                         # primary
        "//span[contains(@class,'s-item__price')]",  # fallback xpath
    ]

    NEXT_PAGE_BUTTON = [
        "a[aria-label='Go to next search page']",  # primary
        "//a[contains(@aria-label,'next')]",        # fallback
    ]

    # ── Main search function ────────────────────────────────────────

    def search_items_by_name_under_price(
        self, query: str, max_price: float, limit: int = 5
    ) -> list[str]:
        """
        Search eBay for `query`, filter by price ≤ max_price,
        return up to `limit` item URLs.

        Handles pagination if fewer than limit results on first page.
        Returns empty list (not error) if nothing found.
        """
        logger.info(
            f"[SearchPage] 🔍 Searching: '{query}' | max_price=${max_price} | limit={limit}"
        )

        self._perform_search(query)
        self._apply_price_filter(max_price)

        collected_urls = []
        page_num = 1

        while len(collected_urls) < limit:
            logger.info(f"[SearchPage] Scraping page {page_num}...")
            page_urls = self._collect_items_under_price(max_price, limit - len(collected_urls))
            collected_urls.extend(page_urls)

            logger.info(
                f"[SearchPage] Page {page_num}: got {len(page_urls)} items. "
                f"Total so far: {len(collected_urls)}/{limit}"
            )

            if len(collected_urls) >= limit:
                break

            # Try to go to next page
            if not self._go_to_next_page():
                logger.info("[SearchPage] No more pages. Stopping.")
                break
            page_num += 1

        result = collected_urls[:limit]
        logger.info(f"[SearchPage] ✅ Final result: {len(result)} URLs collected.")
        self.take_screenshot(f"search_results_{query}")
        return result

    # ── Private helpers ─────────────────────────────────────────────

    @retry_on_failure(max_attempts=3, backoff_factor=1.5)
    def _perform_search(self, query: str):
        """Type query in search box and submit."""
        search_box = self.smart(self.SEARCH_BOX, "Search box").find()
        search_box.clear()
        search_box.fill(query)
        self.smart(self.SEARCH_BUTTON, "Search button").find().click()
        self.wait_for_load()

    def _apply_price_filter(self, max_price: float):
        """
        Apply max price filter if the input fields are available.
        Gracefully skips if the filter UI is not present.
        """
        try:
            max_input = self.smart(self.MAX_PRICE_INPUT, "Max price input").find(timeout=4000)
            max_input.clear()
            max_input.fill(str(int(max_price)))
            self.smart(self.PRICE_FILTER_SUBMIT, "Price filter submit").find().click()
            self.wait_for_load()
            logger.info(f"[SearchPage] ✅ Price filter applied: max=${max_price}")
        except Exception:
            logger.warning(
                "[SearchPage] ⚠️  Price filter UI not found — "
                "will filter manually from results."
            )

    def _collect_items_under_price(self, max_price: float, needed: int) -> list[str]:
        """
        Extract URLs of items whose price ≤ max_price from current page.
        Returns up to `needed` URLs.
        """
        urls = []
        try:
            item_links = self.smart(self.ITEM_TITLES, "Item links").find_all(timeout=6000)
        except Exception:
            logger.warning("[SearchPage] No item links found on this page.")
            return urls

        for link in item_links:
            if len(urls) >= needed:
                break
            try:
                # Get the price sibling element
                parent = link.locator("xpath=ancestor::li").first
                price_text = parent.locator(self.ITEM_PRICE[0]).first.inner_text()
                price = self._parse_price(price_text)

                if price is not None and price <= max_price:
                    href = link.get_attribute("href")
                    if href and href.startswith("http"):
                        urls.append(href)
                        logger.debug(f"[SearchPage] ✅ Added: ${price} — {href[:60]}...")
                else:
                    logger.debug(f"[SearchPage] ⏭️  Skipped: ${price} > ${max_price}")

            except Exception as e:
                logger.debug(f"[SearchPage] Could not parse item: {e}")
                continue

        return urls

    def _parse_price(self, price_text: str) -> float | None:
        """
        Parse price string like '$45.99' or '$45.99 to $59.99' → 45.99 (takes lower).
        Returns None if unparseable.
        """
        if not price_text:
            return None
        # Remove currency symbols, take first number found
        numbers = re.findall(r"[\d,]+\.?\d*", price_text.replace(",", ""))
        if numbers:
            return float(numbers[0])
        return None

    def _go_to_next_page(self) -> bool:
        """
        Click 'Next' button if it exists and is enabled.
        Returns True if navigated, False otherwise.
        """
        try:
            next_btn = self.smart(self.NEXT_PAGE_BUTTON, "Next page button").find(timeout=3000)
            if next_btn.is_enabled():
                next_btn.click()
                self.wait_for_load()
                return True
        except Exception:
            pass
        return False
