#!/usr/bin/env python3
"""
Telegram Webhook Server for Trading Logs
Receives trading notifications from Telegram and writes to local log files
"""

import os
import json
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess

# Configuration
PORT = int(os.environ.get('WEBHOOK_PORT', 8080))
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'webhook.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramWebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle incoming Telegram webhook"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            update = json.loads(post_data.decode('utf-8'))
            logger.info(f"Received update: {json.dumps(update, ensure_ascii=False)}")
            
            # Extract message data
            if 'message' not in update:
                logger.warning("No message in update")
                self.send_response(200)
                self.end_headers()
                return
            
            message = update['message']
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')
            date = message.get('date', 0)
            
            # Verify chat ID matches our target
            if str(chat_id) != str(CHAT_ID) and str(chat_id) != CHAT_ID:
                logger.warning(f"Chat ID mismatch: {chat_id} != {CHAT_ID}")
                self.send_response(200)
                self.end_headers()
                return
            
            if not text:
                logger.warning("Empty message text")
                self.send_response(200)
                self.end_headers()
                return
            
            # Convert timestamp to ISO format
            message_time = datetime.fromtimestamp(date).isoformat()
            log_date = datetime.fromtimestamp(date).strftime('%Y-%m-%d')
            
            # Write to log file
            os.makedirs(LOGS_DIR, exist_ok=True)
            log_file = os.path.join(LOGS_DIR, f"{log_date}.log")
            
            log_entry = f"[{message_time}] TELEGRAM {text}\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            logger.info(f"Logged to {log_file}")
            
            # Trigger git commit and push
            self.trigger_git_push()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode())
            
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            self.send_response(500)
            self.end_headers()
    
    def do_GET(self):
        """Health check endpoint"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'ok',
                'chat_id': CHAT_ID,
                'logs_dir': LOGS_DIR
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def trigger_git_push(self):
        """Trigger git commit and push"""
        try:
            logger.info("Triggering git commit and push...")
            os.chdir(SCRIPT_DIR)
            
            # Check for changes
            result = subprocess.run(
                ['git', 'diff', '--quiet'],
                capture_output=True
            )
            
            if result.returncode != 0:
                # Has changes, commit
                subprocess.run(
                    ['git', 'add', '-A'],
                    capture_output=True,
                    check=True
                )
                subprocess.run(
                    ['git', 'commit', '-m', f'Auto-commit trading logs at {datetime.now().isoformat()}'],
                    capture_output=True,
                    check=True
                )
                logger.info("Changes committed")
            
            # Push
            subprocess.run(
                ['git', 'push', 'origin', 'main'],
                capture_output=True,
                check=True,
                timeout=30
            )
            logger.info("Git push successful")
            
        except subprocess.TimeoutExpired:
            logger.error("Git push timeout")
        except subprocess.CalledProcessError as e:
            logger.error(f"Git error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in git push: {e}")
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info("%s - %s" % (self.address_string(), format % args))

def main():
    # Load environment from .env file
    env_file = os.path.join(SCRIPT_DIR, '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
                    logger.info(f"Loaded {key} from .env")
    
    # Update globals from environment
    global TOKEN, CHAT_ID
    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
    
    if not TOKEN or not CHAT_ID:
        logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return 1
    
    # Create logs directory
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Start server
    server = HTTPServer(('0.0.0.0', PORT), TelegramWebhookHandler)
    logger.info(f"Starting Telegram webhook server on port {PORT}")
    logger.info(f"Webhook URL should be: http://<your-server-ip>:{PORT}/")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()
    
    return 0

if __name__ == '__main__':
    exit(main())
