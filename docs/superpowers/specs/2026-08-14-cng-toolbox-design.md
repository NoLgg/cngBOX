---
comet_change: cng-toolbox
role: technical-design
canonical_spec: openspec
archived-with: 2026-08-15-cng-toolbox
status: final
---

# 草泥鸽工具箱 — 技术设计文档

## Context

「草泥鸽工具箱」是一个 Windows 桌面工具箱应用（Python + PySide6，PyInstaller 打包单 exe），整合四大能力：截图置顶、剪贴板历史 + 贴屏、取色器，配游戏化个性 UI 与高自由度设置。OpenSpec 上游事实源：`openspec/changes/cng-toolbox/`（proposal.md / design.md / specs/）。本文档为实施层面的技术设计，聚焦模块结构、数据流、关键实现方案、风险与测试策略。

## Goals / Non-Goals

**Goals:**
- 提供可直接实施的模块划分与接口边界
- 解决全局热键、多显示器截图、剪贴板防回环、贴图交互等关键技术点的实现方案
- 定义可自动化测试的核心逻辑与手动验证清单
- 保持模块化，便于 v2 扩展新工具（OCR/放大镜等）

**Non-Goals:**
- 不重复 OpenSpec spec 的需求描述（canonical spec 在 openspec）
- 不做跨平台支持（v1 仅 Windows x64）
- 不做云同步/账号/网络功能

## 模块结构

```
src/cng_toolbox/
├── main.py                 # 入口：QApplication + 单实例锁 + 挂载工具
├── shell/                  # 应用壳（app-shell）
│   ├── config_store.py     # ConfigStore：JSON 读写、默认值合并、损坏回退
│   ├── hotkey_manager.py   # HotkeyEngine 接口 + HotkeyManager（注册/冲突/分发）
│   ├── tray_app.py         # TrayApp：托盘图标、菜单、气泡通知
│   ├── tool_registry.py    # ToolRegistry：工具模块注册表与生命周期
│   └── main_window.py      # MainWindow：工具箱卡片网格主面板
├── tools/
│   ├── screenshot.py       # ScreenshotTool：全屏遮罩 + 框选截图
│   ├── pin.py              # PinManager + PinWindow：贴图管理
│   ├── clipboard_tool.py   # ClipboardTool：监听 + 历史面板 + 贴屏
│   ├── color_picker.py     # ColorPickerTool：取色器
│   └── settings_dialog.py  # SettingsDialog：设置面板
├── storage/
│   ├── history_db.py       # HistoryDB：SQLite 元数据
│   └── image_store.py      # ImageStore：图片文件 + 缩略图缓存
├── theme/                  # 主题定义（THEMES）、QSS、图标生成
└── resources/              # 静态资源（托盘图标等）
```

**依赖方向**：`tools/*` → `shell/*`（ConfigStore、HotkeyManager、ToolRegistry 接口）与 `storage/*`、`theme/*`；`shell/*` 不依赖 `tools/*`（通过 ToolRegistry 反向注册）。工具模块之间互不依赖。

## 关键实现方案

### 1. ConfigStore（shell/config_store.py）

- 路径：`~/.cng-toolbox/config.json`；默认值定义在 `DEFAULTS` dict（含热键、主题、边框、剪贴板上限等全部可配置项）。
- 加载：`deep_merge(DEFAULTS, user_config)`；JSON 解析失败 → 重命名 `config.json.bak` 并用默认值重建。
- 保存：原子写（写临时文件后 `os.replace`）。
- 变更通知：`ConfigStore.changed` Qt 信号（带 key 列表），各模块监听刷新（主题切换、边框变更即时生效的机制）。

### 2. 热键引擎（shell/hotkey_manager.py）

- 接口 `HotkeyEngine`：`register(hotkey_id, sequence) -> bool`、`unregister(hotkey_id)`、信号 `triggered(hotkey_id)`。
- 主实现 `QHotkeyEngine`（qthotkey 库，PySide6 兼容）：按 `QKeySequence` 注册；失败返回 False。
- 兜底实现 `Win32HotkeyEngine`（ctypes `RegisterHotKey` + `QAbstractNativeEventFilter` 拦截 `WM_HOTKEY`）：零第三方依赖。
- `HotkeyManager`：启动时按 config 注册全部热键；注册失败 → 托盘气泡提示冲突、该热键跳过；热键设置变更 → 全量重注册；工具禁用 → 对应热键注销。
- 默认热键：截图置顶 `Ctrl+Shift+A`、取色器 `Ctrl+Shift+C`、粘贴板面板 `Ctrl+Shift+V`、显示面板 `Ctrl+Shift+P`。

### 3. 截图（tools/screenshot.py）

- 流程：抓屏（见下）→ 显示全屏遮罩窗口（覆盖虚拟桌面，基于已抓画面绘制，保证画面一致且遮罩不进入截图）→ 鼠标框选 → Esc/右键取消 → 完成回调。
- 抓屏：遍历 `QGuiApplication.screens()`，逐屏 `grabWindow(0, sx, sy, w, h)` 按虚拟坐标抓取，再按 `virtualGeometry()` 拼接为整张 QPixmap；Qt6 每屏 devicePixelRatio 已由 Qt 处理。
- 遮罩窗口：无边框全屏（虚拟桌面范围），`WA_TransparentForMouseEvents` 关闭；绘制：半透明黑（alpha≈0.3）+ 框选区域高亮（反色）+ 选区边缘实时显示 `宽×高`。
- 回调：选区 QRect → 从拼接大图裁剪 QPixmap → `ScreenshotResult`（pixmap + rect）；由调用方决定贴图/复制。
- 空选区（<4×4）忽略并退出。

### 4. 贴图（tools/pin.py）

- `PinWindow(QWidget)`：flags = `FramelessWindowHint | WindowStaysOnTopHint | Tool`（无任务栏条目）；内容模型为 QPixmap（图片）或 QPixmap 化文本（text 贴图：按最大宽度 800px 自动换行排版）。
- paintEvent：按当前边框样式绘制（无/细线/粗线/虚线/发光/圆角）+ 内容（缩放绘制，>100% 用 `SmoothTransformation`）。发光用 `QGraphicsDropShadowEffect`（仅发光预设启用），圆角用 clip 路径。
- 交互：`mousePress/Move` 拖动（记录按下偏移）；`wheelEvent` 缩放（20%~500%，以鼠标位置为锚点调整窗口几何）；`contextMenuEvent` 菜单（关闭/复制/点击穿透切换/保存到文件）；`mouseDoubleClickEvent` 复制。
- 点击穿透：切换 `Qt.WindowTransparentForInput` 后 hide/show 重生效；兜底 Win32 `WS_EX_TRANSPARENT`。
- `PinManager`：`dict[int, PinWindow]`；`create(pixmap)` / `close(id)` / `close_all()` / `toggle_hide_all()`；上限 20 张（超出气泡提示）；监听 ConfigStore 边框变更 → 广播刷新全部贴图。

### 5. 剪贴板历史（tools/clipboard_tool.py + storage/*）

- 监听：`QApplication.clipboard().dataChanged` → 读取 mimeData：
  - 文本：`text()`，去重（与最近条目内容 hash 相同则跳过，仅更新时间戳）
  - 图片：`image()`，>20MB 跳过；hash 去重
  - 自身写入防回环：模块内维护 `last_self_write = (monotonic_ts, content_hash)`，自身复制操作写入后 500ms 内触发的 dataChanged 且 hash 匹配则忽略
- HistoryDB（SQLite，`~/.cng-toolbox/clipboard.db`）：
  - 表 `entries(id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT CHECK(type IN ('text','image')), content_hash TEXT UNIQUE, text_content TEXT, image_path TEXT, pinned INTEGER DEFAULT 0, created_at INTEGER)`
  - 索引：`(pinned DESC, created_at DESC)`；查询：按类型筛选、按 `text_content LIKE %kw%` 搜索
- ImageStore：图片存 `~/.cng-toolbox/images/<content_hash>.png`；缩略图内存缓存（最长边 512px，LRU 上限 100 张）；原图懒加载（预览窗口时再读全尺寸）
- 清理：插入后与启动时执行：`DELETE FROM entries WHERE pinned=0 AND id NOT IN (SELECT id ORDER BY created_at DESC LIMIT <limit>)`，limit 默认 500（config 可配）；同时删除孤儿图片文件
- 历史面板：QListWidget + 自定义 item widget（文本预览 / 图片大缩略图 + 时间）；顶部筛选（全部/文本/图片）+ 搜索框；单击 → 复制；右键 → 固定/删除/贴屏；双击图片缩略图 → 预览窗口（QScrollArea + 缩放）
- 贴屏入口：面板条目右键「贴屏」+ 托盘菜单「贴出剪贴板」；文本 → 排版为 pixmap；图片 → 原尺寸；空剪贴板 → 气泡提示

### 6. 取色器（tools/color_picker.py）

- 进入取色模式：全屏遮罩（基于抓屏画面）；鼠标移动 → 从抓屏 pixmap 读当前像素色值（逻辑坐标换算，处理 DPI）；放大镜绘制鼠标周围 10×10 区域放大（缩放比 8×）到预览框；HEX/RGB 实时文本。
- 单击 → 复制 HEX → 退出；Esc → 取消退出。
- 历史：`~/.cng-toolbox/color_history.json`（最近 10 个），取色面板/设置内展示色块列表，点击重新复制。

### 7. 设置面板（tools/settings_dialog.py）

- 分组（QTabWidget）：通用（开机自启开关、剪贴板上限 spinbox）、热键（自定义 `HotkeyEdit` 控件：聚焦后捕获按键组合，冲突检测）、外观（主题 ComboBox、配色 ComboBox、边框预设 ComboBox + 颜色按钮 `QColorDialog` + 粗细 spinbox）、工具（三个开关）。
- 开机自启：`winreg` 写 HKCU `Software\Microsoft\Windows\CurrentVersion\Run` 键 `CaoNiGeToolbox` = exe 路径（含引号）；关闭时删除。
- 所有变更 → ConfigStore 保存 + changed 信号 → 各模块即时刷新。

### 8. 生命周期（main.py）

- `QLockFile(~/.cng-toolbox/singleton.lock)` 单实例；重复启动 → 通过命名管道/单实例消息（v1 用 `QLockFile` + 轮询共享文件或简单方案：向已有实例发 WM 消息）唤起已有实例主面板。v1 简化：二次启动直接显示提示并退出 + 尝试唤起（用 Windows 消息 `RegisterWindowMessage` + `FindWindow` 兜底）。
- 启动顺序：ConfigStore → 单实例 → QApplication → 主题应用 → ToolRegistry 注册工具 → TrayApp → HotkeyManager 注册热键 → 常驻。

## 测试策略

### 自动化（pytest + pytest-qt）
- `test_config_store.py`：默认合并、损坏回退、原子写
- `test_history_db.py`：CRUD、hash 去重、上限清理（含固定条目保护）、类型筛选/搜索 SQL
- `test_image_store.py`：文件存取、hash 命名、缩略图缓存
- `test_theme.py`：主题/配色解析、QSS 生成
- `test_hotkey_serialize.py`：热键序列化与解析
- `test_main_window.py`（pytest-qt）：主面板渲染、工具卡片列表
- `test_history_panel.py`（pytest-qt）：列表加载、搜索过滤、类型筛选

### 手动验证清单（docs/manual-test-checklist.md）
1. 全局热键：四个默认热键在任意前台窗口生效；热键冲突提示
2. 截图：多显示器跨屏框选、Esc 取消、选区尺寸显示、截图结果贴图+入剪贴板
3. 贴图：拖动/滚轮缩放（20%~500%）/右键菜单四项/点击穿透/双击复制/上限 20 提示/一键全部关闭
4. 边框：6 预设切换即时刷新、自定义颜色粗细、重启保持
5. 剪贴板：文本+图片记录、去重、>20MB 跳过、重启保留、搜索/筛选/固定/删除、图片放大预览、贴屏（文本/图片/空）
6. 取色器：实时色值、放大镜、单击复制 HEX、Esc 取消、历史 10 个
7. 设置：热键自定义/禁用/冲突、开机自启注册表写入移除、主题/配色即时切换、工具开关联动
8. 打包：PyInstaller 构建、体积 ≤80MB、Win10/11 冒烟、单实例

## 风险与对策

- [qthotkey 在个别系统注册失败] → Win32HotkeyEngine 兜底，热键引擎接口化，设置面板可切换
- [剪贴板监听回环] → last_self_write 时间窗 + hash 匹配防回环
- [Windows 退出清空剪贴板] → v1 文档说明；v2 用 `AddClipboardFormatListener` 保活
- [抓屏与遮罩时序] → 先抓屏后显示遮罩，遮罩基于抓屏结果绘制
- [高 DPI 坐标偏移] → 全链路用 Qt 逻辑坐标 + 虚拟桌面几何，禁用 Qt 自动缩放例外
- [打包体积] → venv 最小依赖 + 排除 Qt 无用模块（QtWebEngine 等），目标 ≤80MB
- [常驻内存] → 缩略图 LRU 缓存上限、原图懒加载、面板关闭即释放

## Migration Plan

全新项目无迁移。首次运行：创建 `~/.cng-toolbox/`（config.json、clipboard.db、images/、color_history.json）。

## Open Questions

1. 二次启动唤起已有实例：v1 用 FindWindow 方案是否足够（无则仅提示）？——已决定：FindWindow + 自定义消息唤起主面板，失败仅提示。
2. 贴图「保存到文件」默认目录：`~/Pictures/CaoNiGeToolbox/` ——已决定。
