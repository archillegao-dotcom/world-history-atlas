# war_fronts：其他战争的真实数据集调研（2026-11-02）

原则：只接入可下载、有出处的矢量或可复现数据；示意/风格化的数据不收；没有数据的战争不画。

| 战争 | 候选数据 | 形式 / 时间分辨率 | 许可 | 结论 |
|---|---|---|---|---|
| 俄乌战争 | ISW/CTP ACoT + DeepStateMap 历史快照（/workspace/ukraine_front） | 多边形，逐日 | ISW 注明出处；DeepState 公开数据，注明出处 | **已接入** |
| 叙利亚内战 2014– | Carter Center "Exploring Historical Control in Syria" https://www.cartercenter.org/programs/conflict-resolution/exploring-historical-control-in-syria/ | 8,099 个居民点，逐月控制方 | 未确认能否下载（网页为交互仪表板） | 候选第一；需确认导出/许可，点→Voronoi 面需注明是推算 |
| 叙利亚内战 2017–2022 | ACLED 分区级控制图（方法公开：https://acleddata.com/methodology/mapping-territorial-control-and-contestation-syria） | 分区（sub-district），逐月；项目已停止 | ACLED 需注册，条款限制再分发 | 可按其公开方法用 ACLED 事件数据复现；许可待查 |
| 叙利亚内战 | Wikipedia Module:Syrian Civil War detailed map（逐村点位，编辑历史即时间序列） | 点，任意日期（按修订） | CC BY-SA 4.0 | 可行但为维基编辑，标 approx；需从修订历史解析 |
| 缅甸内战 | HDX "Myanmar – Areas of Control"（https://data.humdata.org/dataset/myanmar-areas-of-control） | 只有 2025-03-08 一张地理配准图片 | CC0（改编自维基） | 单日、栅格，不适合逐日；可作单日快照 |
| 二战东线 | archiv-oberaussem.com 德军陆军总司令部原始态势图（1941-06-16 至 1945-04-30，约 90 张） | 扫描图片，无矢量 | 原始档案图；版权待查 | 需人工数字化，目前不接入 |
| 二战东线 | real-stats.ru 交互图 | 71 个日期，作者自称"折线风格化" | — | **不收**（风格化，不是真实线位） |
| 二战（整体） | Ararat Petrosyan "Second World War Operational Atlas" | 18 条前线，作者注明为示意种子数据 | — | **不收**（示意） |
| 二战 斯摩棱斯克战役 | Purdue OPMAPS（Matei & Kirchubel，据 OKW 每日态势图数字化） | 1941-07-10 至 09-10 | 未公开下载 | 联系作者后再定 |
| 国界层面 | CShapes 2.0（1886–2019 国家边界） | 国界，非前线 | CC BY-NC-SA | 可用于校核底图，不属于前线 |

下一步建议：先确认 Carter Center 叙利亚数据能否导出；二战前线目前没有找到可直接使用的开放逐日矢量数据，需要数字化原始态势图（工作量大，需用户决定）。
