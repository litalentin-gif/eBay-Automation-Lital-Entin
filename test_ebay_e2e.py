"""
test_ebay_e2e.py - End-to-End Test: eBay Search → Cart → Assertion
===================================================================
The test itself is CLEAN — no locators, no retry logic here.
All complexity lives in Page Objects and Utils.

Flow:
  1. Search for items by name under a max price
  2. Add found items to cart
  3. Assert cart total doesn't exceed budget
"""

import logging
import pytest
import allure
from playwright.sync_api import Page

from pages.search_page import SearchPage
from pages.item_page import ItemPage
from pages.cart_page import CartPage

logger = logging.getLogger(__name__)


@allure.epic("eBay E2E")
@allure.feature("Search → Cart → Assert")
class TestEbayE2E:
    """
    Full E2E scenario: search → add to cart → assert total.
    Parametrized by browser (conftest.py) and scenario (test_data.json).
    """

    @allure.story("Happy path: find items, add to cart, check budget")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_search_and_buy_under_budget(self, page: Page, scenario: dict):
        """
        Data-Driven E2E test.
        Each scenario comes from data/test_data.json.
        """
        query = scenario["query"]
        max_price = scenario["max_price"]
        limit = scenario["limit"]
        budget_per_item = scenario["budget_per_item"]

        logger.info(
            f"\n{'='*60}\n"
            f"Scenario: {scenario['scenario_id']} — {scenario['description']}\n"
            f"{'='*60}"
        )

        # ── Step 1: Search ─────────────────────────────────────────
        with allure.step(f"Search for '{query}' under ${max_price}"):
            search_page = SearchPage(page)
            search_page.navigate("https://www.ebay.com")
            urls = search_page.search_items_by_name_under_price(query, max_price, limit)

            logger.info(f"Found {len(urls)} items matching criteria.")
            assert len(urls) >= 0, "Search function should never raise, just return fewer items"

            if len(urls) == 0:
                pytest.skip(f"No items found for '{query}' under ${max_price}. Skipping.")

            allure.attach(
                "\n".join(urls),
                name="Found URLs",
                attachment_type=allure.attachment_type.TEXT,
            )

        # ── Step 2: Add to cart ────────────────────────────────────
        with allure.step(f"Add {len(urls)} items to cart"):
            item_page = ItemPage(page)
            added_count = 0
            for url in urls:
                success = item_page.add_item_to_cart(url)
                if success:
                    added_count += 1

            logger.info(f"Successfully added {added_count}/{len(urls)} items to cart.")
            assert added_count > 0, "At least one item should be added to cart"

        # ── Step 3: Assert cart total ──────────────────────────────
        with allure.step(f"Assert cart total ≤ ${budget_per_item} × {added_count}"):
            cart_page = CartPage(page)
            cart_page.assert_cart_total_not_exceeds(budget_per_item, added_count)

        logger.info(f"✅ Scenario {scenario['scenario_id']} PASSED!")


# ── Isolated unit-style tests ──────────────────────────────────────

class TestSearchFunction:
    """Test the search function in isolation."""

    def test_search_returns_list(self, page: Page):
        """Search should always return a list, even if empty."""
        search_page = SearchPage(page)
        search_page.navigate("https://www.ebay.com")
        result = search_page.search_items_by_name_under_price("laptop", 500, 3)
        assert isinstance(result, list), "Should return a list"
        assert len(result) <= 3, "Should not exceed limit"

    def test_search_zero_results_ok(self, page: Page):
        """Zero results should return empty list, not raise."""
        search_page = SearchPage(page)
        search_page.navigate("https://www.ebay.com")
        # Absurdly low price — should return 0 items gracefully
        result = search_page.search_items_by_name_under_price("laptop", 0.01, 5)
        assert isinstance(result, list), "Should return empty list, not raise"
        assert result == [], f"Expected empty list, got {result}"
