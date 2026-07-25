
import zlib
from uuid import UUID

def generate_deterministic_numeric_id(uuid_val: UUID) -> int:
    """
    Generates a deterministic 8-10 digit numeric ID from a UUID.
    Uses CRC32 hashing which is stable and cross-platform.
    """
    # Use the hex representation for hashing
    return zlib.crc32(str(uuid_val).encode('utf-8')) & 0xffffffff
