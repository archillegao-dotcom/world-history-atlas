# v0.5 进度日志（Europe/Paris 时间）

## 2026-11-01 21:57 恢复
- 环境被重置：/tmp 清空、.venv 丢失 → 已重建 .venv（requirements.txt）。辅助脚本移到 tools/dev/（不再放 /tmp）。
- 发现并修复：首次 enrich_text 的机器翻译全是乱码 —— ctranslate2 4.8.4 在 inter_threads>1 时批量结果错乱（实测）。
  改为 inter_threads=1；加入质量把关 plausible()；加入 unapply() 先撤销旧译文（可重复运行）；乱码缓存已丢弃。
- enrich_text 重新运行中：logs/enrich.log（MT 缓存 21k/133k 起续）。

## 阶段 A：服务器 8792 + 关键验证截图
- 22:08 enrich_text 完成（MT 缓存 133k 条）；22:19 加强质量把关后重跑（只用缓存）
- 22:20 发现 int8 量化同样产生乱码；改为 float32 + beam 4 + 按句翻译，新缓存 data/cache/mt_en_zh_f32.json.gz，后台重跑 logs/enrich3.log
- 22:23 修复：restart 脚本只杀本项目进程；run.py 端口检测加 SO_REUSEADDR（以前会悄悄换到 8793）；任期只精确到年的卸任以下一任精确就任日为准（单人职位），1950-06 台湾行政院长只显示陈诚

## 2026-11-01 22:48 新会话接手
- 服务器 8792 仍在运行（pid 102662，22:23 启动）；enrich3 进度 133k/136k 仍在跑。开始阶段 A 验证。
- 22:53 enrich3 完成（float32+beam4）；重启服务器以加载新数据
- 22:58 .venv 缺 playwright → pip install playwright + chromium（截图工具用）
- 23:05 先秦君主（Q38702033）前841年以前加「传统纪年」注释、显示名改为「王（君主）」（leaders.py LEGENDARY / OFFICE_NAME_ZH）；扫描 -123000…-1448 所有多边形，无罗马等时代错乱（tools/dev/scan_anachron.py）
- 23:00 修复：英属香港时期（1990）面板误显示「特别行政区/主权国 China」。build_transitions 增加 ERAS：香港、澳门按时期拆分（英属香港 1841-01-26–1997-07-01 / 香港特区；葡属澳门 1557–1999-12-20 / 澳门特区），名称、主权国、类别随日期变化；territory_info 增加 hk_uk / mo_pt 类别与主权国中文名；leaders 过滤外国驻华大使等外交职位。备份：tools/dev/build_transitions.py.bak、data/cache/transitions.json.gz.bak_2250
- 23:09 阶段 A 完成。截图 screenshots/v05/01–12（tools/dev/shots_v05.sh，日志 logs/shots_v05.log），逐张人工检查通过：
  1950 大陆=中华人民共和国、台湾=中华民国、无满洲国（1944 仍有满洲国）；2020 中华人民共和国/中华民国面板分开；-1448 商朝（王 祖丁，附传统纪年注）；
  -5000/-3000 无罗马等时代错乱国家（全多边形扫描 tools/dev/scan_anachron.py）；香港 1990 英属/2020 特区；澳门 1980 葡属；《南京条约》中文简介。
  服务器 8792 运行中（tools/dev/restart.sh）。
- 未完成（阶段 B+）：AUDIT_REPORT.md 未写（只有 data/audit/*.json）；official_offices 只覆盖 4 个职位；机器翻译覆盖率统计；Seshat 交叉核对（data/xcheck/seshat.json 已有，未整合进报告）；war_fronts 模块未开始（复用 /workspace/ukraine_front）。
  小问题记录：-2000「Canaan」名称匹配到「腓尼基」；香港特区 1997 面板仍出现「王室法律顾问」（Wikidata 任期无终止）；1950 中华人民共和国面板含「主席夫人/第一夫人」重复条目；1980 葡属澳门无总督任职记录；香港范围 1860/1898 年前为现代范围近似。

## 阶段 B（2026-11-01 23:10 起）
- 23:10 开始：小问题修复 → audit → official offices → 翻译覆盖率 → Seshat → 中国抽样 → AUDIT_REPORT.md
- 23:13 收到新需求：sub-national control zones 图层（data/curated/control_zones.json，通用格式供 war_fronts 复用）：海南、舟山、金马、大陈、万山、西藏/昌都、缅北国民党残军、1949–50 西南战区；截图 1950-03 华南、1950-06。
- 23:13 已完成：Canaan 名称排除表（data/curated/match_block.json + polity.py）；leaders 过滤配偶/第一夫人/QC 等非领导头衔
- 23:40 official offices：新增来源 爱丽舍宫（法总统，核对）、美国国务院历史办公室（国务卿，核对）、英文维基 Governor of Macau（澳门总督 107 条，1980 伊芝迪）、Premier of the Soviet Union（12 条）、Wikidata P39 补充（苏共总书记等）；backend/official.py 支持 qid 与多来源键；覆盖率 tools/official_coverage.py → data/audit/official_coverage.json
- 00:05 control zones：data/curated/control_zones.json（10 区）+ tools/build_control_zones.py → data/control_zones.json.gz；backend/control_zones.py、modules/layer_control_zones.py、frontend/modules/control_zones.js；as_polity 区域并入 transitions（海南/舟山/万山/大陈/西南/昌都）；HK 英属起始改为 1842-08-29 + 范围近似说明
- 00:30 Seshat 交叉核对修正匹配：不再去掉 empire/kingdom 等类型词、名称 ≥5 字母、人工排除表（原 82 条中「罗马帝国↔Roman Kingdom」「鄂国↔Dynasty of E」等误配去除）→ 57 条；translation_coverage.py；audit.py 新增 leader_terms/city_country/event_attribution/control_zones 与经济映射未覆盖统计
- 23:53 更正：上面两条「00:05」「00:30」的时间写错了（实际都在 23:52 之前，系统时钟为准）。
- 23:53 audit 修正与重跑：
  - leader_terms 误报（同一人多段任期，如 Q310829 国务卿两段任期）→ 改为「此人任一段任期覆盖该日」才算合法；月精度给 1 个月余量 → term_violations 1626 → 0。
  - 同盟：集安组织—乌兹别克斯坦成员期出现倒序区间（Wikidata 一个陈述多个起止限定词，SPARQL 笛卡尔积）→ data/curated/alliance_member_fixes.json（1992-05-15–1999、2006–2012-06-28，来源英文维基）+ tools/dev/apply_alliance_fixes.py（build_states 也调用，并丢弃倒序区间）→ reversed 1 → 0。
  - 金朝：historical-basemaps 1100/1200 年快照都把淮河以北画成宋朝 → 实际控制区新增 jin_north_china_1127（1127-01–1234-02，《绍兴和议》淮河—大散关线手工近似，大致范围）、mongol_north_china_1234（–1271-12-18）、yuan_north_china_1271（–1279-03-19）。1150 年洛阳=金朝、杭州=南宋。
  - 城市首都：Wikidata 无起止的首都记录按政权整个存在期显示，导致 220 年北京为首都等 → data/curated/capital_fixes.json（北京、平壤、德黑兰、里斯本、哥本哈根、奥斯陆、明斯克、贝尔格莱德、喀布尔、维尔纽斯，以及西安/洛阳/南京/开封/杭州历代都城，均注来源）；backend/modules/layer_cities.py 读取；audit 新增 undated_long_capital 统计（206 条剩余）。
  - 中国皇帝：Wikidata 部分任职记录 P1001 只写「汉朝/宋朝」或缺失，导致西汉无刘邦、北宋 970 无宋太祖、武周无武则天 → tools/build_china_emperor_fill.py（只补缺口、排除并立称帝者）→ data/ruler_fills.json.gz（9 条）；data/curated/ruler_blocks.json 去掉「赵佗=西汉皇帝」；leaders 配偶过滤加「皇后/王后/可敦」。
  - 中国抽样表改为经运行中的服务查询（含过渡层/控制区）：tools/china_table.py → data/audit/china_table.md / .json。
  - 截图 screenshots/v06_stageB/01–13（tools/dev/shots_B.sh）。
- 00:03 补充：只有终止、无开始的首都记录（29 条，如成都「中华民国首都 至 1949」）在城市图层改为从所属政权成立起算；capital_fixes 增加许昌（196–220）、成都（蜀汉/前蜀/后蜀/中华民国 1949-11-29–12-10），共 17 城 54 段。
- 00:03 最终 audit（logs/audit_B3.log，data/audit/audit_results.json）：lifespan 违规 0；leader_terms 0；同盟倒序 0；控制区 13 个全部有来源；城市无起止长期首都 206→194。
- 00:04 AUDIT_REPORT.md 写完（检查项与前后计数、修正、控制区、官方名单覆盖率、翻译覆盖率、Seshat、中国抽样表、已知缺口、来源与许可）。截图 screenshots/v06_stageB/01–15 已逐张查看。服务器 8792 运行中。阶段 B 完成；未开始 war_fronts；未推送。

## 阶段 C（11-02，巴黎时间）
- 00:16 (1) 金/辽修正：新增控制区 jin_former_liao_1125（1125 至 1127-01-01，辽 1100 快照多边形 → 金，来源 Wikipedia 辽朝/天祚帝/西辽、Wikidata Q4958）；jin_north_china_1127 / mongol_north_china_1234 / yuan_north_china_1271 几何加 union 辽故地，名称改为「金朝（辽朝故地 + 淮河—秦岭以北）」等。build_control_zones.py 支持 union。控制区共 14 个。
- 00:16 同色问题：前端填色改为按解析出的政权 QID，同一政权不同多边形同色；改日期后 restyle。
- 00:16 解散政权多边形残留：tools/dev/scan_succession.py 扫描（logs/scan_succession2.log 366 例 → data/audit/succession_scan.json）。PolityResolver 新增「分裂」判定：多个后继同时成立时不指定单一后继，面板显示「已分裂为 X、Y 等；边界到下一张快照才更新」（法蒂玛→的黎波里伯国、西罗马→汪达尔、秘鲁、拉普拉塔、马拉塔等）。同一领土的政体更替（巴西、伊朗等）不受影响；170 例无后继者保持未匹配。阿根廷 1840 无 Wikidata 首都，分裂列表不全（已知缺口）。
- 00:16 截图 screenshots/v07/01_1124、02_1130、03_1150 已查看：1130/1150 东北+华北为同一金朝多边形，面板为金太宗/完颜亮。audit 重跑（logs/audit_C.log）：lifespan 违规 0，leader_terms 0。
- 00:16 (2) war_fronts 开始：tools/build_war_fronts_ukraine.py 从 /workspace/ukraine_front 直接读取（ISW 2022-02-24–04-02，DeepState 2022-04-03 起，2014 克里米亚 / 2015 顿巴斯基线），生成 data/war_fronts/russo_ukrainian_war.json.gz（3,128 条记录，control_zones 格式 + dataset/snapshot/area_km2）和 1,582 个几何文件，数据到 2026-11-01，共 34 MB。
- 00:16 backend/modules/layer_war_fronts.py（默认关闭；同数据集内与上一快照比较面积；超出数据截止日会提示）+ frontend/modules/war_fronts.js（红=占领，灰=灰色区，近似范围用虚线，说明框附来源链接）。截图 screenshots/v07/10_2018 基线、11_2022-03-15（ISW，122,002 km²）、12_2022-11-15（107,855 km²）、13_2026-11-01（116,426 km² + 灰色区 1,637 km²）已查看。
- 00:16 其他战争数据调研 → data/war_fronts/CANDIDATES.md：叙利亚（Carter Center 逐月 8,099 个居民点，候选；ACLED；维基模块）可行；二战没有找到开放的逐日矢量前线数据（只有原始态势图扫描；风格化/示意数据不收）。未推送。
- 00:26 用语调整（用户决定）：自撰中文叙述中「国民党军/国军/国民党残军」→「国民革命军（残部）」，「解放军」→「共军」。共 11 处：data/curated/control_zones.json 9 处、backend/modules/layer_control_zones.py 1 处、AUDIT_REPORT.md 1 处；专名「云南反共救国军」、「中华民国军队」、英文条目名不改。重建 control_zones.json.gz、transitions.json.gz，服务器已重启。
- 00:26 v0.5.0 发布准备：从 GitHub 拉取 v0.4.1（codeload），把仓库独有的 launcher.py、packaging/、.github/、退出按钮（index.html、app.py 的 /quit 与 /api/shutdown、boot()）、config.py/registry.py/requirements.txt 合并进本地（备份 tools/dev/premerge_v050/）。official.py、layer_war_fronts.py 改走 datafile（支持 .xz）。spec/workflow 版本默认 0.5.0。README 增加更新记录；MERGE_NOTES.md。暂存目录 /workspace/wh_v050_stage（数据全转 .xz，51 MB）；用仓库 smoke_check.py 测试暂存目录和三个 zip 解压后的目录均通过。zip：/workspace/wh_v050_part1–3.zip。未推送。

## 阶段 D：v0.5.0 用户 bug 修复 + 二战/中日战争控制区 + 战争审计（11-02，巴黎时间；补记）
- 02:20 补记（00:26 之后完成、未及时记录的内容；时间取文件修改时间，精确到「约」）：
  - 约 01:00–01:28 CShapes 2.0 底图接入（1886-01-01–2019-12-31）：backend/cshapes.py（快照 ID「cs@YYYYMMDD」，fid 300000+行、390000+补充、200000+特殊领土；CShapes 未覆盖部分用 historical-basemaps 裁剪剩余）；tools/build_cshapes.py → data/cshapes.json.gz（3.25 MB，26 个补充：微型国家/小岛、满洲国 Q30623 1932-03-01–1945-08-19 近似几何、斯洛文尼亚/克罗地亚 1991-10-08 起、波黑 1992-04-06 起、密克罗尼西亚 1986-11-03 起）。geo.py/polity.py 增加 cs/csx 候选（gwcode→Wikidata，带时段），殖民地无独立政权时回退到宗主国并标「（宗主国+地位）」。
  - 01:43 二战欧洲：tools/build_ww2_europe.py 读取 Stanford Spatial History Lab「Building the New Order: 1938-1945」逐月 shapefile（data/ww2_raw/，1938-02–1945-05，重投影+简化）→ data/ww2_europe.json.gz（88 个月，282 个去重几何）。只记录吞并与新设实体，不含前线。许可：学术使用，禁止商业。
  - 01:51 backend/ww2.py 战线引擎 + tools/curated_src/war_fronts_hist.py → data/curated/war_fronts_hist.json：东线 17 步（1941-06-22–1945-06-05，含敖德萨/塞瓦斯托波尔/斯大林格勒/布达佩斯/柯尼斯堡/布雷斯劳等包围圈）、西线 1940 与 1944–45、意大利 7 步、北非 9 步、突尼斯 2 步；每步注明精度与来源（USMA 西点军校历史地图集图名、Wikipedia）。参战方随日期切换（意大利 1943-09-08、罗马尼亚 1944-08-23、保加利亚 1944-09-09、芬兰 1944-09-19）。
  - 01:52 中日战争/太平洋：tools/curated_src/zones_asia_ww2.py 重写控制区 sino_japanese_war / ww2_asia / ccw_manchuria 三组（56 区，全部 70 区）：1931–32 东北、热河 1933-03-04 起、冀东、察北、蒙疆、日占区 8 级阶梯 × 各伪政权（临时政府、华北政务委员会、维新政府、汪政权 1940-03-30）、共军根据地（近似）、苏军占领东北 1945-08-19–1946-05-03、共军控制东北分阶段至 1949-10-01；香港、马来亚、新加坡、婆罗洲、荷属东印度、菲律宾、缅甸、印度支那、帝汶、安达曼、关岛、瑙鲁、吉尔伯特。build_control_zones.py 新增 cshapes / intersect 几何规格，跳过空几何。
  - 01:51 tools/build_runtime_states.py → data/curated/runtime_states.json（38 个 states.json 缺失的 QID，从 Wikidata 取，opencc 转简体）。
  - 战前必过项第一轮（logs/mustpass2.log 之前的一次）：1992 苏联 15 国、新加坡 1950 殖民地/1964 马来西亚/1966 独立、满洲国 1940、1952 中华人民共和国、1947 中华民国、捷克 1993/捷克斯洛伐克 1992-12-31、德国 1990-10-04 统一/10-02 民主德国、港澳面板、波兰 1950 —— 通过；克罗地亚 1992-01-01 显示南斯拉夫 → 已加早期补充（待复测）。
- 02:20 性能：cs@19421201 合成原需 507 s（对全球覆盖做 difference）。改为 STRtree 局部 union、Stanford 切割按（行, 相交 Stanford 几何集）缓存、HB 剩余按候选集合缓存并用简化几何判断覆盖 → 战时月份约 12 s、普通年份约 2.5 s。备份 tools/dev/premerge_v050/cshapes.py.bak_E。
- 02:25 合成结果磁盘缓存：CShapes.compose 结果按数据版本（相关数据/代码文件大小+修改时间的哈希）pickle 到用户数据目录 cache/cs_compose/，再次打开同一日期 0.0–0.2 s。tools/dev/warm_cs.py 并行预热（logs/warm_cs_1931_1950.log）。
- 02:25 按日期国旗：tools/build_flags.py → data/flags.json.gz（Wikidata P41 全部语句含起止，2010 个政权、256 个带日期；排除「Fictitious」虚构旗）；data/curated/flag_overrides.json（中华民国：五色旗 1912-01-10–1928-12-17，青天白日满地红 1928-12-17 起，来源英文维基「Flag of the Republic of China」/《中华民国国徽国旗法》）；backend/flags.py flag_at（有带日期语句但都不覆盖所选日期时不显示，不拿别的年代的旗充数）。
- 02:25 政权更替链：tools/curated_src/regime_chains.py → data/curated/regime_chains.json（法、德、意、西、俄、中、日、波 8 国 63 行，1800 年至今，每行英文维基来源、QID 经维基 API 解析，并立政权标出）；backend/regimes.py；政权面板显示「所选日期的政权」和更替表；当前行非并立政权时把国家总条目并入同组（领导人按日期过滤）。cshapes_periods 加法国 220（第三共和国→维希→临时政府→第四共和国→1958-10-04 起法国/第五共和国），意大利共和国改为 1946-06-02。重建 cshapes.json.gz。
- 02:25 验收脚本 tools/accept/api_mustpass.py（约 110 条：苏联 15 国、南斯拉夫、捷克斯洛伐克、德国统一、满洲国、东北 1947、只选年份 1940/1950/1952、新加坡、港澳/波兰/格陵兰/波多黎各面板、法国等政权链、国旗、西汉、二战欧洲/北非、中日战争、太平洋）开始运行（logs/accept_api_D1.log）。
- 02:38 验收第一轮（logs/accept_api_D1.log）：109/117 = 93.2%。失败项与修正：
  - 1938-12 南京显示「日军占领区（华中/华南）」：华中/华南框与维新政府框重叠、后画的覆盖前者 → 华中/华南框去掉维新政府辖区（SOUTH_NOT_EAST）。
  - 1940-07 / 1942-12 维希、克莱蒙费朗显示「德占法国」：Stanford 数据把停战后的法国本土整体标为德意占领 → 新增 tools/curated_src/zones_europe_ww2.py：按停战分界线（法文维基逐省走向，依据 1941 年米其林地图；城镇连线 ±5–15 km）画出非占领区（1940-06-25–1942-11-11，维希政府直接管辖）与 1942-11-11 后的「维希法国（被德意占领）」（至 1944-08-25）。意大利占领区未画（列入已知缺口）。
  - 1945-06-01 柏林显示「德意志国」：CShapes 1945-05-08 起的东/西德「占领」行没有分期 → 265：苏占区 Q55300（–1949-10-07）；260：盟军占领下的德国 Q2415901（–1949-05-23）；305 奥地利：1945-04-27–1955-07-27 盟军占领下的奥地利 Q596239。
  - 政权链新增奥地利、土耳其、南斯拉夫（共 11 国 82 行）。
  - 斯大林格勒 1942-12-24 城区为被围的德军第 6 集团军所据，原测试期望写错，改为伏尔加河东岸=苏联、城区=德军、罗斯托夫=德军。
  - 西汉公元 1 年：tools/build_china_eras.py 解析英文维基「List of Chinese era names」→ data/china_eras.json.gz（1104 个年号、650 位君主，QID 经维基 API；本名取中文维基首句「庙号/谥号+本名（」模式及 Wikidata P1477/P1559，163 位有本名）；data/curated/regents.json（王莽、霍光、多尔衮、载沣，各注来源）；领导人面板显示「汉平帝（刘衎）」、摄政/辅政、年号「元始」。
- 02:45 微型国家/虚构排除：tools/build_state_exclusions.py → data/curated/state_exclusions.json（instance of 微型国家/虚构国家/虚构地点，及无起始时间的虚构实体，共 91 个，含 Zaqistan Q23135734），PolityResolver 加载后不作为候选。
- 02:45 前端：乌克兰战线在 2014-02-20 后、地图视野包含乌克兰时自动开启（用户手动关闭后不再自动开）；小于 1.2° 的多边形另画最小 5 px 圆点（世界尺度可点击微型国家）；点击城市标记改为选中所在政权（Ctrl/⌘-点击打开维基条目）。
- 02:45 验收第三轮（logs/accept_api_D3.log）：116/119 = 97.5%；失败：1939-10-15 华沙/利沃夫（Stanford 1939-09 月份文件尚未体现瓜分）、1941 的黎波里（CShapes 620 利比亚无意属分期）→ war_fronts_hist.json 加 stanford_month_override（1939-09-28–1939-11-01 使用 1939-10 月份），cshapes_periods 620：意属利比亚 Q284568 1934-01-01–1943-05-13、英法军管 Q16953965 –1951-12-24、利比亚王国 Q31454 –1969-09-01、之后 Q1016。重建（logs/rebuild_D4.log）。
- 02:45 连续审计第一轮（1900 年起每月 1/15 日，logs/audit_cont_*.log，修正前运行）：-3000–1899 124、1900–1930 77、1931–1950 119（另 494 未匹配）、1951–1985 348、1986–2026 60。主因：1800 年后只精确到年的存在期被放宽 ±1 年（年精度键值为年中），导致 1959 年尼日尔等法属殖民地、1989 年纳米比亚在独立前即显示为独立国家 → polity.alive 对 1800 年后改为「该年 1 月 1 日–12 月 31 日」严格判断。服务器已重启，全量预热 1886–2026（logs/warm_cs_all_D4.log）。
- 02:53 连续审计第二轮（logs/audit_cont2_*.log，严格存在期）：1900–1930、1931–1950、1951–1985、1986–2026 每月 1/15 日违规均为 0（1931–1950 另有 494 个多边形-日期属于没有 Wikidata 起始时间的人工控制区，按其自身起止显示，不计违规；分期与 Wikidata 不一致 48 处单列）；-3000–1899（每年 7 月 1 日）74 处，全部是古代政权只精确到年的端点（±1 年放宽规则仍在 1800 年前使用）。
- 02:53 中国君主逐年覆盖测试 tools/accept/china_monarchs.py（前221–1911 每年 7 月 1 日，洛阳/西安/南京/杭州/北京依次点选）：第一轮 2112/2132（99.1%）。修正：朝代起止只精确到年时用首任/末任皇帝任职日期细化（polity.py；1644-07 由明朝改为南明/清）；同一多边形的朝代候选中，没有在位皇帝的朝代让位（后梁 581–587）；Toba Wei 多边形组加隋朝、主序列加西楚（前206–前202）。南越国误显示于洛阳（前205–前203）随之消失（待复测）。
- 03:09 补记（02:53–03:08）：
  - API 验收第五轮（logs/accept_api_D5.log）：119/119 = 100%（波兰 1939-10、的黎波里修正生效）。
  - 中国君主逐年覆盖第二轮（logs/china_monarchs.log）：2125/2132 = 99.7%，2 个有据空位期（前74 汉昭帝卒—刘贺立；1333 元宁宗卒—元顺帝立），数据缺口 前206–前202 西楚（Wikidata 只有项羽、无任期）→ leaders.py：存续 ≤30 年且只有一位无日期元首的政权，在存续期内显示该元首并注明「任期取该政权存续期」（待复测）。
  - 全球战争审计第一轮 tools/accept/war_audit.py（logs/war_audit.log）：58/83 = 69.9%。查出 CShapes 行没有对应政权的问题（tools/dev/unresolved_scan.py → data/audit/unresolved_cs.json）：埃塞俄比亚 1886–1995、北也门 1919–62、科威特 1961–90、南也门 1968–89、但泽、马达加斯加 1886–96、斯威士兰 1895–1901、越南国 1954–55、爱尔兰 1922、土耳其 1923、二战时期微型国家 → cshapes_periods 新增 530/678/680/690（含 1990-08-02—1991-02-26 伊拉克科威特省）/291/580/572/817/205/640 分期（均注英文维基来源）；Stanford 名称表中安道尔/列支敦士登/摩纳哥/圣马力诺改用 QID。重建 logs/rebuild_D6.log 完成。
  - UN 点击测试 tools/accept/click_un.py 2020 跑到 134/193 时中止：发现城市名称标签拦截点击（点以色列南部选中埃及、点列支敦士登选中瑞士）→ style.css：城市图标容器不拦截点击，只有圆点/★可点。赤道几内亚、新西兰的 Natural Earth 标注点在海上 → 测试改用多边形内点。
- 03:10 KNOWN_ISSUES.md 初稿（二战欧洲/中日/1886 前底图/CShapes 不表示的占领/君主/国旗/城市首都误标）。服务器已重启，全量预热中（logs/warm_cs_all_D6.log），UN 点击 2020 重跑中（logs/click_un_2020.log）。
- 03:11 新增用户式截图脚本 tools/accept/shots_v08.py（顶栏输入年份/选月日或不选 → 跳转 → 点击地图 → 切换标签 → 截图，标题与正文记入 logs/shots_v08.json）；试拍 60_2020 法国面板已查看：所选日期的政权=法兰西第五共和国，三色旗，政权更替表正确。war_audit.py 修正期望（台湾日据时期、佛朗哥时期、马尔维纳斯群岛为同一条目）并新增俄乌前线图层点位检查 6 条。
- 03:12 书籍交叉核对脚本 tools/accept/book_xcheck.py：OpenStax World History 第 1/2 卷 18 条带日期的政权更替（君士坦丁堡 1453、莫卧儿 1526、意大利 1861/1870、德意志 1871、台湾 1895、朝鲜 1910、印巴 1947、印尼 1949、加纳 1957），每条附章节网址与原文要点。
- 03:15 书籍核对第一轮 16/18：1452 君士坦丁堡显示奥斯曼（historical-basemaps 1400 快照把城画入奥斯曼）、1872 柏林显示普鲁士（1815 快照仍为各邦）→ 新增控制区组 europe_19c：拜占庭帝国（君士坦丁堡近似范围，1400-01-01—1453-05-29）、德意志帝国（1871-01-18—1878-01-01，用 1878 快照德国范围），注 OpenStax 与英文维基来源。重建 control_zones/transitions，重启并重新全量预热（logs/warm_cs_all_D7.log）。
- 03:22 预热完成。后台依次运行：API 验收（accept_api_D7）、战争审计（war_audit_D7）、书籍核对（book_xcheck_D7）、君主覆盖（china_monarchs_D7）；UN 点击 2020/1950 及微型国家（logs/click_un_*.log）。
- 03:25 结果：API 验收 accept_api_D7 119/119 = 100%；书籍核对 book_xcheck_D7 18/18 = 100%（加 europe_19c 控制区后）；中国君主覆盖 china_monarchs_D7 2130/2132 = 99.9%，数据缺口 0，2 年为有据空位期（前74、1333）；战争审计 war_audit_D7 70/86 = 81.4%（余下失败见 KNOWN_ISSUES：1886 前底图 6、旅顺 2、1949 南京、1949 开城、北塞浦路斯、1982 福克兰、ISW 2022-03-15 快照不含库皮扬斯克；另 3 条为期望用词问题：阿比西尼亚帝国=埃塞俄比亚帝国、科威特省=伊拉克科威特省，已改）。新增关东州控制区（俄国 1898-03-27—1905-09-05，日本 1905-09-05—1945-08-22，北界普兰店湾—皮口近似 ±15 km），待点击测试结束后重建。国旗前 60 审计脚本修正后重跑。
- 03:32 发现前端问题：面板标题要等全部 9 个模块返回后才换成按日期解析的政权名（事件/人物模块慢时延迟数秒）→ app.js 改为政权模块一返回就更新标题。点击测试改用 textContent 读取标题（inner_text 自动等待导致每次点击约 6 秒）。重建 runtime_states/control_zones/transitions（关东州）并重启、预热（logs/rebuild_warm_D8.log）。
- 03:32 国旗前 60 审计第一轮（data/audit/flags_top60_before.md）：政权-年 10854，有日期依据 41.0%，只有无日期语句 51.3%，无国旗 7.6%；发现无日期语句挂了带年份的历史旗（尼泊尔 1743–1962 旗用到 2007、菲律宾 1985–1986 旗用于 1886 起、背风群岛 1952–58 旗用于 1815 起、埃塞俄比亚、葡属澳门、百慕大、塞拉利昂、巴巴多斯等）→ flags.py：文件名自带年份范围的旗只在该范围 ±1 年内使用（人工修正除外）。重跑中。新喀里多尼亚用 FLNKS 旗（非官方）未修，列入已知缺口。
- 03:38 国旗修正生效（文件名需先 URL 解码）：前 60 政权-年中「只有无日期语句」51.3%→45.4%，年代不符的旗改为不显示（无国旗 7.6%→14.3%），有日期依据 40.2%（data/audit/flags_top60.md）。
- 03:43 第八轮：API 验收 119/119=100%；书籍核对 18/18=100%；君主覆盖 2130/2132（数据缺口 0，2 年有据空位期）；战争审计 73/86→关东州两条改按 QID 判断（Wikidata 中文标签为「达里尼」「旅大租借地」）后 75/86 = 87.2%，余 11 条见 KNOWN_ISSUES。
- 03:44 AUDIT_REPORT.md 新增阶段 D 第 11–15 节：验收与连续审计汇总、1800 年至今逐场战争审计表、OpenStax 书籍核对、UN 点击测试（待填）、一战/俄国内战/中日战争可行性。
- 03:44 README 数据许可表补 CShapes 2.0（CC BY-NC-SA 4.0，非商业）、Stanford「Building the New Order」（学术/非商业）、OpenStax（CC BY 4.0，只用于核对）。
- 03:59 恢复：UN 点击 2020 仍在运行（155/193，目前全部命中且 QID 一致）。计划：2020 跑完后停止后续链，修战争审计失败项（1949 渡江后控制区、开城/三八线、北塞浦路斯、1982 福克兰），重建预热后再跑 1950/微型国家/截图。
- 04:00 新增控制区组 wars_misc（11 区）：1949 共军控制区 5 阶段（省级，按省会易手日期，1949-01-31 起至 10-01）、朝鲜半岛 1948–1950 三八线（开城属大韩民国、襄阳一带属朝鲜）、北塞浦路斯（1974 土耳其占领 → 1975 塞浦路斯土族邦 → 1983 北塞浦路斯）、1982-04-02—06-14 阿根廷占领福克兰群岛；均注英文维基来源。
- 04:01 build_control_zones 完成（85 区，wars_misc 11 区几何正常）；后台运行 build_runtime_states + build_transitions（logs/build_wars_misc.log）。
- 04:04 UN 点击 2020-06-01 完成：面板 193/193=100%，精确 QID 192/193（唯一差异荷兰：联合国会员为荷兰王国 Q29999，欧洲本土解析为构成国荷兰 Q55，属同一国家条目）；click_un.py 增加 SAME 映射，按此口径 193/193。已停止后续链（1950 刚开始），先做战争修复构建。
- 04:04 build_runtime_states（补 46 个 QID，含中共 Q17427）与 build_transitions 完成；重启服务并后台预热缓存（logs/warm_D10.log）。
- 04:05 shots_v08.py 增加 5 张：澳门 1999-12/2000-06、2020 波兰面板、1949-05 南京共军控制区、1990 北塞浦路斯（共 42 张）。
- 04:05 查明 v0.5.0 发布流程：stage_data_xz.py 转数据，launcher.py --no-terminal --no-browser --port 18790 --home /tmp/wha-smoke/home 启动暂存目录后跑 packaging/smoke_check.py。版本号（config.py/spec/workflow/README）待测试全部跑完再改，避免预热缓存失效。
- 04:13 预热完成（619 个时间点）。后台跑 war_audit → api_mustpass → book_xcheck → china_monarchs（logs/*_D10.log）。
- 04:15 D10 复测：战争审计 78/86（南京 1949、开城 1949、斯坦利 1982 通过；凯里尼亚 1980 解析为塞浦路斯土族邦 Q784851，史实正确，审计用例补「土族邦」关键词）；API 必过 119/119；书籍 18/18；君主 2130/2132（2 个有据空位）。
- 04:17 新增 19 世纪控制区 5 个（europe_19c）：美利坚联盟国 1861–1865（11 州近似）、法兰西帝国并入荷兰 1810–1813（1800 快照巴达维亚多边形）、普鲁士吞并汉诺威 1866–1871（1815 快照汉诺威多边形）、阿尔萨斯属法国 1815–1871（修正底图把斯特拉斯堡画进巴登）、墨西哥北部 1821–1848（加州/内华达/犹他/亚利桑那/新墨西哥近似）；KIND_ZH 增「吞并」。华沙公国：底图无对应多边形，未做。开始构建。
- 04:21 战争审计 D11：84/86 = 97.7%（19 世纪 5 项全部修复）。剩余：1808 华沙公国（底图无对应多边形）、2022-03-15 库皮扬斯克（ISW 当日快照未覆盖，源数据缺口）。预热进行中。
- 04:25 预热完成。后台链 logs/run_D11.sh：必过→书籍→君主→UN 点击 1950→1950 微型→2020 微型→shots_v08（42 张）。
- 04:26 版本号改为 0.6.0：backend/config.py、packaging spec、.github/workflows/build.yml、README 标题与更新记录（v0.6.0 条目）。
- 04:26 spec hiddenimports 增加 cshapes/ww2/flags/regimes/china_eras；MERGE_NOTES.md 顶部加 v0.6.0 说明。
- 04:27 D11 复测：API 必过 119/119，书籍 18/18，君主 2130/2132。stage_data_xz.py 的 SKIP 增加 cshapes_raw、ww2_raw（原始数据 850 MB 不进发布包）。UN 点击 1950 进行中。
- 04:27 AUDIT_REPORT §11/§12 更新为 D11 战争审计结果（84/86）及新增控制区。
- 04:28 KNOWN_ISSUES.md 改写为 v0.6.0 定稿稿（第 3/4 节按新控制区更新，补国旗、新喀里多尼亚、UN 口径、书籍、控制区精度；第 9 节待填最终数字）。
- 04:40 新建 tools/dev/stage_release.sh（复制代码 + stage_data_xz 转 .xz + v08 用户截图）；stage_data_xz 支持 XZ_WORKERS 限制并发（内存 15 GB，避免与点击测试争抢）。UN 点击 1950 约 20 秒/国（1950 年多边形多，渲染慢），预计 1 小时。
- 04:40 后台开始组装 /workspace/wh_v060_stage（logs/stage_v060.log）。
- 04:48 UN 点击 1950 越跑越慢（46 国时约 33 秒/国，测试进程本身 CPU 60%）：停掉旧链，click_un.py 改为每 20 国重新载入页面，重开链 logs/run_D12.sh（1950→1950 微型→2020 微型→shots_v08）。暂存目录已组装（转换 1697 个文件，59 MB，未含截图）。
- 04:49 恢复：run_D12 链仍在跑（PID 347038，click_un 1950 刚开始），不重复启动。补记：04:48 暂存目录 smoke_check 通过（meta version=0.6.0，modules=15，events=71778，cities=7342；logs/smoke_stage_v060.log）。
- 04:49 暂存目录（.xz 数据）抽查：1949-05 南京→中国共产党（共军控制区）、1980 凯里尼亚→塞浦路斯土族邦、1862 里士满→美利坚联盟国，均正确；关闭暂存测试服务。
- 04:56 发现：UN 1950 点击巴林 MISS——1971 年前巴林没有任何多边形（点到麦纳麦城市点）。扫描 1950/1930/1900 年 UN 会员点位，无多边形的有 BHR、FSM、KIR、MHL、NRU、PLW、STP、SYC、TUV、VUT（1900 另有 COM、GRD、LCA、VCT）。新增控制区组 colonies_misc 8 区（Wikidata QID 与起止日期逐条核对）：巴林及其属地、葡属圣多美和普林西比、新赫布里底、吉尔伯特和埃利斯群岛、南洋群岛、太平洋群岛托管地、瑙鲁托管地、塞舌尔（大英帝国）。待 1950 点击跑完后构建（构建+重启会打断测试）。
- 04:56 1950 结果会受新控制区影响：停掉 run_D12（1950 跑到约 35 国），后台构建 colonies_misc + 重启 + 预热（logs/build_D13.log），之后重跑点击链。
- 05:07 抽查新控制区：1950 巴林/瑙鲁/托管地/南洋（1930）/塞舌尔/圣多美/新赫布里底均正确；但 1942 塔拉瓦被吉尔伯特和埃利斯殖民地盖过日占（过渡层后写者优先）。把 colonies_misc 移到 pac_ 各区之前，重建 control_zones + transitions，重启并预热（logs/build_D14.log）。已知：巴林、瑙鲁托管地在 Wikidata 无中文标签，面板显示英文名。
- 05:07 新建 tools/dev/make_parts.py（分卷：代码文档小数据 / 底图+每日新闻 / 战争前线 / 截图，超 25 MB 报错）。
- 05:17 重建与预热完成；1942 塔拉瓦恢复为日占吉尔伯特群岛，1950 吉尔伯特和埃利斯群岛正确。
- 05:20 查明点击慢的原因：1950 年 CShapes 合成边界（gzip 1.0 MB，2011 年 NE 为 0.37 MB）在无头浏览器里每次 setView 要 17–22 秒（其余步骤 <1 秒），不是页面泄漏。click_un.py 增加 --shard=k/n；新链 logs/run_D15.sh：1950 三路并行 → 1950 微型、2020 微型、shots_v08 三路并行。
- 05:25 1950 三路并行约 8 国/分钟。巴林仍 MISS：NE 标注点正好落在麦纳麦城市点上（点城市点按设计弹出城市信息），接口 locate 已返回巴林多边形。
- 05:26 D14 复测：API 必过 119/119、战争审计 84/86、书籍 18/18、君主 2130/2132。后台低优先级重跑连续审计（logs/audit_cont3_*.log）。
- 05:38 连续审计重跑：1886–1950 违规 0（unknown 494 与之前相同，均为没有起止日期的共军根据地条目）；1951–2026 违规 0；-3000–1885 违规 74（与之前相同，年精度端点）。
- 05:39 恢复。1950 点击三路分片各停在 38 国（共 114/193，MISS 5：BHR、FJI、FSM、GAB、KIR），之后的微型与 shots_v08 都未开始。逐张看 MISS 截图：FSM/FJI/GAB 是点到了控制区标签文字（整段标签拦截点击，弹出控制区说明而不是政权面板），KIR 的点位在基里巴斯最大岛（圣诞岛，莱恩群岛未画进吉尔伯特和埃利斯殖民地）落在海上。修正前端：控制区标签文字不拦截点击，只有「◇」可点开说明（control_zones.js + style.css，与城市标签的修法一致）。按用户要求改口径：1950 用 locate API 全量 + 浏览器抽 30 国。
- 05:40 1950 locate API 全量（tools/accept/locate_un.py → logs/locate_un_1950-06-01.json）：有多边形且有政权 187/193 = 96.9%；无多边形 6 国：KWT（1961 年前科威特无多边形）、KIR（莱恩群岛）、DMA/KNA/LCA/VCT（加勒比英属小殖民地）。时间有限，这 6 项列为已知缺口。setsid 后台链 logs/run_D16.sh 四路并行：shots_v08、1950 抽 30 国点击、1950 微型、2020 微型。
- 05:40 后台重新组装暂存目录（数据、前端、文档已变；logs/stage_v060b.log），截图拍完后再补拷。
- 05:46 1950 抽样中 FSM 仍弹出控制区说明：「◇」正好压在标签点（即小岛本身）上。控制区标签整体右移 6px（iconAnchor [-6,8]），抽样结束后重跑抽样。2020 微型（z=2.5）：面板 32/34，精确 QID 25/34——世界尺度下梵蒂冈→意大利、澳门→香港、加勒比小国→邻近法/荷属地，PLW、COM 点在海上。
- 05:58 1950 抽样第一轮（旧标签锚点）面板 26/29；1950 微型（z=2.5）面板 27/34。用新锚点重跑 1950 抽样 30 国（TWN 非联合国会员，换成 SYC）。shots_v08 已拍 13/42（每张 1–1.5 分钟）。
- 05:59 看截图 01–13：13（1944-12 桂林）面板显示中华民国，但接口返回汪政权控制区——固定 2.5 秒等待不够（渲染慢），面板未更新；11（1938-12 南京）点中了控制区标签「◇」弹出说明、面板为前一张的满洲国。shots_v08.py 改为点击前清空标题、点击后最多等 40 秒直到标题出现，支持逗号分隔的多个筛选词。本轮拍完后重拍有问题的几张。
- 05:59 停掉旧 shots 进程，用新脚本两路并行重拍其余 37 张（logs/shots_v08_a.log、_b.log）；01–04、06 已逐张看过，保留。
- 06:10 查明 13 号桂林的原因：shots 脚本在新日期边界还没加载完时就点击，点到了上一个日期的多边形（接口与 /api/basemap 都正确：桂林属汪政权控制区 fid 200097）。脚本改为等 location.hash 写入新日期（setDate 最后一步）再点；两路重拍 37 张。1950 抽样第二轮进行中（21/30，仅 KIR MISS）。
- 06:24 查明并修正前端真实 bug：loadSnapshot 里 FeatureGroup.bringToBack() 逐个把要素移到最底层，把绘制顺序整个颠倒，使大国多边形盖住后加的实际控制区/领地多边形——1944-12 在浏览器点桂林得到中华民国（接口为汪政权控制区）。改为倒序逐个 bringToBack 保持原顺序；另加快照请求序号，较早的请求后返回时不再覆盖地图（app.js）。验证：浏览器点桂林 → 汪精卫国民政府。此前的浏览器点击结果都受影响，全部重跑：shots 37 张两路 + 1950 抽样 + 两个微型。
- 06:30 恢复。shots 路 A 在 13 号处浏览器渲染进程崩溃（4 个浏览器并行，内存紧），已拍 05、11；用剩余 16 张重启路 A（logs/shots_v08_a2.log）。路 B 正常（已 5 张）。2020 微型重跑完：面板 32/34、精确 QID 25/34（与修复前相同）。1950 抽样进行中 12/30。
- 06:37 1950 抽样 30 国（修复后）：面板 28/30 = 93.3%（MISS：KIR 点位在海上、SYC 待查），与当今国家 QID 一致 12/30（1950 多为殖民地/前身政权，属正常）。按要求启动 2020 抽 30 国重跑（含 UKR/GEO/MDA/AZE/CYP 等有控制区的国家；logs/click_un_2020_sample.log）。
- 06:44 2020 抽 30 国（修复后）：面板 30/30、精确 QID 30/30 = 100%。shots 两路结束。
- 06:45 逐张查看 37 张重拍：13 桂林已正确（汪精卫国民政府）；其余政权与日期一致。问题：61–64 国旗张停在上一张的「领导人」标签，看不到国旗——给这 4 张指定「政权性质」标签重拍（logs/shots_v08_flags.log）。另记：1950/1952 中华人民共和国面板「所选日期的政权」同时列出中华民国（宪政）；1920 年中华民国领导人标签无任职记录（Wikidata 北洋时期元首无起止）；1964 马来西亚首都显示「、吉隆坡」。
- 06:49 61–64 重拍并查看：1920 五色旗、1935 青天白日满地红、2020 台湾中华民国国旗、1942 维希法国均正确。42 张全部人工看过。1950 微型（z=2.5，修复后）：面板 29/34 = 85.3%（PLW/MHL/KIR/COM/TON 点到海上或邻近政权的最小圆点外），与当今国家 QID 一致 7/34（1950 多为殖民地）。所有浏览器测试结束。
- 06:50 AUDIT_REPORT §14 填入 UN 点击/接口测试全部结果与修正。
- 06:50 KNOWN_ISSUES.md 定稿：补截图中发现的显示问题、1950 年无多边形的地区、第 9 节最终数字、第 10 节性能。
- 06:50 README 更新记录补充本轮修正。开始重新组装暂存目录（最新前端、数据、文档、42 张截图；logs/stage_v060c.log）。
- 06:57 暂存目录重建完成：/workspace/wh_v060_stage，77M（data 57M、截图 19M）。已确认含 app.js 绘制顺序修复、zl-dot 标签修复、colonies_misc 控制区、42 张截图，文档与工作区一致。下一步：smoke_check 暂存目录。
- 06:57 smoke_check 暂存目录通过（version=0.6.0，15 个模块，1789-07-14 快照与巴士底事件均正常，用户目录正常）；已停测试服务器。开始打分卷 zip。
- 06:58 分卷 zip 完成：part1 18.3 MiB、part2 15.8 MiB、part3 18.4 MiB、part4 18.4 MiB，都小于 25MB。下一步：解压后 smoke_check。
- 06:58 4 卷解压到 /tmp/wha-unz8/world-history-atlas，与暂存目录逐文件一致（diff 无差异），smoke_check 通过；测试服务器已停。全部完成，未推送、未发布。
- 08:54 新任务 v0.6.1：空位期/摄政/共治领导人（任务 A）+ 已知问题修复（任务 B）。v0.6.0 不发布。先读 leaders.py 与 regents.json 结构。
- 08:58 已抓取补充职位（幕府将军/关白/摄政/执权/护国公，Wikidata SPARQL → data/curated/extra_offices.json）和 34 个英文维基条目全文（data/refs/wiki/）用于核对空位期日期。
- 09:01 核对完各案例日期（中英文维基全文在 data/refs/wiki/），开始写 data/curated/interregna.json（tools/curated_src/interregna.py 生成）。
- 09:04 后端：backend/interregna.py（案例按日期与政权匹配）、polity.py 读 office_links / extra_offices / name_candidates；leaders.py 输出 interregna；前端领导人标签顶部加「实际掌权者」框（角色标签、本官、名义君主、另一说、来源）。重启验证。
- 09:05 案例增至 30 个（加日本院政 3 例、波兰选王空位 3 例），所有人物/政权 QID 已用 wbgetentities 逐个核对标签（修正：索尼 Q41187 是索尼公司 → 索尼（满洲大臣）Q2301595；院政三上皇 QID）。执权职位加管辖日本 Q17。
- 09:06 新验收 tools/accept/interregna.py（中国前841–1912 逐年 + 30 个案例 + 全世界君主空档扫描），后台运行 → logs/interregna_r1.log。
- 09:07 B1：regime.py「所选日期的政权」在国号链有多个并立的「至今」行时，只显示所点政权自己那一行（国旗同理）。
- 09:07 interregna.py 修正排序错误后重跑；全世界扫描：225 处君主职位空档（月精度以上记录），已覆盖 7 处，绝大多数是 Wikidata 任职记录不全，列入 data/audit/leader_gaps.md 供人工核对。
- 09:08 B3 首都去掉无名称条目（「、吉隆坡」）；B4 面板标题只显示中文政权名，底图英文原名移到说明行「底图名称」；B5 巴林保护国、瑙鲁托管地加中文名（runtime_states.json，注明人工译名）。
- 09:13 中国逐年首轮 2747/2753，案例 30/30。缺口：前681–前677（Wikidata 缺周釐王）、前250（秦孝文王服丧期）→ extra_holders 据《史记》补两条（注明来源）。B2：北洋政府总统/国务总理（Wikidata Q887003/Q702650 只记在 Q865 下）加到 1912–1949 中华民国，SPARQL 取到的 1928 年前记录只有 4/5 条，需补。
- 09:13 收到任务 C：检查所有英文名是否都译成中文（zh_coverage.py、Wikidata 中文标签补译、截图验证）。先完成北洋领导人。
- 09:14 B2 完成：北洋大总统 16 条、国务总理 43 条任期（解析英文维基列表 Timeline，QID/中文名取 Wikidata，繁转简）；1920 显示徐世昌，1926 显示颜惠庆。周釐王、秦孝文王补上。B1 验证：1952 北京「所选日期的政权」只剩中华人民共和国；B3 马来西亚首都只剩吉隆坡。
- 09:15 B6：新增 11 个殖民地/保护国控制区（科威特酋长国、莱恩群岛、英属向风/背风群岛、西印度联邦、圣卢西亚殖民地、圣克里斯托弗-尼维斯-安圭拉、西印度联系邦），日期据英文维基；重建控制区 → 补政权条目 → 过渡层（logs/run_v061_build.log）。
- 09:16 控制区补 bbox 后重跑构建。B9：Stanford 1939-10 月快照的「波兰总督府」在 1939-10-26 前改为前身「德国军事当局（Q6851954）」（name_candidates.json ww2_before；polity.py）。
- 09:16 B7：微型国家圆点移到单独图层面板（z-index 650，高于城市点），按面积从大到小画（最小的在最上），点击不再穿透。
- 09:17 B8：加「意大利占领区（法国东南部）」控制区 1942-11-11→1943-09-08（按省近似，Q2570590，英文维基）；Stanford 数据没有单独的意占区边界。1940–42 年芒通小块未画。
- 09:18 第一次构建完成（11 个殖民地区）；加入意占区后再次构建（logs/run_v061_build2.log）。
- 09:19 任务 C：tools/zh_fill.py 从 Wikidata 中文标签/中文维基条目名/英文维基中文语言链接补中文名（后台，logs/zh_fill.log）。
- 09:20 tools/accept/zh_coverage.py 写好；「之前」基线（--raw，未应用补译）后台运行。
- 09:22 「之前」数据层：220380 个名称中 30564 个没有汉字（13.9%）；接口层因 basemap gzip 解码出错重跑。后端补译接入：polity.py（政权/人物/职位/机构）、事件、人物列表、城市、条约；找不到中文名的显示「原名（暂无通用译名）」；底图原名（文化/地区）用中文维基链接名。
- 09:31 修复服务器崩溃：并发请求同一边界合成时 GEOS 重复释放（double free）导致进程退出；新增 backend/geolock.py，三处合成缓存加可重入锁。16 并发 × 60 请求压力测试两轮无崩溃。
- 09:33 补译结果：Wikidata/中文维基按 QID 找到 131/26690；底图名称 297/2172，经 P31/消歧义自动核对删 52 条、人工复核删 49 条、恢复 4 条、改 4 条，保留 200；英文维基条目中文链接再补 2 条（赫梯、科尔多瓦）；人工意译 7 个描述性政权名（data/curated/zh_manual.json）。之前/之后覆盖率统计后台运行（之前用 WHA_ZH_RAW=1 服务器）。
- 09:38 B11 渲染耗时排查：同一份 1950 边界在无头浏览器中 SVG 绘制约 50–70 ms、平移 60–175 ms，Canvas 无明显优势，已撤回 Canvas 改动；服务器端新月份合成（无并发时）约 1.1 s + 底图序列化 0.4 s，之后读磁盘缓存 0.2 s。之前记录的 17–22 s 是并发负载（截图脚本 + 统计任务同时请求）与首次合成叠加的结果，不是前端渲染。
- 09:55 补译接入面板/详情/图层（disp 标注）；带拉丁字母的离线机器翻译（如「KV14 车次（译名）」）改回原文并标注；873 个无中英文标签的人物取 Wikidata 其他语言标签（872 个）。验收链 logs/run_v061_accept.sh 后台运行。
- 09:57 验收：interregna 中国 2753/2753、个案 30/30；china_monarchs 已跑完。新增 3 个空位期个案（蒙古脱列哥那摄政 1241–1246、海迷失后摄政 1248–1251、法兰西 1316 腓力摄政），共 33 个；需重启后复验。
- 09:58 runtime_states 22 个繁体名转简体（build_runtime_states.py 同步加 t2s）；Q6851954 改为「德军波兰军事管理区」（原标签有歧义，mustpass 唯一失败项）；重启后重跑整条验收链。
- 10:03 被中断后恢复：验收链仍在运行（已完成 interregna/monarchs/mustpass/book/war/locate/zhcov，正在 click_un 2020），截图 v09 正在跑。
- 10:05 中文名补漏：殖民地多边形标题（宗主国+地位）原名改用中文名（CShapes 86 个多边形名按新华社/大陆通用译名对照）；职位名、无姓名人物（显示「Qxx（未记录姓名）」）补标注。
- 10:33 前端：小国标记点击改为按坐标解析（1950 多米尼克点到底图「文化/地区」）；底图原名提示只显示中文；polity_names 接口并入补译名；METHOD_ZH 加 curated-name。2020 点击 193/193；1950 点击 shard2 浏览器崩溃待重跑。
- 10:44 1950 点击三个分片并行时浏览器内存不足崩溃；重启服务器后改为顺序重跑：1950 点击、微型国家、interregna、monarchs、mustpass、中文覆盖、v09 截图（logs/run_v061_accept2.sh）。
- 10:55 恢复：验收链 run_v061_accept2.sh 仍在运行（1950 点击 shard0 进行中），未重启。
- 11:08 1950 全量浏览器点击太慢（每国约半分钟，且并行会崩溃），改为抽样 36 国（含科威特、多米尼克、圣卢西亚、圣文森特、圣基茨、瑙鲁）+ 微型国家；1950 全量以接口 locate_un 193/193 为准。logs/run_v061_accept3.sh。
- 11:24 1950 抽样 33/35（KIR 测试点落在海上无多边形——v0.6.0 同样；VCT 慢点击超时，单独重测通过；KNA 原为「文化/地区」）。修：底图「Saint Kitts and Nevis」按名称对应英属背风群岛/西印度联邦/殖民地；底图文化/地区多边形点击改按坐标解析。重启后重跑验收链 3。
- 11:24 KNOWN_ISSUES 更新（v0.6.1 已修正项、性能、中文名一节）；第 9 节测试表待验收链结束后填。
- 11:44 恢复：验收链 3 仍在运行（PID 479263），等待中，不重启。
- 12:07 验收：1950 抽样 33/35、微型 1950 30/34、2020 微型见日志；interregna/monarchs/mustpass/中文覆盖重跑完，截图进行中。
- 12:07 KNOWN_ISSUES 第 9 节已填。
- 12:08 AUDIT_REPORT 第 16 节已写。
- 12:34 v09 截图 41 张已生成；08/13/14/25 四张面板标题为空（点击后未选中），后台单独重拍（logs/shots_v09_redo.log）。控制台 54 个 404 均为换日期时用旧 fid 刷新面板（/api/modules/*?fid=旧快照编号，返回「没有这个政权」），无缺失文件。
- 12:41 查明 08/13/14/25 截图失败原因：过渡层求差后留下线/点/GeometryCollection，前端把点画成 Marker，导致 bringToBack/setStyle 报错，整层点击失效（1410、685、1575、1950 等快照）。修复：geo.raw_bytes 只发送多边形部分，前端加防护。重启服务器。
- 12:41 文档补记几何修复、404 原因、意占区黑框与裸 QID 职位；stage_release.sh 改带 screenshots/v09。
- 12:46 重拍 08/12/13/14 成功并已查看；25 科威特截图仍未选中（点到上一快照的 fid 62，404）——浏览器点击测试 KWT 通过，记为截图问题。mustpass 修复后复跑见日志。开始重建暂存目录。
- 12:52 暂存目录 /workspace/wh_v061_stage（72M）重建完成；launcher 启动后 smoke_check 通过（version=0.6.1，15 模块，巴士底事件、用户目录正常）。开始打分卷 zip。
- 12:53 分卷 zip：/workspace/wh_v061_part1–4.zip（19.1/15.8/18.4/11.3 MiB，根目录 world-history-atlas/），解压后与暂存目录一致（只差 smoke 运行产生的空目录 data/live，已删），解压目录 smoke_check 通过。未推送、未发布。修复后的 1950 微型国家复测仍在后台跑（logs/click_un_1950_micro_b.log）。
- 13:01 新任务：逐条核对 leader_gaps.md 剩余 216 处君主空档（a 补君主 / b 空位期个案 / c 精度或数据假象 / d 未记录），并修 3 个显示问题。
- 13:03 空档核对第 1 步（tools/audit/gap_verify.py，按面板逻辑逐月取样）：225 处中 98 处面板整段都有君主 → c；127 处仍有空月份，进入第 2 步（Wikidata P39 反查补人）。用量 57.3%。
- 13:28 空档核对第 2–4 步完成：Wikidata P39 反查 + P1365/P1366 前后任链（tools/audit/gap_wd.py、gap_chain.py）；人工判定数据 tools/curated_src/gap_data.py（a 类 116 条任职记录 → extra_offices.json extra_holders，gap_fix 标记）、interregna_gaps.py（新增 76 个个案，interregna.json 共 103 个）；QID 全部经 wbgetentities 核对（151 个条目名，全部 P31=Q5）。修正 leaders._holding：只精确到年的卸任记录只在下一任精确就任日落在卸任年/月之内时才截断（巴赫拉姆五世 420–438 等长期在位被整段截掉的假象）。结果 data/audit/gap_resolutions.json + leader_gaps.md 末尾表格。
- 13:29 显示问题修复：①波兰 1650 职位裸 QID Q9394451 → tools/orig_labels.py 扩展到职位/组织（406 个取到原文标签，显示「łożniczy（暂无通用译名）」）；②意占区黑色矩形 = 点击后 SVG 路径的浏览器焦点框 → style.css 去掉 .leaflet-interactive:focus 的 outline；③1950 科威特面板「没有这个政权」：当前服务 API 正常（cs@19500517 fid 200115 → 科威特酋长国），截图待重拍核实。interregna 验收：leaders 为空的空位期个案只要求面板显示个案。服务已用新数据重启。启动顺序验收 logs/run_v061_accept4.sh（用量 58.4%）。
- 13:55 恢复：accept4 仍在跑（click_un 2020）；用量 59.1%。interregna 个案已修正 states（新朝/武周/大越/卡尔马联合/加洛林帝国）与 nomap 标记，验收脚本支持切换「其他可能的政权」；待 accept4 结束后重启服务、重跑 interregna 验收与 gap_resolve。
- 14:45 恢复（用量 60.1%）：accept4 结果已出 mustpass 119/119、war_audit 84/86、book 18/18、monarchs 2132/2132、zh 覆盖（接口 3 个无任何语言标签的人物标「未记录姓名」）、click 2020 193/193、1950 抽样 33/35；等微型国家与截图。
- 15:07 accept4 完成：微型国家 1950 30/34、2020 32/34；重拍 25/33/42。
- 15:09 科威特截图根因：点击落在控制区标签的 ◇（zl-dot）上，只弹说明不选政权 → control_zones.js 标签点击同时 WHA.selectAt；复测选中 fid 200115 科威特酋长国。重启服务，重跑 interregna 与 gap_resolve。
- 15:13 interregna 验收：中国 2753/2753（145 年由实际掌权者覆盖）、个案 97/97（另 6 个无独立多边形不计入）；gap_resolve：a45 b66 c109 d5。科威特已重拍，v09b 截图进行中。用量 60.8%。
- 15:21 v09b 截图 21 张已逐张看过：18 张面板直接显示新补的君主或个案；15 柔佛（底图为英属马来亚，个案标 nomap）、18 法兰克 842（默认选中加洛林帝国，个案需在下拉切换到法兰克王国）、20 萨珊 430（默认选中「波斯」，巴赫拉姆五世需切换到萨珊王朝）未直接显示。科威特、意占区（无黑框）、波兰 1650（łożniczy）重拍已看。开始更新文档。
- 15:21 文档已更新（README v0.6.1、KNOWN_ISSUES 第 9 节测试表、AUDIT_REPORT 第 17 节）。开始重建暂存目录。
- 15:26 暂存目录 /workspace/wh_v061_stage（80M）重建；分卷 /workspace/wh_v061_part1–4.zip（18.9/15.8/18.4/18.7 MiB），解压后与暂存目录逐文件一致；解压目录用 launcher 启动，smoke_check 通过（version=0.6.1，15 模块）。测试服务已停。未推送、未发布。
- 15:26 全部完成，用量 61.6%。写最终报告。
- 15:34 新任务：面板默认政权（法兰克 842、萨珊 430、柔佛 1870 等）。
- 15:40 通用默认政权规则（_state_common._prefer_ruled）完成：默认条目当天无在位者/案例时改选有案例或在位者的更具体候选；全快照扫描 3647 个多边形只改变 7 个（萨珊 400/450、马林 1300–1446、瑞典 1600），log logs/prefer_sweep3.log。用量 62.6%。下一步：柔佛/霹雳/雪兰莪/日惹控制区。
- 15:57 柔佛/霹雳/雪兰莪/日惹 10 个政权区（tools/curated_src/zones_malay_java.py，group princely_states）+ lifespan_overrides（Q183032/Q188953/Q189710）+ zone_regime 地位框（科威特原误显示「英国海外领地」一并修正）；interregna nomap 余 2（isis_2023、bohemia_1440）。下一步：验收。
- 16:24 检查：accept7 只在 sleep 循环里等 accept6 的 CHAIN_DONE，不会并行开浏览器（当前只有 click_un 2020 一个浏览器进程），两个都保留；accept6 已完成 mustpass 119/119、interregna 101/101(+2 nomap)、monarchs 2132/2132。
- 16:49 click_un 2020 全量 193/193（EXACT 193/193），微型国家 2020 32/34、1950 30/34，与上一轮完全相同。1950 抽样进行中。
- 17:11 截图 v09b 11 张 + 科威特已人工看过；萨珊面板巴赫拉姆五世重复两行 → leaders 去重同人同起止。重跑 mustpass + 20_ 截图。
- 17:12 mustpass 重跑 119/119；20_ 重拍已看（巴赫拉姆五世一行）。下一步：文档、staging、zip、smoke。
- 17:13 文档更新（README、KNOWN_ISSUES、AUDIT_REPORT）。下一步：staging/zip/smoke。

## 2026-11-08 03:54（欧洲/巴黎）0.6.2 第一批 P0，未发布

工作分支 `cursor/p0-history-062-3bcf`，从已发布的 main（0.6.1，`cb79230`）分出。2026-11-05 的未发布源码附件盖上了 0.6.2 的程序、整理数据和工具；大型运行时数据（底图、cshapes、同盟、职务等成品 xz）仍用仓库里已有的，没有用空文件替换，也没有退回成「只有 0.6.1 程序」。没有合并 main，没有打 tag，没有发 Release，没有跑发布 workflow。

这一批只做四项，不是整个 0.6.2。2026-11-02 写过的 mustpass 119/119、manchuria_no_roc、截图，凡本批没有重跑的，都标待复验（见 KNOWN_ISSUES 第 9、12 节）。

### 这一批改了什么

- 维希 1941-04-25 不再出现裸编号 `Q1934893@Q142`。该职是德军职务，Wikidata 只有德/法标签 Militärbefehlshaber，没有中文名，面板写 `Militärbefehlshaber（暂无通用译名）`，并且只挂在纳粹德国。维希不再混入法国 Q142 和第三共和国的职务。没有名称的职位显示「职位名称未记录」。来源：[Q1934893](https://www.wikidata.org/wiki/Q1934893)、[Otto von Stülpnagel](https://en.wikipedia.org/wiki/Otto_von_St%C3%BClpnagel)、[Q68590](https://www.wikidata.org/wiki/Q68590)。
- 1941-04-25 台北是台湾日据时期 Q137816，不是中华民国。1895-04-20 仍是清治，1895-06-15 是台湾民主国，1895-10-22 台南是日治。朝鲜 1910-08-25（已签字、未生效）仍是大韩帝国，1910-08-29 起是朝鲜日治。南桦太 1910 是大日本帝国。来源：[Republic of Formosa](https://en.wikipedia.org/wiki/Republic_of_Formosa)、[乙未戰爭](https://zh.wikipedia.org/wiki/%E4%B9%99%E6%9C%AA%E6%88%B0%E7%88%AD)、日韩合并以 1910-08-29 为生效日。
- Q5035992 不再显示「台南话（译名）」，也不再把中华民国写成当事方。名称是 `Capitulation of Tainan（暂无通用译名）`。当事方是大日本帝国与台湾民主国。来源：[Capitulation of Tainan](https://en.wikipedia.org/wiki/Capitulation_of_Tainan)、[Q5035992](https://www.wikidata.org/wiki/Q5035992)。
- 苏联同盟成员从 1941-06-22 起，南斯拉夫王国从 1941-04-06 起。1940-11-15 两者都不是同盟国，里加是苏联且不着同盟色。满洲国、汪政权等改为附庸标签，不计入轴心签署国。1944-12-01 桂林是日军军事占领（大日本帝国），不是汪政权。来源：[Operation Barbarossa](https://en.wikipedia.org/wiki/Operation_Barbarossa)、[Anglo-Soviet Agreement](https://en.wikipedia.org/wiki/Anglo-Soviet_Agreement)、[Invasion of Yugoslavia](https://en.wikipedia.org/wiki/Invasion_of_Yugoslavia)、[Battle of Guilin–Liuzhou](https://en.wikipedia.org/wiki/Battle_of_Guilin%E2%80%93Liuzhou)、[桂柳会战](https://zh.wikipedia.org/wiki/%E6%A1%82%E6%9F%B3%E4%BC%9A%E6%88%98)。

### 2026-11-08 实际跑过的命令

- `WHA_PORT=8792 python3 tools/accept/p0_1941.py` → 22/22，退出码 0。
- `python3 tools/accept/api_mustpass.py 中日战争` → 10/10。
- `python3 tools/accept/api_mustpass.py 二战` → 19/19。
- `python3 tools/accept/api_mustpass.py 法国` → 10/10。
- `WHA_PORT=8792 python3 tools/accept/ww2_occupation_bloc.py` → 72 个快照，1516 次占领区检查，0 处缺失。
- `WHA_PORT=8792 python3 tools/accept/manchuria_no_roc.py` → 162 个月，311 处失败（兴安南仍是 China；1933-04 起热河与满洲国两个多边形）。未改几何。
- `python3 packaging/test_launcher_translocation.py` → 通过。
- 没有跑整份 119 条 mustpass，没有跑截图。

### 本批明确没做

交接清单里其余项当时还留在后面。第一批结束时工作区没有 `data/basemaps_raw/` 和 `data/cshapes_raw/`。

## 2026-11-08 第二批（欧洲/巴黎）：换回 11-05 运行时，并做法国、周/商、台湾 1945–49

第一批的 311 处满洲失败是因为把 0.6.2 源码盖在已发布的 0.6.1 运行时上，热河被拆成第二块满洲国，兴安南落在旧的「Manchuria」多边形外面。不是 2026-11-05 快照本身的结果。本批换回该快照的 `cshapes`、`control_zones`、`transitions`。`ww2_europe` 解压后与仓库里的文件相同，没有换。桂林日军占领是在快照几何上挖掉原有广西折线，没有新造边界，复测仍是大日本帝国。

四包原始数据已放进 `data/basemaps_raw/`、`data/basemaps/1930.geojson.gz`、`data/cshapes_raw/`。快照里的满洲国已经是两段（1932-03-01 至 1933-03-04 不含热河，1933-03-04 起含热河和黑吉辽补块）。没有重跑 `build_cshapes.py`，避免把这份快照再改偏。单独的热河控制区从整理数据里去掉，免得以后又画出两个满洲国。

台湾：CShapes 在 1945-08-15 把岛屿并回中国多边形，点选会先命中中国。本批把 1945-08-15 至 1949-12-08 的中国行挖去原有台湾岛几何，并把日治多边形延到 1945-10-25、10-25 至 12-08 复用同一块岛。澎湖不在这块里。来源：[Retrocession Day](https://en.wikipedia.org/wiki/Retrocession_Day)。

2000-06-01 巴黎：政权链当前行是法兰西第五共和国（1958-10-04 起），旗是 Flag of France (1976–2020)。Wikidata「法国」Q142 的起点仍是 481 年，面板注明那不是第五共和国的成立日。来源：[French Fifth Republic](https://en.wikipedia.org/wiki/French_Fifth_Republic)。

前 1136 年：Sinic 多边形是商朝；Zhoa 多边形改为周，不再是第二块商。周灭商采用约前 1046 年，传统约前 1122 年不作为依据。底图是前 1500 年快照。来源：[Western Zhou](https://en.wikipedia.org/wiki/Western_Zhou)、[Xia–Shang–Zhou Chronology Project](https://en.wikipedia.org/wiki/Xia%E2%80%93Shang%E2%80%93Zhou_Chronology_Project)。

TNO / 钢铁雄心 IV 风格地图仍在队列里，本批没有做。只参考视觉，不用游戏数据当史料。M6 / Apple 芯片原生包按用户指示免做，现有 Mac 包不因此取消。完整队列见 `docs/REQUIREMENTS_0.6.2.md`。

### 本批命令（都在 8792、版本 0.6.2 上）

- `tools/accept/p0_batch2.py`：16 条通过，退出码 0。
- `tools/accept/p0_1941.py`：22/22。
- `tools/accept/api_mustpass.py`：119/119。
- `tools/accept/manchuria_no_roc.py`：162 个月，0 处失败。
- `tools/accept/ww2_occupation_bloc.py`：72 个快照，1444 次检查，0 处缺失。

没有跑截图，没有跑打包版。维希条约、1911 各省、甘丹颇章、藏南、1950 海南和李弥部、悬停经济和宪法页都还没做。

## 2026-11-08 第三批（欧洲/巴黎）：策略地图的一部分，以及悬停满 5 秒的经济

前两批的历史修复没有改几何。这一批只加画法和一个浮窗。

策略地图是软件自己的画法，用来参考策略游戏怎么分清边界、占领区和名称。不是 TNO 或钢铁雄心的官方地图，没有使用那些游戏的图。普通样式还在，年代和实控没有改。放大到 5 级后的细线来自已有的 Natural Earth 1:10m 一级行政区（公有领域），并写明是现代行政区，不是历史省界。没有地形数据，所以没有画地形，也没有新造省界。

经济浮窗：指针停在一个政权上满 5 秒才出现，离开就消失。换政权、拖动、缩放、改日期、关图层会取消计时和未返回的请求。数字只用 Maddison Project Database 2023 里正好等于所选年份的值（CC BY 4.0，https://doi.org/10.34894/INZBF2 ）。没有这一年就是「暂无数据」，不用邻年，也不把更晚的数填进来。点开的民生经济面板仍保留原来的插值标注。

### 本批命令（端口 8792，版本 0.6.2）

- `WHA_PORT=8792 python3 tools/accept/p0_batch3.py`：16 项通过，退出码 0。这是接口，不是鼠标。
- `WHA_PORT=8792 python3 tools/accept/p0_1941.py`：22/22。
- `WHA_PORT=8792 python3 tools/accept/p0_batch2.py`：16 条通过。
- `python3 tools/accept/api_mustpass.py`：119/119。
- `node tools/accept/browser_batch3.mjs`（系统 Chrome，无头）：退出码 0。控制台错误 0（补了页面图标后不再请求 favicon）。策略描边 0.6 变为 1.35。现代行政区线 172 条，约 0.7 秒。2020 年点击澳门圆点得到「澳门」。2000 年法国悬停 3.2 秒没有浮窗，5021 毫秒后出现 33410 国际元和 6081 万人；指针离开后浮窗消失；中途改日期不再出现。
- 没有用触屏设备试长按。代码里用指针按下、移动和松开处理。没有重跑满洲 162 个月、阵营 72 个月和打包版。

截图在验收记录里，不放进仓库。维希条约、1950 年沿海和李弥部、甘丹颇章、1911 各省、藏南和阿克赛钦、宪法和基本法、全域审计都还没做。T01 也不能算做完。

## 2026-11-08 第四批（欧洲/巴黎）：策略地图改深色，并核对四份法国文件和 1950 年沿海

用户看过第三批后说还不够 TNO。暖纸底和加粗边线不作为通过。本批先看了两张公开画面，再改画法。参考只用于视觉：r/TNOmod 的 *Fate of Nations*（https://www.reddit.com/r/TNOmod/comments/7ll37n/development_update_i_fate_of_nations/ ）里那张 “Europe and North Africa, 1962”，以及 r/imaginarymaps 的 1962 年总览（https://www.reddit.com/r/imaginarymaps/comments/m2ppaz/the_new_order_last_days_of_europe_1962/ ）。没有抄界面、旗帜或边界，也没有拿它们当史料。

策略地图现在是深灰蓝海面和低饱和陆色，国界深于行政细线，国名按画面中心优先、同一个简称只标一次。4 级只留首都星。普通地图仍可切回。没有地形数据，没有假装有地形。T01 仍是部分完成。

经济浮窗把来源和“现代国家范围、不是当时政权、也不是后来某个共和国的统计”收成底部一句。

四份法国文件：第二次贡比涅停战协定 1940-06-22 签署、06-25 生效，签署方是法兰西第三共和国和纳粹德国。法国-意大利停战协定 06-24 签署、06-25 生效。巴黎议定书 1941-05-28 签署，未批准，不作为生效条约。法日印度支那议定书 1941-07-29 签署当日公布实施，没有议会批准。后两份不在 Wikidata 导出里，用 curated id，没有发明 QID。维基为辅助。斯洛伐克、克罗地亚独立国、汪精卫政权、满洲国、意大利社会共和国的条约没有编目。

1950 年：海南不再整岛可点成中华民国。海口框到 04-23，榆林和三亚一带到 04-30。腹地点到底图上的中国，不是对其余每一点的实测。琼崖纵队没画。舟山维持到 05-17。大陈改到 1955-02-12，当天起该海点没有底图多边形。一江山大致框到 1955-01-20；离大陈太近，轮廓结束后点击可能仍落到大陈。李弥部缩到景栋、孟萨一带，不是主权。1911 年各省没有做。

### 本批命令（端口 8792，版本 0.6.2）

- `python3 tools/accept/p0_batch4.py`：退出码 0。
- `python3 tools/accept/p0_1941.py`：22/22。
- `python3 tools/accept/p0_batch2.py`：16 条通过。
- `python3 tools/accept/p0_batch3.py`：16 项通过。
- `python3 tools/accept/api_mustpass.py`：119/119。
- `node tools/accept/browser_batch4.mjs`：系统 Chrome 无头。1944-12-01 欧洲（48°N, 8°E，4 级）和东亚（32°N, 114°E，4 级）各一张，普通地图同一欧洲视角一张，2000-06-01 法国悬停一张。3.2 秒时浮窗未出现。浮窗写明现代国家「法国」范围，来源只在底部出现一次。页面错误 0。4 级没有城市名，只有首都星。

没有重跑满洲 162 个月、阵营 72 个月和打包版。没有合并，没有发布。截图不放进仓库。

2026-11-08 05:08（欧洲/巴黎）用户把《中华民国史事纪要》排到这一批视觉之后。本批没有展开该书的检索或录入。T01 仍不能勾完。

2026-11-08 05:21（欧洲/巴黎）用户改了顺序：中华民国史扩充放在所有其他更新之后，不只是放在 TNO 之后。已经做完的民国史修正不回滚。第五批仍先做地图。

## 2026-11-08 第五批（欧洲/巴黎）：地图更大，国名回到自己的土地上，补上满洲国西缘的缺口

用户看第四批截图后指出两件事：欧洲画面上「苏联」跑到不列颠北面的海里；东亚满洲国西缘、蒙疆名称北面有一小块和中华民国同色的地。随后又要求地图本身更大，不是只把截图存得更清晰。05:21 的顺序是先做完这些，其余功能随后，《中华民国史事纪要》最后。

那块褐色是 CShapes「China」（第 547 行，1921-03-13 至 1945-08-15）从两块近似多边形之间露出来的。代表点约北纬 45.4 度、东经 118.8 度。它不是苏联，也不是另一块政权。今锡林郭勒盟公开区划写到东经 120 度、北纬 46 度 41 分。兴安南省所辖是科尔沁各旗和扎赉特旗，旗治在这块地以东，那些点本来就在满洲国多边形里。1944 年 12 月这里不是重庆国民政府的实地控制。本批把蒙疆近似范围补到既有满洲国多边形和外蒙古多边形为止，没有新画一条国界。外蒙古原来就有的重叠没有扩大。来源：内蒙古区情网哲里木盟建置（https://www.nmgqq.com.cn/quqinggailan/jianzhiyange/tls/13336/13336.html ），行政区划网锡林郭勒盟范围（http://xzqh.org/html/show/nm/3806.html ）。蒙疆折线本身仍是大致范围。

国名不再用外接矩形中心。1944-12-01、北纬 48 度、东经 8 度、4 级时，「苏联」落在北纬 58.89 度、东经 43.32 度，点选是苏联，不是不列颠附近的海。东亚同一天，「大日本帝国」落在本州或九州，桂柳会战那块单独标成「桂柳（日军）」，提示里写明控制方是大日本帝国。地图上的简称是核对过的叫法，全名在提示里。没有核对过的长名整段显示，不用省略号。

地图占窗口的比例提高了。桌面默认缩放从 2.5 提到 3.5，先看到欧洲到东亚，缩小和「全世界」还在。窄屏默认 3 级。顶栏和底栏收紧，图层、图例和边界说明默认收起，点开还能看。侧栏仍是盖在地图上的，关掉就不占地方。改日期不重置已经选好的中心和缩放。来源署名还在地图角，窄屏上可以滚动看全文，没有为了省地方删掉。

地形用 Natural Earth 1:50m Shaded Relief（公有领域）。水面临时去掉，只留陆地起伏，改到 Web 墨卡托后叠在政权颜色上。文件在 `frontend/assets/ne50m_hillshade.png`，随软件走，打开地图时不下载。它是现代自然地形，不是历史国界，源数据里的海是平的，所以没有海底深浅。T01 仍不能勾完。

### 本批命令（端口 8792，版本 0.6.2）

- `python3 tools/accept/p0_batch5.py`：缺口内三点是蒙疆，东侧和兴安南、海拉尔、赤峰、承德仍是满洲国，北侧两点仍是外蒙古，西安和河套仍是 China。失败 0。
- `python3 tools/accept/p0_batch4.py`、`p0_1941.py`（22/22）、`p0_batch2.py`、`p0_batch3.py`：失败 0。
- `python3 tools/accept/api_mustpass.py`：119/119。
- `python3 tools/accept/manchuria_no_roc.py`：162 个月，失败 0。
- `python3 tools/accept/ww2_occupation_bloc.py`：72 个快照，1444 次占领区检查，0 处既不是阵营成员也没有附庸标签。
- `node tools/accept/browser_batch5.mjs`：系统 Chrome 无头。欧洲画面的「苏联」经度大于 20；改月份后中心和缩放不变；普通地图能切回；窄屏没有横向溢出，署名仍含 historical-basemaps 和 Wikidata。

同一窗口尺寸的前后截图：桌面 1440×900，窄屏 390×844。桌面地图高度约从 783 像素到 803 像素，顶栏从 45 像素到 34 像素；窄屏地图高度约从 570 像素到 677 像素，顶栏从 202 像素到 118 像素。默认打开时的缩放也更高。没有靠把浏览器整页放大来充数。

没有合并，没有发布。《中华民国史事纪要》没有检索，也没有录入。1911 年各省没有做。

## 2026-11-08 核查批（欧洲/巴黎）：撤掉蒙疆填补，改口现代参考线

第五批把约北纬 45.4 度、东经 118.8 度补进蒙疆，依据是今天锡林郭勒的经度范围，以及哲里木盟、兴安南省的旗治在这块地以东。这次核对后认为不够。

内蒙古党史方志网写明：民国 26 年（1937）七七事变后，东乌珠穆沁旗隶属伪蒙古联盟自治政府，1939 年改属伪蒙疆联合自治政府，1945 年 8 月复归察哈尔省。这段用的是「今旗境」。同站现代四至约为北纬 44°4′ 至 46°10′、东经 115°10′ 至 120°07′。1932 年兴安南分省列的是科尔沁各旗和扎赉特旗，不包括乌珠穆沁。扎鲁特旗 1933 年后属兴安西分省，西界在这一纬度有没有到东经 118.8 度，没有查到当时的实测。1940 年《蒙古地方行政区划图》只见到著录，图幅没有打开。名义隶属、现代行政范围和实地控制是三件事。证据不够，蒙疆折线恢复到第五批之前的手绘范围，不再为了消掉缝隙往外扩。

露出的底图改标「空隙（未核实）」：灰色虚线，没有控制方，点选名称和颜色一致，不写成蒙疆，也不写成中华民国实地控制。外缘是两块近似多边形之间的洞，不是新测边界。边界精度标成大致。1944-12-01 的东侧、兴安南、海拉尔、赤峰、承德仍是满洲国，北侧两点仍是外蒙古，蒙疆腹地、西安、河套和桂柳没有被这块空隙吞掉。

图上的浅线改称现代一级行政区参考线。历史省界未做，这一批没有再下载数据来凑。T01 各子项见 `docs/REQUIREMENTS_0.6.2.md`，都不能写成验收通过。画面外不显示国名，只说明该名称不在当前窗口里，不是锚点已经全部核对完。

119 条、满洲 162 个月、阵营 72 个快照的第五批结果保留，这一批没有重跑。针对改过的空隙重跑了 `p0_batch5.py`。没有合并，没有发布。《中华民国史事纪要》没有检索，也没有录入。

## 2026-11-08 视觉批（欧洲/巴黎）：国名按字框避让，海岸光晕去掉

用户看过核查批的真实截图后指出两件事：1944-12-01 欧洲画面上「波希米亚和摩拉维亚保护国」太长，和苏军收复区、苏占匈牙利以及巴尔干国名挤在一起；手机东亚首屏「苏联」贴着顶栏。海岸还有一圈发白发灰的粗边和海里的像素块。

国名改成先量出实际字宽字高，再在本国多边形里找放得下的位置。字心必须在本多边形内。两端可以落在海上，不能落进另一个政权。字框之间留 5 像素。主权国先放，其余区域和未核实范围靠后，放不下就不再往上堆。地图尺寸若和可见区域不一致，先按可见区域重算，避免字画进底栏或画出屏幕。全名仍在悬停和点选里。末尾的「保护国」「王国」「共和国」只在全名放不下时去掉，不另造简称。没有名称的多边形不再标成「未命名区域」。

4 级欧洲画面上，波希米亚和摩拉维亚保护国的外接范围大约 65×36 像素，全名约 223 像素宽，去掉「保护国」仍约 167 像素宽，都比这块地宽，所以地上不标，悬停仍是全名。匈牙利王国去掉「王国」后约 56 像素宽，意大利社会共和国约 149 像素宽，也都放不进各自的范围，不缩成看不清的字，也不写成「意大利」以免和南边的意大利王国相混。罗马尼亚、保加利亚王国、希腊王国、意大利王国、纳粹德国、法国临时政府和苏联都标在本国里，字框不相交，也不出屏幕。苏占匈牙利这类控制区在策略地图上只留菱形，名称在点开的说明里。图例写明：写不进该范围就悬停或点选看全名。

手机 390×844、1944-12-01、北纬 32 度、东经 114 度、4 级时，「苏联」不再贴顶栏，画面里的国名不出上下左右。这一视角的东缘大约在东经 131 度，日本本州大部分在画面外，可见的一截放不下「大日本帝国」，所以不把字裁在屏幕边上。把视角移到本州上时，这个名字标在日本境内。

海岸光晕的原因：上一张晕渲先对整幅图做了高通，海里的亮色留在透明像素里，浏览器放大后沿海岸拉出白边和碎块。这一张先把陆地和海分开，只在陆地上做起伏，透明像素改成中性灰，岸边不额外提亮。阿尔卑斯一带的起伏还在，海面不再铺一层发灰的像素。许可署名仍是 Natural Earth，文件仍随软件离线打包。没有把整张地图模糊掉。

历史省界没有做。现代一级行政区参考线的叫法不变。约北纬 45.4 度、东经 118.8 度的空隙仍是「空隙（未核实）」，这一批没有再考据，也没有再填。119 条、满洲 162 个月、阵营 72 个快照没有重跑。T01 仍不能勾完。《中华民国史事纪要》没有检索，也没有录入。没有合并，没有发布。

### 本批命令（端口 8792，版本 0.6.2）

- `node tools/accept/browser_batch6.mjs`：系统 Chrome 无头。1944-12-01 欧洲（48°N，8°E，4 级，1440×900）、手机东亚（32°N，114°E，4 级，390×844）和手机默认视图。标签不出屏幕、不相交、无省略号。波希米亚全称不画在地上，悬停仍有波希米亚和摩拉维亚保护国、匈牙利王国、意大利社会共和国。欧洲苏联经度大于 20。手机默认缩放仍是 3。
- `python3 tools/accept/hillshade_coast.py`：透明像素不是中性灰的为 0，紧挨海水且过亮的陆地像素为 0。

## 2026-11-08 宪法第一批（欧洲/巴黎）：先记下海岸细点，再做宪法页

手机华东和南海岸边的细碎像素还在。上一批已经去掉发白的粗边；剩下的是 3200 像素晕渲沿海岸重采样，以及真实小岛。没有再重做栅格，也没有删岛礁或把边界模糊掉。历史省界仍然没画，细线仍叫现代一级行政区参考线。约北纬 45.4 度、东经 118.8 度的空隙仍是「空隙（未核实）」。T01 不能勾完。

宪法页按点到的政权和所选日期显示当时正在施行的文本。生效日含当天，结束日不含当天。通过、公布、生效、废止分开写。没有正在施行的文本时，这一页不出现，说明里也不使用「无宪法」。类型有正式宪法、临时宪法/约法、不成文宪法、基本法、帝国/钦定宪法、宪章；维希那一组标成类型待考。

1944年12月1日的巴黎是临时政府，只显示1944年8月9日恢复共和合法性法令，不是1946年宪法。1946年10月26日仍是那两部临时文本，10月27日才是1946年宪法。1958年10月3日仍是1946年宪法，10月4日换成1958年宪法。英国不是单一成文宪法。1947年5月2日的东京仍是大日本帝国宪法，5月3日才是日本国宪法。1949年5月23日的波恩不显示基本法，5月24日才显示。柏林同一天是苏占区，不显示基本法。英属印度、重庆和北京都没有被套上这批文本。

没有收录的还包括更早的法国宪法、1852年宪法、1871年德意志帝国宪法、1968年东德宪法，以及中华民国、中华人民共和国的宪法。不能把这一批说成全球齐全。

窄屏上，打开的政权页改到图例和边界说明上面，避免那两个按钮压住宪法正文。

《中华民国史事纪要》没有检索，也没有录入。没有合并，没有发布。

### 本批命令（端口 8792，版本 0.6.2）

- `python3 tools/accept/constitutions.py`：49 条前后一日查询，0 处失败。
- `node tools/accept/browser_constitutions.mjs`：系统 Chrome 无头。桌面 1440×900 点巴黎，从 1944-12-01 跳到 1946-10-26 再跳到 1946-10-27；1944-12-01 点柏林，宪法页不出现。手机 390×844 点东京，从 1947-05-02 跳到 1947-05-03；再点 2000-06-01 的伦敦。
- `python3 tools/accept/api_mustpass.py`：119/119。满洲 162 个月和阵营 72 个快照这一批没有改几何，没有重跑。
