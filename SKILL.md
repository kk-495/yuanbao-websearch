---
name: yuanbao-websearch
description: 用腾讯云元宝搜索（WSA SearchPro）实时检索互联网，返回标题、摘要、URL、发布时间、站点与相关度。需要最新资讯、事实核查、时效数据（股价/金价/天气/汇率）、指定站点或指定时间范围的检索时使用。中文信源覆盖优于通用搜索。需要配置环境变量 TENCENTCLOUD_WSA_APIKEY。
allowed-tools: Bash, Read
homepage: https://cloud.tencent.com/product/wsa
license: MIT
metadata: {"openclaw":{"emoji":"🔍","requires":{"bins":["python3"],"env":["TENCENTCLOUD_WSA_APIKEY"]}}}
---

# 元宝搜索 Skill

腾讯云元宝搜索（Tencent Yuanbao Search，WSA）的检索封装。以全网公开资源为基础叠加腾讯内容生态，返回结构化的网页结果，适合喂给大模型做检索增强。

## 什么时候用

- 用户要**最新信息**：「最近」「今年」「今天」「刚出的」「有什么新变化」
- **事实核查**：不确定的新闻、政策、版本号、发布时间、数据口径
- **时效性数据**：股价、金价、汇率、天气、票房、赛程
- **定向检索**：只在某个站点找（知乎、政府网站、arxiv），或排除某些站点
- **垂直领域**：政策文件（gov）、新闻（news）、论文（acad）、财经（finance）

## 什么时候不用

- 纯逻辑、写代码、翻译、格式转换 —— 不需要联网，别浪费配额
- 用户明确要求「不要搜」「按你已知的回答」
- 常识性、稳定的知识（数学公式、语言语法）

## 执行方式

脚本在 skill 目录的 `scripts/yuanbao_search.py`，**用绝对路径调用**（不要 cd 进去）：

```bash
python3 <SKILL_DIR>/scripts/yuanbao_search.py --query "关键词"
```

Windows 上若没有 `python3`，用 `python` 或 `py -3`。

### 先自检（第一次用、或报错时）

```bash
python3 <SKILL_DIR>/scripts/yuanbao_search.py --doctor
```

它会打印密钥来源（打码）、试调一次接口，并把错误码翻译成「原因 + 该去哪解决」。密钥没配好时退出码为 2。

### 常用调用

```bash
# 基础检索
--query "三星堆的由来"

# 只要最近 3 天，20 条
--query "英伟达财报" --cnt 20 --freshness d3

# 股价/金价/天气这类实时数据，走混合模式拿垂直信源
--query "贵州茅台股价" --mode 2 --industry finance

# 只搜知乎
--query "长上下文模型评测" --site zhihu.com

# 排除内容农场
--query "AI 监管" --site "exclude:sohu.com|163.com"

# 指定日期区间
--query "中央经济工作会议" --freshness 2026-10-01,2026-10-23

# 机器可读，落盘
--query "开源许可证对比" --format json --out result.json
```

## 参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `--query` / `-q` | 是 | 搜索词，UTF-8 不超过 1500 字节（约 500 汉字） |
| `--cnt` | 否 | 返回条数，只能取 10 / 20 / 30 / 40 / 50（极速版不支持） |
| `--freshness` | 否 | `d7` 近 7 天、`m3` 近 3 月、`y2` 近 2 年、`2026-10-01` 指定日、`2026-10-01,2026-10-23` 区间 |
| `--site` | 否 | 限定站点 `zhihu.com`；排除 `exclude:a.com\|b.com`（最多 5 个） |
| `--mode` | 否 | `0` 公开网页（默认）、`1` 权威垂直信源、`2` 混合 |
| `--industry` | 否 | `gov` / `news` / `acad` / `finance` |
| `--format` | 否 | `md`（默认，给模型读）、`json`（给程序读）、`text`（纯文本） |
| `--snippet-len` | 否 | 摘要截断长度，默认 300，`0` 不截断 |
| `--out` | 否 | 输出写入文件 |
| `--api-key` | 否 | 临时指定密钥（共享环境慎用） |
| `--key-file` | 否 | 密钥文件路径 |
| `--doctor` | 否 | 环境自检 |

## 输出

默认 markdown，一条结果一段：

```
## 查询词：贵州茅台股价 ｜ 结果 10 条 ｜ 版本 standard

1. [贵州茅台(600519)股票行情](https://...)
   - 摘要：……
   - 发布时间 2026/10/22 15:00:00 ｜ 站点 东方财富网 ｜ 相关度 0.91
```

`--format json` 时每条结果含：`title / url / date / site / score / authority_level / text / passage / content / pics / deeplinks / is_vertical`。

## 把 query 写好

检索质量七成取决于 query，不是取决于参数。

- **关键词化，别整段复制问题**。「2026年10月央行降准了多少个基点」比「你能帮我看看最近央行是不是降准了降了多少」好得多
- **带上专有名词和时间锚点**：「DeepSeek V4 发布时间」而不是「那个新模型什么时候出的」
- **需要权威来源时加 `--industry gov` 或 `--site gov.cn`**，别指望默认结果里全是官方文件
- **一次没搜到就换词**，不要原样重试；或者去掉 `--freshness` 放宽时间

## 结果怎么用

1. **引用要给出来源**：把 `url` 和 `site` 一起给用户，别只转述摘要
2. **注意时间**：`date` 就是内容的发布时间，跨年的老文别当新消息
3. **多源交叉**：只取 1 条结论容易翻车，重要事实至少两条独立来源
4. **摘要可能被截断**：需要原文细节时抓 `url` 全文，别硬猜
5. **区分标准版与旗舰版**：标准版不返回 `authority_level`、`deeplinks`，`content` 也可能缺失 —— 字段为空是正常的，不是出错

## 报错怎么办

| 错误码 | 原因 | 处理 |
|---|---|---|
| `UnauthorizedOperation` | 密钥错/被删 | 去控制台核对 API KEY |
| `ResourceNotFound` | 服务未开通 | 控制台开通，等几分钟生效 |
| `ResourceUnavailable` | 欠费 | 充值 |
| `RequestLimitExceeded` | 并发超限 | 降频；脚本已自动重试一次 |
| `InvalidParameter` | 参数不合法 | 常见是 `Cnt` 传了 3 这类非法值 |

退出码：`0` 成功 / `2` 缺密钥 / `3` 接口报错 / `4` 网络异常 / `5` 参数错误。

更细的字段与错误码见 `references/api.md`，密钥配置见 `references/setup.md`。

## 配额提醒

按调用次数计费，有免费额度（额度规则以腾讯云活动页为准）。批量检索时合并 query、控制 `--cnt`，不要循环里反复重试。
