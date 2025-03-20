import sys

from .profiles import (
    get_successful_profiles,
    get_profile_locations,
)

from .main import (
    add_profiles_to_map,
    make_interactive_map
)


from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")
