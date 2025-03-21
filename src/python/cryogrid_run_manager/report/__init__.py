import sys

from .main import add_profiles_to_map, make_interactive_map
from .profiles import (
    get_profile_locations,
    get_successful_profiles,
)

__all__ = [
    "get_successful_profiles",
    "get_profile_locations",
    "add_profiles_to_map",
    "make_interactive_map",
]


from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")
