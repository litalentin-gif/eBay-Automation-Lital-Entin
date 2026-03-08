"""
conftest.py - pytest Fixtures
==============================
Handles: browser launch, page setup, logging config,
         test teardown with screenshots on failure.
"""

import os
import json
import logging
import pytest
import yaml
from datetime import datetime
from playwright.sync_api import sync_playwright, Browser, Page


# ── Load config ────────────────────────────────────────────────────

def load_config() -> dict:
    with open("config/config.yaml") as f:
        return yaml.safe_load(f)

CONFIG = load_config()


# ── Logging setup ──────────────────────────────────────────────────

def setup_logging(run_id: str):
    os.makedirs("reports/logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f"reports/logs/run_{run_id}.log"),
        ],
    )

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
setup_logging(RUN_ID)
logger = logging.getLogger(__name__)


# ── Data-Driven: load test scenarios ──────────────────────────────

def load_test_data() -> list[dict]:
    with open("data/test_data.json") as f:
        return json.load(f)["test_scenarios"]

TEST_SCENARIOS = load_test_data()


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def playwright_instance():
    """Start one Playwright instance per test session."""
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(params=["chromium", "firefox"], ids=["chrome", "firefox"])
def browser(playwright_instance, request):
    """
    Parametrized: runs each test on multiple browsers.
    Each browser is a fresh, isolated instance (no shared state).
    """
    browser_name = request.param
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    logger.info(f"[conftest] 🌐 Launching {browser_name} (headless={headless})")

    browser_launcher = getattr(playwright_instance, browser_name)
    browser_instance: Browser = browser_launcher.launch(headless=headless)

    yield browser_instance

    browser_instance.close()
    logger.info(f"[conftest] 🔒 Closed {browser_name}")


@pytest.fixture
def page(browser, request) -> Page:
    """
    Each test gets a fresh, isolated browser context + page.
    On test failure → auto screenshot + trace saved.
    """
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        locale="en-US",
    )
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    page_instance = context.new_page()
    page_instance.set_default_timeout(CONFIG["timeouts"]["default"])

    yield page_instance

    # ── Teardown ──────────────────────────────────────────────────
    test_name = request.node.name.replace("/", "_").replace(" ", "_")

    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        # Save failure screenshot
        os.makedirs("reports/screenshots", exist_ok=True)
        path = f"reports/screenshots/FAIL_{test_name}_{RUN_ID}.png"
        page_instance.screenshot(path=path)
        logger.error(f"[conftest] 📸 Failure screenshot: {path}")

    # Save trace
    os.makedirs("reports/traces", exist_ok=True)
    trace_path = f"reports/traces/{test_name}_{RUN_ID}.zip"
    context.tracing.stop(path=trace_path)

    context.close()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to attach test result to request node (used in page fixture above)."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# ── Parametrize test scenarios ─────────────────────────────────────

def pytest_generate_tests(metafunc):
    """
    If a test uses 'scenario' fixture → inject all scenarios from test_data.json.
    This powers Data-Driven testing.
    """
    if "scenario" in metafunc.fixturenames:
        metafunc.parametrize(
            "scenario",
            TEST_SCENARIOS,
            ids=[s["scenario_id"] for s in TEST_SCENARIOS],
        )
