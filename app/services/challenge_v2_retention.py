import asyncio
import logging

from app.services.challenge_v2 import enabled
from app.services.challenge_v2_evidence import purge_expired


async def retention_loop():
    """Minute sweep plus read-time expiry. No user/photo values are logged."""
    while True:
        try:
            if enabled():
                await purge_expired()
        except Exception:
            logging.getLogger(__name__).error("Challenge photo retention sweep failed; operator action required")
        await asyncio.sleep(60)
