"""
SearchPage - eBay Search Page Object
"""

import logging
import re
from pages.base_page import BasePage
from utils.retry_utils import retry_on_failure

logger = logging.getLogger(__name__)


class SearchPage(BasePage):

    SEARCH_BOX = [
        "input#gh-ac",
        "input[aria-label='Search for anything']",
    ]

    SEARCH_BUTTON = [
        "input#gh-btn",
        "button[type='submit']",
        "[aria-label='Search']",
    ]

    MAX_PRICE_INPUT = [
        "input[aria-label='Maximum Value in $']",
        "input[placeholder='Max']",
    ]

    PRICE_FILTER_SUBMIT = [
        "button[aria-label='Submit price range']",
        "button.x-price-filter__submit",
    ]

    NEXT_PAGE_BUTTON = [
        "a[aria-label='Go to next search page']",
        "a.pagination__next",
    ]

    def search_items_by_name_under_price(self, query, max_price, limit=5):
        logger.info(f"[SearchPage] Searching: '{query}' | max_price={max_price} | limit={limit}")

        self._perform_search(query)
        self._apply_price_filter(max_price)

        collected_urls = []
        page_num = 1
        max_pages = 3

        while len(collected_urls) < limit and page_num <= max_pages:
            logger.info(f"[SearchPage] Scraping page {page_num}...")
            page_urls = self._collect_items_under_price(max_price, limit - len(collected_urls))
            collected_urls.extend(page_urls)
            logger.info(f"[SearchPage] Page {page_num}: got {len(page_urls)} items. Total: {len(collected_urls)}/{limit}")

            if len(collected_urls) >= limit:
                break

            if not self._go_to_next_page():
                logger.info("[SearchPage] No more pages.")
                break
            page_num += 1

        result = collected_urls[:limit]
        logger.info(f"[SearchPage] Final result: {len(result)} URLs collected.")
        self.take_screenshot(f"search_results_{query}")
        return result

    @retry_on_failure(max_attempts=3, backoff_factor=1.5)
    def _perform_search(self, query):
        self._close_popup_if_present()
        search_box = self.smart(self.SEARCH_BOX, "Search box").find()
        search_box.clear()
        search_box.fill(query)
        self.smart(self.SEARCH_BUTTON, "Search button").find().click()
        self.wait_for_load()

    def _close_popup_if_present(self):
        try:
            close_btn = self.page.locator(
                "button[aria-label='Close'], .lightbox-dialog__close, button.dialog__close"
            ).first
            close_btn.wait_for(state="visible", timeout=3000)
            close_btn.click()
            self.page.wait_for_timeout(500)
            logger.info("[SearchPage] Closed blocking popup")
        except Exception:
            logger.debug("[SearchPage] No popup found")

    def _apply_price_filter(self, max_price):
        try:
            max_input = self.smart(self.MAX_PRICE_INPUT, "Max price input").find(timeout=4000)
            max_input.clear()
            max_input.fill(str(int(max_price)))
            self.smart(self.PRICE_FILTER_SUBMIT, "Price filter submit").find().click()
            self.wait_for_load()
            logger.info(f"[SearchPage] Price filter applied: max={max_price}")
        except Exception:
            logger.warning("[SearchPage] Price filter UI not found - filtering manually.")

    def _collect_items_under_price(self, max_price, needed):
        try:
            self.page.wait_for_load_state("networkidle", timeout=15000)
            self.page.wait_for_timeout(1000)

            js_code = """
                (maxPrice) => {
                    var items = document.querySelectorAll('li.s-item, li.s-card');
                    var urls = [];
                    for (var i = 0; i < items.length; i++) {
                        if (urls.length >= 10) break;
                        var item = items[i];
                        var link = item.querySelector('a.s-card__link, a.s-item__link');
                        var priceEl = item.querySelector('.s-item__price, .s-card__price, [class*=price]');
                        if (!link || !priceEl) continue;
                        var priceText = priceEl.innerText || '';
                        var cleaned = priceText.replace(/[^0-9.]/g, ' ').trim();
                        var parts = cleaned.split(' ').filter(function(x) { return x.length > 0; });
                        if (parts.length === 0) continue;
                        var price = parseFloat(parts[0]);
                       var href = link.href;
                        if (!isNaN(price) && price <= maxPrice && href.includes('www.ebay.com') && !href.includes('itm/123456')) {
                        urls.push(href);
                        }
                    }
                    return urls;
                }
            """

            results = self.page.evaluate(js_code, max_price)
            logger.info(f"[SearchPage] Found {len(results)} items under {max_price}")
            return results[:needed]

        except Exception as e:
            logger.warning(f"[SearchPage] JS extraction failed: {e}")
            return []

    def _go_to_next_page(self):
        try:
            next_btn = self.smart(self.NEXT_PAGE_BUTTON, "Next page button").find(timeout=3000)
            if next_btn.is_enabled():
                next_btn.click()
                self.wait_for_load()
                return True
        except Exception:
            pass
        return False