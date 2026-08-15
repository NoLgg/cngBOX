---
change: cng-toolbox
design-doc: docs/superpowers/specs/2026-08-14-cng-toolbox-design.md
base-ref: 2044a68342b7fdc8b1803ef688743a6a4f892ca6
archived-with: 2026-08-15-cng-toolbox
---

# 草泥鸽工具箱 — 实施计划

## 目标

按 OpenSpec change `cng-toolbox` 的 7 个能力规格与 Design Doc，实现 Windows 桌面工具箱应用（Python + PySide6，PyInstaller 单 exe）：截图置顶、粘贴板（历史+贴屏）、取色器、设置面板、托盘常驻、游戏化 UI。

## 交付物

- `src/cng_toolbox/` 完整应用源码（shell/tools/storage/theme）
- `tests/` 单元测试与组件测试（pytest + pytest-qt）
- `pyproject.toml` 与 `build.spec`（PyInstaller）
- `docs/manual-test-checklist.md` 手动验证清单
- `README.md` 使用说明

## 实施顺序（对应 tasks.md 1~7 组）

### Phase 1: 项目脚手架（tasks 1.1–1.4）
1. pyproject.toml（项目元数据、依赖：PySide6、Pillow、qthotkey；dev：pytest、pytest-qt）
2. src/cng_toolbox 包骨架 + main.py 占位
3. 运行时目录引导（~/.cng-toolbox/：config.json、clipboard.db、images/、color_history.json）
4. build.spec（PyInstaller onefile noconsole，图标，排除 QtWebEngine）
   - 提交 1

### Phase 2: 应用壳 app-shell（tasks 2.1–2.6）
1. ConfigStore（DEFAULTS/deep_merge/原子写/损坏回退/changed 信号）
2. HotkeyEngine 接口 + QHotkeyEngine + Win32HotkeyEngine（ctypes 兜底）+ HotkeyManager（冲突/重注册/禁用联动）
3. TrayApp（托盘图标 QSystemTrayIcon、菜单、气泡）
4. 单实例（QLockFile + FindWindow 唤起）
5. ToolRegistry（register/unregister/依赖注入）
6. MainWindow（工具箱卡片网格 + QSS 主题骨架）
   - 提交 2（每完成一个任务提交一次，至少按功能块提交）

### Phase 3: 截图置顶（tasks 3.1–3.6）
1. ScreenshotTool：虚拟桌面抓屏拼接 + 全屏遮罩 + 框选交互 + 尺寸显示 + Esc 取消
2. PinManager：贴图注册表、上限 20、关闭全部、隐藏/显示切换
3. PinWindow：置顶无边框、拖动、滚轮缩放（20–500% 鼠标锚点）
4. 右键菜单：关闭/复制/点击穿透/保存到文件
5. 边框系统：6 预设 + 颜色/粗细自定义 + ConfigStore 联动即时刷新
6. 截图联动：贴图 + 复制到剪贴板 + 空选区忽略

### Phase 4: 粘贴板（tasks 4.1–4.6）
1. ClipboardTool 监听：dataChanged、文本/图片分类、hash 去重、20MB 上限、防回环
2. HistoryDB（SQLite schema + CRUD + 清理策略）+ ImageStore（hash 文件 + 缩略图 LRU）
3. 历史面板 UI（列表/大缩略图/筛选/搜索/时间）
4. 条目操作（单击复制/固定/删除）
5. 图片预览窗口（缩放）
6. 贴屏（文本排版/图片/空剪贴板提示，复用 PinManager）

### Phase 5: 取色器（tasks 5.1–5.3）
1. 取色模式（遮罩 + 放大镜 + HEX/RGB 实时）
2. 单击复制 / Esc 取消
3. 取色历史（10 个，json 持久化）

### Phase 6: 设置面板（tasks 6.1–6.5）
1. 设置页 UI（通用/热键/外观/剪贴板 分组）
2. HotkeyEdit 控件 + 冲突检测 + 即时生效
3. 开机自启（winreg HKCU Run）
4. 外观（主题/配色/边框预设+自定义）
5. 工具开关联动（热键注销 + 入口隐藏）

### Phase 7: 视觉与打包（tasks 7.1–7.4）
1. 游戏化主题落地（配色/图标 SVG/圆角卡片/托盘图标）
2. 全功能联调（手动清单走查）
3. pytest 全绿 + PyInstaller 打包 + 体积检查（≤80MB）
4. README + 发布说明

## 验证定义

- 每阶段结束运行 `python -m pytest tests/ -x`（无测试时先补）
- 手动验证：docs/manual-test-checklist.md 全项走查
- 打包验证：`pyinstaller build.spec` 产物体积 ≤80MB，Win10/11 冒烟

## 风险提示

- 本机无 GUI 验证环境时，截图/热键/托盘类功能以代码审查 + 手动清单交付，标注待验证项
- qthotkey 如与 PySide6 版本不兼容，直接启用 Win32HotkeyEngine 兜底实现

## 环境记录（2026-08-14，build 暂停点）

**暂停原因**：本机网络全不可达（pypi 清华/阿里/腾讯镜像、pypi.org、GitHub、choco、winget 均失败，本地代理 127.0.0.1:7890 未运行），无法安装 PySide6。

**环境事实**：
- Python 3.11（D:\Python）+ pip 25.2（源已配清华镜像）
- 已装：pyinstaller 6.14.2、pillow 10.3.0、pywin32 311、opencv 4.12.0
- 未装：PySide6 / shiboken6 / qthotkey / pytest（pytest 可用 unittest 替代）
- tkinter 8.6 可用（标准库）
- Git Bash：D:\编程软件\Git\bin\bash.exe（comet 脚本依赖，需 danger-full-access 运行）

**恢复步骤**：
1. 网络恢复后：`pip install PySide6 qthotkey pytest pytest-qt`（建议同时装 Pillow 至 venv）
2. 从 `/comet` 恢复：phase=build、plan 已存在、isolation=branch、build_mode=direct（direct_override=true）
3. 从 tasks.md 1.1 开始继续实施

**备选方案（若网络长期不可用，需用户重新决策）**：切换 tkinter + pywin32 + Pillow 技术栈（全部已就绪，UI 用 Canvas 自绘实现游戏化风格；热键用 win32 RegisterHotKey；托盘用 Shell_NotifyIcon；截图用 Pillow ImageGrab）。此方案需按 comet build Step 4 流程更新 Design Doc 与 delta spec 后实施。
