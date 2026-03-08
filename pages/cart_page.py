"""
CartPage - eBay Shopping Cart Page Object
==========================================
Handles: opening cart, reading totals, asserting budget.
"""

import logging
import re
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage

logger = logging.getLogger(__name__)


class CartPage(BasePage):
    """Page Object for the eBay shopping cart."""

    CART_URL = "https://cart.payments.ebay.com/sc/view"

    # ── Locators ───────────────────────────────────────────────────

    CART_SUBTOTAL = [
        "//span[@id='subtotal-value']",                         # primary xpath
        "span.sc-subtotal-amount",                              # fallback css
        "//div[contains(@class,'sc-subtotal')]//span[contains(@class,'amount')]",  # deep fallback
    ]

    CART_ITEM_COUNT = [
        "//span[@class='sc-quantity-update-qty']",
        ".sc-quantity-update-qty",
    ]

    CART_ITEMS_WRAPPER = [
        "div#CART",
        "//div[@id='CART']",
    ]

    # ── Main assertion function ────────────────────────────────────

    def assert_cart_total_not_exceeds(
        self, budget_per_item: float, items_count: int
    ) -> None:
        """
        Open cart, read the subtotal, and assert it doesn't exceed
        budget_per_item × items_count.

        Raises AssertionError with details if budget is exceeded.
        """
        max_allowed = budget_per_item * items_count
        logger.info(
            f"[CartPage] [assert] Asserting cart total ≤ ${max_allowed:.2f} "
            f"({items_count} items × ${budget_per_item})"
        )

        self.navigate(self.CART_URL)
        self.wait_for_load(timeout=15000)

        # Read total
        actual_total = self._read_cart_total()
        logger.info(f"[CartPage] [total] Cart total: ${actual_total:.2f} | Max allowed: ${max_allowed:.2f}")

        # Save evidence
        self.take_screenshot("cart_assertion")
        self._save_trace_info(actual_total, max_allowed, items_count)

        # Assert
        assert actual_total <= max_allowed, (
            f"[CartPage] [fail] Cart total ${actual_total:.2f} EXCEEDS "
            f"budget of ${max_allowed:.2f} "
            f"({items_count} items × ${budget_per_item})"
        )

        logger.info(
            f"[CartPage] [ok] Assertion PASSED: ${actual_total:.2f} ≤ ${max_allowed:.2f}"
        )

    # ── Helpers ────────────────────────────────────────────────────

    def _read_cart_total(self) -> float:
        """
        Read the subtotal from the cart page.
        Falls back to summing individual item prices if subtotal element not found.
        """
        try:
            total_text = self.smart(self.CART_SUBTOTAL, "Cart subtotal").find(timeout=8000).inner_text()
            price = self._parse_price(total_text)
            if price is not None:
                return price
        except Exception as e:
            logger.warning(f"[CartPage] [warning]  Could not read subtotal element: {e}")

        # Fallback: sum individual item prices
        logger.info("[CartPage] Falling back to summing individual item prices...")
        return self._sum_item_prices()

    def _sum_item_prices(self) -> float:
        """Sum all individual item prices in the cart."""
        total = 0.0
        price_elements = self.page.locator(
            ".sc-item-price"
        ).all()
        for el in price_elements:
            price = self._parse_price(el.inner_text())
            if price:
                total += price
        logger.info(f"[CartPage] Summed {len(price_elements)} items = ${total:.2f}")
        return total

    def _parse_price(self, text: str) -> float | None:
        """Parse '$1,234.56' → 1234.56. Returns None if cannot parse."""
        if not text:
            return None
        cleaned = text.replace(",", "")
        numbers = re.findall(r"\d+\.?\d*", cleaned)
        return float(numbers[0]) if numbers else None

    def _save_trace_info(self, actual: float, max_allowed: float, count: int):
        """Log a summary trace of the cart assertion."""
        import os
        os.makedirs("reports", exist_ok=True)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"reports/cart_trace_{ts}.txt"
        with open(path, "w") as f:
            f.write(f"Cart Assertion Report — {ts}\n")
            f.write(f"{'='*40}\n")
            f.write(f"Items in cart:   {count}\n")
            f.write(f"Actual total:    ${actual:.2f}\n")
            f.write(f"Max allowed:     ${max_allowed:.2f}\n")
            f.write(f"Result:          {'PASS [ok]' if actual <= max_allowed else 'FAIL [fail]'}\n")
        logger.info(f"[CartPage] [cart] Trace saved: {path}")
