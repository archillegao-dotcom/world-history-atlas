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
