"""
Selenium harness for the ecoStock frontend.

  pytest                      # visible Chrome window, slowed down for a live demo
  pytest --headless           # CI mode
  pytest --delay 1.5          # seconds to pause between visible steps (default 0.9)
  pytest -m blackbox          # only the 5 black-box tests
  pytest -m whitebox          # only the 5 white-box tests

The suite starts the Next.js server itself (building first if needed). To use an
already-running instance set BASE_URL=http://localhost:3000.
"""
import glob
import os
import shutil
import signal
import socket
import subprocess
import time
import urllib.request

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FRONTEND = os.path.join(ROOT, "frontend")
PORT = int(os.environ.get("ECOSTOCK_PORT", "3000"))
BASE_URL = os.environ.get("BASE_URL", f"http://localhost:{PORT}")


def pytest_addoption(parser):
    parser.addoption("--headless", action="store_true", help="run Chrome without a window")
    parser.addoption("--delay", type=float, default=None, help="pause (s) between visible steps")


def _port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _assert_is_ecostock(url):
    """Fail fast if something else (e.g. the FastAPI backend) is answering on the port."""
    try:
        html = urllib.request.urlopen(url, timeout=3).read().decode("utf-8", "replace")
    except Exception as e:
        pytest.exit(f"Nothing usable at {url} ({e}). Free the port or set ECOSTOCK_PORT=<free port>.", returncode=2)
    if 'data-testid="landing-title"' not in html:
        pytest.exit(
            f"{url} is responding, but it is not the ecoStock frontend (another app is using the port). "
            "Stop it, or run with a free port, e.g.  ECOSTOCK_PORT=3100 pytest tests/e2e",
            returncode=2,
        )


@pytest.fixture(scope="session")
def server():
    if "BASE_URL" in os.environ or _port_open(PORT):
        _assert_is_ecostock(BASE_URL)
        yield BASE_URL
        return
    if not os.path.isdir(os.path.join(FRONTEND, "node_modules")):
        subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=FRONTEND, check=True)
    if not os.path.isdir(os.path.join(FRONTEND, ".next")):
        subprocess.run(["npm", "run", "build"], cwd=FRONTEND, check=True)
    proc = subprocess.Popen(["npx", "next", "start", "-p", str(PORT)], cwd=FRONTEND,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)  # own process group so npx + next-server die together
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(BASE_URL, timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("Next.js server did not start")
        yield BASE_URL
    finally:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)


def _chrome_binary():
    if os.environ.get("CHROME_BIN"):
        return os.environ["CHROME_BIN"]
    found = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return found[-1] if found and not shutil.which("google-chrome") and not shutil.which("chrome") else None


class Browser:
    """Thin wrapper adding demo pacing + element highlighting on top of WebDriver."""

    def __init__(self, driver, delay, base):
        self.d, self.delay, self.base = driver, delay, base
        self.wait = WebDriverWait(driver, 10)

    def pause(self, factor=1.0):
        time.sleep(self.delay * factor)

    def open(self, path="/"):
        self.d.get(self.base + path)
        self.wait.until(lambda d: d.execute_script("return !!window.__ECOSTOCK__ || document.querySelector('[data-testid=landing-title]') !== null"))
        self.pause()

    def tid(self, testid, timeout=10):
        return WebDriverWait(self.d, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-testid="{testid}"]')))

    def all(self, testid):
        return self.d.find_elements(By.CSS_SELECTOR, f'[data-testid="{testid}"]')

    def highlight(self, el):
        if self.delay:
            self.d.execute_script("arguments[0].scrollIntoView({block:'center'});arguments[0].style.outline='3px solid #f59e0b';arguments[0].style.outlineOffset='2px';", el)

    def click(self, testid):
        el = WebDriverWait(self.d, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'[data-testid="{testid}"]')))
        self.highlight(el)
        self.pause(0.5)
        el.click()
        self.pause(0.5)

    def type(self, testid, text):
        el = self.tid(testid)
        self.highlight(el)
        el.clear()
        el.send_keys(text)
        self.pause(0.5)

    def select(self, testid, value):
        from selenium.webdriver.support.ui import Select
        el = self.tid(testid)
        self.highlight(el)
        Select(el).select_by_value(str(value))
        self.pause(0.5)

    def state(self):
        return self.d.execute_script("return JSON.parse(JSON.stringify(window.__ECOSTOCK__.state))")

    def logic(self, expr, *args):
        """Evaluate a function from lib/logic.js in the page, e.g. logic('fefoSort', batches)."""
        return self.d.execute_script(f"return window.__ECOSTOCK__.logic.{expr}(...arguments)", *args)

    def text(self, testid):
        return self.tid(testid).text

    def cells(self, table_testid, col):
        return [c.text for c in self.d.find_elements(By.CSS_SELECTOR, f'[data-testid="{table_testid}"] tbody td[data-col="{col}"]')]


@pytest.fixture
def b(request, server):
    headless = request.config.getoption("--headless")
    delay = request.config.getoption("--delay")
    if delay is None:
        delay = 0 if headless else 0.9
    opts = webdriver.ChromeOptions()
    binary = _chrome_binary()
    if binary:
        opts.binary_location = binary
    opts.add_argument("--window-size=1400,950")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    if headless:
        opts.add_argument("--headless=new")
    driver_path = os.environ.get("CHROMEDRIVER_PATH")
    if driver_path:  # pinned driver; tolerate minor browser/driver skew
        service = Service(driver_path, service_args=["--disable-build-check"])
        driver = webdriver.Chrome(service=service, options=opts)
    else:  # Selenium Manager downloads the matching driver automatically
        driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(0)
    yield Browser(driver, delay, server)
    driver.quit()
