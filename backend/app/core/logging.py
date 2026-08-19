import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Default record fields
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "file": record.filename,
            "line": record.lineno
        }
        
        # Inject standard identifiers from extra if present
        for key in ["concept_id", "search_run_id", "population_run_id", "video_id", "observation_id", "request_id"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)
                
        # Inject other custom extras
        if hasattr(record, "extra_data"):
            log_data.update(getattr(record, "extra_data"))
            
        return json.dumps(log_data)

def setup_logging(log_level: str = "INFO", log_format: str = "json") -> logging.Logger:
    logger = logging.getLogger("CreatorIQ")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if log_format.lower() == "json":
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                "[%(asctime)s] %(levelname)s in %(filename)s:%(lineno)d: %(message)s"
            ))
        logger.addHandler(handler)
        
    return logger

logger = setup_logging()
