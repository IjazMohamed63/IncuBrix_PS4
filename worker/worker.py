import asyncio
import signal
from core.config import get_settings
from core.logging import get_logger, setup_logging

settings = get_settings()
logger = get_logger("worker")


class WorkerService:
    def __init__(self):
        self.running = True

    async def start(self):
        setup_logging(settings.log_level)
        logger.info(f"IncuBrix background worker service started (env: {settings.app_env})")

        # Handle termination signals
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.shutdown)
            except NotImplementedError:
                # Signal handlers not implemented on Windows event loop
                pass

        while self.running:
            # Heartbeat and job polling loop
            await asyncio.sleep(2)

    def shutdown(self):
        logger.info("Worker shutting down...")
        self.running = False


if __name__ == "__main__":
    worker = WorkerService()
    try:
        asyncio.run(worker.start())
    except (KeyboardInterrupt, SystemExit):
        worker.shutdown()
