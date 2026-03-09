from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            print("\n" + "="*50)
            print("🔔  WEBHOOK RECEIVED FROM OPS API!")
            print(f"Event ID:   {data.get('event_id')}")
            print(f"Event Type: {data.get('event_type')}")
            print(f"Wallet:     {data.get('wallet_id')}")
            print(f"Severity:   {data.get('severity')}")
            print("Payload:")
            print(json.dumps(data.get('payload', {}), indent=2))
            print("="*50 + "\n")
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Acknowledged')
        except Exception as e:
            print(f"Error: {e}")
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default logging to keep output clean
        pass

if __name__ == '__main__':
    port = 9099
    server = HTTPServer(('localhost', port), WebhookHandler)
    print(f"🚀 Mock Webhook Server listening on http://localhost:{port}/webhook")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
