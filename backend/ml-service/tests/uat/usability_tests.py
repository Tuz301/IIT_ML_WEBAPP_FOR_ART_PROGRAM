"""
Usability Testing Framework for IIT ML Service
"""
import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class UsabilityMetric:
    """Represents a usability testing metric"""
    task_name: str
    completion_time: float
    success: bool
    errors: int
    user_feedback: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class UsabilityTester:
    """Automated usability testing framework"""

    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.driver = None
        self.metrics: List[UsabilityMetric] = []
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        """Initialize WebDriver with accessibility testing capabilities"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Run in headless mode for CI
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        # Enable accessibility testing
        options.add_experimental_option("w3c", True)

        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)

    def teardown_driver(self):
        """Clean up WebDriver"""
        if self.driver:
            self.driver.quit()

    def measure_task_completion(self, task_name: str, task_function) -> UsabilityMetric:
        """Measure time and success of a task"""
        start_time = time.time()
        errors = 0
        success = False

        try:
            success = task_function()
        except Exception as e:
            self.logger.error(f"Task {task_name} failed: {e}")
            errors += 1

        completion_time = time.time() - start_time

        metric = UsabilityMetric(
            task_name=task_name,
            completion_time=completion_time,
            success=success,
            errors=errors
        )

        self.metrics.append(metric)
        return metric

    def test_login_workflow(self) -> bool:
        """Test user login workflow"""
        try:
            self.driver.get(f"{self.base_url}/login")

            # Wait for login form
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )

            password_field = self.driver.find_element(By.ID, "password")
            login_button = self.driver.find_element(By.ID, "login-button")

            # Test keyboard navigation
            username_field.send_keys("test_user")
            username_field.send_keys(Keys.TAB)
            assert self.driver.switch_to.active_element == password_field

            password_field.send_keys("test_password")
            password_field.send_keys(Keys.TAB)
            assert self.driver.switch_to.active_element == login_button

            # Submit login
            login_button.click()

            # Wait for dashboard or error
            WebDriverWait(self.driver, 10).until(
                lambda driver: "dashboard" in driver.current_url or
                              driver.find_elements(By.CLASS_NAME, "error-message")
            )

            return "dashboard" in self.driver.current_url

        except Exception as e:
            self.logger.error(f"Login test failed: {e}")
            return False

    def test_patient_search_workflow(self) -> bool:
        """Test patient search and selection workflow"""
        try:
            # Navigate to patient list
            self.driver.get(f"{self.base_url}/patients")

            # Wait for patient list to load
            patient_list = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "patient-list"))
            )

            # Test search functionality
            search_box = self.driver.find_element(By.ID, "patient-search")
            search_box.send_keys("John Doe")
            search_box.send_keys(Keys.ENTER)

            # Wait for search results
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "patient-card"))
            )

            # Test patient selection
            patient_cards = self.driver.find_elements(By.CLASS_NAME, "patient-card")
            if patient_cards:
                patient_cards[0].click()

                # Wait for patient detail view
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "patient-detail"))
                )

                return True

            return False

        except Exception as e:
            self.logger.error(f"Patient search test failed: {e}")
            return False

    def test_prediction_workflow(self) -> bool:
        """Test risk prediction workflow"""
        try:
            # Navigate to prediction form
            self.driver.get(f"{self.base_url}/predict")

            # Wait for form to load
            form = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "prediction-form"))
            )

            # Fill out prediction form (simplified)
            age_field = self.driver.find_element(By.ID, "age")
            age_field.send_keys("45")

            # Submit prediction
            submit_button = self.driver.find_element(By.ID, "submit-prediction")
            submit_button.click()

            # Wait for results
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "prediction-result"))
            )

            # Verify prediction result elements
            risk_score = self.driver.find_element(By.CLASS_NAME, "risk-score")
            confidence = self.driver.find_element(By.CLASS_NAME, "confidence-score")

            return risk_score.is_displayed() and confidence.is_displayed()

        except Exception as e:
            self.logger.error(f"Prediction workflow test failed: {e}")
            return False

    def test_keyboard_navigation(self) -> bool:
        """Test keyboard accessibility"""
        try:
            self.driver.get(f"{self.base_url}/dashboard")

            # Get all focusable elements
            focusable_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                'a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
            )

            if not focusable_elements:
                return False

            # Test tab navigation
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.TAB)

            for i in range(min(10, len(focusable_elements))):
                active_element = self.driver.switch_to.active_element
                if active_element not in focusable_elements:
                    self.logger.warning(f"Unexpected element focused: {active_element.tag_name}")
                    return False
                active_element.send_keys(Keys.TAB)

            return True

        except Exception as e:
            self.logger.error(f"Keyboard navigation test failed: {e}")
            return False

    def test_responsive_design(self) -> bool:
        """Test responsive design across different screen sizes"""
        screen_sizes = [
            (1920, 1080),  # Desktop
            (1366, 768),   # Laptop
            (768, 1024),   # Tablet
            (375, 667)     # Mobile
        ]

        results = []

        for width, height in screen_sizes:
            try:
                self.driver.set_window_size(width, height)
                time.sleep(1)  # Allow time for responsive changes

                # Check if critical elements are visible
                nav = self.driver.find_elements(By.CLASS_NAME, "navigation")
                content = self.driver.find_elements(By.CLASS_NAME, "main-content")

                results.append(bool(nav and content))

            except Exception as e:
                self.logger.error(f"Responsive test failed for {width}x{height}: {e}")
                results.append(False)

        return all(results)

    def run_usability_test_suite(self) -> Dict:
        """Run complete usability test suite"""
        self.setup_driver()

        try:
            # Run all usability tests
            tests = [
                ("login_workflow", self.test_login_workflow),
                ("patient_search", self.test_patient_search_workflow),
                ("prediction_workflow", self.test_prediction_workflow),
                ("keyboard_navigation", self.test_keyboard_navigation),
                ("responsive_design", self.test_responsive_design)
            ]

            results = {}
            for test_name, test_func in tests:
                metric = self.measure_task_completion(test_name, test_func)
                results[test_name] = {
                    "success": metric.success,
                    "completion_time": metric.completion_time,
                    "errors": metric.errors
                }

            return {
                "test_results": results,
                "overall_success_rate": sum(1 for r in results.values() if r["success"]) / len(results),
                "average_completion_time": sum(r["completion_time"] for r in results.values()) / len(results),
                "total_errors": sum(r["errors"] for r in results.values())
            }

        finally:
            self.teardown_driver()

    def generate_report(self, results: Dict) -> str:
        """Generate usability testing report"""
        report = f"""
# Usability Testing Report
Generated: {datetime.now()}

## Summary
- Overall Success Rate: {results['overall_success_rate']:.1%}
- Average Completion Time: {results['average_completion_time']:.2f}s
- Total Errors: {results['total_errors']}

## Detailed Results
"""

        for test_name, result in results['test_results'].items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            report += f"""
### {test_name.replace('_', ' ').title()}
- Status: {status}
- Completion Time: {result['completion_time']:.2f}s
- Errors: {result['errors']}
"""

        return report


# Pytest fixtures and test cases
@pytest.fixture
def usability_tester():
    tester = UsabilityTester()
    yield tester
    tester.teardown_driver()


@pytest.mark.usability
def test_login_usability(usability_tester):
    """Test login workflow usability"""
    usability_tester.setup_driver()
    metric = usability_tester.measure_task_completion(
        "login_workflow",
        usability_tester.test_login_workflow
    )

    assert metric.success, f"Login workflow failed with {metric.errors} errors"
    assert metric.completion_time < 30, f"Login took too long: {metric.completion_time}s"


@pytest.mark.usability
def test_patient_search_usability(usability_tester):
    """Test patient search workflow usability"""
    usability_tester.setup_driver()
    metric = usability_tester.measure_task_completion(
        "patient_search",
        usability_tester.test_patient_search_workflow
    )

    assert metric.success, f"Patient search failed with {metric.errors} errors"
    assert metric.completion_time < 20, f"Patient search took too long: {metric.completion_time}s"


@pytest.mark.usability
def test_prediction_usability(usability_tester):
    """Test prediction workflow usability"""
    usability_tester.setup_driver()
    metric = usability_tester.measure_task_completion(
        "prediction_workflow",
        usability_tester.test_prediction_workflow
    )

    assert metric.success, f"Prediction workflow failed with {metric.errors} errors"
    assert metric.completion_time < 15, f"Prediction took too long: {metric.completion_time}s"


@pytest.mark.accessibility
def test_keyboard_navigation(usability_tester):
    """Test keyboard navigation accessibility"""
    usability_tester.setup_driver()
    success = usability_tester.test_keyboard_navigation()
    assert success, "Keyboard navigation test failed"


@pytest.mark.accessibility
def test_responsive_design(usability_tester):
    """Test responsive design across screen sizes"""
    usability_tester.setup_driver()
    success = usability_tester.test_responsive_design()
    assert success, "Responsive design test failed"


if __name__ == "__main__":
    # Run usability tests manually
    tester = UsabilityTester()
    results = tester.run_usability_test_suite()
    report = tester.generate_report(results)

    print(report)

    # Save report to file
    with open("usability_test_report.md", "w") as f:
        f.write(report)
