# 打包要求

1. 打包使用的 HBuilderX 版本号，必须使用 4.45 以上

   HBuilderX 版本：`4.45`

2. Uniapp 打包后的资源包

3. Uniapp App ID：`__UNI__882CCF1`

4. Uniapp App key：`2b78b3e878310b084550b0efd28ab762`

5. AbiFilters：`"armeabi-v7a"`

6. UrlSchemes：`identifyField`

7. manifest.json 中配置的版本名称 versionName、版本号 versionCode

   版本名称 versionName：`1.0.0`

   版本号 versionCode：`100`

8. 提供 Android 基座需要添加、移除的权限列表，基座默认权限如下：

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
<uses-feature android:name="android.hardware.camera"/>
<uses-feature android:name="android.hardware.camera.autofocus"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE"/>
<uses-permission android:name="android.permission.CAMERA"/>
<uses-permission android:name="android.permission.CHANGE_NETWORK_STATE"/>
<uses-permission android:name="android.permission.CHANGE_WIFI_STATE"/>
<uses-permission android:name="android.permission.FLASHLIGHT"/>
<uses-permission android:name="android.permission.GET_ACCOUNTS"/>
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS"/>
<uses-permission android:name="android.permission.MOUNT_UNMOUNT_FILESYSTEMS"/>
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>
<uses-permission android:name="android.permission.READ_LOGS"/>
<uses-permission android:name="android.permission.READ_PHONE_STATE"/>
<uses-permission android:name="android.permission.RECORD_AUDIO"/>
<uses-permission android:name="android.permission.VIBRATE"/>
<uses-permission android:name="android.permission.WAKE_LOCK"/>
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>
<uses-permission android:name="android.permission.WRITE_SETTINGS"/>
```

9. 模块信息：

   > - Share : weixin
   > - Maps : amap
   > - Payment : weixin
   > - Payment : alipay
   > - Geolocation : system
   > - LivePusher
   > - Camera
   > - VideoPlayer

10. 第三方平台配置信息：

   ```yml

wechat:
appid: wxfdc91fa8da31c36f
amap:
appkey: 0cce8770e83236802f5fd1babf5685f1
   ```
