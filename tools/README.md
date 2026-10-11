# tools 目录说明（建议的阅读与运行顺序）

脚本都是 Python 3（只用标准库 + ctypes），互相同目录引用，建议放在同一文件夹里跑。

## 核心工具

| 文件 | 作用 |
| --- | --- |
| `skullgirls_gfs.py` | `.gfs`（Reverge Package File 1.1）解包 / 列出 / 打包。支持 `list`、`extract`、`pack`。做过逐字节往返验证。 |
| `gdi_font.py` | 用 Windows GDI 把汉字栅格化成 8 位灰度位图（字形来源）。 |
| `dxt5enc.py` | 把灰度图编码成 DXT5 的 DDS（头部与游戏原图完全一致，含 NVTT 标记）。 |

## 字体生成

| 文件 | 说明 |
| --- | --- |
| `fontfinal8.py` | **当前采用的脚本**（对应发布版 v22）。做法：放大目标字体的图集（逻辑与贴图同时放大、保持 1.5 比例），原图集内容整体搬到左上角（原字形一字节不改），再把中文按格子铺进新扩区域。运行后输出 `patch17/ui-win.gfs`、`patch17/core.gfs`。 |
| `fontv28.py` | 实验版：**不动图集尺寸**，只把中文填进原有贴图的空白处。覆盖少但按键提示正常；不过实测加到 8 个字体以上会白屏。 |
| `fontjp3.py` | 日文槽实验：把 `_JP` 字体的字形表"原地替换"成中文。结论是**不可行**（日文字体用老日文编码，非 Unicode），保留作为反例。 |

## 打包与安装器

| 文件 | 说明 |
| --- | --- |
| `build_v22.py` | 比较原版与生成版 `ui-win.gfs`，把改动/新增的条目连同 core.gfs 的 json、exe 字节补丁压成 `payload_v17.bin`。 |
| `build_installer_v22.py` | 调用 csc 编译 `Installer.cs`，并把 payload 追加到 exe 尾部（末尾写 `u64 偏移, u64 长度, "SGPATCH1"`）。 |
| `Installer.cs` | 补丁程序源码（C# WinForms）。含图形界面（安装/卸载/选择游戏目录/打开目录）、静默参数 `/install`、`/uninstall`、payload 读取、`.gfs` 条目写入、备份与还原。 |
| `app.manifest` | 让程序以普通权限运行、并声明支持高 DPI。 |

## 运行顺序（做一版新补丁）

1. 准备好干净的原版 `ui-win.gfs` / `core.gfs`（Steam 验证完整性后复制一份）。
2. `python fontfinal8.py` → 生成 `patch17/ui-win.gfs`、`patch17/core.gfs`。
3. `python build_installer_v22.py` → 生成 payload 并编译出带界面的补丁程序。
4. 用补丁程序安装，进游戏验证。

## 自检建议

改动字体后，至少验证三件事（脚本里已有类似检查）：

1. 每个 `TNFG` 块的 `size` 等于 `100 + 40 × 字形数`；
2. 每个字体的字形页码连续，且不超过该字体实际存在的 `.dds` 页号；
3. `skullgirls_gfs.py list` 能把包完整列出来（说明包结构没写坏）。
