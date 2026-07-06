import json
import logging
import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

def log_structured_event(
    event_name: str,
    level: int = logging.INFO,
    metadata: Dict[str, Any] = None
):
    """
    Logs machine-filterable structured events containing UTC timestamps.
    Automatically scrubs secrets.
    """
    if metadata is None:
        metadata = {}
        
    scrubbed_meta = {}
    # Scrub potential secrets or tokens
    sensitive_keys = ["token", "webhook", "secret", "password", "key"]
    for k, v in metadata.items():
        if any(sk in k.lower() for sk in sensitive_keys):
            scrubbed_meta[k] = "[SCRUBBED]"
        else:
            scrubbed_meta[k] = v
            
    payload = {
        "event": event_name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "level": logging.getLevelName(level),
        "metadata": scrubbed_meta
    }
    
    # Write to logging stream as json string
    log_msg = json.dumps(payload)
    logger.log(level, log_msg)
