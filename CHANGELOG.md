# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-10-23

首个版本。

### 新增

- `scripts/yuanbao_search.py`：元宝搜索（WSA · SearchPro）命令行客户端，仅依赖 Python 标准库
- 密钥三级回退：`--api-key` → 环境变量 `TENCENTCLOUD_WSA_APIKEY` → `~/.config/yuanbao-search/key`
- `--doctor` 自检：检查 Python 环境、密钥来源（打码显示指纹）、试调接口并诊断账号状态
- 三种输出格式：`md`（默认，给模型读）/ `json`（给程序读）/ `text`（纯文本），支持 `--out` 落盘
- 完整参数支持：`Query` / `Cnt` / `Mode` / `Site`（含 `exclude:` 排除语法）/ `Industry` / `Freshness`
- 垂直信源（天气、股价、金价、汇率）解析：统一处理 `vr` / `display` 结构，缺失时回落 `content` / `passage`
- 错误码翻译：`UnauthorizedOperation`、`ResourceNotFound`、`ResourceUnavailable`、`RequestLimitExceeded`、`InvalidParameter` 均给出原因与处理路径，附 `RequestId`
- 失败自动重试：429 / 5xx / 网络异常按 1.5s、3s 退避，次数可调 `--retry`
- 入参前置校验：query 长度（≤1500 字节）、`Cnt` 合法值（10/20/30/40/50），非法值在发请求前拦下
- 明确的退出码：`0` 成功 / `2` 缺密钥 / `3` 接口报错 / `4` 网络异常 / `5` 参数错误
- 文档：`SKILL.md`（触发时机与 query 写法）、`references/api.md`（接口全表）、`references/setup.md`（各客户端配置）
