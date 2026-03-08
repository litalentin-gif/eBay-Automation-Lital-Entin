# eBay Automation Suite 🤖

End-to-end automation for eBay: Search → Filter by price → Add to Cart → Assert total.

Built with **Python + Playwright + pytest**, following POM, OOP, and Data-Driven patterns.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium firefox
```

### 3. Run all tests (single browser)
```bash
pytest
```

### 4. Run in parallel (2 browsers × 3 scenarios = 6 tests at once)
```bash
pytest -n 4
```

### 5. Run with Allure report
```bash
pytest --alluredir=reports/allure-results
allure serve reports/allure-results
```

### 6. Run headless (for CI)
```bash
HEADLESS=true pytest -n 4
```

---

## 🗂️ Project Architecture

```
ebay_automation/
├── pages/                 ← Page Object Model
│   ├── base_page.py       ← Shared logic (navigation, screenshots, smart locator factory)
│   ├── search_page.py     ← Search + price filter + pagination
│   ├── item_page.py       ← Variant selection + Add to Cart
│   └── cart_page.py       ← Cart total reading + assertion
│
├── utils/                 ← Infrastructure layer
│   ├── locator_utils.py   ← SmartLocator: multi-locator fallback with logging
│   └── retry_utils.py     ← @retry_on_failure decorator + RetryContext
│
├── tests/
│   └── test_ebay_e2e.py   ← Clean tests (no locators, no retry logic here)
│
├── data/
│   └── test_data.json     ← Test scenarios (Data-Driven)
│
├── config/
│   └── config.yaml        ← Timeouts, browsers, credentials
│
├── reports/               ← Auto-generated on each run
│   ├── allure-results/
│   ├── screenshots/
│   ├── traces/
│   └── logs/
│
├── conftest.py            ← pytest fixtures, browser setup, parametrization
├── pytest.ini             ← pytest config
└── requirements.txt
```

### Key Design Decisions

**Smart Locators** — each element has 2+ locators. If the primary fails,
`SmartLocator` silently tries the next one and logs which succeeded/failed.
Tests don't know this is happening — they stay clean.

**Retry + Backoff** — `@retry_on_failure(max_attempts=3, backoff_factor=1.5)`
on any function that touches the network. Wait grows: 1s → 1.5s → 2.25s.

**Session isolation** — each test gets its own browser context via `browser.new_context()`.
No shared state between parallel tests.

**Data-Driven** — `data/test_data.json` drives all test scenarios.
Add a new scenario → no code changes needed.

---

## ⚙️ Configuration

Edit `config/config.yaml`:
```yaml
timeouts:
  default: 10000       # ms per action
  navigation: 30000    # ms for page loads

retry:
  max_attempts: 3
  backoff_factor: 1.5
```

Add/remove browsers in `conftest.py`:
```python
@pytest.fixture(params=["chromium", "firefox"])  # add "webkit" for Safari
```

---

## 📊 Reports

| Type | Path | How to view |
|------|------|-------------|
| Allure | `reports/allure-results/` | `allure serve reports/allure-results` |
| HTML | `reports/report.html` | Open in browser |
| Traces | `reports/traces/*.zip` | `playwright show-trace <file>` |
| Screenshots | `reports/screenshots/` | Open directly |
| Logs | `reports/logs/` | Any text editor |

---

## ⚠️ Limitations & Assumptions

- **Login**: eBay allows guest browsing and adding to cart without login.
  Cart state is stored in cookies per browser session.
- **Currency**: All prices assumed to be USD ($). Parsing handles `$X.XX` and `$X,XXX.XX`.
- **eBay UI changes**: Smart Locators with 2-3 fallbacks per element reduce
  but don't eliminate risk from UI changes. Locators may need updating over time.
- **Variants**: Some items require variant selection (size/color) before Add to Cart.
  The test selects randomly from available options — some combinations may be out of stock.
- **Cart**: Items are added to a guest cart tied to browser cookies.
  Cart persists within a test session but not across sessions.
- **Parallel limits**: Running >4 workers may trigger eBay rate limiting.
  Recommended: `-n 2` or `-n 4`.

---

## 🧪 Adding New Test Scenarios

Edit `data/test_data.json` — no code changes needed:
```json
{
  "scenario_id": "TC_004",
  "description": "Search for keyboard under $80",
  "query": "mechanical keyboard",
  "max_price": 80,
  "limit": 5,
  "budget_per_item": 80
}
```
