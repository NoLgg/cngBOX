"""config — 包级公共常量。

与 ConfigStore 的 DEFAULTS 区分：这里是规格层面的硬约束常量
（贴图上限、缩放范围、取色历史上限等），不随用户配置变化。
"""

# 贴图数量上限（spec: pin-to-top）
PIN_LIMIT = 20
# 贴图缩放范围（spec: 20% ~ 500%）
PIN_SCALE_MIN = 0.2
PIN_SCALE_MAX = 5.0
# 取色历史上限（spec: 10 个）
COLOR_HISTORY_LIMIT = 10
# 文本贴图最大宽度（像素）
TEXT_PIN_MAX_WIDTH = 800
# 截图空选区判定阈值（spec: <4×4 忽略）
MIN_SELECTION = 4
