# Trading Logs 交易日志

本仓库用于自动化交易的留痕验证，记录所有开仓/平仓操作。

## 📁 目录结构

```
trading-logs/
├── logs/              # 交易日志文件
│   └── YYYY-MM-DD.log # 按日期分割的日志
├── auto-push.sh       # 自动推送脚本
├── .env               # 环境变量（含 GitHub Token，已 gitignore）
└── README.md          # 本文件
```

## 📝 日志格式示例

```
[2026-02-23T03:55:00+00:00] OPEN  BTC/USDT  LONG  @ 52340.5  qty: 0.1  leverage: 10x  order_id: 12345
[2026-02-23T04:12:00+00:00] CLOSE BTC/USDT  LONG  @ 52580.0  qty: 0.1  pnl: +23.95 USDT  order_id: 12346
```

## 🤖 自动化

- **推送频率**: 每分钟检查一次
- **触发条件**: 本地仓库有新内容时自动 push
- **Cron 任务**: 已配置，无需手动干预

## 🔧 首次配置

运行 setup 脚本配置 Token：

```bash
cd /root/.openclaw/workspace/trading-logs
./setup-remote.sh
```

按提示输入你的 GitHub Token。

## 📊 验证

查看推送历史：
```bash
cd /root/.openclaw/workspace/trading-logs
git log --oneline
```

查看推送日志：
```bash
tail -f /root/.openclaw/workspace/trading-logs/push.log
```

## 🔐 安全提示

- Token 存储在 `.env` 文件中，已加入 `.gitignore`
- 不要将 `.env` 文件提交到仓库
- 如需更换 Token，重新运行 `setup-remote.sh`
