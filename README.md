# Trading Logs 交易日志

本仓库用于自动化交易的留痕验证，记录所有开仓/平仓操作。

## 📁 目录结构

```
trading-logs/
├── logs/                  # 交易日志文件
│   └── YYYY-MM-DD.log     # 按日期分割的日志
├── webhook-server.py      # Telegram Webhook 服务器
├── auto-push.sh           # Git 自动推送脚本
├── setup-webhook.sh       # Webhook 配置脚本
├── keep-tunnel-alive.sh   # 隧道保活脚本
├── setup-remote.sh        # GitHub 远程配置脚本
├── .env                   # 环境变量（已 gitignore）
├── .env.example           # 环境变量示例
├── webhook.log            # Webhook 日志（已 gitignore）
├── push.log               # Git 推送日志（已 gitignore）
└── README.md              # 本文件
```

## 🤖 自动化流程（Webhook 方案）

```
Telegram 群组消息
    ↓
Telegram Webhook (HTTPS)
    ↓
webhook-server.py (端口 8080)
    ↓
写入 logs/YYYY-MM-DD.log
    ↓
自动 git commit & push
    ↓
GitHub 仓库留痕
```

**全程零大模型调用**，纯系统级自动化。

## 📝 日志格式示例

```
[2026-02-23T13:31:59+08:00] TELEGRAM 🧪 Webhook 测试消息
OPEN BTC/USDT LONG @ 52340.5 qty: 0.1
时间：2026-02-23T13:31:59+08:00
```

## 🚀 快速开始

### 1. 配置环境变量

编辑 `.env` 文件：

```bash
GITHUB_TOKEN=ghp_xxx
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
TELEGRAM_CHAT_ID=-1003784966844
```

### 2. 启动 Webhook 服务器

```bash
# 启动 Webhook 服务（systemd）
systemctl start telegram-webhook

# 配置 HTTPS 隧道和 Telegram Webhook
cd /root/.openclaw/workspace/trading-logs
./setup-webhook.sh
```

### 3. 保持隧道运行（可选）

```bash
# 后台运行保活脚本
nohup ./keep-tunnel-alive.sh > tunnel.log 2>&1 &
```

### 4. 测试

在 Telegram 群组中发送任意消息，检查：
- `logs/YYYY-MM-DD.log` - 日志文件
- `webhook.log` - Webhook 服务器日志
- GitHub 仓库 - 自动推送记录

## 🔧 组件说明

### webhook-server.py
Python HTTP 服务器，接收 Telegram Webhook 推送：
- 监听端口：8080
- 健康检查：`http://localhost:8080/health`
- 日志文件：`webhook.log`

### setup-webhook.sh
配置脚本，执行：
1. 启动 localtunnel HTTPS 隧道
2. 配置 Telegram Webhook URL
3. 验证配置

### keep-tunnel-alive.sh
保活脚本，自动重连断开的隧道。

## 📊 验证

```bash
# 查看 Webhook 状态
curl -s "https://api.telegram.org/botTOKEN/getWebhookInfo" | jq .

# 查看今日日志
cat logs/$(date +%Y-%m-%d).log

# 查看 Webhook 日志
tail -f webhook.log

# 查看 Git 历史
cd /root/.openclaw/workspace/trading-logs
git log --oneline

# 检查服务状态
systemctl status telegram-webhook
```

## 🔐 安全提示

- `.env` 已加入 `.gitignore`，不会泄露
- Token 存储在本地，仅脚本可读（权限 600）
- Webhook 使用 HTTPS 隧道（localtunnel）
- 定期在 GitHub 检查推送记录

## 🆘 故障排查

```bash
# 检查 Webhook 服务器
systemctl status telegram-webhook

# 查看 Webhook 日志
tail -50 webhook.log

# 测试健康检查
curl http://localhost:8080/health

# 检查隧道状态
cat .tunnel_pid 2>/dev/null && ps aux | grep lt

# 重新配置 Webhook
./setup-webhook.sh
```

## 📝 注意事项

1. **localtunnel URL 会变化** - 每次重启隧道会生成新 URL，需要重新配置 Webhook
2. **机器人自己的消息不会触发 Webhook** - 只有其他用户/机器人的消息会被推送
3. **生产环境建议** - 使用固定域名 + HTTPS 证书替代 localtunnel
