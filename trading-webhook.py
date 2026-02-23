#!/usr/bin/env python3
"""
Trading Webhook Endpoint Server
Receives trading notifications directly from trading system and syncs to GitHub
"""

import os
import json
import hmac
import hashlib
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import fcntl
from pathlib import Path

# Configuration
PORT = int(os.environ.get('WEBHOOK_PORT', 8080))
SECRET_TOKEN = os.environ.get('WEBHOOK_SECRET', '')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
LOGS_DIR = os.environ.get('LOGS_DIR', 'logs')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCK_FILE = os.path.join(SCRIPT_DIR, '.git_push.lock')

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

class TradingWebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle incoming trading webhook"""
        start_time = datetime.now()
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        # Get headers for logging
        headers = {k: v for k, v in self.headers.items()}
        
        logger.info(f"Received webhook from {self.address_string()}")
        logger.info(f"Headers: {json.dumps(headers, ensure_ascii=False)}")
        
        try:
            # Parse payload
            try:
                payload = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                payload = {'raw': post_data.decode('utf-8')}
            
            logger.info(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            # Verify signature if secret is configured
            if SECRET_TOKEN:
                signature = self.headers.get('X-Webhook-Signature', '')
                expected_signature = hmac.new(
                    SECRET_TOKEN.encode(),
                    post_data,
                    hashlib.sha256
                ).hexdigest()
                
                if signature and not hmac.compare_digest(signature, expected_signature):
                    logger.warning("Signature verification failed")
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b'Invalid signature')
                    return
            
            # Extract trading information
            log_entry = self.format_log_entry(payload, headers)
            
            # Write to log file
            log_file = self.write_log(log_entry)
            logger.info(f"Logged to {log_file}")
            
            # Trigger git commit and push (with lock to prevent concurrent pushes)
            self.trigger_git_push_with_lock()
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'ok': True,
                'timestamp': datetime.now().isoformat(),
                'log_file': str(log_file),
                'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'ok': False, 'error': str(e)}).encode())
    
    def format_log_entry(self, payload, headers):
        """Format log entry from payload"""
        timestamp = datetime.now().isoformat()
        
        # Try to extract common trading fields
        action = payload.get('action', payload.get('type', 'UNKNOWN'))
        symbol = payload.get('symbol', payload.get('pair', payload.get('instrument', 'N/A')))
        side = payload.get('side', payload.get('direction', payload.get('type', 'N/A')))
        price = payload.get('price', payload.get('entry_price', payload.get('fill_price', 'N/A')))
        quantity = payload.get('quantity', payload.get('qty', payload.get('size', 'N/A')))
        order_id = payload.get('order_id', payload.get('id', payload.get('trade_id', 'N/A')))
        pnl = payload.get('pnl', payload.get('profit_loss', ''))
        
        # Build log entry
        log_parts = [f"[{timestamp}] {action.upper()}"]
        
        if symbol != 'N/A':
            log_parts.append(symbol)
        if side != 'N/A':
            log_parts.append(str(side).upper())
        if price != 'N/A':
            log_parts.append(f"@ {price}")
        if quantity != 'N/A':
            log_parts.append(f"qty: {quantity}")
        if order_id != 'N/A':
            log_parts.append(f"order_id: {order_id}")
        if pnl:
            log_parts.append(f"pnl: {pnl}")
        
        # Add full payload as JSON for completeness
        log_entry = ' '.join(log_parts)
        log_entry += f"\n# Raw: {json.dumps(payload, ensure_ascii=False)}"
        
        return log_entry
    
    def write_log(self, log_entry):
        """Write log entry to daily log file"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = Path(LOGS_DIR) / f"{today}.log"
        
        # Ensure logs directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Append to log file
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n\n')
        
        return log_file
    
    def trigger_git_push_with_lock(self):
        """Trigger git commit and push with file lock to prevent concurrent execution"""
        lock_fd = None
        try:
            # Create lock file
            lock_fd = open(LOCK_FILE, 'w')
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            logger.info("Acquired git push lock")
            self._do_git_push()
            
        except BlockingIOError:
            logger.info("Git push already in progress, skipping")
        finally:
            if lock_fd:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                lock_fd.close()
                try:
                    os.remove(LOCK_FILE)
                except:
                    pass
    
    def _do_git_push(self):
        """Execute git commit and push"""
        try:
            os.chdir(SCRIPT_DIR)
            
            # Check for changes
            result = subprocess.run(
                ['git', 'diff', '--cached', '--quiet'],
                capture_output=True
            )
            
            has_unstaged = subprocess.run(
                ['git', 'diff', '--quiet'],
                capture_output=True
            ).returncode != 0
            
            if has_unstaged:
                subprocess.run(
                    ['git', 'add', '-A'],
                    capture_output=True,
                    check=True
                )
                logger.info("Staged changes")
            
            has_staged = subprocess.run(
                ['git', 'diff', '--cached', '--quiet'],
                capture_output=True
            ).returncode != 0
            
            if has_staged:
                timestamp = datetime.now().isoformat()
                subprocess.run(
                    ['git', 'commit', '-m', f'Auto-commit trading logs at {timestamp}'],
                    capture_output=True,
                    check=True
                )
                logger.info("Changes committed")
            
            # Check if we have remote
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Push changes
                env = os.environ.copy()
                if GITHUB_TOKEN:
                    # Inject token into push URL
                    env['GIT_ASKPASS'] = '/bin/echo'
                
                subprocess.run(
                    ['git', 'push', 'origin', 'main'],
                    capture_output=True,
                    check=True,
                    timeout=30,
                    env=env
                )
                logger.info("Git push successful")
            else:
                logger.info("No remote configured, skipping push")
            
        except subprocess.TimeoutExpired:
            logger.error("Git push timeout")
        except subprocess.CalledProcessError as e:
            logger.error(f"Git error: {e.stderr.decode() if e.stderr else e}")
        except Exception as e:
            logger.error(f"Unexpected error in git push: {e}")
    
    def do_GET(self):
        """Handle GET requests for health check and status"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'ok',
                'timestamp': datetime.now().isoformat(),
                'logs_dir': LOGS_DIR,
                'script_dir': SCRIPT_DIR
            }).encode())
        
        elif self.path == '/status':
            os.chdir(SCRIPT_DIR)
            try:
                # Get git status
                git_status = subprocess.run(
                    ['git', 'status', '--porcelain'],
                    capture_output=True,
                    text=True
                ).stdout.strip()
                
                # Get last commit
                git_log = subprocess.run(
                    ['git', 'log', '--oneline', '-1'],
                    capture_output=True,
                    text=True
                ).stdout.strip()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'ok',
                    'git_clean': not bool(git_status),
                    'git_status': git_status or 'clean',
                    'last_commit': git_log,
                    'logs_dir': LOGS_DIR
                }).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
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
    global PORT, SECRET_TOKEN, GITHUB_TOKEN, LOGS_DIR
    PORT = int(os.environ.get('WEBHOOK_PORT', 8080))
    SECRET_TOKEN = os.environ.get('WEBHOOK_SECRET', '')
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
    LOGS_DIR = os.environ.get('LOGS_DIR', 'logs')
    
    # Ensure logs directory exists
    Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)
    
    # Start server
    server = HTTPServer(('0.0.0.0', PORT), TradingWebhookHandler)
    logger.info("=" * 60)
    logger.info("Trading Webhook Endpoint Server")
    logger.info("=" * 60)
    logger.info(f"Listening on: http://0.0.0.0:{PORT}")
    logger.info(f"Logs directory: {LOGS_DIR}")
    logger.info(f"Script directory: {SCRIPT_DIR}")
    logger.info(f"Secret token: {'configured' if SECRET_TOKEN else 'not configured'}")
    logger.info(f"GitHub token: {'configured' if GITHUB_TOKEN else 'not configured'}")
    logger.info("=" * 60)
    logger.info("Endpoints:")
    logger.info(f"  POST /         - Webhook endpoint")
    logger.info(f"  GET  /health   - Health check")
    logger.info(f"  GET  /status   - Status check")
    logger.info("=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()
    
    return 0

if __name__ == '__main__':
    exit(main())
