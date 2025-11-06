"""
内嵌浏览器组件模块

支持多种内嵌浏览器实现：
1. CEF Python (推荐) - 完整的 Chromium 浏览器
2. tkinterhtml - 轻量级 HTML 渲染
3. pywebview - 降级方案（独立窗口）
"""

import logging
import threading
import sys

# 检查 CEF Python 可用性，包括 Python 版本兼容性
CEF_AVAILABLE = False
cef = None
try:
    # 检查 Python 版本是否支持 CEF
    python_version = sys.version_info
    if python_version.major == 3 and python_version.minor <= 12:
        # CEF Python 支持 Python 3.8-3.12
        try:
            from cefpython3 import cefpython as cef

            CEF_AVAILABLE = True
            logging.info("CEF Python 可用")
        except ImportError:
            logging.info("CEF Python 未安装")
        except Exception as e:
            logging.warning(f"CEF Python 初始化失败: {e}")
    else:
        logging.info(f"Python {python_version.major}.{python_version.minor} 不支持 CEF Python（需要 3.8-3.12）")
except Exception as e:
    logging.error(f"检查 CEF Python 可用性时发生错误: {e}")

# 检查 TkinterHTML 可用性
TKINTERHTML_AVAILABLE = False
try:
    import importlib.util

    if importlib.util.find_spec("tkinterhtml"):
        TKINTERHTML_AVAILABLE = True
except (ImportError, AttributeError):
    pass

try:
    import webview

    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False
    webview = None


class EmbeddedBrowser:
    """内嵌浏览器组件基类"""

    def __init__(self, parent_frame, url: str, width: int = 800, height: int = 600):
        self.parent_frame = parent_frame
        self.url = url
        self.width = width
        self.height = height
        self.browser = None

    def create_browser(self):
        """创建浏览器实例"""
        raise NotImplementedError

    def navigate(self, url: str):
        """导航到指定URL"""
        raise NotImplementedError

    def destroy(self):
        """销毁浏览器"""
        raise NotImplementedError


class CEFBrowser(EmbeddedBrowser):
    """CEF Python 内嵌浏览器"""

    def __init__(self, parent_frame, url: str, width: int = 800, height: int = 600):
        super().__init__(parent_frame, url, width, height)
        self.cef_initialized = False

    def create_browser(self):
        """创建 CEF 浏览器"""
        if not CEF_AVAILABLE:
            return False

        try:
            # 初始化 CEF（只需要一次）
            if not self.cef_initialized:
                self._initialize_cef()
                self.cef_initialized = True

            # 获取父窗口句柄
            window_handle = self._get_window_handle()
            if not window_handle:
                logging.error("无法获取父窗口句柄")
                return False

            # CEF 浏览器设置
            browser_settings = {
                "plugins": False,
                "universal_access_from_file_urls": True,
                "file_access_from_file_urls": True,
                "web_security": False,
            }

            window_info = cef.WindowInfo()
            window_info.SetAsChild(window_handle, [0, 0, self.width, self.height])

            # 创建浏览器
            self.browser = cef.CreateBrowserSync(window_info=window_info, url=self.url, settings=browser_settings)

            logging.info(f"CEF 浏览器创建成功: {self.url}")
            return True

        except Exception as e:
            logging.error(f"创建 CEF 浏览器失败: {e}")
            return False

    def _initialize_cef(self):
        """初始化 CEF"""
        try:
            # CEF 设置
            settings = {
                "debug": False,
                "log_severity": cef.LOGSEVERITY_ERROR,
                "log_file": "",
                "multi_threaded_message_loop": False,
            }

            # 初始化 CEF
            cef.Initialize(settings)

            # 启动消息循环线程
            self.message_loop_thread = threading.Thread(target=self._cef_message_loop, daemon=True)
            self.message_loop_thread.start()

            logging.info("CEF 初始化成功")

        except Exception as e:
            logging.error(f"CEF 初始化失败: {e}")
            raise

    def _cef_message_loop(self):
        """CEF 消息循环"""
        try:
            cef.MessageLoop()
        except Exception as e:
            logging.error(f"CEF 消息循环错误: {e}")

    def _get_window_handle(self):
        """获取父窗口句柄"""
        try:
            # 尝试获取窗口句柄
            if hasattr(self.parent_frame, "winfo_id"):
                return self.parent_frame.winfo_id()
            return None
        except Exception as e:
            logging.error(f"获取窗口句柄失败: {e}")
            return None

    def navigate(self, url: str):
        """导航到指定URL"""
        if self.browser:
            try:
                self.browser.LoadUrl(url)
            except Exception as e:
                logging.error(f"导航失败: {e}")

    def destroy(self):
        """销毁 CEF 浏览器"""
        if self.browser:
            try:
                self.browser.CloseBrowser(True)
                self.browser = None
            except Exception as e:
                logging.error(f"关闭 CEF 浏览器失败: {e}")


class TkinterHtmlBrowser(EmbeddedBrowser):
    """TkinterHTML 轻量级浏览器"""

    def __init__(self, parent_frame, url: str, width: int = 800, height: int = 600):
        super().__init__(parent_frame, url, width, height)
        self.html_widget = None

    def create_browser(self):
        """创建 TkinterHTML 浏览器"""
        if not TKINTERHTML_AVAILABLE:
            return False

        try:
            import tkinterhtml as tkhtml

            # 创建 HTML 组件
            self.html_widget = tkhtml.HtmlFrame(
                self.parent_frame, horizontal_scrollbar="auto", vertical_scrollbar="auto"
            )
            self.html_widget.pack(fill="both", expand=True)

            # 加载 URL
            self.html_widget.load_url(self.url)

            logging.info(f"TkinterHTML 浏览器创建成功: {self.url}")
            return True

        except Exception as e:
            logging.error(f"创建 TkinterHTML 浏览器失败: {e}")
            return False

    def navigate(self, url: str):
        """导航到指定URL"""
        if self.html_widget:
            try:
                self.html_widget.load_url(url)
            except Exception as e:
                logging.error(f"导航失败: {e}")

    def destroy(self):
        """销毁浏览器"""
        if self.html_widget:
            try:
                self.html_widget.destroy()
                self.html_widget = None
            except Exception as e:
                logging.error(f"销毁 TkinterHTML 浏览器失败: {e}")


class WebViewBrowser(EmbeddedBrowser):
    """pywebview 降级方案（独立窗口）"""

    def __init__(self, parent_frame, url: str, width: int = 800, height: int = 600):
        super().__init__(parent_frame, url, width, height)
        self.window = None

    def create_browser(self):
        """创建 WebView（独立窗口）"""
        # 这个方法不会真正嵌入，只是准备
        return WEBVIEW_AVAILABLE

    def launch_standalone_window(self):
        """启动独立窗口"""
        if not WEBVIEW_AVAILABLE:
            return False

        try:
            webview.create_window(
                title="管理看板",
                url=self.url,
                width=self.width,
                height=self.height,
                resizable=True,
                shadow=True,
                on_top=False,
            )
            webview.start()
            return True
        except Exception as e:
            logging.error(f"启动 WebView 窗口失败: {e}")
            return False

    def navigate(self, url: str):
        """导航到指定URL"""
        self.url = url

    def destroy(self):
        """销毁浏览器"""
        pass


def create_embedded_browser(parent_frame, url: str, width: int = 800, height: int = 600) -> EmbeddedBrowser:
    """
    创建内嵌浏览器的工厂函数

    优先级：
    1. CEF Python (最完整)
    2. TkinterHTML (轻量级)
    3. WebView (降级方案)
    """

    # 尝试 CEF Python
    if CEF_AVAILABLE:
        logging.info("使用 CEF Python 创建内嵌浏览器")
        return CEFBrowser(parent_frame, url, width, height)

    # 尝试 TkinterHTML
    elif TKINTERHTML_AVAILABLE:
        logging.info("使用 TkinterHTML 创建内嵌浏览器")
        return TkinterHtmlBrowser(parent_frame, url, width, height)

    # 降级到 WebView
    else:
        logging.info("使用 WebView 创建降级方案")
        return WebViewBrowser(parent_frame, url, width, height)


def get_browser_capabilities():
    """获取浏览器能力信息"""
    return {
        "cef_available": CEF_AVAILABLE,
        "tkinterhtml_available": TKINTERHTML_AVAILABLE,
        "webview_available": WEBVIEW_AVAILABLE,
        "recommended": "cefpython3" if CEF_AVAILABLE else "tkinterhtml" if TKINTERHTML_AVAILABLE else "webview",
    }
