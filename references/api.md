# 元宝搜索接口参考（SearchPro）

官方文档：<https://cloud.tencent.com/document/product/1806/121811>

## 基本信息

| 项 | 值 |
|---|---|
| 接口地址 | `https://api.wsa.cloud.tencent.com/SearchPro` |
| 方法 | `POST` |
| Content-Type | `application/json; charset=utf-8` |
| 鉴权 | `Authorization: Bearer <API_KEY>` |
| 超时建议 | 10–30 秒（默认 30） |

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `Query` | string | 是 | 搜索词，UTF-8 ≤ 1500 字节 |
| `Cnt` | int | 否 | 10 / 20 / 30 / 40 / 50。**只能取这五个值**，传 3 会报 `illegal Cnt`。极速版不支持 |
| `Mode` | int | 否 | `0` 公开网页信源；`1` 优质权威垂直信源；`2` 混合。不传默认 0。极速版不支持 |
| `Site` | string | 否 | 限定站点：`zhihu.com`。排除：`exclude:a.com\|b.com`，最多 5 个。与 `Mode` 共用时只对自然结果生效，对垂直信源（VR）不生效 |
| `Industry` | string | 否 | `gov` / `news` / `acad` / `finance`。极速版不支持 |
| `Freshness` | string | 否 | `d[N]` 近 N 天（1–30）；`m[N]` 近 N 月（1–12）；`y[N]` 近 N 年（1–5）；`yyyy-mm-dd` 指定日；`yyyy-mm-dd,yyyy-mm-dd` 区间。五种形态不可混用 |
| `Deeplinks` | bool | 否 | 返回附件子链，仅旗舰版生效 |

> 注意 `Cnt` 在 **MCP 通道里必须传字符串**（`"10"`），在 HTTP API 里传数字。同一个服务，两种通道的参数类型不一样，容易踩。

## 返回结构

```json
{
  "Response": {
    "Query": "原始查询词",
    "Version": "standard",
    "RequestId": "xxxx",
    "Pages": ["{...}", "{...}"]
  }
}
```

`Pages` 是**字符串数组**，每一项还得再 `json.loads` 一次 —— 这是最容易写错的地方。

单条结果的字段：

| 字段 | 说明 | 版本 |
|---|---|---|
| `title` | 标题 | 全版本 |
| `url` | 原文地址 | 全版本 |
| `date` | 发布时间 | 全版本 |
| `passage` | 标准摘要（长度稳定） | 全版本 |
| `content` | 动态摘要（更长、更贴合 query） | 极速版不返回 |
| `site` | 站点名，冷门站可能为空 | 全版本 |
| `score` | 相关度 0–1（`Mode=2` 混合结果里垂直项可能大于 1，那是排序分不是概率） | 全版本 |
| `pics` | 图片列表 `[{caption, origin_url}]`，0–10 条 | 极速版不返回 |
| `authority_level` | 权威度 0–5 | 仅旗舰版 |
| `deeplinks` | 附件子链 `[{title, url}]`，最多 10 条 | 仅旗舰版，需入参 `Deeplinks: true` |
| `vr` / `display` | 垂直信源标记与展示结构（天气/金价/股价等） | 垂直结果 |

## 错误码

| 错误码 | 含义 | 排查 |
|---|---|---|
| `UnauthorizedOperation` | 未授权 | 密钥错、被删、或子账号没有 WSA 权限 |
| `ResourceNotFound` | 服务未开通 | 控制台开通，几分钟后生效 |
| `ResourceUnavailable` | 资源不可用 | 账号欠费 |
| `RequestLimitExceeded` | 频率/并发超限 | 降频或申请提额 |
| `InvalidParameter` | 参数错误 | 多为 `Cnt` 非法、`Freshness` 格式错、`Query` 超长 |
| `InternalError` | 服务端错误 | 重试，持续报错带 `RequestId` 提工单 |

## 最小可用示例

```bash
curl -s -X POST "https://api.wsa.cloud.tencent.com/SearchPro" \
  -H "Authorization: Bearer $TENCENTCLOUD_WSA_APIKEY" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{"Query":"三星堆的由来","Cnt":10}' | jq -r '.Response.Pages[] | fromjson | .title'
```

Python（本 skill 的脚本已封装好，这里是原理）：

```python
import json, os, urllib.request

req = urllib.request.Request(
    "https://api.wsa.cloud.tencent.com/SearchPro",
    data=json.dumps({"Query": "三星堆的由来"}).encode(),
    headers={
        "Authorization": "Bearer " + os.environ["TENCENTCLOUD_WSA_APIKEY"],
        "Content-Type": "application/json; charset=utf-8",
    },
    method="POST",
)
with urllib.request.urlopen(req, timeout=30) as r:
    data = json.loads(r.read())["Response"]
for page in data["Pages"]:
    d = json.loads(page)      # 二次解析，别忘了
    print(d["title"], d["url"])
```

## 三个通道的差别

| 通道 | 地址 | 适用 |
|---|---|---|
| HTTP API | `POST /SearchPro` | 后端集成、脚本、批量任务 |
| MCP | `POST /Mcp`（Streamable HTTP，JSON-RPC 2.0） | Agent 原生工具调用，`Cnt` 需字符串 |
| Skill | 本仓库 | 给 Agent 装一套「会自己找时机搜索」的说明书 + 脚本 |

三者信源一致，区别只在调用形态和参数类型细节。
