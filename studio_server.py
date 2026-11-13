#!/usr/bin/env python3
"""Zero-dependency, localhost-only configurator server backed by the C++ generator."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote
import argparse
import json
import mimetypes
import secrets
import subprocess

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / 'studio'
GENERATED = ROOT / 'output' / 'web'
ENGINE = ROOT / 'build' / 'midi_generator'
MAX_SPEC_CHARS = 12000

class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, data, content_type='application/octet-stream', code=200):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(data)

    def fail(self, message, status=400):
        self.send_bytes(json.dumps({'error': str(message)}).encode(), 'application/json; charset=utf-8', status)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == '/':
            file = STATIC / 'index.html'
        elif path.startswith('/generated/'):
            file = (GENERATED / path[len('/generated/'):]).resolve()
            if not file.is_relative_to(GENERATED.resolve()):
                return self.fail('Invalid file location', 403)
        elif path.startswith('/studio/'):
            file = (STATIC / path[len('/studio/'):]).resolve()
            if not file.is_relative_to(STATIC.resolve()):
                return self.fail('Invalid file location', 403)
        else:
            return self.fail('Not found', 404)
        if not file.is_file():
            return self.fail('File not found', 404)
        ctype, _ = mimetypes.guess_type(file.name)
        self.send_bytes(file.read_bytes(), ctype or 'application/octet-stream')

    def do_POST(self):
        if urlparse(self.path).path != '/api/generate':
            return self.fail('Unknown API', 404)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > 15000:
                return self.fail('Request is empty or too large', 413)
            payload = json.loads(self.rfile.read(length))
            spec = payload.get('spec', '')
            if not isinstance(spec, str) or not 0 < len(spec) <= MAX_SPEC_CHARS:
                return self.fail('Enter a specification (up to 12,000 characters)')
            seed = int(payload.get('seed', 7))
            count = int(payload.get('variants', 3))
            if count < 1 or count > 6 or seed < 0 or seed > 1000000:
                return self.fail('Variants must be 1..6 and seed must be 0..1,000,000')
            if not ENGINE.is_file():
                return self.fail('C++ executable missing; build it with cmake first', 500)
            run_id = secrets.token_hex(7)
            folder = GENERATED / run_id
            folder.mkdir(parents=True, exist_ok=True)
            input_path = folder / 'request.board'
            input_path.write_text(spec, encoding='utf-8')
            proc = subprocess.run([str(ENGINE), str(input_path), str(folder), str(seed), str(count)],
                                  capture_output=True, text=True, timeout=30, cwd=ROOT)
            if proc.returncode:
                return self.fail(proc.stderr.strip() or 'Generation failed')
            variants = []
            for index in range(1, count + 1):
                model = json.loads((folder / f'design_{index}.json').read_text())
                url = f'/generated/{run_id}/design_{index}'
                variants.append({'model': model, 'obj': url + '.obj', 'svg': url + '.svg', 'json': url + '.json'})
            self.send_bytes(json.dumps({'variants': variants, 'notes': proc.stderr.strip().splitlines()}).encode(),
                            'application/json; charset=utf-8')
        except (TypeError, ValueError, json.JSONDecodeError) as e:
            self.fail(str(e))
        except subprocess.TimeoutExpired:
            self.fail('Layout timed out. Try fewer components or larger dimensions.', 504)
        except Exception as e:
            self.fail(str(e), 500)


def main():
    parser = argparse.ArgumentParser(description='Local MIDI design configurator')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    GENERATED.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'\nOpen in your browser: http://127.0.0.1:{args.port}\n')
    print('Press Ctrl+C to stop the local studio.\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        httpd.server_close()

if __name__ == '__main__':
    main()
