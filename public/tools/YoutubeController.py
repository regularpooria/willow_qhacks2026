from typing import Optional, Any

try:
	from playwright.sync_api import sync_playwright, Page, Browser
except Exception:
	# If Playwright isn't installed in the environment, keep module importable
	sync_playwright = None
	Page = Any
	Browser = Any

class PlaywrightController:
	"""Simple sync Playwright controller.

	Usage: call `start()` to launch a browser, then use `page`.
	Keep a single browser/page instance for sequential tool calls.
	"""

	def __init__(self):
		self._playwright = None
		self._context = None  # Add this
		self.browser: Optional[Browser] = None
		self.page: Optional[Page] = None

	def start(self, headless: bool = True) -> None:
		if sync_playwright is None:
			raise RuntimeError("playwright is not installed in this environment")
		if self._playwright is None:
			self._playwright = sync_playwright().start()
		if self.browser is None:
			self.browser = self._playwright.chromium.launch(headless=headless)
			self._context = self.browser.new_context()
			self.page = self._context.new_page()
        # If browser already running, reuse existing page — don't create a new one!

	def stop(self) -> None:
		if self.browser:
			try:
				self.browser.close()
			finally:
				self.browser = None
		if self._playwright:
			try:
				self._playwright.stop()
			finally:
				self._playwright = None
				self.page = None