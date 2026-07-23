#!/usr/bin/env python
"""Debug Server for collecting runtime logs"""
import http.server
import json
from datetime import datetime
import threading

# 创建日志存储
logs = []
logs_lock = threading.Lock()

class DebugHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/log':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                log_entry = json.loads(post_data.decode('utf-8'))
                log_entry['timestamp'] = datetime.now().isoformat()
                with logs_lock:
                    logs.append(log_entry)
                    # 同时写入文件
                    with open('/Users/jinshaomin/Documents/jinsm/test_hub/grt_testhub/.dbg/trae-debug-log-scheduled-task.ndjson', 'a') as f:
                        f.write(json.dumps(log_entry) + '\n')
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
            except Exception as e:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == '/logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            with logs_lock:
                self.wfile.write(json.dumps(logs, indent=2).encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'healthy', 'logs_count': len(logs)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # 抑制默认日志

if __name__ == '__main__':
    PORT = 9999
    server = http.server.HTTPServer(('127.0.0.1', PORT), DebugHandler)
    print(f'Debug Server started on http://127.0.0.1:{PORT}')
    print(f'Log endpoint: POST http://127.0.0.1:{PORT}/log')
    print(f'Query endpoint: GET http://127.0.0.1:{PORT}/logs')
    print(f'Health check: GET http://127.0.0.1:{PORT}/health')
    print(f'Logs also saved to: .dbg/trae-debug-log-scheduled-task.ndjson')
    server.serve_forever()