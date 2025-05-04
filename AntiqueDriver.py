from time import sleep

import requests
import undetected_chromedriver as uc
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from undetected_chromedriver import ChromeOptions

DETECTION_KEY = "UniteApi"
DATA_DIR = "underwear_uc"
url_base = "https://uniteapi.dev/"


# url_base = "https://uniteapi.dev/"
# chrome_options = Options()
# chrome_options.add_argument("--user-data-dir=selenium")
# driver = uc.Chrome(use_subprocess=True, options=chrome_options)
# driver.get(url_base)
# # Bypass Cloudflare DDoS protection 5s wait
# WebDriverWait(driver, 10).until(EC.title_contains("Unite Api"))

class AntiqueDriver:
    def __init__(self):
        self.driver = None
        self.session = None

    def updateDriver(self):
        if self.driver is not None:
            self.quitDriver()
        options = ChromeOptions()
        options.add_argument(f"--user-data-dir={DATA_DIR}")
        # Use the newer headless mode which is closer to headful behavior
        options.add_argument("--headless=new")
        # Required for container or root environments
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # Optional: disable GPU
        options.add_argument("--disable-gpu")
        # Allow ChromeDriver to attach
        options.add_argument("--remote-debugging-port=0")
        # Set a realistic user agent to avoid detection
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.7103.59 Safari/537.36"
        )
        self.driver = uc.Chrome(options=options, use_subprocess=False)
        self.driver.get(url_base)
        self.driver.execute_script("""window.open('{0}', "_blank");""".format(url_base))
        self.driver.implicitly_wait(5)
        sleep(5)
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(EC.title_contains(DETECTION_KEY))

    def updateSession(self):
        if self.session:
            return
        if not self.driver:
            self.updateDriver()
        _session = requests.Session()
        selenium_user_agent = self.driver.execute_script("return navigator.userAgent;")
        _session.headers.update({"user-agent": selenium_user_agent})
        for cookie in self.driver.get_cookies():
            _session.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])
        self.session = _session
        self.quitDriver()

    # def loading(self):
    #     self.driver.get(AntiqueScoreUtil.url_base)
    #     # Bypass Cloudflare DDoS protection 5s wait
    #
    #     cookies = []
    #     for cookie in self.driver.get_cookies():
    #         cookies.append(cookie["name"] + '=' + cookie["value"])
    #     with open('cookie.txt', 'w') as f:
    #         f.write("; ".join(cookies))

    def get(self, url):
        for i in range(2):
            self.updateSession()
            response = self.session.get(url)
            if response.status_code == 200:
                return response
            self.session = None
        return None

    def quitDriver(self):
        self.driver.quit()
        self.driver = None
