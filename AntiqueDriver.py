import logging
import os
import platform
import re
import subprocess
from time import sleep
from typing import Optional

import requests
import undetected_chromedriver as uc
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException
from undetected_chromedriver import ChromeOptions

# 配置常量
DETECTION_KEY = "UniteApi"
DATA_DIR = "../underwear_uc"
URL_BASE = "https://uniteapi.dev/"

# 超时和重试配置
IMPLICIT_WAIT_TIMEOUT = 5
PAGE_LOAD_TIMEOUT = 10
SLEEP_AFTER_LOAD = 5
MAX_RETRIES = 2

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_chrome_version() -> Optional[str]:
    """
    检测本地 Chrome 浏览器版本号
    macOS: 优先读取 Info.plist，失败则执行 --version
    Linux/Windows: 执行 --version
    失败返回 None
    """
    system = platform.system()

    # macOS: 优先从 Info.plist 读取（无需启动浏览器）
    if system == "Darwin":
        plist_path = "/Applications/Google Chrome.app/Contents/Info.plist"
        if os.path.exists(plist_path):
            try:
                result = subprocess.run(
                    ["/usr/libexec/PlistBuddy", "-c", "Print :CFBundleShortVersionString", plist_path],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0 and result.stdout.strip():
                    version = result.stdout.strip()
                    if re.match(r"\d+\.\d+\.\d+\.\d+", version):
                        logger.info(f"检测到 Chrome 版本: {version}")
                        return version
            except:
                pass  # 失败则尝试下一种方法

    # 回退：执行浏览器 --version
    if system == "Darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]
    elif system == "Linux":
        candidates = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]
    elif system == "Windows":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    else:
        candidates = []

    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode == 0:
                match = re.search(r"(\d+\.\d+\.\d+\.\d+)", result.stdout)
                if match:
                    version = match.group(1)
                    logger.info(f"检测到 Chrome 版本: {version}")
                    return version
        except:
            continue

    logger.warning("无法检测 Chrome 版本，将使用默认值")
    return None


def build_user_agent(chrome_version: Optional[str] = None) -> str:
    """
    构建 User Agent 字符串
    
    Args:
        chrome_version: Chrome 版本号，如果为 None 则自动检测
        
    Returns:
        完整的 User Agent 字符串
    """
    if chrome_version is None:
        chrome_version = get_chrome_version()
    
    # 如果还是获取不到，使用一个合理的默认值
    if chrome_version is None:
        chrome_version = "131.0.0.0"
        logger.info(f"使用默认 Chrome 版本: {chrome_version}")
    
    user_agent = (
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{chrome_version} Safari/537.36"
    )
    return user_agent


class AntiqueDriver:
    """
    使用 undetected_chromedriver 绕过 Cloudflare 保护的驱动类
    通过 Selenium 获取 cookies 后创建 requests.Session 进行 API 调用
    """

    def __init__(self):
        self.driver: Optional[uc.Chrome] = None
        self.session: Optional[requests.Session] = None

    def updateDriver(self) -> None:
        """初始化或更新 Chrome 驱动"""
        if self.driver is not None:
            self.quitDriver()

        try:
            options = ChromeOptions()
            
            # 使用绝对路径作为 user data dir，避免路径问题
            abs_data_dir = os.path.abspath(DATA_DIR)
            os.makedirs(abs_data_dir, exist_ok=True)
            options.add_argument(f"--user-data-dir={abs_data_dir}")
            
            # 使用新的 headless 模式，更接近有头模式的行为
            options.add_argument("--headless=new")
            
            # 容器和无图形界面环境必需的选项
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-software-rasterizer")
            
            # Linux 服务器额外需要的选项
            if platform.system() == "Linux":
                options.add_argument("--disable-setuid-sandbox")
                options.add_argument("--single-process")  # 避免多进程问题
                options.add_argument("--disable-features=VizDisplayCompositor")
                logger.info("检测到 Linux 环境，应用额外配置")
            
            # 性能和稳定性优化
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-infobars")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--remote-debugging-port=0")
            
            # 禁用 blink 特性以减少检测
            options.add_argument("--disable-blink-features=AutomationControlled")
            
            # 自动构建 User Agent 以隐藏 HeadlessChrome 特征
            # 在 headless 模式下，默认 UA 会包含 "HeadlessChrome"，容易被 Cloudflare 检测
            user_agent = build_user_agent()
            options.add_argument(f"--user-agent={user_agent}")
            logger.info(f"设置 User Agent: {user_agent}")

            logger.info(f"正在初始化 Chrome 驱动 (系统: {platform.system()})...")
            self.driver = uc.Chrome(options=options, use_subprocess=False)
            self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            logger.info("驱动创建成功")
            
            # 验证 User Agent（用于日志）
            try:
                actual_ua = self.driver.execute_script("return navigator.userAgent;")
                logger.info(f"实际 User Agent: {actual_ua}")
            except Exception as e:
                logger.warning(f"无法获取 User Agent: {e}")
            
            # 访问目标网站
            logger.info(f"正在访问 {URL_BASE}")
            self.driver.get(URL_BASE)
            logger.info("页面加载完成")
            
            # 打开新标签页（某些情况下有助于绕过检测）
            try:
                self.driver.execute_script(f"""window.open('{URL_BASE}');""")
                logger.debug("新标签页已打开")
            except Exception as e:
                logger.warning(f"打开新标签页失败: {e}")
            
            self.driver.implicitly_wait(IMPLICIT_WAIT_TIMEOUT)
            sleep(SLEEP_AFTER_LOAD)
            
            # 刷新页面
            logger.info("刷新页面...")
            self.driver.refresh()
            
            # 等待页面标题包含检测关键字
            logger.info(f"等待页面标题包含 '{DETECTION_KEY}'...")
            WebDriverWait(self.driver, PAGE_LOAD_TIMEOUT).until(
                EC.title_contains(DETECTION_KEY)
            )
            logger.info("✅ Chrome 驱动初始化成功，成功绕过 Cloudflare")

        except TimeoutException:
            current_title = "无法获取"
            current_url = "无法获取"
            try:
                current_title = self.driver.title
                current_url = self.driver.current_url
            except:
                pass
            logger.error(f"❌ 超时：页面标题未包含 '{DETECTION_KEY}'")
            logger.error(f"   当前标题: {current_title}")
            logger.error(f"   当前 URL: {current_url}")
            logger.error(f"   这可能是因为：")
            logger.error(f"   1. Cloudflare 检测到了自动化工具")
            logger.error(f"   2. 网络连接问题")
            logger.error(f"   3. Linux 服务器缺少必要的系统依赖")
            self.quitDriver()
            raise
        except WebDriverException as e:
            logger.error(f"❌ WebDriver 错误: {e}")
            logger.error(f"   可能原因：")
            logger.error(f"   1. Chrome/Chromium 未正确安装")
            logger.error(f"   2. 缺少系统依赖库")
            logger.error(f"   Linux 服务器请确保安装: apt-get install -y chromium-browser chromium-chromedriver")
            self.quitDriver()
            raise
        except Exception as e:
            logger.error(f"❌ 初始化驱动时发生未知错误: {e}")
            logger.error(f"   错误类型: {type(e).__name__}")
            self.quitDriver()
            raise

    def updateSession(self) -> None:
        """从 Selenium 驱动创建 requests.Session"""
        if self.session:
            logger.debug("Session 已存在，跳过创建")
            return

        try:
            if not self.driver:
                logger.info("驱动不存在，先初始化驱动")
                self.updateDriver()

            _session = requests.Session()
            
            # 获取并设置 User Agent
            selenium_user_agent = self.driver.execute_script("return navigator.userAgent;")
            _session.headers.update({"user-agent": selenium_user_agent})
            
            # 复制 cookies
            cookie_count = 0
            for cookie in self.driver.get_cookies():
                _session.cookies.set(
                    cookie["name"], 
                    cookie["value"], 
                    domain=cookie["domain"]
                )
                cookie_count += 1
            
            self.session = _session
            logger.info(f"Session 创建成功，复制了 {cookie_count} 个 cookies")
            
            # 关闭驱动以节省资源
            self.quitDriver()

        except Exception as e:
            logger.error(f"创建 Session 时发生错误: {e}")
            self.quitDriver()
            raise

    def get(self, url: str) -> Optional[requests.Response]:
        """
        使用 Session 发送 GET 请求，失败时自动重试
        
        Args:
            url: 目标 URL
            
        Returns:
            requests.Response 或 None（失败时）
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(f"尝试第 {attempt} 次请求: {url}")
                self.updateSession()
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    logger.debug(f"请求成功: {url}")
                    return response
                else:
                    logger.warning(
                        f"请求返回状态码 {response.status_code}: {url}"
                    )
                    # 如果是 403/429，可能是 session 过期，重置 session
                    if response.status_code in [403, 429]:
                        logger.info("Session 可能过期，重置 session")
                        self.session = None
                        
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常 (尝试 {attempt}/{MAX_RETRIES}): {e}")
                self.session = None
            except Exception as e:
                logger.error(f"未知错误 (尝试 {attempt}/{MAX_RETRIES}): {e}")
                self.session = None

        logger.error(f"请求失败，已达最大重试次数: {url}")
        return None

    def quitDriver(self) -> None:
        """安全地关闭驱动"""
        if self.driver:
            try:
                self.driver.quit()
                logger.debug("驱动已关闭")
            except Exception as e:
                logger.warning(f"关闭驱动时发生错误: {e}")
            finally:
                self.driver = None
    def close(self) -> None:
        """清理所有资源"""
        self.quitDriver()
        if self.session:
            self.session.close()
            self.session = None
        logger.info("所有资源已清理")

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出时自动清理资源"""
        self.close()

    def __del__(self):
        """析构时确保资源清理"""
        try:
            self.close()
        except:
            pass

