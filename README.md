# 元宝搜索 Skill · yuanbao-websearch

给 AI Agent 装一个「会自己判断什么时候该搜」的联网检索能力，底层是腾讯云**元宝搜索**（Tencent Yuanbao Search，WSA · SearchPro）。

只依赖 Python 标准库，无需 `pip install`。密钥走环境变量，仓库里不含任何凭证。

- GitHub：<https://github.com/kk-495/yuanbao-websearch>
- Gitee：<https://gitee.com/kk_495/yuanbao-websearch>

```
## 查询词：贵州茅台股价 ｜ 结果 10 条 ｜ 版本 standard

1. [贵州茅台(600519)行情](https://quote.eastmoney.com/sh600519.html)
   - 摘要：截至收盘，贵州茅台报 1486.00 元，涨 1.23%……
   - 发布时间 2026/10/22 15:00:00 ｜ 站点 东方财富网 ｜ 相关度 0.91
```

## 为什么用它

- **中文信源强**：全网公开资源 + 腾讯内容生态（新闻、公众号、视频号），中文query 的召回明显好于纯英文搜索引擎
- **时效可控**：`--freshness d3` 只要最近三天，`2026-10-01,2026-10-23` 精确到区间
- **能定向**：只搜 `gov.cn`、只搜 `zhihu.com`，或者把内容农场排除掉
- **有垂直信源**：股价、金价、汇率、天气这类实时数据，`--mode 2` 能拿到结构化卡片
- **给模型读的格式**：默认输出 markdown，字段带发布时间和站点，方便模型自己判断可信度

## 快速开始

### 1. 拿一个 API KEY

去 [元宝搜索控制台](https://console.cloud.tencent.com/wsapi/index) 开通服务，创建「服务 API KEY」。有免费额度，具体规则见[活动页](https://console.cloud.tencent.com/wsapi/activity)。

### 2. 装 skill

把整个目录复制到你的 Agent 的 skills 目录：

```bash
git clone https://github.com/kk-495/yuanbao-websearch.git
cp -r yuanbao-websearch ~/.workbuddy-ai/skills/     # WorkBuddy
# cp -r yuanbao-websearch ~/.claude/skills/         # Claude Code
# cp -r yuanbao-websearch ~/.codex/skills/          # Codex
```

国内访问 GitHub 慢的话用 Gitee 镜像：

```bash
git clone https://gitee.com/kk_495/yuanbao-websearch.git
```

其他客户端的目录见 [`references/setup.md`](references/setup.md)。

### 3. 配密钥

```bash
export TENCENTCLOUD_WSA_APIKEY="sk-你的密钥"
```

Windows：`[Environment]::SetEnvironmentVariable("TENCENTCLOUD_WSA_APIKEY","sk-你的密钥","User")`

也可以写进 `~/.config/yuanbao-search/key`，脚本会自动读。

### 4. 自检

```bash
python3 scripts/yuanbao_search.py --doctor
```

看到 `结论：一切正常` 就装好了。

## 用法

```bash
# 基础检索
python3 scripts/yuanbao_search.py --query "三星堆的由来"

# 最近三天，20 条
python3 scripts/yuanbao_search.py --query "英伟达财报" --cnt 20 --freshness d3

# 实时行情走混合模式
python3 scripts/yuanbao_search.py --query "贵州茅台股价" --mode 2 --industry finance

# 只搜知乎 / 排除内容农场
python3 scripts/yuanbao_search.py --query "长上下文模型评测" --site zhihu.com
python3 scripts/yuanbao_search.py --query "AI 监管" --site "exclude:sohu.com|163.com"

# 指定日期区间
python3 scripts/yuanbao_search.py --query "中央经济工作会议" --freshness 2026-10-01,2026-10-23

# 给程序读
python3 scripts/yuanbao_search.py --query "开源许可证对比" --format json --out result.json
```

| 参数 | 说明 |
|---|---|
| `--query` / `-q` | 搜索词，≤ 1500 字节 |
| `--cnt` | 10 / 20 / 30 / 40 / 50 |
| `--freshness` | `d7` `m3` `y2` `2026-10-01` `2026-10-01,2026-10-23` |
| `--site` | 限定站点，或 `exclude:a.com\|b.com` |
| `--mode` | `0` 网页 / `1` 权威垂直 / `2` 混合 |
| `--industry` | `gov` `news` `acad` `finance` |
| `--format` | `md`（默认）/ `json` / `text` |
| `--snippet-len` | 摘要截断长度，默认 300，`0` 不截断 |
| `--out` | 写文件 |
| `--doctor` | 环境自检 |

## 和官方 skill 的差别

官方那份 `tencent-yuanbao-standard-search` 能用，但工程细节上有些坑，这个版本针对性地补了：

| 项 | 官方版 | 本版 |
|---|---|---|
| 垂直信源（天气/股价） | 解析有冗余逻辑，`display` 处理不一致 | 统一走 `vr`/`display`，缺失时回落 `content`/`passage` |
| 密钥位置 | 只认环境变量 | 参数 / 环境变量 / 配置文件三级回退 |
| 错误处理 | 只打印原始 message | 错误码翻译成「原因 + 该去哪解决」，带 RequestId |
| 重试 | 无 | 429/5xx/网络异常自动退避重试 |
| 自检 | 无 | `--doctor` 一条命令验证密钥与连通性 |
| 输出 | 只有 markdown | `md` / `json` / `text` 三选一，可落盘 |
| 参数校验 | 无 | 校验 query 长度、`Cnt` 合法值，超限提前拦 |
| 依赖 | 标准库 | 标准库（同样零依赖） |

## 目录结构

```
yuanbao-websearch/
├── SKILL.md                  # 技能说明（Agent 读这个决定何时调用）
├── scripts/
│   └── yuanbao_search.py     # 检索脚本，零依赖
├── references/
│   ├── api.md                # 接口参数、返回字段、错误码全表
│   └── setup.md              # 各客户端密钥配置
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## 发布到 SkillHub

1. 确认包里没有密钥：`grep -rn "sk-" . --include="*.py" --include="*.md" --include="*.json"`
2. 打 zip：`zip -r yuanbao-websearch.zip yuanbao-websearch -x "*.pyc" -x "__pycache__/*"`
3. 到 <https://skillhub.cn> 用「发布 Skill」上传 zip，填写名称、描述、分类（信息检索）、是否需要 API Key
4. 首次发布建议版本号从 `1.0.0` 起，后续改动同步更新 `CHANGELOG.md`

## 注意事项

- **计费**：按调用次数计。免费额度用完会产生费用，批量任务记得控量
- **不要提交密钥**：仓库里出现的 `sk-` 开头字符串只应存在于文档示例中
- **结果需要交叉验证**：搜索引擎给的是候选，不是结论。重要事实至少两条独立来源
- **接口可能变更**：参数与字段以[官方文档](https://cloud.tencent.com/document/product/1806/121811)为准

## License

MIT，见 [LICENSE](LICENSE)。接口能力归腾讯云所有，本项目只是客户端封装。
