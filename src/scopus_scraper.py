from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
import json
import os
import traceback
from typing import Dict, Optional, Tuple

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ScopusScraper:
    def __init__(self):
        self.driver = None

    def setup_driver(self) -> None:
        """Set up Chrome driver with stealth settings"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Initialize the driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

        # Apply stealth settings
        stealth(
            self.driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    def wait_and_get_element(self, selector: str, timeout: int = 10) -> Optional[str]:
        """Wait for an element to be present and return its text"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element.text.strip()
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {selector}")
            return None
        except Exception as e:
            logger.error(f"Error getting element {selector}: {str(e)}")
            return None

    def extract_metrics(self) -> Tuple[Optional[int], Optional[int]]:
        """Extract h-index and citation count from the page"""
        try:
            # Try multiple selectors to find the metrics
            selectors = {
                "h_index": [
                    '[data-testid="metrics-section-h-index"] .Typography-module__ix7bs',
                    ".highcharts-metrics h-index",
                    "#metrics-section-h-index",
                    ".author-metrics .h-index",
                ],
                "citations": [
                    '[data-testid="metrics-section-citations-count"] .Typography-module__ix7bs',
                    ".highcharts-metrics citations",
                    "#metrics-section-citations-count",
                    ".author-metrics .citation-count",
                ],
            }

            h_index = None
            citations = None

            # Try each selector for h-index
            for selector in selectors["h_index"]:
                value = self.wait_and_get_element(selector)
                if value:
                    try:
                        h_index = int(value.replace(",", ""))
                        logger.info(
                            f"Found h-index: {h_index} using selector: {selector}"
                        )
                        break
                    except ValueError:
                        continue

            # Try each selector for citations
            for selector in selectors["citations"]:
                value = self.wait_and_get_element(selector)
                if value:
                    try:
                        citations = int(value.replace(",", ""))
                        logger.info(
                            f"Found citations: {citations} using selector: {selector}"
                        )
                        break
                    except ValueError:
                        continue

            return h_index, citations

        except Exception as e:
            logger.error(f"Error extracting metrics: {str(e)}")
            logger.error(traceback.format_exc())
            return None, None

    def scrape_author(self, author_id: str, max_retries: int = 3) -> Dict:
        """
        Scrape author metrics from Scopus with retry mechanism
        """
        for attempt in range(max_retries):
            try:
                if self.driver is None:
                    self.setup_driver()

                url = f"https://www.scopus.com/authid/detail.uri?authorId={author_id}"
                logger.info(
                    f"Accessing URL: {url} (Attempt {attempt + 1}/{max_retries})"
                )

                # Load the page
                self.driver.get(url)

                # Wait for page to load and potential protection to clear
                time.sleep(5)

                # Get the page source for debugging
                if os.getenv("DEBUG"):
                    with open(
                        f"page_source_{attempt}.html", "w", encoding="utf-8"
                    ) as f:
                        f.write(self.driver.page_source)

                # Extract metrics
                h_index, citations = self.extract_metrics()

                if h_index is not None or citations is not None:
                    logger.info(
                        f"Successfully scraped metrics - H-index: {h_index}, Citations: {citations}"
                    )
                    return {
                        "status": "success",
                        "h_index": h_index,
                        "citations": citations,
                    }

                logger.warning(f"Attempt {attempt + 1} failed to find metrics")
                time.sleep(5)  # Wait before retry

            except Exception as e:
                logger.error(f"Error during attempt {attempt + 1}: {str(e)}")
                logger.error(traceback.format_exc())
                time.sleep(5)  # Wait before retry

            finally:
                if attempt == max_retries - 1 and self.driver:
                    self.driver.quit()
                    self.driver = None

        return {
            "status": "error",
            "message": f"Failed to extract metrics after {max_retries} attempts",
            "h_index": None,
            "citations": None,
        }


def main():
    author_id = "8303001500" 
    scraper = ScopusScraper()
    result = scraper.scrape_author(author_id)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
