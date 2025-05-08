"""
这个文件用于存储公共的常量
"""

# 模块的名称映射
MODULES_MAP = {
    "Geolocation": "Geolocation（定位）",
    "Push": "Push（消息推送）",
    "Share": "Share（分享）",
    "OAuth": "OAuth（登录鉴权）",
    "Maps": "Maps（地图）",
    "Payment": "Payment（支付）",
    "Speech": "Speech（语音输入）",
    "Statistic": "Statistic（统计）",
    "Webview-x5": "Android X5 Webview（腾讯 TBS）",
    "VideoPlayer": "VideoPlayer（视频播放）",
    "LivePusher": "LivePusher（直播推流）",
    "Barcode": "Barcode（扫码）",
    "Bluetooth": "Bluetooth（低功耗蓝牙）",
    "Camera": "Camera（相机/相册）",
    "Contacts": "Contacts（通讯录）",
    "Fingerprint": "Fingerprint（指纹识别）",
    "Messaging": "Messaging（短彩邮件消息）",
    "Recorder": "Record（录音）",
    "SQLite": "SQLite（数据库）",
}

# 默认权限列表
DEFAULT_PERMISSIONS = """```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.READ_PHONE_STATE" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
<uses-permission android:name="com.asus.msa.SupplementaryDID.ACCESS" />
<uses-permission android:name="com.huawei.android.launcher.permission.CHANGE_BADGE" />
<uses-permission android:name="android.permission.INSTALL_PACKAGES" />
<uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />
```"""
