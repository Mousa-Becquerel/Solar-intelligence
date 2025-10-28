import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', 5000)}"
backlog = 2048

# Worker processes - Optimized for concurrent users
# With async agent + thread-safe conversation memory, we can now use multiple workers
# NOTE: For conversation memory to work across requests, use 1 worker OR implement sticky sessions/Redis
# Single worker still supports 8+ concurrent users thanks to async architecture
workers = 1  # Single worker = conversation memory preserved across requests
worker_class = "gthread"  # Thread-based workers (can switch to "uvicorn.workers.UvicornWorker" for full async)
threads = 8  # 8 threads = 8+ concurrent requests (async makes this non-blocking)
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Restart workers after this many requests, to help prevent memory leaks
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'becqsight-pv-chatbot-refactored'

# Worker timeout - Increased for long-running agent queries
timeout = 300  # 5 minutes for complex agent processing
graceful_timeout = 300  # Allow 5 minutes for graceful shutdown
keepalive = 5

# SSL (if needed)
# keyfile = None
# certfile = None
