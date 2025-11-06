# 内嵌浏览器安装指南

本文档说明如何为构建管理客户端安装真正的内嵌浏览器功能。

## 🌟 功能对比

| 方案 | 特点 | 优势 | 劣势 | 推荐度 |
|------|------|------|------|--------|
| **CEF Python** | 完整的 Chromium 浏览器 | 🚀 完整功能<br>🎨 现代渲染<br>⚡ 高性能 | 📦 体积较大<br>🔧 安装复杂 | ⭐⭐⭐⭐⭐ |
| **TkinterHTML** | 轻量级 HTML 渲染 | 🪶 轻量级<br>📦 体积小<br>⚡ 启动快 | 🔸 功能有限<br>🎨 渲染较简单 | ⭐⭐⭐ |
| **pywebview** | 系统默认浏览器 | 🔧 无需安装<br>🎯 简单易用 | ❌ 独立窗口<br>❌ 非真正嵌入 | ⭐⭐ |

## 🚀 方案一：CEF Python（推荐）

CEF Python 提供最完整的内嵌浏览器体验，基于 Chromium 引擎。

### 系统要求

- Windows 10/11（推荐）
- Python 3.8+
- 至少 200MB 磁盘空间

### 安装步骤

1. **安装 CEF Python**
   ```bash
   # 激活虚拟环境
   source .venv/bin/activate  # Linux/Mac
   # 或
   .venv\Scripts\activate     # Windows

   # 安装 CEF Python
   pip install cefpython3==66.0
   ```

2. **验证安装**
   ```bash
   # 测试是否安装成功
   python -c "from cefpython3 import cefpython; print('CEF Python 安装成功')"
   ```

3. **重新启动应用**
   ```bash
   uv run manager-client
   ```

### 预期效果

- ✅ 真正的内嵌浏览器窗口
- ✅ 完整的 HTML5/CSS3/JavaScript 支持
- ✅ 现代化的网页渲染
- ✅ 无缝集成到 GUI 界面

## 🪶 方案二：TkinterHTML（轻量级）

TkinterHTML 是一个轻量级的 HTML 渲染库，适合简单的页面显示。

### 安装步骤

1. **安装 TkinterHTML**
   ```bash
   pip install tkinterhtml
   ```

2. **验证安装**
   ```bash
   python -c "import tkinterhtml; print('TkinterHTML 安装成功')"
   ```

3. **重新启动应用**
   ```bash
   uv run manager-client
   ```

### 适用场景

- 📊 简单的数据展示页面
- 🎨 不需要复杂 JavaScript 的页面
- ⚡ 对性能要求较高的场景

## 🔧 故障排除

### CEF Python 常见问题

1. **安装失败**
   ```bash
   # 尝试从清华源安装
   pip install -i https://pypi.tuna.tsinghua.edu.cn/simple cefpython3
   ```

2. **运行时错误**
   ```bash
   # 检查系统架构
   python -c "import platform; print(platform.architecture())"
   ```

3. **DLL 缺失**
   - 确保 Visual C++ Redistributable 已安装
   - 尝试安装完整版的 CEF Python

### TkinterHTML 常见问题

1. **渲染不完整**
   - TkinterHTML 不支持现代 CSS 特性
   - JavaScript 支持有限

2. **性能问题**
   - 对于复杂页面，考虑使用 CEF Python

## 📋 浏览器能力检测

应用启动时会自动检测可用的浏览器引擎：

```python
# 在应用中查看当前能力
from manager_client.gui.embedded_browser import get_browser_capabilities
capabilities = get_browser_capabilities()
print(capabilities)
```

输出示例：
```json
{
  "cef_available": true,
  "tkinterhtml_available": true,
  "webview_available": true,
  "recommended": "cefpython3"
}
```

## 🎯 推荐配置

### 开发环境
```bash
# 安装完整依赖
uv sync --extra dev
pip install cefpython3==66.0
```

### 生产环境
- **Windows 推荐使用 CEF Python**
- **Linux 考虑使用系统默认浏览器**
- **Docker 环境使用浏览器降级方案**

## 🔄 卸载说明

如需卸载内嵌浏览器：

```bash
# 卸载 CEF Python
pip uninstall cefpython3

# 卸载 TkinterHTML
pip uninstall tkinterhtml
```

卸载后应用会自动降级到浏览器打开方案。

## 📞 技术支持

如果遇到安装问题：

1. 检查 Python 版本是否为 3.8+
2. 确保虚拟环境已激活
3. 尝试使用管理员权限安装
4. 查看详细错误日志

---

**注意**：即使没有安装任何内嵌浏览器，应用仍然可以正常工作，会自动降级到在默认浏览器中打开看板。