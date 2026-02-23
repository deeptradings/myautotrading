# Trading Logs 交易日志

本仓库用于自动化交易的留痕验证，记录所有开仓/平仓操作。

## 📁 目录结构

```
trading-logs/
├── logs/                  # 交易日志文件
│   ├── YYYY-MM-DD.log     # 按日期分割的日志
│   └── .gitkeep           # 目录占位
├── auto-push.sh           # 自动推送脚本（含 Telegram 获取）
├── fetch-telegram.sh      # Telegram 消息获取脚本
├── setup-remote.sh        # GitHub 远程配置脚本
├── .env                   # 环境变量（已 gitignore）
├── .env.example           # 环境变量示例
├── .telegram_state        # Telegram 消息偏移量（已 gitignore）
├── push.log               # 推送日志（已 gitignore）
└── README.md              # 本文件
```

## 🤖 自动化流程

```
系统 Crontab (每分钟)
    ↓
fetch-telegram.sh → 从 Telegram 获取新消息
    ↓
解析交易信息 → 写入 logs/YYYY-MM-DD.log
    ↓
auto-push.sh → Git commit & push
    ↓
GitHub 仓库留痕
```

**全程零大模型调用**，纯系统级自动化。

## 📝 日志格式示例

```
[2026-02-23T03:55:00+00:00] TELEGRAM 🔔 新开仓通知 品种：BTC/USDT 方向：LONG ...
[2026-02-23T04:12:00+00:00] TELEGRAM 🔔 平仓通知 品种：BTC/USDT 方向：LONG ...
```

## 🔧 配置说明

### 环境变量

`.env` 文件包含以下配置：

```bash
GITHUB_TOKEN=ghp_xxx
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
TELEGRAM_CHAT_ID=5708394864
```

### 消息解析

当前脚本将 Telegram 消息原文写入日志。如需结构化解析，可修改 `fetch-telegram.sh` 中的解析逻辑。

## 📊 验证

```bash
# 查看推送历史
cd /root/.openclaw/workspace/trading-logs
git log --oneline

# 查看推送日志
tail -f push.log

# 查看 Telegram 获取状态
cat .telegram_state

# 查看今日日志
cat logs/$(date +%Y-%m-%d).log
```

## 🔐 安全提示

- `.env` 和 `.telegram_state` 已加入 `.gitignore`，不会泄露
- Token 存储在本地，仅脚本可读（权限 600）
- 如需更换 Token，直接编辑 `.env` 文件
- 定期在 GitHub 检查推送记录，确保正常同步

## 🆘 故障排查

```bash
# 手动运行一次完整流程
cd /root/.openclaw/workspace/trading-logs
bash fetch-telegram.sh
bash auto-push.sh

# 查看错误日志
tail -50 push.log

# 检查 Cron 任务
crontab -l | grep trading-logs
```
