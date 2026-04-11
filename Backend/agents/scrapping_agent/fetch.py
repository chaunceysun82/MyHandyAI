from playwright.async_api import async_playwright
from utils import normalize_url

async def fetch_html(url: str, timeout_ms: int = 45000) -> tuple[str, int | None, str]:
    url = normalize_url(url)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            locale="en-US",
            timezone_id="America/Detroit",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = await context.new_page()
        resp = await page.goto(url, wait_until="networkidle", timeout=timeout_ms)

        await page.wait_for_timeout(600)
        await page.mouse.wheel(0, 1200)
        await page.wait_for_timeout(600)

        try:
            await page.wait_for_selector("h1", timeout=8000)
        except Exception:
            pass

        html = await page.content()
        status = resp.status if resp else None
        final_url = page.url

        await context.close()
        await browser.close()
        return html, status, final_url