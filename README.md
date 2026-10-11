# 骷髅女孩 (Skullgirls) 汉化重制项目

作者：A.Aitherine　　许可证：MIT（见 LICENSE）

把 2013 年《骷髅女孩》的老汉化（游侠 LMAO 汉化组 v1.0）移植到当前 Steam 版本（appid 245170）。

开源说明：简体中文译文与用字顺序**基于游侠 LMAO 汉化组的旧版汉化**；逆向分析、文本迁移、字形重绘、打包工具与补丁程序均为本项目原创。

## 一、做了什么

1. 把老汉化的译文迁移到当前版本的本地化文件 `core.gfs → core/localization/en_loc.json`（9788 个键全量替换为中文）。
2. 字体重建：用黑体 (SimHei) 重新栅格化当前译文需要的 2517 个汉字，写进游戏原有字体的字形图集。
3. 打包成一个可自选游戏路径、可安装/卸载的单文件补丁程序。

## 二、逆向结论

### .gfs 包格式（Reverge Package File 1.1）

头部为：u32be dataOffset + PascalString(magic="Reverge Package File") + PascalString(version="1.1") + u64be count + 每条目(u64be nameLen, name, u64be size, u32be flags)，之后是顺序排列的数据区。注意 PascalString 长度是 u64be。工具见 tools/skullgirls_gfs.py，已用 core.gfs 做过逐字节往返验证。

### 签名校验绕过

新版 exe 用 libtomcrypt DSA 校验每个 .gfs，失败会报 "Package xxx.gfs not verified"。
绕过点：SkullGirls.exe 文件偏移 0x5B47D（VA 0x45C07D）6 字节，把 `8A 85 6F FE FF FF` 改成 `B0 01 90 90 90 90`。

### 文本位置

当前版本真正读取的是 core.gfs 里的 core/localization/<语言>_loc.json（9788 键，UTF-8，键值都是字符串）。ui.gfs 里已经没有 2013 版的老路径 temp/localization/*.lua；前端菜单文本同样走这份 json。游戏目录里若存在散装 data01/core/localization/en_loc.json，以**包内**为准。

### 字体格式（TNFG 块）

字体不是独立文件，而是塞在 ui-win.gfs 的 .gbs（UI 数据块）里，结构为：

```
[tag "TNFG"][u32 size = 100 + 40*n][u32 id][name 64B]
[头部 6×u32：字号, 逻辑宽, 逻辑高, 行高, 页数, 字形数]
[n × 字形条目 10×u32：字符码, 页码, x, y, w, h, 行高, advance, 标志, 保留]
```

要点：字形表起点是 name+88（头部只有 24 字节，不是 32 字节）；贴图页在同包 ui/Win/Fonts/<字体名>_<页码>.dds（DXT5，白字+alpha，通常 768²，大字体会是 1536²）；坐标是"逻辑"坐标，实际贴图像素 = 逻辑 × (贴图宽 / 逻辑宽)，当前版本这个比例恒为 1.5；有些字体的字形表后面还跟着一段"块尾数据"，不能随便动。

## 三、失败经验（重要）

- 直接覆盖老汉化的 ui.gfs / ui-win.gfs：游戏起不来，2013 数据结构和路径都变了。
- 只换译文不换字体：全是问号，字体里没有汉字字形。
- 新增字体贴图页：全是问号。**引擎只认 page 0**，字形指向 page 1 以上取不到贴图。
- 用字体声明了但没用的空闲页（page 1..N-1）放中文：**闪退**，同样是 page≥1 拿不到贴图。
- 只拿 _JP（日文）字体做简体中文：满屏乱码。**日文字体用的是老日文编码（非 Unicode）**，简体独有字（说/们/这/时/对/愿 等）既装不进也查不到。
- 放大逻辑尺寸但贴图比例不是 1.5（如逻辑 2048 配贴图 2048）：全是问号。**逻辑:贴图 必须保持 1.5**。
- 放大图集并大量新增字形记录：能显示中文，但**右下角按键提示错位**（放大图集这个动作会扰动那块 UI 排版）。
- 完全不动图集、只填原有空白，但给很多字体加记录：中文能显示，但**主菜单白屏**。

## 四、当前进度与现状

已完成：文本迁移（core.gfs 的一万键全中文）；字体机制完全逆向；可用的字形重绘流程；带路径选择、自动备份、可完整卸载的补丁程序。

可用版本：

- `Skullgirls_Han_Patch.exe`（推荐，对应内部版本 v22）：放大 10 个字体图集，主力字体 1711~2545 字、旁白 768 字；代价是右下角按键提示图标会错位。可正常进游戏，覆盖最好。
- v25：不动图集、只填 7 个字体原有空白，每字体几百字；按键提示正常但问号多。
- v28：不动图集、8 个字体；实测仍白屏，未采用。

已知问题：

1. 白屏。给"很多"字体同时插入新字形记录后，主菜单背景美术会消失。现象是 7 个字体没事、8 个以上就白，但 v20（原地替换、不改文件长度）改 24 个字体却完全正常——真正诱因尚未定位，是最大的未解问题。
2. 右下角按键提示错位。该排版由引擎按文字宽度计算，界面配置里没有位置字段，补丁层面改不动。
3. 开场旁白有缺字。旁白用的 AttractText 图集原本是满的（只有 158 条记录、无空白），除非放大它否则放不下更多汉字。
4. 少数低频字仍是问号（每个字体容量有限，按界面用字与字频裁剪）。

## 五、目录结构

```
Skullgirls_Han/
  Skullgirls_Han_Patch.exe   补丁程序（安装/卸载，可选游戏路径）
  README.md                  本文档
  LICENSE                    MIT
  docs/GITHUB上传教程.md      怎么把项目传到 GitHub
  tools/                     全部脚本源码
    skullgirls_gfs.py        .gfs 解包/打包
    gdi_font.py              用 GDI 把汉字栅格化成 8 位灰度图
    dxt5enc.py               灰度图 → DXT5 DDS
    fontfinal8.py            当前采用的字体重绘脚本（放大图集版）
    fontv28.py               不动图集、只填空白的实验版脚本
    fontjp3.py               日文槽实验脚本（已证否）
    build_v22.py             把脚本产物打成补丁 payload
    build_installer_v22.py   编译补丁程序
    Installer.cs             补丁程序源码（C#，含路径选择）
    app.manifest
  localization/
    中文_en_loc.json          迁移好的中文文本（9788 键）
    characters.json          重绘所需字符集（2517 汉字 + 其它）
    translation_memory_en_zh.json  英→中对照表
  reference/
    老汉化_DefaultFont_中文字库图集.png    老汉化字库（参考）
    当前版本_DefaultFont_英文字库图集.png  当前版本字库（参考）
```

## 六、使用方法

### 使用到的工具

**使用者需要**

- Steam 版《骷髅女孩》(appid 245170)。
- 本项目的 Skullgirls_Han_Patch.exe（单文件，无额外依赖；Windows 自带的 .NET Framework 4.x 即可运行）。
- 可选：7-Zip（想自己拆开补丁程序看内容时用）。

**开发与逆向用到的**

- **7-Zip**：拆开 2013 老汉化的安装程序。那个 AutoIt 安装器运行时会在 %TEMP% 释放 `patch.dll`，它其实是一个 7-Zip 自解压包，里面就是老汉化的 `ui.gfs` / `ui-win.gfs` / `dev.gfs` / `SkullGirls.exe`。
- **Python 3**（自写脚本，见 tools/）：解析与重打包 `.gfs`、解码 DDS(DXT5)、用 GDI 栅格化汉字、编码 DXT5、写字节补丁、批量重绘字体。
- **MinGW objdump**（`objdump -d -M intel`）：反汇编 SkullGirls.exe，定位 DDS 解析器、字形查找、字体页加载循环、签名校验等关键代码。
- **Windows GDI**（用 ctypes 调 gdi32/user32）：把 SimHei 汉字渲染成 8 位灰度位图，作为字形来源。
- **.NET 自带 csc.exe**（C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe）：编译补丁程序（C# WinForms），并把 payload 追加到 exe 尾部。
- **Windows 事件查看器 + 游戏自带崩溃转储**（`crash-dumps/*.dmp`）：定位闪退。异常偏移 0xDCAB0 最终定位到 DDS 解析器里的空指针取值（`mov eax,[esi]`，esi=NULL）。
- **Windows 资源/转储与十六进制查看**：确认 exe 的补丁字节、`.gfs` 头部、DDS 头逐字节对比。
- **Steam**：用"验证游戏完整性"取得干净的原版文件作为基线。
- **SimHei（黑体）**：中文字形来源；参考老汉化的 `DefaultFont_中文字库图集.png` 与当前版本的英文字库图集（用自写解码器从 .dds 转出）。

打补丁：关掉游戏 → 双击 Skullgirls_Han_Patch.exe → 若没自动认出游戏目录就点「选择游戏目录…」选到 ...\steamapps\common\Skullgirls（里面有 SkullGirls.exe 和 data01）→ 点「安装汉化」→ 完成后启动游戏。游戏内语言保持**英文**（补丁打在英文槽）。

还原：再运行点「卸载汉化」，会从 data01/_sg_chs_backup_v2/ 完整还原，不需要 Steam 验证完整性。

手动方式：替换 data01/ui-win.gfs 与 data01/core.gfs，LOCALE.txt 保持 JAPAN，并把 exe 的 0x5B47D 那 6 字节改成上述补丁值。

## 七、字体是怎么做的

1. 从当前版本 ui-win.gfs 读出每个目标字体的字形表、每个字形的贴图矩形与对应贴图页。
2. 选定字符集（当前译文用到的 2517 个汉字与标点，按"界面短文案优先、其次字频"排序）。
3. 用 SimHei 通过 GDI 栅格化成 8 位灰度，再用自写的极简 DXT5 编码器写成 DDS（头部与游戏原图完全一致，含 NVTT 标记）。
4. 把原图集内容整体搬到新图集左上角（原字形一字节不改，原有英文与数字渲染完全一致），再把中文按格子铺在新扩出来的区域。
5. 逻辑尺寸与贴图尺寸同时放大且保持 1.5 比例，否则引擎会取错贴图。

## 八、后续路线

1. 定位白屏触发条件：以"只改 1 个字体"的最小补丁为基线，对同一字体分别做原地替换、插入记录、放大图集三种操作，看哪种或哪个字体触发白屏。搞定后覆盖就能线性增加。
2. 把"插入新记录"改成整段重建、偏移一次算对，并处理带块尾数据的字体（内部可能有文件绝对偏移）。
3. 处理 AttractText（旁白字体）：它没有空白位，需要单独放大或另想办法。
4. 若按键提示错位不可接受，可考虑同时改 ui.gfs 的界面配置 ui/config/**/*.ini，但那些文件里没有位置字段，大概率要动引擎层，收益有限。

## 九、致谢与声明

译文来源：游侠 LMAO 汉化组《骷髅女孩》汉化补丁 v1.0（2013）。
中文字形：SimHei（黑体），Windows GDI 栅格化重绘。
其余（逆向、工具链、补丁程序、文档）：A.Aitherine。
本项目仅供学习与个人使用，请勿用于商业用途；游戏本体版权归 Lab Zero Games / Hidden Variable / Autumn Games 所有。
