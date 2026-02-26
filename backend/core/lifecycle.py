"""Lifecycle helpers to keep server.py thinner."""
import logging

logger = logging.getLogger(__name__)


async def shutdown_resources(db_client, scheduler_instance=None):
    """Gracefully stop scheduler and close DB client."""
    if scheduler_instance is not None:
        try:
            if getattr(scheduler_instance, "running", False):
                scheduler_instance.shutdown(wait=False)
                logger.info("Scheduler stopped")
        except Exception as exc:
            logger.warning(f"Error stopping scheduler: {exc}")

    try:
        db_client.close()
        logger.info("MongoDB connection closed")
    except Exception as exc:
        logger.warning(f"Error closing MongoDB client: {exc}")
