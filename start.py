"""
Startup wrapper that catches ALL crashes and logs them before uvicorn starts.
"""
import sys
import logging
import traceback

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("start")

def main():
    try:
        logger.info("=== DROOTLE STARTUP WRAPPER ===")
        logger.info(f"Python: {sys.version}")
        logger.info(f"Args: {sys.argv}")
        
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
        
        import os
        port = int(os.environ.get("PORT", 8080))
        logger.info(f"Starting uvicorn on port {port}...")
        
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            loop="asyncio",
            workers=1,
            log_level="info",
            access_log=True,
        )
    except Exception as e:
        logger.critical(f"FATAL CRASH: {e}\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
