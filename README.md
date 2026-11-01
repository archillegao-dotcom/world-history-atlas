# 世界历史地图 · World History Atlas（v0.4）

一个在本机运行的「世界历史地图」：拖动时间轴，地图边界随历史变化；点击某个国家/政权，
就能看到那一天（或那一年）前后在那里发生的**事件**、**每日新闻**，以及当时在世的**文学家、哲学家、政治家**。
地图上还会标出**当时已经存在的主要城市**（★ = 当时的国家首都）。

> 只使用公开的真实数据，不编造任何事件、人物或日期。每一条内容都附有来源链接（Wikidata / 维基百科 / 新闻来源）。

## 免安装版（推荐，不需要安装 Python）

在本仓库的 **Releases** 页面（或 Actions 里构建出的 Artifacts）下载对应压缩包。解压后直接打开，**不需要安装 Python**。

| 系统 | 下载 | 打开方式 |
|---|---|---|
| macOS（M1/M2/M3/M4 芯片） | `WorldHistoryAtlas-macos-arm64.zip` | 双击解压得到 `WorldHistoryAtlas.app`，建议拖到“应用程序”文件夹 |
| macOS（Intel 芯片） | `WorldHistoryAtlas-macos-x64.zip` | 同上 |
| Windows 10/11 | `WorldHistoryAtlas-windows-x64.zip` | 右键 → “全部解压缩”，打开解压出的 `WorldHistoryAtlas` 文件夹，双击 `WorldHistoryAtlas.exe` |

> 不确定 Mac 是哪种芯片：点屏幕左上角的苹果图标 → “关于本机”，“芯片”写 Apple M… 就选 arm64，写 Intel 就选 x64。
>
> 最低系统版本不是“打包那台电脑的系统版本”。每个 App 会按实际带上的库声明自己的最低 macOS 版本（写在 Release 说明里，也写在 App 的“最低系统版本”里）。Apple 芯片的包不能在 Intel Mac 上运行；Intel 包可以在 Intel Mac 上运行，也可以在 Apple 芯片的 Mac 上通过 Rosetta 2 运行。

启动后会弹出一个 **黑色窗口**（Mac 上是“终端”窗口），并自动打开浏览器 http://localhost:8790/ （端口被占用时会自动换一个，窗口里会显示实际地址）。
**使用期间不要关闭这个黑色窗口；关闭它就是退出软件。** 再次双击时如果软件已在运行，只会重新打开浏览器页面。

### Mac 第一次打开（软件未经 Apple 签名，系统会拦截一次）

1. 第一次 **不要直接双击**：在“访达”里 **按住 Control 键点按（或右键）`WorldHistoryAtlas.app` → 选“打开”** → 在弹窗里再点 **“打开”**。
2. 如果弹窗里没有“打开”按钮（较新的 macOS 15/26 常见）：先双击一次让它被拦截，然后打开
   **系统设置 → 隐私与安全性**，在页面下方找到“已阻止使用 WorldHistoryAtlas”，点 **“仍要打开”**，输入开机密码确认，再双击一次即可。
3. 只需做一次，以后直接双击。系统可能询问是否允许“终端”运行，点“好”。
4. 仍然打不开（提示“已损坏”）时，可在“终端”里执行下面一行后再双击（把路径换成 app 实际位置）：
   `xattr -dr com.apple.quarantine /Applications/WorldHistoryAtlas.app`

### Windows 第一次打开

Windows 可能弹出蓝色的 “Windows 已保护你的电脑”（SmartScreen）：点 **“更多信息” → “仍要运行”**。
杀毒软件如误报，请选择“允许”。务必先**解压**再运行，不要在压缩包里直接双击。

### 数据保存在哪里

历史地图、事件、人物都在软件包里，**只读**，程序不会改这些文件。
每天自动更新的「每日新闻」和维基百科摘要缓存写在你的用户目录（第一次启动会放一份说明文件进去，已有文件不会被覆盖）：

- macOS：`~/Library/Application Support/WorldHistoryAtlas`（访达 → 前往 → 前往文件夹，粘贴此路径）
- Windows：`%APPDATA%\WorldHistoryAtlas`（在资源管理器地址栏粘贴）
- Linux：`~/.local/share/WorldHistoryAtlas`

删掉这个文件夹会清掉已下载的更新和缓存，不会删掉软件自带的历史数据。

### 自己打包（开发者）

```
pip install -r requirements.txt pyinstaller
python packaging/build.py          # 生成 dist/WorldHistoryAtlas(.app) 和 dist/WorldHistoryAtlas-<系统>-<架构>.zip
```
推送 `v*` 标签（如 `git tag v0.4.0 && git push origin v0.4.0`）后，GitHub Actions（`.github/workflows/build.yml`）会自动在
macOS（Apple 芯片 + Intel）和 Windows 上构建。两个 macOS 压缩包会先挂到 Release（Windows 失败不会挡住这次发布）；Windows 构建成功后再把 Windows 压缩包补到同一个 Release。也可在 Actions 页面手动运行 “Build apps”（手动运行只产生可下载的 Artifacts，不发布 Release）。

## 从源码打开（需要已安装 Python）

| 系统 | 操作 |
|---|---|
| macOS | 双击 `start.command`（第一次如被拦截：右键 → 打开） |
| Windows | 双击 `start.bat` |
| Linux | 运行 `./start.sh` |

第一次运行会自动创建 Python 运行环境并安装依赖（需要联网，约 1 分钟；需要已安装 Python 3.10+）。
之后会自动打开浏览器访问 `http://127.0.0.1:8790/`（端口被占用时自动换下一个）。关闭终端窗口即退出。

除了「每日新闻」的自动更新，其它功能完全离线可用（地图库 Leaflet 已打包在本地，不依赖 CDN）。

## 使用方法

- **时间**：底部滑块（史前部分被压缩、近代被拉伸）；或在顶部输入年份（勾选「公元前」）、选择月、日后点「跳转」。
  `◀ ▶` 前后一步（选了日期时按「天」走，否则按年/十年/百年走），`▶ 播放` 自动推进历史，「今天」跳到今天。
- **点击地图上的政权** → 右侧面板出现标签页：政权性质 / 领导人 / 事件 / 每日新闻 / 文学家 / 哲学家 / 政治家。点条目会在地图上定位；链接打开 Wikidata 或维基百科。
  - **政权性质**：当时的政体、执政党（当时元首/首脑所属政党）、意识形态、首都、所属阵营、国旗，以及中文维基百科条目首句作为定义。
  - **领导人**：当时的国家元首、政府首脑和重要职位（如「中华民国总统」「行政院院长」）。点人名打开**人物页面**（维基百科摘要、照片、生卒、担任过的职务）；点职位打开**机构卡片**（职位与所领导机构的介绍、历任者）。
  - 面板顶部「对应 Wikidata 政权」可以切换：同一块地图区域在同一时间可能对应多个 Wikidata 条目（如「中华民国」有 1912–1949 与 1912 至今两个条目）。
- **🌍 全世界**：不限地区，看这一天前后全世界的内容。
- **经济**（图层）：勾选「经济」后，地图按所选年份给**现代国界**着色，左上角可选指标：人均 GDP / GDP 总量 / 人口（Maddison 2023），以及世界银行 1960 年起的 GDP、人均 GDP、预期寿命、农业/工业/服务业占比、城镇化率、识字率等。历史边界只保留细线叠在上面；悬停历史区域会显示与它重叠最多的现代国家的数值。虚线边框表示该国的数值是插值或沿用最近数据。
- **资源**（图层）：矿山、油田、天然气田（Wikidata，有坐标），点开看产品、开采年代与链接。
- **民生经济**（面板）：所点区域与哪些现代国家重叠（面积比例），这些国家在所选年份的各项指标（每个数值注明来源与所属年份；插值会标出前后两个基准年），以及人均 GDP、人口、预期寿命的小趋势图（红色虚线 = 所选年份；数据点相隔超过 100 年时折线断开）。
- **国家精神**（面板）：所选日期该政权作为签署方、正在生效的条约与同盟卡片（同盟 / 和约 / 经贸 / 领土 / 其他）。点卡片看详情：签订/生效/终止日期、全部签署方、维基百科摘要、维基文库原文链接。
- **阵营地图**：在左上角「图层」勾选「阵营地图」，地图会按所选日期的同盟/阵营给国家着色；在出现的图例里勾选要显示的阵营（默认显示当时最知名的两个），点阵营名称打开**阵营面板**（成立/解散时间、成员加入/退出时间、Wikidata 记录的领导人物）。
- **图层**：左上角可开关「主要城市」。放大地图会显示更多城市；鼠标悬停看详情（当时的官方名称、人口等），点击打开维基百科。
- 右上角显示「每日新闻已更新至 …」。
- 网址后面的 `#date=1789-07-14&name=France&tab=events` 记录当前状态，可以收藏或分享。还可以加 `&layers=alliances&blocs=Q7184,Q41644`（打开阵营图层并选定阵营）、`&person=Q16574` / `&office=Q702650` / `&bloc=Q43056`（直接打开人物/机构/阵营窗口）。

## 数据来源与规模（v0.4 构建时）

| 内容 | 来源 | 数量 | 时间精度 |
|---|---|---|---|
| 历史边界 | [historical-basemaps](https://github.com/aourednik/historical-basemaps)（A. Ourednik，GPL-3.0） | 55 张快照：公元前123000年 … 2010年 | 只在快照年份变化 |
| 现代边界 | [Natural Earth](https://www.naturalearthdata.com/) 1:50m（公有领域） | 242 个国家/地区，用于 2011 年至今 | 约 2020 年代的边界 |
| 事件 | Wikidata（「发生的事件」类条目，有时间点 P585 或开始时间 P580，≥6 个语言版本） | 71,778（加载时再过滤掉年份条目等非事件）| 日/月/年/十年/世纪（按 Wikidata 记录） |
| 文学家 | Wikidata（职业：作家、诗人、小说家、剧作家、儿童文学作家、散文家；≥10 个语言版本） | 35,515 | 生卒日期 |
| 哲学家 | Wikidata（职业：哲学家；≥6 个语言版本） | 7,663 | 同上 |
| 政治家 | Wikidata（职业：政治家、君主、国务活动家、国家元首、总统；≥12 个语言版本） | 31,540 | 同上 |
| 主要城市 | Wikidata（城市/首都 ≥40 个语言版本；古城 ≥12） | 7,342 | 建立/废弃时间 |
| 每日新闻 | 英文维基百科 [Portal:Current events](https://en.wikipedia.org/wiki/Portal:Current_events)（2002 年 7 月起每日页面）+ 1995–2002 年份条目 | 119,809 条（9,627 天），1995-01-01 至今，**每天自动更新** | 日 |
| 政权（国家）| Wikidata（国家、主权国家、历史国家、帝国、王国等 9 类及其子类，≥5 个语言版本）：存在期、首都（含起止）、政体 P122、意识形态 P1142、元首 P35、首脑 P6、国旗 | 5,495 | 起止日期 |
| 地图区域 → 政权 | 本应用计算（见方法说明） | 55 张快照共 17,805 个区域中 5,370 个有候选（无候选的多为「狩猎采集者」等人群区域） | — |
| 职位与任职者 | Wikidata（管辖区 P1001 为上述政权、≥3 个语言版本、任职者 ≤400 人的职位；P39 任职记录及起止） | 2,789 个职位，823 个所领导机构（P2389） | 任期起止 |
| 人物（领导人） | Wikidata（以上元首、首脑、任职者）：生卒、所属政党 P102（含起止）、照片 | 40,058 | — |
| 阵营/同盟 | Wikidata（military alliance、multinational military coalition、alliance、koinon 及子类，且至少 2 个政权成员）；成员来自 P527/P710/P1891 与成员国的 P463，含加入/退出时间 | 70 | 成立/解散、加入/退出 |
| 经济（历史）| [Maddison Project Database 2023](https://www.rug.nl/ggdc/historicaldevelopment/maddison/releases/maddison-project-database-2023)（Bolt & van Zanden 2024，*Journal of Economic Surveys*；官方文件 mpd2023_web.xlsx，doi:10.34894/INZBF2）：人均 GDP（2011 年国际元）与人口 | 169 个国家（含前苏联、前南斯拉夫、捷克斯洛伐克整体），39,241 个数据点，公元 1 年 – 2022 年；1820 年以前多数国家只有少数基准年 | 年 |
| 经济（1960 起）| [世界银行 World Development Indicators](https://data.worldbank.org/)（API v2，CC BY 4.0）：10 个指标 | 每个指标 207–261 个国家/地区 | 年 |
| 资源点 | Wikidata：mine Q820477、oil field Q211748、natural gas field Q1349255 及子类，有坐标、≥2 个语言版本 | 3,993（矿山 3,529、油田 274、天然气田 190；590 个有开始年代） | 开始/关闭年代 |
| 条约 | Wikidata：treaty Q131569 及全部子类（和约、同盟条约、投资/贸易协定、边界条约……），≥2 个语言版本或有签署方 | 6,221 份，其中 4,661 份有签署方/参与方记录、3,368 份能对应到本应用的政权；中文/英文维基文库原文 240 / 357 份，另有 580 份有全文链接 P953 | 签订/生效/终止 |
| 维基百科摘要 | 维基百科 REST 接口（中文优先，简体；没有中文时英文），**在线获取**并缓存 30 天 | 按需 | — |
| 政权中文名 | Wikidata（经英文维基同名条目）+ Natural Earth 中文名 | 3,078 个名称中 903 个有中文 | — |

构建数据时通过 [QLever](https://qlever.dev/wikidata)（弗赖堡大学的 Wikidata SPARQL 端点，基于完整 Wikidata 转储）查询；也可切换回官方 WDQS。

## 数据是怎么来的（方法说明）

**1. 日期 → 地图快照**：使用「不晚于所选日期的最近一张快照」。例如 1789-07-14 用 1783 年快照，公元前221年用公元前300年快照。
两张快照之间的边界变化不会显示，界面左下角总会说明当前用的是哪一张。公元前3000年以前（文字出现以前）的「边界」是对考古文化与人群分布的粗略复原，不是国家。

**2. 点击的政权 ↔ 事件/人物（最难的部分）**：historical-basemaps 的政权只有英文名，没有 Wikidata ID，
所以主要用 **坐标落在多边形内**（point-in-polygon）来判断归属，这跨越各个时代都稳定：
- 事件：依次使用事件自身坐标（P625）、地点坐标（P276）、参与方（P710，如交战国）的坐标或其首都坐标、国家（P17）的坐标；**任一**落在所点击的多边形内就算；
- 人物：用**出生地**（P19）坐标。所以人物显示在出生地所在的政权，后来可能迁居别处；
- 完全没有坐标时，退回用「国家/国籍」的名称与政权名称比对（标记为「国籍」）。

**3. 人物「在世」**：出生 ≤ 所选日期 ≤ 去世；没有去世日期的，假定不超过 100 岁。
排序：描述中明确写了该职业的优先（Wikidata 的职业很宽泛，例如化学家拉瓦锡也被标为 writer），其次按维基百科语言版本数（知名度）。

**4. 事件排序**：当天 > 当月 > 同一年 > 正在进行中 > 距离越近；同组内按知名度。默认时间窗口：1500 年以后 ±2 年，
公元元年至 1500 年 ±10 年，公元前 ±50～150 年（越古老数据越稀疏）。持续几百年的「时代」类条目只在非常著名时显示。

**5. 城市何时出现**：有建立时间（P571）就从那时起，有废弃时间（P576）就到那时止。没有建立时间的，用「作为首都的最早日期」或「带日期的历史官方名称」推断；
仍然没有的，只在 1800 年以后显示（宁可少显示，也不把现代城市画到古代）。若当时有效的官方名称是中文（如 1928–1937 年的「北平」），就用这个名称；其它语言的历史名称显示在悬停提示里。
首都 ★：Wikidata「首都所属」（P1376）在当日有效，且所属是国家级政权。

**6. 每日新闻**：解析维基百科每日页面的分类与多级列表，最末一级才是一条新闻，上级作为「话题」。条目里链接的地点（国家、城市、行政区）用本地地名表
（`data/gazetteer.json.gz`，13 万个有英文维基条目的地点）定位，任一地点落在所点击的政权内就显示。新闻正文是**英文原文**（中文维基没有对应的每日页面）；地点名称显示中文。

**7. 中文**：标签按 zh-cn → zh-hans → zh → zh-hant 的顺序选择，统一用 OpenCC 转成简体；没有中文时显示英文。

### 地图区域如何对应到 Wikidata 政权（阵营/领导人/政权性质都依赖这一步）

historical-basemaps 的区域只有英文名（如 `Germany`、`English territory`），没有 Wikidata ID。`tools/build_polity_map.py` 为每张快照的每个区域收集候选政权：
1. Natural Earth 自带的 QID（2011 年后的现代边界）；
2. 同名的英文维基条目（`polity_names.json`）；
3. 英文名/英文别名规范化后相同（去掉 Kingdom of、Empire 等）；少数描述性名称用一个很小的别名表（如 `English territory` → Kingdom of England，见脚本中的 `NAME_ALIASES`）；
4. 政权的首都（按首都的起止时间）落在区域内；名称相近的标为「首都位于此范围且名称相近」；
5. 政权自身坐标落在区域内。
候选的存在期必须与快照时期重叠（±30 年）。运行时（`backend/polity.py`）再按**所选日期**筛出当时存在的候选：只精确到年的起止允许 1 年误差。
排序：1–3 和「名称相近」的为「强候选」，排在前面；强候选中存在期**最短**且包含该日期的优先——同一地区同名的多个条目里，它通常就是当时那个具体政权（例如 1938 年的 `Germany` → 「纳粹德国」而不是「德国」）。只凭首都/坐标匹配的「弱候选」（多为下级行政区）不参与阵营着色。

### 阵营、任期的时间判断

- **阵营成员**：成员记录有自己的加入/退出时间就用它；没有就用阵营的成立/解散时间（P571/P576、P580/P582，或「性质」声明上的起止限定，如「同盟国」1939–1945）。同一成员有多条记录时任一条有效即算成员（Wikidata 偶有矛盾，如北约条目把荷兰的加入写成 2004 年，而荷兰条目写 1949 年，两条都列在阵营面板里供核对）。成员政权在该日期本身必须存在。
- 只显示有时间信息的阵营。**既没有解散时间、成员也都没有加入/退出时间的阵营，只在成立后 100 年内显示**（否则像公元前 481 年的 Hellenic League 会一直显示到今天）；图例里标「无解散记录」。
- **任期**：开始 ≤ 日期 ≤ 结束；只精确到年（月）的卸任时间视为该年（月）末。没有卸任时间的，只在此后没有新任职者且不超过 15 年时视为在任。**没有开始时间的任职记录不显示**，这些职位列在「任期未记录的职位」里。
- **执政党**：当时国家元首/政府首脑所属政党（P102，按起止时间；没有时间限定的会标注「未注明时间」）。Wikidata 没有直接的「执政党」属性，这是近似。
- **领导人物**：阵营面板只显示 Wikidata 记录的主席 P488、元首 P35、首脑 P6、负责人 P1037、创始人 P112、重要人物 P3342；没有记录就写「没有记录」，不推测。

### 经济数据怎么对应到地图

Maddison 和世界银行都按**现代国家**统计（Maddison 的历史数值是「今天这个国家范围内」的估计）。所以经济图层画的是现代国界（Natural Earth），不是当时的边界；
面板里列出与所点历史区域**面积重叠**最多的现代国家（≥15%，最多 3 个，`tools/build_econ.py` 预先计算每张快照每个区域与现代国家的重叠比例）。
点到苏联、南斯拉夫、捷克斯洛伐克（当时存在时）会另外列出 Maddison 的「整体」数值；继承国自己没有某年人均 GDP 时，地图用解体前整体的人均值并标注（总量不这样分摊）。

取值规则（`backend/econ.py`）：有该年数据直接用；没有时，若前后数据点相隔 ≤100 年（Maddison）/ ≤5 年（世界银行）则**线性插值并标注**「插值（a–b 年之间）」；
晚于最后一个数据点 ≤5 年 / ≤3 年时沿用最近一年并标注「最近数据：某年」；其余一律「无数据」，不外推。

### 条约与「国家精神」

- 签署方来自 P1891 签署方、P710 参与方；签署人是个人时，用其「代表」限定 P1268 给出的国家；代表也是个人（如君主）时，按 Wikidata 中该君主任该国元首（P35 及任期）的记录找出国家；都没有时才用条约的「国家」P17。
- 生效日期优先 P7588，其次签订 P585、开始 P580。**没有记录终止时间的**条约单独列为「已签订、未记录终止」，只要签署的那个政权当时仍然存在就列出——Wikidata 很少记录条约失效，这不代表条约仍然有效。
- 同盟条约喂给阵营地图：Wikidata 的同盟条目自身没有成员、但与某些条约互相引用时，用条约签署方作成员；类型名含 alliance 的条约本身也作为阵营。
  **英葡同盟**在 Wikidata 中与 1373 年英葡条约、1386 年温莎条约之间没有任何链接，本应用按英文维基百科条目的说明人工关联（`tools/build_treaties.py` 中的 `CURATED_LINKS`，只此一例），成员仍只取两份条约在 Wikidata 中记录的签署方/参与方（英格兰王国、英格兰、葡萄牙）。

## 每日新闻自动更新

应用运行期间，后台线程每 60 分钟（可配置）抓取**最近 3 天**的维基百科每日页面（当天的页面一天里会不断补充）。
如果电脑很久没有打开，下次启动会自动补抓缺失的日期（一次最多 400 天）。没有网络时静默跳过，下次再试。
从源码运行时，新数据写入 `data/live/`（这个目录不可写时用系统用户目录）。
免安装版始终写入 `~/Library/Application Support/WorldHistoryAtlas`（Windows 是 `%APPDATA%\WorldHistoryAtlas`），不会改动软件包里的数据。

环境变量：`WHA_AUTO_UPDATE=0` 关闭自动更新；`WHA_UPDATE_MINUTES=30` 改为每 30 分钟。
请求遵守 MediaWiki API 规范：带 User-Agent、串行、每次最多 50 页、间隔 ≥1 秒。

## 目录结构

```
（仓库根目录就是程序目录）
├─ start.command / start.sh / start.bat   源码启动脚本（需要本机已安装 Python）
├─ run.py                                  源码启动入口
├─ launcher.py                             免安装版入口（用户数据目录、自动选端口、打开浏览器）
├─ packaging/                              PyInstaller 配置、打包脚本、冒烟测试
├─ .github/workflows/build.yml             macOS / Windows 自动打包与发布
├─ requirements.txt
├─ backend/
│  ├─ config.py        路径/端口等配置（都可用环境变量覆盖：WHA_PORT、WHA_DATA_DIR、WHA_USER_DATA_DIR …）
│  ├─ app.py           FastAPI 接口
│  ├─ registry.py      ★ 模块注册表（插件架构）
│  ├─ geo.py           边界快照加载与空间查询
│  ├─ timeutil.py      日期（含公元前）工具
│  ├─ polity.py        ★ 地图区域 + 日期 → Wikidata 政权
│  ├─ details.py       人物页面 / 机构卡片 / 阵营面板接口
│  ├─ datafile.py      读取 .json.gz / .json.xz 数据文件
│  ├─ econ.py          经济数据与取值/插值规则
│  ├─ live/            每日新闻抓取、解析与后台调度；wiki.py 维基百科摘要（在线 + 缓存）
│  └─ modules/         ★ 内容模块：每个文件一个模块，自动发现
│     ├─ events.py               事件
│     ├─ news.py                 每日新闻
│     ├─ people_writer.py        文学家
│     ├─ people_philosopher.py   哲学家
│     ├─ people_politician.py    政治家
│     ├─ regime.py               政权性质
│     ├─ leaders.py              领导人
│     ├─ layer_cities.py         地图图层：主要城市
│     ├─ layer_alliances.py      地图图层：阵营地图
│     ├─ layer_economy.py        地图图层：经济（现代国界分级设色）
│     ├─ layer_resources.py      地图图层：资源点
│     ├─ econ_panel.py           民生经济
│     ├─ spirits.py              国家精神（条约与同盟）
│     ├─ _people_base.py         人物类模块的通用实现
│     └─ _common.py              共用工具（以 _ 开头的文件不会被注册）
├─ frontend/
│  ├─ index.html / app.js / style.css
│  ├─ modules/cities.js          城市图层的前端绘制
│  ├─ modules/alliances.js       阵营图层（着色、图例）
│  ├─ modules/statepanels.js     政权性质/领导人/国家精神面板、人物页面、机构卡片、阵营面板、条约详情
│  ├─ modules/economy.js         经济图层、资源图层、民生经济面板（趋势图）
│  └─ vendor/leaflet/            本地 Leaflet
├─ data/                         数据（可与程序分开更新）
└─ tools/                        数据构建脚本（需要联网）
```

## 如何添加新的内容（模块）

模块有两种：**侧边栏标签页**（`kind="panel"`，点击政权后显示列表）和**地图图层**（`kind="layer"`，随日期叠加在地图上）。
后端启动时会自动导入 `backend/modules/` 下所有不以 `_` 开头的文件，注册其中的 `MODULE`（或 `MODULES` 列表）；
前端从 `/api/modules` 读取清单，自动生成标签页和图层开关。**新增一个类别 = 新增一个文件**，不需要改其它代码。

### 例 1：新增一个人物类别「画家」

1. 在 `tools/build_wikidata.py` 的 `PEOPLE_CATEGORIES` 里加一行：
   `"painter": ("画家", ["Q1028181"], 15, 20000),`（Q1028181 = painter），然后运行
   `python tools/build_wikidata.py --only people --cats painter`，生成 `data/people_painter.json.gz`。
2. 新建 `backend/modules/people_painter.py`：
   ```python
   from ._people_base import PeopleModule
   MODULE = PeopleModule("people_painter", "画家", "people_painter.json.gz", order=45,
                         keywords=("画家", "painter"))
   ```
3. 重启应用，侧边栏就多了「画家」标签页。

### 例 2：全新的侧边栏模块

```python
# backend/modules/my_topic.py
from ..registry import ContentModule

class MyTopic(ContentModule):
    id, title, order = "my_topic", "我的主题", 60
    description = "说明文字"
    source = "数据来源说明"

    def load(self, ctx):            # 启动时读取自己的数据文件（ctx.data_dir）
        ...

    def query(self, ctx, polity, date, params):
        # polity: {"props": {...}, "geom": shapely 多边形}；None 表示「全世界」
        # date: HDate(y, m, d)，y<0 为公元前
        return {"items": [ {"id": "Q1", "title": "…", "date": "…", "subtitle": "…",
                            "coord": [经度, 纬度], "match": "coord",
                            "links": [{"label": "Wikidata", "url": "…"}]} ],
                "total": 1, "note": "说明"}

MODULE = MyTopic()
```
返回统一格式的条目时，前端自动用通用列表显示；如需特殊界面，设置 `frontend = "modules/my_topic.js"`，
在该脚本里调用 `WHA.registerRenderer("my_topic", (result, manifest) => DOM元素)`。

### 例 3：地图图层（以后的「阵营地图」「经济地图」都按这种方式加）

后端继承 `LayerModule`，实现 `layer_query(ctx, date, params)`；前端脚本调用
`WHA.registerLayer("id", {init(map), update(data, state), clear()})`。参考 `layer_cities.py` + `frontend/modules/cities.js`。
要给国家着色的图层（如阵营地图）用 `WHA.setFillOverride(f => ({fillColor, fillOpacity}) 或 null)`；
地图区域对应的政权 QID 可在后端用 `resolver(ctx).strong(snap, fid, date)` 取得（见 `layer_alliances.py`）。
前端还可使用 `WHA.showPerson(qid)` / `WHA.showOffice(qid)` / `WHA.showBloc(qid)` 打开详情窗口。

## 重新构建数据（可选，需要联网）

```bash
.venv/bin/pip install requests opencc-python-reimplemented
python tools/build_basemaps.py            # 边界（原始 GeoJSON 放在 data/basemaps_raw/）
python tools/build_wikidata.py            # 事件 + 人物 + 国家表（几分钟）
python tools/build_places.py              # 城市 + 地名表
python tools/build_polity_names.py        # 政权中文名
python tools/build_current_events.py --from 1995-01-01   # 每日新闻回填（约 10 分钟）
python tools/build_states.py              # 政权、职位、人物、阵营（约 10 分钟）
python tools/build_polity_map.py          # 地图区域 → 政权候选（几秒）
python tools/build_treaties.py            # 条约（并把同盟条约追加到阵营数据；须在 build_states 之后）
python tools/build_resources.py           # 资源点
.venv/bin/pip install openpyxl && python tools/build_econ.py   # Maddison 2023 + 世界银行 + 现代国家重叠（约 2 分钟）
python tools/make_zip.py                  # 打包（数据改用 .xz 压缩，内容不变）
```

## 已知局限

- 边界只在快照年份更新；中国古代快照很粗（如公元前300年快照里秦只占西部）；许多政权名称还没有中文（显示英文原名）。
- Wikidata 对欧洲、近现代的覆盖远多于其他地区和上古；公元前2000年前后几乎没有精确到年的事件。**没有记录 ≠ 没有发生**。
- Wikidata 本身偶有错误（例如某条古代战争的「地点」写成整个「东亚」），本应用照原样使用，并附上 Wikidata 链接便于核对。
- 职业标签宽泛：一些人会同时出现在几个类别里。
- 中国古代城市较少：Wikidata 中许多城市条目描述的是现代地级市（建立时间为 20 世纪），古都（如长安）常是单独的、知名度较低的条目。
- 每日新闻为英文原文；1995–2002 年只来自年份条目，条目较少。
- **阵营**：只有 70 个阵营在 Wikidata 里有 ≥2 个政权成员。许多著名同盟在 Wikidata 中没有成员数据，例如**英葡同盟（1373）没有成员**，所以 1373 年的英格兰只能显示「老同盟」（法国—苏格兰）一侧；条约类同盟计划在后续「条约 / 国家精神」阶段补充。轴心国、同盟国的成员没有各自的加入/退出时间，整段 1940–1945 / 1939–1945 都按成员显示（例如南斯拉夫同时出现在两边）。
- 地图边界仍按快照：1942 年用的是 1938 年快照（看不到维希法国、被占领区等）。
- **领导人**：许多职位的任职记录缺少任期（例如「立法院长」的大多数任职者），这些职位只列名称，不判断谁在任。中国古代王朝的皇帝在 Wikidata 中多用「君主」等通用职位记录，覆盖较差。
- 「政体」若 Wikidata 没有时间限定，会列出该条目的全部政体并标「未注明时间」（例如纳粹德国条目同时列有共和制、总统制等）。
- **经济**：1820 年以前 Maddison 多数国家只有几个基准年（如 1500、1600、1700），中间年份是标注出来的插值；公元前没有数据。数值都按现代国界，不能当作当时政权的数值。
- **资源**：Wikidata 的矿山/油气田条目以欧洲、北美、澳大利亚为主，只有约 15% 记录了开始年代（无年代的只在 2000 年以后显示）；这不是完整的资源分布图。
- **条约**：Wikidata 很少记录条约终止，所以「未记录终止」一栏会包括早已失效的条约；维也纳会议最后议定书只能确认 4 个签署国（其余签署人在 Wikidata 中没有可用的「代表」/元首记录）；1386 年温莎条约的参与方记为「英格兰」而非「英格兰王国」；Wikidata 记的 1373 年英葡条约日期是 6 月 24 日，英文维基写 6 月 16 日（照 Wikidata 原样显示）。
- 经济图层打开时，历史区域的填色（包括阵营着色）会变透明。
- 人物页面、机构卡片、维基百科定义需要联网（离线时只显示 Wikidata 简介和本地数据）。

## 许可

代码供个人学习使用。数据许可：historical-basemaps GPL-3.0；Wikidata CC0；维基百科内容 CC BY-SA 4.0；Natural Earth 公有领域；Leaflet BSD-2-Clause。
