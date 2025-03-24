# 打包要求

1. 打包使用的 HBuilderX 版本号，必须使用 4.45 以上

   HBuilderX 版本：`4.45`

2. Uniapp 打包后的资源包

3. Uniapp App ID：`填写hbuilderx中显示的uniapp应用标识`

4. Uniapp App key：`填写dcloud开发者中心申请的appkey`

   [申请 Appkey](https://nativesupport.dcloud.net.cn/AppDocs/usesdk/appkey.html)

5. manifest.json 中配置的版本名称 versionName、版本号 versionCode

   版本名称 versionName：`1.0.0`

   版本号 versionCode：`100`

6. 提供 Android 基座需要添加、移除的权限列表，基座默认权限如下：

   ```xml
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
   ```

   需要额外添加：

   ```xml
   <!-- 在此处填写需要添加的权限 -->
   ```

   需要移除：

   ```xml
   <!-- 在此处填写需要移除的权限 -->
   ```

7. uniapp 中使用的模块，请参照[uni 官方文档](https://nativesupport.dcloud.net.cn/AppDocs/)下的**模块及三方 SDK 配置**栏目，提供准确的模块名称列表（模块包含多个实现的，需要列出完整的子项实现），例如：

   > Geolocation（定位）
   >
   > ​ - 高德定位
   >
   > Share（分享）
   >
   > ​ - 微信分享
   >
   > Map（地图）
   >
   > ​ - 高德地图（需要标注页面为 vue、nvue）
   >
   > Payment（支付）
   >
   > ​ - 支付宝、微信支付
   >
   > Android X5 Webview（腾讯 TBS）

8. 如果涉及到的第三方平台需要在 AndroidManifest 清单中注册的，需要提供第三方平台的 sdk 相关信息与涉及的各类密钥信息，注意微信登录、分享都需要提供 `secret` 字段。

   ```yml
   wechat:
     appid: 微信开放平台申请应用的AppID
     secret: 微信开放平台申请应用的Secret
   amap:
     appkey: 高德地图开放平台申请的AppKey
   baidu:
     appkey: 百度地图开放平台申请的AppKey
   ```
