# v0.6.1 说明（在 v0.6.0 基础上，2026-11-02；未推送、未发布）

- 版本号：`backend/config.py` `APP_VERSION = "0.6.1"`；`packaging/world_history_atlas.spec` 与 `.github/workflows/build.yml` 默认版本 0.6.0 → 0.6.1。
- spec 的 hiddenimports 增加 `backend.interregna`（空位期/摄政/共治）、`backend.zh`（中文名补译）、`backend.geolock`（几何合成线程锁）。
- 新的 curated 数据：`interregna.json`、`extra_offices.json`（幕府将军/关白/摄政/执权/护国公/北洋总统与国务总理）、`office_links.json`、`name_candidates.json`、`zh_labels.json`、`zh_basemap_names.json`、`zh_manual.json`。
- 修复服务器在并发请求同一边界时崩溃（GEOS double free）：几何合成加锁。

---

# v0.6.0 说明（在 v0.5.0 合并包基础上，2026-11-02）

v0.5.0 已经把本地源码与仓库 v0.4.1 的打包/退出改动合好；v0.6.0 继续以本地源码为主，没有再从仓库拉取新代码。

- 版本号：`backend/config.py` `APP_VERSION = "0.6.0"`；`packaging/world_history_atlas.spec` 默认 `WHA_VERSION` 0.5.0 → 0.6.0；`.github/workflows/build.yml` 手动运行时的默认版本 `'0.5.0'` → `'0.6.0'`（打标签时仍用标签名）。
- spec 的 hiddenimports 增加 v0.6 新模块：`backend.cshapes`、`backend.ww2`、`backend.flags`、`backend.regimes`、`backend.china_eras`。
- 新的运行时数据（发布包里都是 `.xz`，由 `datafile.read_json` 读取）：`cshapes.json`（CShapes 2.0）、`ww2_europe.json`（Stanford）、`transitions.json`、`control_zones.json`、`flags.json`、`china_eras.json`；`curated/` 下的 JSON 原样复制。
- 首次打开某个 1886 年以后的日期时，边界要合成几秒到十几秒，结果写到用户目录的 `cache/cs_compose/`，之后直接读取。
- 测试结果见 `AUDIT_REPORT.md`，已知缺口见 `KNOWN_ISSUES.md`。

---

# v0.5.0 合并说明（本地 /workspace/world_history → GitHub archillegao-dotcom/world-history-atlas，基线 main = v0.4.1）

本上传包已经把两边合好：**以本地 v0.5 源码为主，重新套上了仓库里 v0.4.1 独有的打包/退出改动**。
用源码 + launcher 跑过仓库自己的 `packaging/smoke_check.py`（1789-07-14 法国事件含攻占巴士底狱、城市图层、`/quit`、`/api/shutdown` 拒绝无头请求、用户目录 README/server.json）以及 `test_launcher_translocation.py`，全部通过。**没有在 macOS/Windows 上跑 PyInstaller**，需要 CI 验证。

## 1. 仓库独有、必须保留的文件（本地原来没有，已原样放进上传包）
| 路径 | 作用 |
|---|---|
| `launcher.py` | 免安装版入口（App Translocation 修复、`--no-terminal`、第二次启动只开浏览器、用户目录种子、server.json） |
| `packaging/world_history_atlas.spec` | PyInstaller 配置（v0.5.0 改动见下） |
| `packaging/build.py`、`smoke.sh`、`smoke_check.py`、`release_notes.py`、`test_launcher_translocation.py`、`user_seed/README.txt` | 打包、冒烟测试、发布说明 |
| `.github/workflows/build.yml` | macOS arm64/Intel + Windows 构建与发布 |
| `.gitignore`、`.gitattributes` | `*.xz`/`*.png` 按二进制处理 |

## 2. 两边都改过的文件（已合并，覆盖时注意不要丢掉仓库那一半）
| 文件 | 仓库独有（保留） | 本地新增（保留） |
|---|---|---|
| `backend/app.py` | `boot()` 延迟加载（`WHA_PYINSTALLER_ANALYZE=1` 时不加载数据）、`set_shutdown()`、`GET /quit`、`POST /api/shutdown`（仅本机且需 `X-WHA-Shutdown: 1` 头） | 按日期快照 `snapshot_at`/组合快照 id（如 `1783@17650510`）、`transitions` 说明、`/api/basemap/{snap:str}`、ISW/DeepState 来源 |
| `backend/config.py` | 用仓库版本：`per_user_dir()`、冻结时数据只读不写软件包、`APP_NAME` | 只改 `APP_VERSION = "0.5.0"` |
| `backend/registry.py` | 用仓库版本：冻结后从 `sys._MEIPASS/backend/modules` 按文件名发现模块 | 无冲突（新模块 `layer_control_zones`、`layer_war_fronts` 自动发现） |
| `frontend/index.html` | 用仓库版本：右上角 `#quitBtn`「退出」及其脚本（smoke_check 检查 `quitBtn`） | 本地 index.html 无其他改动；新前端模块由后端清单动态加载 |
| `requirements.txt` | 用仓库版本（`certifi`、`tzdata`） | 无新增依赖 |
| `run.py` | 仓库的说明文字 | 本地的 `SO_REUSEADDR` |
| `README.md` | 免安装版说明、打包说明、目录结构里的 launcher/packaging | v0.5 章节、构建顺序、许可表；新增「更新记录」v0.5.0 |

## 3. 为适配仓库的 .xz 数据约定而改的本地代码
仓库 `data/` 只放 `.json.xz` / `.geojson.xz`（`build.py` 要求 `data/events.json.xz`）。上传包的数据也全部转成 .xz（`tools/dev/stage_data_xz.py`，内容不变）。
- `backend/official.py`：原来直接 `gzip` 读 `official_offices.json.gz` → 改用 `datafile.read_json/exists`（否则打包版官方名单会静默丢失）。
- `backend/modules/layer_war_fronts.py`：同样改用 `datafile`，`.gz`/`.xz` 都能读。
- 其余新模块（transitions、control_zones、territory_info、rulers…）本来就走 `datafile`。

## 4. 版本号
- `backend/config.py` `APP_VERSION = "0.5.0"`
- `packaging/world_history_atlas.spec` 默认 `WHA_VERSION` 0.4.0 → 0.5.0；hiddenimports 增加 `backend.control_zones`、`backend.official`、`backend.territory_info`、`backend.transitions`
- `.github/workflows/build.yml` 手动运行时的默认版本 `'0.4.1'` → `'0.5.0'`（打标签时仍用标签名，发布请推 `v0.5.0` 标签）

## 5. 上传时要删除 / 不要带的
- 仓库里 v0.4.1 的旧数据文件全部被新的同名 .xz 覆盖；仓库里没有、本地新增的数据：`control_zones`、`transitions`、`territories`、`rulers`、`ruler_persons`、`ruler_fills`、`official_offices`、`territory_qids.json`、`curated/`、`xcheck/`、`audit/`、`war_fronts/`。
- 不带：`.venv`、`mtvenv`、`logs/`、`data/cache`、`data/basemaps_raw`、`data/econ_raw`、`data/xcheck_raw`、`data/live`、`*.bak*`、`__pycache__`。

## 6. 风险
- **体积**：运行时数据 v0.4.1 约 31 MB → v0.5.0 约 51 MB（其中战争前线 22 MB，1,582 个逐日文件）。App 包会相应变大约 20 MB；每多一天 DeepState 数据约 +15 KB。
- **启动内存/时间**：transitions 与政权解析在启动时加载；源码 + launcher 冒烟测试约 10 秒内就绪（本机 Linux）；PyInstaller 版未测。
- 仓库 main 若在 v0.4.1 之后又有提交，需要按第 2 节再对一次。
