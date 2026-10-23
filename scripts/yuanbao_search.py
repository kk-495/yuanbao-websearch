#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""腾讯云元宝搜索（WSA · SearchPro）命令行客户端

只依赖 Python 标准库，无第三方依赖。

用法示例：
    python3 scripts/yuanbao_search.py --query "三星堆的由来"
    python3 scripts/yuanbao_search.py --query "英伟达财报" --cnt 20 --freshness d3
    python3 scripts/yuanbao_search.py --query "茅台股价" --mode 2 --industry finance
    python3 scripts/yuanbao_search.py --query "大模型" --site zhihu.com
    python3 scripts/yuanbao_search.py --query "大模型" --site "exclude:sohu.com|163.com"
    python3 scripts/yuanbao_search.py --query "AI 监管" --freshness 2026-10-01,2026-10-23
    python3 scripts/yuanbao_search.py --query "AI 监管" --format json --out result.json
    python3 scripts/yuanbao_search.py --doctor

密钥读取优先级：
    1. --api-key 参数
    2. 环境变量 TENCENTCLOUD_WSA_APIKEY
    3. 配置文件（默认 ~/.config/yuanbao-search/key，可用 --key-file 指定）

退出码：
    0 成功  2 缺少密钥  3 接口报错  4 网络异常  5 参数错误
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

__version__ = "1.0.0"

ENDPOINT = "https://api.wsa.cloud.tencent.com/SearchPro"
ENV_KEY = "TENCENTCLOUD_WSA_APIKEY"
MAX_QUERY_BYTES = 1500
VALID_CNT = (10, 20, 30, 40, 50)

# 错误码 -> (人类可读原因, 建议动作)
ERROR_HINTS = {
    "UnauthorizedOperation": (
        "密钥无效或已删除",
        "去 https://console.cloud.tencent.com/wsapi/index?tab=apikey 检查 API KEY 是否正确、是否被删除",
    ),
    "ResourceNotFound": (
        "服务未开通",
        "去 https://console.cloud.tencent.com/wsapi/index 开通元宝搜索（开通后约需几分钟生效）",
    ),
    "ResourceUnavailable": (
        "账号欠费或资源不可用",
        "去 https://console.cloud.tencent.com/expense/overview 检查余额并及时充值",
    ),
    "RequestLimitExceeded": (
        "触发并发/频率限制",
        "降低调用频率，或联系腾讯云商务提升并发；脚本已自动重试过",
    ),
    "InvalidParameter": (
        "参数不合法",
        "检查 Cnt 是否为 10/20/30/40/50、Freshness 格式是否正确、Query 是否超长",
    ),
    "InternalError": ("服务端内部错误", "稍后重试；持续报错请带 RequestId 提交工单"),
}


# ---------------------------------------------------------------- 密钥与配置

def default_key_file() -> str:
    if os.name == "nt":
        base = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    else:
        base = os.path.expanduser("~")
    return os.path.join(base, ".config", "yuanbao-search", "key")


def resolve_key(cli_key: str | None, key_file: str | None) -> tuple[str | None, str]:
    """返回 (密钥, 来源说明)"""
    if cli_key:
        return cli_key.strip(), "--api-key 参数"
    env = os.environ.get(ENV_KEY, "").strip()
    if env:
        return env, "环境变量 %s" % ENV_KEY
    path = key_file or default_key_file()
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8-sig") as f:
                text = f.read().strip()
            if text:
                return text, "配置文件 %s" % path
        except OSError:
            pass
    return None, ""


# ---------------------------------------------------------------- 调用接口

def build_payload(args) -> dict:
    payload: dict = {"Query": args.query}
    if args.site:
        payload["Site"] = args.site
    if args.mode is not None:
        payload["Mode"] = int(args.mode)
    if args.cnt is not None:
        payload["Cnt"] = int(args.cnt)
    if args.industry:
        payload["Industry"] = args.industry
    if args.freshness:
        payload["Freshness"] = args.freshness
    return payload


def call_api(payload: dict, api_key: str, timeout: float, retries: int) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json; charset=utf-8",
    }

    last_err = ""
    for attempt in range(retries + 1):
        req = urllib.request.Request(ENDPOINT, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            last_err = "HTTP %s %s" % (e.code, detail[:400])
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(last_err)
        except urllib.error.URLError as e:
            last_err = "网络异常: %s" % e.reason
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(last_err)
        except json.JSONDecodeError:
            raise RuntimeError("返回内容不是合法 JSON")
    raise RuntimeError(last_err or "请求失败")


# ---------------------------------------------------------------- 结果解析

def normalize(pages: list) -> list[dict]:
    """把 Pages（JSON 字符串数组）转成统一结构"""
    docs: list[dict] = []
    for page in pages or []:
        try:
            d = json.loads(page) if isinstance(page, str) else page
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(d, dict):
            continue

        # 垂直信源（天气/金价/股价等）会带 vr/display 结构
        display = d.get("display") if d.get("vr") else None
        if isinstance(display, dict):
            title = display.get("title") or d.get("title") or ""
            url = display.get("url") or d.get("url") or ""
            date = display.get("date") or d.get("date") or ""
        else:
            title = d.get("title") or ""
            url = d.get("url") or ""
            date = d.get("date") or ""

        passage = d.get("passage") or ""
        content = d.get("content") or ""
        text = passage if len(passage) >= len(content) else content
        if not title and not text:
            continue

        docs.append(
            {
                "title": title,
                "url": url,
                "date": date,
                "site": d.get("site") or "",
                "score": d.get("score"),
                "authority_level": d.get("authority_level"),
                "text": text,
                "passage": passage,
                "content": content,
                "pics": d.get("pics") or [],
                "deeplinks": d.get("deeplinks") or [],
                "is_vertical": bool(d.get("vr")),
            }
        )
    return docs


# ---------------------------------------------------------------- 输出

def clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if limit and len(text) > limit:
        return text[:limit].rstrip() + "…"
    return text


def render_markdown(result: dict, snippet_len: int) -> str:
    docs = result["results"]
    head = "## 查询词：%s ｜ 结果 %d 条 ｜ 版本 %s" % (
        result["query"],
        len(docs),
        result["version"] or "未知",
    )
    lines = [head]
    if result["msg"]:
        lines.append("> 接口提示：%s" % result["msg"])
    if not docs:
        lines.append("\n未检索到结果。可尝试放宽 `--freshness`、换更短的关键词，或去掉 `--site` 限制。")
        return "\n".join(lines)

    for i, d in enumerate(docs, 1):
        title = d["title"] or "(无标题)"
        lines.append("\n%d. [%s](%s)" % (i, title, d["url"] or "#"))
        if d["text"]:
            lines.append("   - 摘要：%s" % clip(d["text"], snippet_len))
        meta = []
        if d["date"]:
            meta.append("发布时间 %s" % d["date"])
        if d["site"]:
            meta.append("站点 %s" % d["site"])
        if d["score"] is not None:
            meta.append("相关度 %.2f" % float(d["score"]))
        if d["authority_level"] is not None:
            meta.append("权威度 %s/5" % d["authority_level"])
        if d["is_vertical"]:
            meta.append("垂直信源")
        if meta:
            lines.append("   - " + " ｜ ".join(meta))
        if d["pics"]:
            pics = " ".join(
                "[%s](%s)" % (p.get("caption") or "图片", p.get("origin_url") or "")
                for p in d["pics"][:5]
                if isinstance(p, dict)
            )
            if pics:
                lines.append("   - 配图：%s" % pics)
        if d["deeplinks"]:
            links = " ".join(
                "[%s](%s)" % (x.get("title") or "子链", x.get("url") or "")
                for x in d["deeplinks"][:5]
                if isinstance(x, dict)
            )
            if links:
                lines.append("   - 子链：%s" % links)
    return "\n".join(lines)


def render_plain(result: dict, snippet_len: int) -> str:
    lines = ["查询：%s   结果：%d 条   版本：%s" % (result["query"], len(result["results"]), result["version"] or "-")]
    for i, d in enumerate(result["results"], 1):
        lines.append("\n[%d] %s" % (i, d["title"] or "(无标题)"))
        meta = " ｜ ".join(x for x in [d["date"], d["site"]] if x)
        if meta:
            lines.append("    " + meta)
        if d["url"]:
            lines.append("    " + d["url"])
        if d["text"]:
            lines.append("    " + clip(d["text"], snippet_len))
    return "\n".join(lines)


# ---------------------------------------------------------------- 自检

def doctor(key: str | None, source: str) -> int:
    print("元宝搜索环境自检")
    print("-" * 40)
    print("Python      : %s" % sys.version.split()[0])
    print("脚本版本    : %s" % __version__)
    print("接口地址    : %s" % ENDPOINT)
    print("密钥来源    : %s" % (source or "未找到"))
    print("密钥指纹    : %s" % (("%s…%s" % (key[:6], key[-4:])) if key and len(key) > 12 else "无"))
    if not key:
        print("\n结论：缺少 API KEY。")
        print("  1) 去 https://console.cloud.tencent.com/wsapi/index?tab=apikey 开通服务并创建 KEY")
        print("  2) 设置环境变量 %s，或写入 %s" % (ENV_KEY, default_key_file()))
        return 2

    print("\n正在试调一次接口…")
    try:
        raw = call_api({"Query": "腾讯云元宝搜索", "Cnt": 10}, key, timeout=30, retries=0)
    except RuntimeError as e:
        print("调用失败：%s" % e)
        return 4
    res = raw.get("Response") or {}
    err = res.get("Error")
    if err:
        code = err.get("Code", "")
        why, todo = ERROR_HINTS.get(code, ("未知错误", "查看 references/api.md 的错误码表"))
        print("接口报错：%s（%s）" % (code, err.get("Message", "")))
        print("  原因：%s" % why)
        print("  建议：%s" % todo)
        return 3
    print("调用成功：版本 %s，返回 %d 条，RequestId %s" % (
        res.get("Version", "?"), len(res.get("Pages") or []), res.get("RequestId", "-")))
    print("\n结论：一切正常，可以直接用。")
    return 0


# ---------------------------------------------------------------- 入口

def main() -> int:
    ap = argparse.ArgumentParser(
        description="腾讯云元宝搜索（WSA SearchPro）命令行客户端",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n"
        "  python3 yuanbao_search.py --query \"三星堆的由来\" --cnt 10\n"
        "  python3 yuanbao_search.py --query \"茅台股价\" --mode 2 --industry finance\n"
        "  python3 yuanbao_search.py --doctor\n",
    )
    ap.add_argument("words", nargs="*", help="搜索词（也可以只用 --query）")
    ap.add_argument("--query", "-q", dest="query", help="搜索词，UTF-8 不超过 1500 字节")
    ap.add_argument("--site", help="限定站点，如 zhihu.com；排除用 exclude:a.com|b.com（最多 5 个）")
    ap.add_argument("--mode", type=int, choices=[0, 1, 2], help="0 公开网页 / 1 权威垂直 / 2 混合")
    ap.add_argument("--cnt", type=int, choices=list(VALID_CNT), help="返回条数 10/20/30/40/50")
    ap.add_argument("--freshness", help="时效：d7 / m3 / y2 / 2026-10-01 / 2026-10-01,2026-10-23")
    ap.add_argument("--industry", choices=["gov", "news", "acad", "finance"], help="垂直领域")
    ap.add_argument("--format", "-f", choices=["md", "json", "text"], default="md", help="输出格式，默认 md")
    ap.add_argument("--snippet-len", type=int, default=300, help="摘要截断长度，0 表示不截断，默认 300")
    ap.add_argument("--out", help="把输出写入文件")
    ap.add_argument("--api-key", help="直接指定 API KEY（优先级最高，慎用于共享环境）")
    ap.add_argument("--key-file", help="密钥文件路径，默认 %s" % default_key_file())
    ap.add_argument("--timeout", type=float, default=30.0, help="单次请求超时秒数，默认 30")
    ap.add_argument("--retry", type=int, default=1, help="失败重试次数，默认 1")
    ap.add_argument("--doctor", action="store_true", help="自检：检查密钥、连通性、账号状态")
    ap.add_argument("--version", action="version", version="yuanbao_search %s" % __version__)
    args = ap.parse_args()

    key, source = resolve_key(args.api_key, args.key_file)

    if args.doctor:
        return doctor(key, source)

    query = args.query or " ".join(args.words)
    if not query:
        print("错误：缺少搜索词。用 --query \"关键词\" 或直接跟关键词。", file=sys.stderr)
        return 5
    if len(query.encode("utf-8")) > MAX_QUERY_BYTES:
        print("错误：搜索词超过 1500 字节（约 500 个中文字），请缩短。", file=sys.stderr)
        return 5

    if not key:
        print("错误：未找到 API KEY。", file=sys.stderr)
        print("  1) 去 https://console.cloud.tencent.com/wsapi/index?tab=apikey 开通并创建 KEY", file=sys.stderr)
        print("  2) 设置环境变量 %s，或写入 %s" % (ENV_KEY, default_key_file()), file=sys.stderr)
        print("  3) 也可以临时用 --api-key 传入", file=sys.stderr)
        return 2

    args.query = query
    try:
        raw = call_api(build_payload(args), key, args.timeout, args.retry)
    except RuntimeError as e:
        print("## 搜索失败\n原因：%s" % e, file=sys.stderr)
        return 4

    res = raw.get("Response") or {}
    err = res.get("Error")
    if err:
        code = err.get("Code", "")
        why, todo = ERROR_HINTS.get(code, ("未知错误", "查看 references/api.md 的错误码表"))
        print("## 搜索失败", file=sys.stderr)
        print("错误码：%s" % code, file=sys.stderr)
        print("原因：%s（%s）" % (why, err.get("Message", "")), file=sys.stderr)
        print("建议：%s" % todo, file=sys.stderr)
        if res.get("RequestId"):
            print("RequestId：%s" % res["RequestId"], file=sys.stderr)
        return 3

    result = {
        "query": res.get("Query", query),
        "version": res.get("Version", ""),
        "msg": res.get("Msg", ""),
        "request_id": res.get("RequestId", ""),
        "results": normalize(res.get("Pages")),
    }

    if args.format == "json":
        output = json.dumps(result, ensure_ascii=False, indent=2)
    elif args.format == "text":
        output = render_plain(result, args.snippet_len)
    else:
        output = render_markdown(result, args.snippet_len)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        print("已写入 %s（%d 条结果）" % (args.out, len(result["results"])))
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
