"""
ItemPage - eBay Individual Item Page Object
===========================================
Handles: variant selection (size/color/quantity),
         Add to Cart button, screenshot logging.
"""

import logging
import random
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage
from utils.retry_utils import retry_on_failure

logger = logging.getLogger(__name__)


class ItemPage(BasePage):
    """Page Object for a single eBay product listing."""

    # ── Locators ───────────────────────────────────────────────────

    ADD_TO_CART_BTN = [
        "//a[contains(@class,'x-atc-action__btn') and contains(.,'Add to cart')]",  # primary xpath
        "a#atcBtn_btn",                             # fallback: ID
        "button[data-testid='ux-call-to-action']",  # fallback: test-id
    ]

    BUY_NOW_BTN = [
        "//a[contains(.,'Buy It Now')]",
        "a#binBtn_btn",
    ]

    # Variant option buttons (size, color, etc.)
    VARIANT_SELECT_WRAPPER = [
        ".x-msku__select-box",                      # primary: select box
        "select.msku-sel",                           # fallback
    ]

    # Quantity input
    QUANTITY_INPUT = [
        "input#qtyTextBox",                          # primary
        "input[aria-label='Quantity']",              # fallback
    ]

    ITEM_TITLE = [
        "h1.x-item-title__mainTitle span",           # primary
        "//h1[@class='x-item-title__mainTitle']//span",  # fallback
    ]

    # ── Main function ──────────────────────────────────────────────

    def _close_popups(self):
        """Close 'Message seller' popup if present."""
        # Close "Message seller" popup if present
        try:
            close_btn = self.page.locator("button[aria-label='Close']").first
            if close_btn.is_visible(timeout=2000):
                close_btn.click()
                self.page.wait_for_timeout(500)
        except:
            pass

        # Also try X button by class
        try:
            close_btn2 = self.page.locator(".message-modal__close, .overlay-close, [class*='close']").first
            if close_btn2.is_visible(timeout=1000):
                close_btn2.click()
                self.page.wait_for_timeout(500)
        except:
            pass
    def add_item_to_cart(self, url: str) -> bool:
        """
        Open the item URL, select variants if required, click Add to Cart.
        Returns True on success, False if item could not be added.
        """
        logger.info(f"[ItemPage] 🛒 Opening item: {url[:80]}...")
        self.navigate(url)
        self.wait_for_load()

        # Get item name for logging
        try:
            title = self.smart(self.ITEM_TITLE, "Item title").find(timeout=4000).inner_text()
            logger.info(f"[ItemPage] Product: {title[:60]}")
        except Exception:
            title = "Unknown item"

        # Select variants (size, color, etc.) if present
        self._select_available_variants()

        # Try to click Add to Cart
        try:
            add_btn = self.smart(self.ADD_TO_CART_BTN, "Add to Cart button").find(timeout=5000)
            self.page.evaluate("el => el.click()", add_btn.element_handle())
            logger.info(f"[ItemPage] [ok] Added to cart: {title[:60]}")
            self.take_screenshot(f"cart_add_{title[:30].replace(' ', '_')}")
            return True

        except Exception as e:
            logger.warning(f"[ItemPage] [warning] Could not add to cart: {e}")
            self.take_screenshot(f"cart_fail_{title[:30].replace(' ', '_')}")
            return False

    # ── Variant selection ──────────────────────────────────────────

    def _select_available_variants(self):
        """
        If the page has variant selectors (size, color, quantity),
        pick a random available option for each.
        """
        try:
            # Handle <select> dropdowns (size/color menus)
            select_elements = self.page.locator("select.msku-sel, .x-msku__select-box select").all()
            for sel in select_elements:
                options = sel.locator("option").all()
                # Filter out placeholder options (empty value or "Select")
                valid_options = [
                    o for o in options
                    if o.get_attribute("value") and o.get_attribute("value") not in ["", "0"]
                    and "select" not in (o.inner_text() or "").lower()
                ]
                if valid_options:
                    chosen = random.choice(valid_options)
                    val = chosen.get_attribute("value")
                    sel.select_option(value=val)
                    logger.info(
                        f"[ItemPage] [info] Selected variant: {chosen.inner_text().strip()}"
                    )

            # Handle button-style variant pickers (clickable size/color swatches)
            swatch_buttons = self.page.locator(
                ".x-msku__select-box-control button:not([aria-disabled='true'])"
            ).all()
            if swatch_buttons:
                chosen_swatch = random.choice(swatch_buttons)
                chosen_swatch.click()
                logger.info("[ItemPage] [info] Selected swatch variant.")

        except Exception as e:
            logger.debug(f"[ItemPage] [debug] Variant selection skipped: {e}")
