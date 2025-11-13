#!/usr/bin/env python3
"""
Simple web server to view Docker container logs in real-time
"""

from flask import Flask, render_template, Response, jsonify
import subprocess
import threading
import time
from datetime import datetime

app = Flask(__name__)

CONTAINERS = [
    'credit-checker-even',
    'credit-checker-odd',
    'creditcheck-scheduler'
]

def get_container_logs(container_name, tail=100):
    """Get logs from a Docker container"""
    try:
        result = subprocess.run(
            ['docker', 'logs', '--tail', str(tail), container_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error getting logs: {e}"

def stream_container_logs(container_name):
    """Stream logs from a Docker container in real-time"""
    try:
        process = subprocess.Popen(
            ['docker', 'logs', '-f', '--tail', '50', container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in iter(process.stdout.readline, ''):
            if line:
                yield f"data: {line}\n\n"
        
    except Exception as e:
        yield f"data: Error streaming logs: {e}\n\n"

def get_container_status():
    """Get status of all containers"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}\t{{.State}}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        containers = {}
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 3:
                    containers[parts[0]] = {
                        'status': parts[1],
                        'state': parts[2]
                    }
        
        return containers
    except Exception as e:
        return {'error': str(e)}

@app.route('/')
def index():
    """Main page with container status and log viewer"""
    return render_template('log_viewer.html', containers=CONTAINERS)

@app.route('/api/status')
def status():
    """API endpoint for container status"""
    return jsonify(get_container_status())

@app.route('/api/logs/<container_name>')
def logs(container_name):
    """API endpoint to get container logs"""
    tail = int(request.args.get('tail', 100))
    if container_name not in CONTAINERS:
        return jsonify({'error': 'Container not found'}), 404
    
    logs = get_container_logs(container_name, tail)
    return jsonify({'logs': logs})

@app.route('/stream/<container_name>')
def stream(container_name):
    """Server-Sent Events endpoint for streaming logs"""
    if container_name not in CONTAINERS:
        return "Container not found", 404
    
    return Response(
        stream_container_logs(container_name),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/api/restart/<container_name>', methods=['POST'])
def restart_container(container_name):
    """API endpoint to restart a container"""
    if container_name not in CONTAINERS:
        return jsonify({'error': 'Container not found'}), 404
    
    try:
        subprocess.run(['docker', 'restart', container_name], check=True, timeout=30)
        return jsonify({'success': True, 'message': f'Container {container_name} restarted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    from flask import request
    print(f"[INFO] Starting log server on http://0.0.0.0:8888")
    print(f"[INFO] Monitoring containers: {', '.join(CONTAINERS)}")
    app.run(host='0.0.0.0', port=8888, debug=False, threaded=True)
