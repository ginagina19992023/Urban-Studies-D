# 自查查重：论文英文正文对照引用文献原文

日期：2026-11-10。这是我自己跑的比对，**不是 Turnitin 或学校的查重系统**，结果只作参考。

## 方法
- 对象：`Draft-Thesis-v2.docx` 的英文正文（引言到结论，不含参考文献、图表说明）。共 4,176 个词，其中 307 个词在引号里。
- 对照：23 份我手里有全文或可检索文字的来源，包括 Zanardo 等、Sisson (2024)、Wynne and Rogers、Yrjänä、Lees、Sisson and Ruming、Khor 等 (AHURI 412)、AHURI 413、Atkinson 等 (AHURI 160)、Future Directions、计划定稿报告、最终规划建议书、设计指南、Turner Studio、LAHC 规划建议书 2020、Scully、ABC 报道、Homes NSW、两份政府新闻稿、City of Sydney 文件、Hochstenbach、Shaw。
- 算法：连续 6 个词相同算一次重合，相邻重合合并成一段；再把每段分成“在引号里”和“不在引号里”。

## 结果
- 与全部来源的重合合计 370 词，占正文 8.9%；其中 191 词（52%）在引号里，是直接引文。
- 不在引号里的重合，只剩短的固定短语：人名、机构名、日期、数字和引用写法。
- 单个来源里，重合最多的是 City of Sydney 文件（154 词，多是长段带引号的引文）和 LAHC 规划建议书 2020（103 词，多是带引号的引文与页码引用）。Yrjänä、Lees、Atkinson、Hochstenbach、Shaw 为 0。

| 来源 | 重合词数 | 不在引号里、连续 8 词以上的重合 |
|---|---|---|
| Zanardo 等 2024 | 7 | 0 |
| Sisson 2024 | 36 | 0 |
| Wynne and Rogers 2021 | 14 | 0 |
| Yrjänä 2026 | 0 | 0 |
| Lees 2008 | 0 | 0 |
| Sisson and Ruming 2025 | 61 | 0 |
| Khor 等 2023 | 20 | 0 |
| AHURI 413 | 6 | 0 |
| Atkinson 等 2011 | 0 | 0 |
| Future Directions 2016 | 39 | 0 |
| 计划定稿报告 2022 | 77 | 1（是论文里“November 2022 (NSW Department of Planning and Environment 2022)”这个引用写法本身） |
| 最终规划建议书 2022 | 47 | 0 |
| 设计指南 2022 | 22 | 0 |
| Turner Studio 2020 | 6 | 0 |
| LAHC 规划建议书 2020 | 103 | 0 |
| Scully 2026 | 12 | 0 |
| Bowring 2026 (ABC) | 18 | 0 |
| Homes NSW 2026 | 35 | 0 |
| NSW Government 2023 | 24 | 0 |
| NSW Government 2024 | 6 | 0 |
| City of Sydney n.d. | 154 | 0 |
| Hochstenbach 2017 | 0 | 0 |
| Shaw 2008 | 0 | 0 |

## 第一次比对发现并改写的 8 处
第一次比对时，下面这些句子里有 8–11 个连续词和来源一样但没有加引号，我改写了：
- Lees：“on the assumption that it will lead to less segregated” → “promoted in the belief that it will reduce segregation”。
- Atkinson：“was around 50 per cent higher than the out-movement” → “ran at about one and a half times the out-movement of similar households elsewhere”。
- Future Directions（引言 1.1 和 4.1 各一处）：“a ratio of 70:30 of private to social housing” → “a 70:30 split between private and social dwellings”，保留引号里的 “to enable more integrated communities”。
- ABC 报道（两处）：改成 “have moved into other public housing, at least 70 of them into…” 和 “could not say what part of the 20 per cent affordable share would be permanent”。
- NSW Government 2023（两处）：改成 “Aboriginal people will get at least 15 per cent of the new social and affordable homes” 和 “a way to rehouse Waterloo South tenants locally”。
- 最终规划建议书：“no less than 5,000 square metres” → “at least 5,000 square metres”。

## 限度
- 只和我有文字的来源比；没有和互联网上的其他文本、其他同学的论文比。
- Shrestha 等 (2025) 没有全文，没法比；Davidson 2018 是扫描页，没有文字层，也没法比。
- 只比了英文正文。中文是翻译，没有查。
- 6 个连续词的算法抓不到“换了词但意思和结构都照搬”的情况。这方面我靠的是写作时的复核：核心论点（规则保证楼面积、回迁只是声明、两条置换通道）是我自己的，不是来源的。
- 正式提交前，请用学校的查重系统（Turnitin 等）再查一次。
