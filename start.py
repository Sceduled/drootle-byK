"""
Startup wrapper that catches ALL crashes and logs them before uvicorn starts.
"""
import sys
import os
import signal
import logging
import traceback
import threading
import time

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger("start")

def signal_handler(signum, frame):
    logger.critical(f"!!! SIGNAL RECEIVED: {signal.Signals(signum).name} ({signum})")
    logger.critical(f"Stack at signal:\n{''.join(traceback.format_stack(frame))}")
    sys.stdout.flush()
    sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def keepalive():
    """Background thread that logs every 30s to prove the process is still alive."""
    while True:
        time.sleep(30)
        try:
            import resource
            mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # MB
            logger.info(f"[KEEPALIVE] Process alive, memory: {mem:.1f} MB")
        except Exception:
            logger.info("[KEEPALIVE] Process alive")
        sys.stdout.flush()

def main():
    try:
        logger.info("=== DROOTLE STARTUP WRAPPER ===")
        logger.info(f"Python: {sys.version}")
        logger.info(f"PID: {os.getpid()}")
        
        # Start keepalive thread
        t = threading.Thread(target=keepalive, daemon=True)
        t.start()
        logger.info("Keepalive thread started")
        
        # Test imports one by one
        logger.info("Importing fastapi...")
        import fastapi
        logger.info(f"  fastapi {fastapi.__version__} OK")
        
        logger.info("Importing uvicorn...")
        import uvicorn
        logger.info(f"  uvicorn OK")
        
        logger.info("Importing core.config...")
        from core.config import settings
        logger.info(f"  config OK, provider={settings.WHATSAPP_PROVIDER}")
        
        logger.info("Importing main app...")
        from main import app
        logger.info(f"  main app OK, routes={len(app.routes)}")
        
        port = int(os.environ.get("PORT", 8080))
        logger.info(f"Starting uvicorn on port {port} (PID {os.getpid()})...")
        sys.stdout.flush()
        
        uvicorn.run(
            "main:app",
            host="::",
            port=port,
            loop="asyncio",
            workers=1,
            log_level="info",
            access_log=True,
        )
        logger.critical("!!! UVICORN EXITED CLEANLY (unexpected)")
    except Exception as e:
        logger.critical(f"FATAL CRASH: {e}\n{traceback.format_exc()}")
        sys.stdout.flush()
        sys.exit(1)

if __name__ == "__main__":
    main()
