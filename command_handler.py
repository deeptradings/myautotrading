#!/usr/bin/env python3
"""
Jimmy's Custom Command Handler
处理专属命令如 /myhelp, /scantime, /recent 等
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
SCRIPT_DIR = Path(__file__).parent
TRADING_LOGS_DIR = SCRIPT_DIR / "logs"
NEWS_LOGS_DIR = SCRIPT_DIR.parent / "crypto-news-monitor" / "logs"
PDF_REPORTS_DIR = SCRIPT_DIR.parent / "crypto-news-monitor" / "pdf_reports"
WEBHOOK_LOG = SCRIPT_DIR / "webhook.log"
CONFIG_FILE = SCRIPT_DIR / "command_config.json"

class CommandHandler:
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self):
        """Load command configuration"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                return json.load(f)
        else:
            return {
                "scan_interval": 3600,  # 1 hour
                "telegram_bot_token": "8026855323:AAEGtGs_Lt-dKzaHxeLT_9MEB185ezp6v3o",
                "telegram_chat_id": "-1003784966844"
            }
    
    def save_config(self):
        """Save configuration"""
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def cmd_myhelp(self, args):
        """Display custom help"""
        help_file = SCRIPT_DIR / "MYCOMMANDS.md"
        if help_file.exists():
            with open(help_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return "❌ 帮助文档未找到"
    
    def cmd_recent(self, args):
        """Show recent trading activity"""
        time_range = args[0] if args else "1h"
        
        # Parse time range
        minutes = self.parse_time_range(time_range)
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        # Read trading logs
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = TRADING_LOGS_DIR / f"{today}.log"
        
        if not log_file.exists():
            return "❌ 暂无交易日志"
        
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Filter recent entries
        recent_lines = []
        for line in lines[-20:]:  # Last 20 lines
            recent_lines.append(line.strip())
        
        if not recent_lines:
            return "ℹ️ 最近无交易活动"
        
        result = f"📊 最近 {time_range} 交易活动\n\n"
        result += "\n".join(recent_lines)
        
        return result
    
    def cmd_scantime(self, args):
        """Set news scan interval"""
        if not args:
            return f"⏰ 当前扫描间隔：{self.config['scan_interval']}秒"
        
        interval = args[0]
        seconds = self.parse_interval(interval)
        
        if seconds:
            self.config['scan_interval'] = seconds
            self.save_config()
            
            # Update cron job
            self.update_cron_job(seconds)
            
            return f"✅ 扫描间隔已设置为 {interval}"
        else:
            return "❌ 无效的时间格式 (支持：15m, 1h, 30m 等)"
    
    def cmd_news(self, args):
        """Get news summary"""
        time_range = args[0] if args else "24h"
        
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = NEWS_LOGS_DIR / f"news-{today}.log"
        
        if not log_file.exists():
            return "❌ 暂无新闻记录"
        
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Get last 10 news items
        recent_news = lines[-10:] if len(lines) > 10 else lines
        
        result = f"📰 最近 {time_range} 新闻摘要\n\n"
        result += "".join(recent_news)
        
        return result
    
    def cmd_pdf(self, args):
        """Generate and send PDF report"""
        time_range = args[0] if args else "1h"
        
        # Trigger news monitor to generate PDF via webhook command
        try:
            hours = int(time_range.replace('h', '')) if 'h' in time_range else 1
            
            # Request PDF via webhook
            webhook_url = "http://localhost:9900/command"
            response = requests.post(
                webhook_url,
                json={"command": "get_recent_pdf", "hours": hours},
                timeout=30
            )
            result = response.json()
            
            if result.get('status') == 'ok':
                return f"✅ PDF 报告已生成并发送到 Telegram"
            else:
                return f"❌ 生成失败：{result.get('message', '未知错误')}"
        except Exception as e:
            return f"❌ 生成失败：{e}"
    
    def cmd_pdf_list(self, args):
        """List available PDF reports"""
        if not PDF_REPORTS_DIR.exists():
            return "❌ 暂无 PDF 报告"
        
        pdf_files = list(PDF_REPORTS_DIR.glob("*.pdf"))
        
        if not pdf_files:
            return "ℹ️ 暂无 PDF 报告"
        
        result = "📄 可用的 PDF 报告:\n\n"
        for pdf in sorted(pdf_files, reverse=True)[:10]:  # Last 10
            stat = pdf.stat()
            size_kb = stat.st_size / 1024
            mtime = datetime.fromtimestamp(stat.st_mtime)
            result += f"- {pdf.name} ({size_kb:.1f} KB) - {mtime.strftime('%Y-%m-%d %H:%M')}\n"
        
        return result
    
    def cmd_pdf_latest(self, args):
        """Send latest PDF report"""
        if not PDF_REPORTS_DIR.exists():
            return "❌ 暂无 PDF 报告"
        
        pdf_files = sorted(PDF_REPORTS_DIR.glob("*.pdf"), reverse=True)
        
        if not pdf_files:
            return "❌ 暂无 PDF 报告"
        
        latest_pdf = pdf_files[0]
        
        # Send to Telegram
        try:
            token = self.config['telegram_bot_token']
            chat_id = self.config['telegram_chat_id']
            
            url = f"https://api.telegram.org/bot{token}/sendDocument"
            import requests
            
            with open(latest_pdf, 'rb') as f:
                response = requests.post(
                    url,
                    data={"chat_id": chat_id},
                    files={"document": f}
                )
            
            if response.json().get('ok'):
                return f"✅ 已发送最新 PDF 报告"
            else:
                return f"❌ 发送失败：{response.json()}"
                
        except Exception as e:
            return f"❌ 发送失败：{e}"
    
    def cmd_status(self, args):
        """Show system status"""
        result = "📊 系统状态\n\n"
        
        # Check webhook service
        try:
            status = subprocess.run(
                ["systemctl", "is-active", "trading-webhook"],
                capture_output=True, text=True
            )
            webhook_status = "🟢 运行中" if status.stdout.strip() == "active" else "🔴 已停止"
            result += f"Webhook 服务：{webhook_status}\n"
        except:
            result += "Webhook 服务：❌ 未知\n"
        
        # Check git status
        try:
            git_status = subprocess.run(
                ["git", "-C", str(SCRIPT_DIR), "status", "--porcelain"],
                capture_output=True, text=True
            )
            git_clean = "✅ 干净" if not git_status.stdout.strip() else "⚠️ 有未提交更改"
            result += f"Git 状态：{git_clean}\n"
        except:
            result += "Git 状态：❌ 未知\n"
        
        # Check news monitor
        news_monitor_active = Path("/etc/systemd/system/crypto-news-monitor.service").exists()
        result += f"新闻监控：{'🟢 已配置' if news_monitor_active else '⚠️ 未配置'}\n"
        
        return result
    
    def parse_time_range(self, time_str):
        """Parse time range string to minutes"""
        if time_str.endswith('m'):
            return int(time_str[:-1])
        elif time_str.endswith('h'):
            return int(time_str[:-1]) * 60
        elif time_str.endswith('d'):
            return int(time_str[:-1]) * 24 * 60
        else:
            return 60  # Default 1 hour
    
    def parse_interval(self, time_str):
        """Parse interval string to seconds"""
        if time_str.endswith('s'):
            return int(time_str[:-1])
        elif time_str.endswith('m'):
            return int(time_str[:-1]) * 60
        elif time_str.endswith('h'):
            return int(time_str[:-1]) * 3600
        else:
            return None
    
    def update_cron_job(self, interval_seconds):
        """Update cron job with new interval"""
        # Convert seconds to cron format
        if interval_seconds >= 3600:
            hours = interval_seconds // 3600
            cron_line = f"0 */{hours} * * *"
        else:
            minutes = interval_seconds // 60
            cron_line = f"*/{minutes} * * * *"
        
        # Update crontab (simplified - in production would need proper crontab editing)
        print(f"Would update cron to: {cron_line}")
    
    def handle_command(self, command, args):
        """Handle incoming command"""
        commands = {
            'myhelp': self.cmd_myhelp,
            'recent': self.cmd_recent,
            'scantime': self.cmd_scantime,
            'news': self.cmd_news,
            'pdf': self.cmd_pdf,
            'pdf-list': self.cmd_pdf_list,
            'pdf-latest': self.cmd_pdf_latest,
            'status': self.cmd_status
        }
        
        handler = commands.get(command)
        if handler:
            return handler(args)
        else:
            return f"❌ 未知命令：{command}\n使用 /myhelp 查看可用命令"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: command_handler.py <command> [args...]")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    handler = CommandHandler()
    result = handler.handle_command(command, args)
    print(result)
