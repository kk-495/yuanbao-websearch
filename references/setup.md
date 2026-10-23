# 密钥配置指南

这个 skill 本身不含任何密钥，用你自己的腾讯云元宝搜索 API KEY。

## 一、拿到 API KEY

1. 登录腾讯云，完成实名认证：<https://cloud.tencent.com/login>
2. 开通元宝搜索服务：<https://console.cloud.tencent.com/wsapi/index>
3. 在控制台「概览 → 服务 API KEY 方式」点**创建 API KEY**，复制保存
   - 明文只在创建时显示一次，之后查不到，务必当场存好
   - 每个账号最多同时持有 3 个 KEY
4. 免费额度见活动页：<https://console.cloud.tencent.com/wsapi/activity>

> 服务刚开通时要等几分钟才生效，这时候调用会报 `ResourceNotFound`，不是配错了。

## 二、把 KEY 交给 skill

脚本按下面顺序找密钥，命中即止：

| 优先级 | 方式 | 说明 |
|---|---|---|
| 1 | `--api-key sk-xxx` | 临时用，会留在 shell history 里，共享环境别用 |
| 2 | 环境变量 `TENCENTCLOUD_WSA_APIKEY` | **推荐**，和官方 skill 同名，可平滑替换 |
| 3 | 配置文件 `~/.config/yuanbao-search/key` | 不想动环境变量时的选择 |

### 方式 A：环境变量（推荐）

macOS / Linux（写进 `~/.zshrc` 或 `~/.bashrc`）：

```bash
export TENCENTCLOUD_WSA_APIKEY="sk-你的密钥"
```

Windows PowerShell（当前用户永久生效）：

```powershell
[Environment]::SetEnvironmentVariable("TENCENTCLOUD_WSA_APIKEY", "sk-你的密钥", "User")
```

Windows CMD：

```cmd
setx TENCENTCLOUD_WSA_APIKEY "sk-你的密钥"
```

设完要**重开终端**（或重启 Agent）才读得到。

### 方式 B：配置文件

```bash
mkdir -p ~/.config/yuanbao-search
printf 'sk-你的密钥\n' > ~/.config/yuanbao-search/key
chmod 600 ~/.config/yuanbao-search/key
```

Windows 路径是 `%USERPROFILE%\.config\yuanbao-search\key`。

这个文件别提交到 Git（`.gitignore` 已排除 `*.key` 和 `.config/`）。

## 三、各客户端的 skills 目录

把整个 `yuanbao-websearch/` 目录放进对应位置：

| 客户端 | 目录 |
|---|---|
| WorkBuddy | `~/.workbuddy-ai/skills/` |
| Claude Code | `~/.claude/skills/` |
| Cursor | `~/.cursor/skills/` 或项目内 `.cursor/skills/` |
| Codex | `~/.codex/skills/` 或项目内 `.agents/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| Windsurf | `~/.codeium/windsurf/skills/` |
| OpenClaw | `~/.openclaw/skills/` |

部分客户端的环境变量要写在自己的配置文件里（如 OpenClaw 的 `~/.openclaw/.env`），否则 Agent 进程读不到。

## 四、验证

```bash
python3 ~/.workbuddy-ai/skills/yuanbao-websearch/scripts/yuanbao_search.py --doctor
```

正常输出长这样：

```
元宝搜索环境自检
----------------------------------------
Python      : 3.13.12
脚本版本    : 1.0.0
接口地址    : https://api.wsa.cloud.tencent.com/SearchPro
密钥来源    : 环境变量 TENCENTCLOUD_WSA_APIKEY
密钥指纹    : sk-40a…d7f7

正在试调一次接口…
调用成功：版本 standard，返回 10 条，RequestId xxxx

结论：一切正常，可以直接用。
```

看到「结论：一切正常」就配好了。报错会直接告诉你原因和该去哪解决。

## 五、常见问题

**Q：报 `python3: command not found`**
Windows 上试 `python` 或 `py -3`。本 skill 只用标准库，Python 3.8+ 都能跑。

**Q：报 `ResourceNotFound`**
服务没开通，或刚开通还在生效中。去控制台确认服务状态。

**Q：报 `UnauthorizedOperation`**
KEY 复制不全（前后空格、少字符）、被删了，或用的是子账号但没给 WSA 权限。子账号需要在访问管理里授予「元宝搜索（WSA）全读写访问权限」。

**Q：明明设了环境变量还是读不到**
环境变量是进程级的。设完要重开终端 / 重启 Agent；IDE 内的 Agent 常常继承的是 IDE 启动时的环境。

**Q：想同时用多个 KEY 轮换**
用 `--key-file` 指向不同文件即可，脚本不限制。
