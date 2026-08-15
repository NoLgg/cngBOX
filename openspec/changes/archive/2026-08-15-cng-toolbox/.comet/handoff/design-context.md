# Comet Design Handoff

- Change: cng-toolbox
- Phase: design
- Mode: compact
- Context hash: 93a6b1ea1a1438c413a1edce5567989578788eeb659c99745eecbdcdc7fe41e2

Generated-by: comet-handoff.sh

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/cng-toolbox/proposal.md

- Source: openspec/changes/cng-toolbox/proposal.md
- Lines: 1-41
- SHA256: 4d77bf578acdcf7008a17a60a6adcfdea847634885cd46d2f0f2bd5eb3075378

```md
## Why

日常电脑使用中，「截图 → 把参考图钉在屏幕上」「复制过的内容找不回来」「临时取个色值」是三个高频痛点，但每个都需要安装一个单独的小工具（Snipaste、Ditto、取色器）。用户希望有一个轻量的 Windows 桌面工具「草泥鸽工具箱」，把截图置顶、剪贴板、取色器整合进一个常驻托盘的 exe 程序，配上个性化的 UI。

## What Changes

创建一个全新的 Windows 桌面应用（Python + PySide6，打包为单文件 .exe）：

- **截图置顶**：全局热键触发屏幕区域截图，截图结果作为「贴图」置顶显示在屏幕最上层；支持同时钉多张贴图，每张贴图可拖动、滚轮缩放、右键菜单关闭/复制。
- **粘贴板（剪贴板历史）**：常驻监听剪贴板，完整记录复制过的文本和图片，提供历史面板（文本预览 + 图片大图缩略图、搜索、固定、一键重新复制、图片点击放大查看原图），历史记录持久化存储。
- **贴屏**：把剪贴板中的文本或图片一键「贴」到屏幕上置顶显示（复用贴图框架）。
- **取色器**：全局热键唤起屏幕取色，实时显示像素色值（HEX/RGB），点击复制。
- **设置面板**：全局热键自定义（截图/取色器/打开主面板）、开机自启开关、外观设置；所有系统级配置集中在设置页。
- **贴图边框自定义**：贴图窗口边框支持多套预设样式（无边框/细线/粗线/虚线/发光/圆角等），颜色与粗细可自定义，随时切换。
- **高自由度原则**：所有可配置项（热键、贴图行为、边框样式、外观主题、剪贴板行为、工具开关）全部开放给用户自定义，不做硬编码。
- **托盘常驻**：程序常驻系统托盘，主面板/工具通过托盘菜单或全局热键唤起。
- **UI**：游戏化、个性风格（贴合「草泥鸽」名称），深色基调 + 高辨识度配色与图标。
- 纯本地运行，无网络依赖，无账号体系。

## Capabilities

### New Capabilities

- `app-shell`: 应用壳——托盘常驻、主窗口框架、全局热键注册与分发、设置持久化（config 文件）。
- `screen-capture`: 屏幕区域截图——热键唤起、全屏遮罩、框选、尺寸/像素信息、截图完成回调。
- `pin-to-top`: 置顶贴图——贴图窗口置顶、多贴图管理、拖动/缩放/右键菜单/点击穿透、贴图生命周期管理。
- `clipboard-history`: 剪贴板历史——文本+图片监听、历史列表、搜索、固定、重新复制、持久化（SQLite）。
- `clip-to-screen`: 贴屏——将剪贴板文本/图片内容生成贴图置顶显示。
- `color-picker`: 取色器——全屏取色、放大预览、HEX/RGB 色值复制、历史色值。
- `settings`: 设置面板——热键配置、开机自启、外观选项、各功能开关。

### Modified Capabilities

（无——全新项目，无既有 spec 需要修改）

## Impact

- 全新代码库，无既有代码受影响。
- 技术依赖：Python 3.11+、PySide6（Qt）、Pillow（图像处理）、pyperclip（剪贴板）或 Qt 原生剪贴板、pynput / QHotkey（全局热键）、SQLite（标准库）、pyinstaller（打包）。
- 系统影响：注册全局热键（需在设置中可关闭）；开机自启写入注册表/启动目录（设置中可关闭）；剪贴板监听为纯本地读取。
- 产物：单文件 `草泥鸽工具箱.exe`（Windows 10/11 x64），打包体积目标 ≤ 80MB。
```

## openspec/changes/cng-toolbox/design.md

- Source: openspec/changes/cng-toolbox/design.md
- Lines: 1-106
- SHA256: 5c252553286869e165147c88898713403721235d1b66eeedb06bd83a91c514f0

[TRUNCATED]

```md
## Context

「草泥鸽工具箱」是一个全新的 Windows 桌面工具（Python + PySide6），将截图置顶、剪贴板历史、贴屏、取色器整合为托盘常驻应用，UI 走游戏化个性风格。项目为全新代码库，无历史包袱；目标用户是 Windows 10/11 桌面用户。约束：单机本地运行、无网络依赖、打包为单文件 exe（≤80MB）。

## Goals / Non-Goals

**Goals:**
- 一个 exe 即可提供截图置顶、剪贴板历史、贴屏、取色器全部功能
- 全局热键可用、可自定义、可关闭；托盘常驻，开机自启可配置
- 剪贴板历史持久化（重启不丢），支持文本与图片
- UI 游戏化个性风格，与「草泥鸽」名称相符，深色基调、高辨识度

**Non-Goals:**
- 不做云同步 / 账号体系 / 多设备
- 不做 OCR、放大镜、快捷短语、二维码（列为 v2 候选）
- 不做截图标注编辑（画笔/箭头等）——v1 只做框选截图
- 不支持 macOS/Linux（v1 仅 Windows x64）

## Decisions

### D1. 技术栈：Python 3.11+ / PySide6（Qt6）

- **理由**：开发速度快、QML/Widgets 都能做出游戏化 UI、生态成熟（打包、剪贴板、热键均有方案）。
- **备选**：C# WPF（原生集成好但开发慢、UI 灵活度低）；Tauri（exe 小但 Rust 成本高、截图/热键生态需自拼）；Electron（体积 150MB+ 对常驻工具过重）。
- **打包**：PyInstaller `--onefile --noconsole`，目标体积 ≤80MB（Pillow/PySide6 精简）。

### D2. 架构：单进程 + 托盘 + 模块化「工具包」

```
┌────────────────────────────────────────────────┐
│  app-shell（应用壳）                            │
│  ├─ TrayApp      托盘菜单 / 退出 / 显示面板      │
│  ├─ HotkeyManager 全局热键注册与分发（QShortcut/ │
│  │                native AHK-free 方案）         │
│  ├─ ConfigStore  JSON 配置持久化（用户目录）     │
│  └─ ToolRegistry 工具模块注册表（插件式扩展）    │
├────────────────────────────────────────────────┤
│  工具模块（互不依赖，仅依赖 shell 接口）          │
│  ├─ ScreenshotTool   截图 → 贴图                │
│  ├─ ClipboardTool    历史监听 + 面板 + 贴屏      │
│  └─ ColorPickerTool  取色 → 复制                 │
└────────────────────────────────────────────────┘
```

- **理由**：工具箱的扩展性来自「工具=独立模块」，后续加 OCR/放大镜只需注册新模块，不动壳。
- **备选**：单体 MainWindow 一把梭（v1 快但 v2 加功能必重构）。

### D3. 全局热键：QHotkey（Qt 原生全局热键绑定）

- 用 `QHotkey`（或 Qt6 原生 + 平台钩子）实现全局热键；所有热键在设置面板可改、可禁用。
- **备选**：pynput 全局监听（线程模型复杂、易与 Qt 事件循环冲突）；AutoHotkey 外部脚本（引入外部依赖，违背单 exe 目标）。

### D4. 截图：Qt 全屏遮罩 + 框选（不依赖第三方截图库）

- 截取虚拟屏幕（多显示器用 `QGuiApplication.screens()` 合并）→ 全屏半透明遮罩窗口 → 鼠标框选 → 返回选区 QPixmap。
- **备选**：mss/pyautogui 截图（额外依赖、多屏 DPI 处理差）；Windows API PrintWindow（复杂）。

### D5. 贴图：独立 frameless 置顶窗口（Qt::WindowStaysOnTopHint + Tool 窗口类型）

- 每张贴图 = 一个无边框置顶窗口，注册到 `PinManager` 统一管理；支持拖动、滚轮缩放、右键菜单（关闭/复制/点击穿透切换）、双击复制。
- 多显示器：贴图可拖到任意屏幕；点击穿透用 `Qt::WindowTransparentForInput` 切换（Win32 WS_EX_TRANSPARENT 兜底）。
- **边框渲染**：贴图窗口内嵌内容 + 边框绘制层；边框样式由全局配置驱动（预设：无边框/细线/粗线/虚线/发光/圆角），颜色/粗细可自定义；配置变更通过 PinManager 广播刷新所有贴图。发光/圆角等特殊样式用 QGraphicsDropShadowEffect / 自绘实现，预设切换即时生效。

### D5b. 高自由度配置原则

- 所有用户可感知的行为与外观（热键、贴图边框、主题、剪贴板行为、工具开关）均进 ConfigStore 并暴露在设置面板；新功能默认带配置项，不硬编码默认行为。

### D6. 剪贴板历史：QClipboard 信号监听 + SQLite 持久化

- 监听 `QClipboard.dataChanged`；文本去重（与最近一条相同则跳过）、图片存文件（`~/.cng-toolbox/images/`）并记录缩略图；SQLite 存元数据（类型/时间/固定标记/搜索索引）。
- 上限：默认保留最近 500 条（可配置）；固定条目不被清理。
- **备选**：纯内存（重启丢失，不满足持久化目标）；文件型 JSON（图片场景难管理）。

### D7. 设置存储：`~/.cng-toolbox/config.json`（单文件）

- 热键、开机自启、外观、各功能开关、剪贴板上限，集中一个 JSON；开机自启写 HKCU 注册表 Run 键。

### D8. UI：PySide6 Widgets + QSS，游戏化个性风

- 深色基调（#1a1d24 系）+ 主色高饱和（青绿/橙黄）+ 圆角卡片 + 自定义图标（emoji/SVG 混合）。
```

Full source: openspec/changes/cng-toolbox/design.md

## openspec/changes/cng-toolbox/tasks.md

- Source: openspec/changes/cng-toolbox/tasks.md
- Lines: 1-54
- SHA256: 1cbdb3b7c44fd9f8ae390634fb7b02fa91c176c1bcbd1876f6ff95a1b608731e

```md
## 1. 项目脚手架

- [ ] 1.1 初始化 Python 项目结构（pyproject.toml、src/cng_toolbox/ 包、venv）
- [ ] 1.2 安装依赖：PySide6、Pillow、pyperclip、QHotkey（或等效 Qt 热键方案）
- [ ] 1.3 配置 PyInstaller 打包脚本（--onefile --noconsole，输出「草泥鸽工具箱.exe」）
- [ ] 1.4 建立 `~/.cng-toolbox/` 运行时目录（config.json、clipboard.db、images/）

## 2. 应用壳（app-shell）

- [ ] 2.1 实现 ConfigStore：config.json 读写、默认值合并、损坏回退（.bak 备份）
- [ ] 2.2 实现 HotkeyManager：全局热键注册/释放/冲突检测/分发（支持自定义）
- [ ] 2.3 实现 TrayApp：托盘图标、菜单（显示面板/工具入口/退出）、气泡通知
- [ ] 2.4 实现单实例锁（QLockFile）与重复启动唤起
- [ ] 2.5 实现 ToolRegistry：工具模块注册表与生命周期挂载
- [ ] 2.6 实现主窗口（工具箱卡片网格）：工具卡片渲染、点击唤起、游戏化主题 QSS

## 3. 截图置顶（screen-capture + pin-to-top）

- [ ] 3.1 实现全屏遮罩截图：多显示器虚拟屏幕合并、框选、尺寸显示、Esc 取消
- [ ] 3.2 实现 PinManager：贴图窗口创建/销毁/上限 20 张/一键全部关闭
- [ ] 3.3 实现贴图交互：拖动、滚轮缩放（20%~500%、鼠标锚点）、置顶无任务栏
- [ ] 3.4 实现贴图右键菜单：关闭/复制/点击穿透切换/保存到文件
- [ ] 3.5 实现贴图边框系统：预设样式（无/细线/粗线/虚线/发光/圆角）+ 颜色/粗细自定义 + 全局即时刷新
- [ ] 3.6 截图完成联动：生成贴图 + 图片复制到剪贴板 + 空选区忽略

## 4. 粘贴板（clipboard-history + clip-to-screen）

- [ ] 4.1 实现剪贴板监听：QClipboard dataChanged、文本/图片分类、去重、>20MB 跳过
- [ ] 4.2 实现历史存储层：SQLite 元数据 + images/ 图片文件、上限 500 条清理、固定条目保护
- [ ] 4.3 实现历史面板 UI：列表、图片大缩略图、类型筛选、搜索、时间显示
- [ ] 4.4 实现条目操作：单击复制、固定/取消固定、删除
- [ ] 4.5 实现图片预览：点击缩略图弹出原图预览窗口（缩放/关闭）
- [ ] 4.6 实现贴屏：文本/图片贴图生成、自动换行、空剪贴板提示、与 PinManager 复用

## 5. 取色器（color-picker）

- [ ] 5.1 实现取色模式：全屏遮罩、放大镜预览、HEX/RGB 实时显示
- [ ] 5.2 实现取色交互：单击复制 HEX、Esc 取消
- [ ] 5.3 实现取色历史：最近 10 个色值展示与点击重新复制

## 6. 设置面板（settings）

- [ ] 6.1 实现设置页 UI：通用/热键/外观/剪贴板分组
- [ ] 6.2 实现热键自定义：点击输入、冲突检测、禁用、即时生效持久化
- [ ] 6.3 实现开机自启：HKCU Run 键写入/移除
- [ ] 6.4 实现外观设置：主题切换（深色默认/浅色预留）、配色方案（青绿/橙黄/紫罗兰）、贴图边框预设与自定义
- [ ] 6.5 实现工具开关：截图/粘贴板/取色器启用禁用联动

## 7. 视觉与打包

- [ ] 7.1 设计并落地游戏化主题：配色、图标（SVG/emoji）、圆角卡片、托盘图标
- [ ] 7.2 全功能联调：托盘、热键、面板、贴图、历史、取色交叉验证
- [ ] 7.3 打包验证：PyInstaller 构建、体积检查（≤80MB）、Win10/11 启动冒烟测试
- [ ] 7.4 编写 README（安装、热键、设置说明）与发布说明
```

## openspec/changes/cng-toolbox/specs/app-shell/spec.md

- Source: openspec/changes/cng-toolbox/specs/app-shell/spec.md
- Lines: 1-61
- SHA256: 213251f0accf865fc70ab04dcf66b8c2264bc1c769cc1273c0612f9e6e50a49e

```md
## ADDED Requirements

### Requirement: 托盘常驻

应用启动后常驻系统托盘，关闭主窗口不退出程序；托盘菜单提供「显示主面板」「截图置顶」「取色器」「粘贴板」「退出」入口。

#### Scenario: 启动后常驻托盘
- **WHEN** 用户启动「草泥鸽工具箱.exe」
- **THEN** 应用在系统托盘显示图标，且无主窗口弹出（除非用户设置开机自启时默认显示）

#### Scenario: 关闭主窗口不退出
- **WHEN** 用户点击主窗口关闭按钮
- **THEN** 主窗口隐藏，程序继续在托盘常驻，全局热键仍然生效

#### Scenario: 从托盘退出
- **WHEN** 用户在托盘菜单选择「退出」
- **THEN** 应用完全退出，释放全部全局热键

### Requirement: 单实例运行

同一时刻只允许运行一个实例；重复启动时激活已有实例并显示主面板。

#### Scenario: 重复启动
- **WHEN** 程序已在运行，用户再次启动 exe
- **THEN** 第二个进程退出，已有实例的主面板被唤起显示

### Requirement: 主窗口（工具箱面板）

主窗口以「工具箱」形式展示所有工具卡片，每张卡片包含图标、工具名称、快捷键提示；点击卡片或按快捷键唤起对应工具；窗口支持移动、关闭，风格为游戏化个性主题。

#### Scenario: 展示工具卡片
- **WHEN** 用户打开主面板
- **THEN** 面板以卡片网格展示全部可用工具（截图置顶、粘贴板、取色器），每张卡片显示图标、名称和对应快捷键

#### Scenario: 点击卡片唤起工具
- **WHEN** 用户点击某张工具卡片
- **THEN** 对应工具被唤起（截图工具进入截图模式 / 粘贴板展开历史面板 / 取色器进入取色模式）

### Requirement: 全局热键注册与分发

HotkeyManager 统一注册全局热键（默认：截图置顶 `Ctrl+Shift+A`、取色器 `Ctrl+Shift+C`、粘贴板面板 `Ctrl+Shift+V`、显示面板 `Ctrl+Shift+P`）；热键在任意前台窗口下生效；热键冲突时不崩溃并提示用户。

#### Scenario: 热键全局生效
- **WHEN** 用户在任何应用中按下已注册热键
- **THEN** 对应工具被唤起，且不干扰当前应用的正常输入

#### Scenario: 热键冲突提示
- **WHEN** 应用注册热键时发现该组合已被其他程序占用
- **THEN** 托盘弹出气泡提示冲突，该热键不注册，其余热键正常工作

### Requirement: 配置持久化

应用配置（热键、开关、外观等）持久化到 `~/.cng-toolbox/config.json`；修改设置立即保存；配置损坏时回退默认值并重建配置文件。

#### Scenario: 修改配置后重启保留
- **WHEN** 用户在设置面板修改热键并重启应用
- **THEN** 新热键在重启后依然生效

#### Scenario: 配置损坏自动恢复
- **WHEN** 配置文件内容损坏（JSON 解析失败）
- **THEN** 应用以默认配置启动，并备份损坏文件为 config.json.bak
```

## openspec/changes/cng-toolbox/specs/clipboard-history/spec.md

- Source: openspec/changes/cng-toolbox/specs/clipboard-history/spec.md
- Lines: 1-61
- SHA256: 6ef59c0ce8a9ab52c6ed9c8f6bbcb914f6d5e96478d6f611b14246b0d21a7fbd

```md
## ADDED Requirements

### Requirement: 剪贴板监听

应用常驻监听系统剪贴板变化，自动记录复制/剪切产生的文本和图片；同一内容连续复制不重复记录（与最近一条相同则忽略）；图片体积超过 20MB 不记录。

#### Scenario: 记录复制文本
- **WHEN** 用户在任何应用中复制一段文本
- **THEN** 该文本出现在剪贴板历史列表中

#### Scenario: 记录复制图片
- **WHEN** 用户复制一张图片
- **THEN** 该图片出现在剪贴板历史列表中，并显示缩略图

#### Scenario: 去重
- **WHEN** 用户连续两次复制相同内容
- **THEN** 历史中只保留一条记录（更新时间戳）

### Requirement: 历史记录持久化

剪贴板历史持久化存储（SQLite + 图片文件），应用重启后历史记录仍可查看；默认保留最近 500 条，固定条目永久保留；超出上限时按时间从旧到新清理非固定条目。

#### Scenario: 重启后历史保留
- **WHEN** 用户重启应用并打开剪贴板面板
- **THEN** 重启前记录的历史条目仍可见

#### Scenario: 历史条数上限
- **WHEN** 历史条目超过 500 条
- **THEN** 最旧的未固定条目被自动清理，固定条目不受影响

### Requirement: 历史面板

历史面板以列表展示：文本条目显示内容预览，图片条目显示大尺寸缩略图（完整呈现图片内容，而非小图标）；支持按类型筛选（全部/文本/图片）；支持搜索框按内容关键词过滤文本条目；每条记录显示复制时间。

#### Scenario: 打开历史面板
- **WHEN** 用户按下粘贴板快捷键或点击托盘菜单
- **THEN** 弹出历史面板窗口，按时间倒序展示历史条目，图片条目以完整内容的大缩略图呈现

#### Scenario: 搜索历史
- **WHEN** 用户在搜索框输入关键词
- **THEN** 列表实时过滤，仅显示内容包含该关键词的文本条目

#### Scenario: 放大查看图片
- **WHEN** 用户点击某图片条目的缩略图
- **THEN** 弹出预览窗口显示该图片原图，支持缩放与关闭

### Requirement: 历史条目操作

单击条目将其内容重新复制到剪贴板；条目支持固定/取消固定；条目支持删除。

#### Scenario: 一键重新复制
- **WHEN** 用户单击某条历史记录
- **THEN** 该条内容被复制回剪贴板，面板保持打开（等待用户自行切换粘贴）

#### Scenario: 固定条目
- **WHEN** 用户固定某条记录
- **THEN** 该记录置顶显示并带固定标记，且不会被自动清理

#### Scenario: 删除条目
- **WHEN** 用户在条目上触发删除（右键菜单/删除键）
- **THEN** 该条目从历史中移除
```

## openspec/changes/cng-toolbox/specs/clip-to-screen/spec.md

- Source: openspec/changes/cng-toolbox/specs/clip-to-screen/spec.md
- Lines: 1-33
- SHA256: 53899a36d2aacf2457ffb1ce1d4fccea50e927758c020acbf71758170db4bebc

```md
## ADDED Requirements

### Requirement: 剪贴板内容贴屏

用户可将剪贴板中的文本或图片一键「贴」到屏幕置顶显示；文本贴图按内容自动排版（自动换行、最大宽度限制），图片贴图按原尺寸显示。

#### Scenario: 贴文本到屏幕
- **WHEN** 用户剪贴板中有文本并触发「贴屏」
- **THEN** 屏幕出现置顶的文本贴图，内容为剪贴板文本，超出最大宽度自动换行

#### Scenario: 贴图片到屏幕
- **WHEN** 用户剪贴板中有图片并触发「贴屏」
- **THEN** 屏幕出现置顶的图片贴图，与原图尺寸一致

#### Scenario: 剪贴板为空时贴屏
- **WHEN** 用户剪贴板为空并触发「贴屏」
- **THEN** 托盘气泡提示「剪贴板为空」，不产生贴图

### Requirement: 贴屏入口

贴屏可通过托盘菜单「粘贴板 → 贴出剪贴板」或历史面板条目上的「贴屏」操作触发；贴屏生成的贴图复用贴图管理（拖动、缩放、右键菜单、上限）。

#### Scenario: 从历史面板贴屏
- **WHEN** 用户在历史面板某条目上触发「贴屏」
- **THEN** 该条目内容以贴图形式置顶显示

#### Scenario: 贴图行为一致
- **WHEN** 贴屏生成的贴图被操作
- **THEN** 其支持拖动、滚轮缩放、右键菜单等与截图贴图一致的行为

#### Scenario: 文本贴图复制文本
- **WHEN** 用户在文本贴图的右键菜单选择「复制」
- **THEN** 贴图内的原始文本被复制到剪贴板（而非渲染后的图片）
```

## openspec/changes/cng-toolbox/specs/color-picker/spec.md

- Source: openspec/changes/cng-toolbox/specs/color-picker/spec.md
- Lines: 1-37
- SHA256: c689a1d1ec6f122f526f7c94b9c14fec565043055b9cf8f4dff6dfe944056104

```md
## ADDED Requirements

### Requirement: 取色模式

按下取色热键进入取色模式：屏幕出现取色遮罩，鼠标位置显示局部放大预览（放大镜）和当前像素色值（HEX 与 RGB）。

#### Scenario: 热键唤起取色器
- **WHEN** 用户按下取色热键
- **THEN** 屏幕进入取色模式，鼠标旁显示放大镜预览与实时色值

#### Scenario: 实时色值显示
- **WHEN** 用户在取色模式下移动鼠标
- **THEN** 放大镜与色值实时跟随更新，HEX 与 RGB 两种格式同时显示

### Requirement: 取色复制

单击确认取色并退出取色模式；取到的颜色以 HEX 格式复制到剪贴板；取色过程中支持 Esc 取消（不复制）。

#### Scenario: 单击复制色值
- **WHEN** 用户在取色模式下单击
- **THEN** 取色模式退出，鼠标所在像素的色值以 HEX 格式复制到剪贴板

#### Scenario: 取消取色
- **WHEN** 用户在取色模式下按 Esc
- **THEN** 取色模式退出，不复制任何内容

### Requirement: 取色历史

最近取过的颜色在取色器中保留（最多 10 个），用户可点击历史色值重新复制。

#### Scenario: 查看取色历史
- **WHEN** 用户再次进入取色模式或打开取色面板
- **THEN** 显示最近取过的颜色列表

#### Scenario: 复制历史色值
- **WHEN** 用户点击历史色值条目
- **THEN** 该色值以 HEX 格式复制到剪贴板
```

## openspec/changes/cng-toolbox/specs/pin-to-top/spec.md

- Source: openspec/changes/cng-toolbox/specs/pin-to-top/spec.md
- Lines: 1-73
- SHA256: 1a985c6cc65f6df2db7393312fbbb539d5db381d5824d7bf1c187590641ac00f

```md
## ADDED Requirements

### Requirement: 贴图置顶显示

贴图窗口始终显示在屏幕最上层（置顶），不进入任务栏；支持同时存在多张贴图，互不干扰。

#### Scenario: 贴图置顶
- **WHEN** 一张贴图生成后
- **THEN** 该贴图窗口显示在屏幕最上层，且任务栏不出现对应条目

#### Scenario: 多张贴图共存
- **WHEN** 用户连续截图生成多张贴图
- **THEN** 所有贴图同时置顶显示，拖动任一张不影响其他贴图

### Requirement: 贴图拖动与缩放

贴图支持鼠标拖动改变位置；支持滚轮缩放（最小 20%，最大 500%）；缩放以鼠标位置为锚点。

#### Scenario: 拖动贴图
- **WHEN** 用户按住贴图拖动
- **THEN** 贴图跟随鼠标移动，松开后停留在新位置

#### Scenario: 滚轮缩放贴图
- **WHEN** 用户将鼠标悬停在贴图上滚动滚轮
- **THEN** 贴图以鼠标位置为锚点放大或缩小，且尺寸不超出最小/最大限制

### Requirement: 贴图右键菜单

贴图右键弹出菜单：关闭贴图、复制图片、点击穿透切换、保存到文件。

#### Scenario: 关闭贴图
- **WHEN** 用户在贴图右键菜单选择「关闭」
- **THEN** 该贴图从屏幕消失

#### Scenario: 复制贴图
- **WHEN** 用户在贴图右键菜单选择「复制图片」
- **THEN** 贴图图片内容被复制到系统剪贴板

#### Scenario: 点击穿透切换
- **WHEN** 用户在贴图右键菜单切换「点击穿透」
- **THEN** 贴图保持显示但不再拦截鼠标事件，鼠标点击穿透到下层窗口；再次切换恢复

#### Scenario: 保存贴图到文件
- **WHEN** 用户在贴图右键菜单选择「保存到文件」
- **THEN** 弹出保存对话框（默认目录 `~/Pictures/CaoNiGeToolbox/`，PNG 格式），保存成功后气泡提示；用户取消则不保存

### Requirement: 贴图边框自定义

贴图窗口支持边框样式：提供多套预设（无边框、细线、粗线、虚线、发光、圆角等）；边框颜色、粗细可自定义；边框设置全局生效，修改后所有贴图即时刷新。

#### Scenario: 切换边框预设
- **WHEN** 用户在设置中选择新的边框预设（如从「细线」切换为「发光」）
- **THEN** 所有现有贴图与新建贴图立即应用新边框样式

#### Scenario: 自定义边框颜色与粗细
- **WHEN** 用户自定义边框颜色（取色器取色/色值输入）与粗细数值
- **THEN** 贴图边框按自定义值渲染并持久化，重启后保持

#### Scenario: 无边框模式
- **WHEN** 用户选择「无边框」预设
- **THEN** 贴图仅显示内容本身，无任何边框修饰

### Requirement: 贴图统一管理

所有贴图由 PinManager 统一管理：支持一键全部关闭；支持「全部隐藏/全部显示」切换；贴图数量上限 20 张，超出时提示。

#### Scenario: 一键关闭全部贴图
- **WHEN** 用户通过托盘菜单或快捷键触发「关闭全部贴图」
- **THEN** 所有贴图全部关闭

#### Scenario: 超过贴图上限
- **WHEN** 贴图数量已达到 20 张，用户再次截图
- **THEN** 截图不生成新贴图，托盘气泡提示「贴图数量已达上限」
```

## openspec/changes/cng-toolbox/specs/screen-capture/spec.md

- Source: openspec/changes/cng-toolbox/specs/screen-capture/spec.md
- Lines: 1-37
- SHA256: 30c2363f9977dbe4738847ffac829c4bb6d07183205edd9936b30db3501b162c

```md
## ADDED Requirements

### Requirement: 热键唤起截图

按下截图热键后进入截图模式：屏幕显示全屏半透明遮罩，支持多显示器；用户可用鼠标框选截图区域。

#### Scenario: 热键唤起截图模式
- **WHEN** 用户按下截图热键
- **THEN** 屏幕出现全屏遮罩，光标变为十字准星，进入框选状态

#### Scenario: 多显示器框选
- **WHEN** 用户在多显示器环境下截图
- **THEN** 遮罩覆盖所有显示器组成的虚拟屏幕，用户可跨屏框选

### Requirement: 区域框选交互

框选过程中实时显示选区尺寸（像素）；支持 Esc 取消截图；支持拖拽调整选区（v1 仅支持新选框选，二次调整列为 v2）。

#### Scenario: 显示选区尺寸
- **WHEN** 用户正在拖动框选
- **THEN** 选区边缘实时显示宽×高像素值

#### Scenario: 取消截图
- **WHEN** 用户按下 Esc 或右键点击
- **THEN** 截图模式退出，不产生任何贴图

### Requirement: 截图完成回调

鼠标松开完成框选后，截图结果进入后续流程：默认生成贴图置顶，同时将截图图片复制到剪贴板。

#### Scenario: 完成框选生成贴图
- **WHEN** 用户完成框选松开鼠标
- **THEN** 选区图片以贴图形式置顶显示，且图片内容已复制到系统剪贴板

#### Scenario: 取消空选区
- **WHEN** 用户框选面积小于 4×4 像素
- **THEN** 视为误触，不生成贴图，退出截图模式
```

## openspec/changes/cng-toolbox/specs/settings/spec.md

- Source: openspec/changes/cng-toolbox/specs/settings/spec.md
- Lines: 1-57
- SHA256: f53823f1b5f8a57b310b292f1d4c02c8ab7fd5945dfdecf0cadfbb7dcc1114b5

```md
## ADDED Requirements

### Requirement: 设置面板

主面板提供「设置」入口，设置页分组展示：通用（开机自启、语言）、热键（各工具热键自定义）、外观（主题/配色）、剪贴板（历史上限、图片上限）。

#### Scenario: 打开设置面板
- **WHEN** 用户在主面板点击「设置」
- **THEN** 显示设置页，按通用/热键/外观/剪贴板分组展示配置项

### Requirement: 开机自启配置

设置中提供「开机自启」开关；开启后写入 HKCU 注册表 Run 键（或启动目录快捷方式），关闭时移除。

#### Scenario: 开启开机自启
- **WHEN** 用户打开「开机自启」开关
- **THEN** 系统登录后自动启动「草泥鸽工具箱」，且开关状态持久化

#### Scenario: 关闭开机自启
- **WHEN** 用户关闭「开机自启」开关
- **THEN** 注册表/启动项被移除，开关状态持久化

### Requirement: 热键自定义

每个全局热键均可自定义：点击热键输入框后按下新组合键完成设置；支持清空（禁用）某热键；设置即时生效并持久化。

#### Scenario: 修改热键
- **WHEN** 用户在设置面板点击某热键输入框并按下新的组合键
- **THEN** 新热键立即生效并保存，旧热键被释放

#### Scenario: 禁用热键
- **WHEN** 用户清空某热键输入框
- **THEN** 该热键被禁用，对应功能仅能通过托盘菜单/主面板触发

#### Scenario: 热键冲突检测
- **WHEN** 用户设置的新热键与另一个已注册热键相同
- **THEN** 设置被拒绝并提示冲突，原热键保持不变

### Requirement: 外观设置

外观设置提供主题选择（默认「游戏化深色」，预留浅色主题）；配色方案可切换（默认青绿主色，备选橙黄/紫罗兰）；贴图边框样式可配置（预设样式 + 颜色/粗细自定义）。

#### Scenario: 切换主题
- **WHEN** 用户在外观设置中切换主题
- **THEN** 主面板、历史面板、贴图样式立即刷新为所选主题并持久化

#### Scenario: 配置贴图边框
- **WHEN** 用户在外观设置中选择边框预设或自定义颜色/粗细
- **THEN** 所有贴图即时应用新边框并持久化

### Requirement: 各工具开关

设置中可为截图置顶、粘贴板、取色器分别提供启用/禁用开关；禁用后对应热键与托盘入口隐藏。

#### Scenario: 禁用某工具
- **WHEN** 用户禁用「取色器」工具
- **THEN** 取色热键失效，主面板与托盘中取色器入口隐藏
```

