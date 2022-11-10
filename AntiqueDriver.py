import requests
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import AntiqueScoreUtil


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
        chrome_options = Options()
        chrome_options.add_argument("--user-data-dir=selenium")
        self.driver = uc.Chrome(use_subprocess=True, options=chrome_options)
        self.driver.get(AntiqueScoreUtil.url_base)
        WebDriverWait(self.driver, 10).until(EC.title_contains("Unite Api"))

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
