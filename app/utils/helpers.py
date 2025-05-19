import json
from typing import Dict, Any, List, Optional
from uuid import UUID
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("crm_server")

def format_uuid(uuid_obj: UUID) -> str:
    """Format UUID object to string"""
    return str(uuid_obj) if uuid_obj else None

def parse_uuid(uuid_str: str) -> Optional[UUID]:
    """Parse UUID string to UUID object"""
    try:
        return UUID(uuid_str) if uuid_str else None
    except ValueError:
        logger.error(f"Invalid UUID: {uuid_str}")
        return None

def safe_json_dumps(obj: Any) -> str:
    """Safely convert object to JSON string"""
    try:
        return json.dumps(obj, default=str)
    except Exception as e:
        logger.error(f"Error serializing to JSON: {e}")
        return "{}"

def safe_json_loads(json_str: str) -> Dict[str, Any]:
    """Safely parse JSON string to object"""
    try:
        return json.loads(json_str) if json_str else {}
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        return {}
