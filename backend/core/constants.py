"""
Application Constants
"""

class B2BRoleName:
    """
    Role slugs used in code logic.
    These must match the 'name' column in the roles table.
    """ 
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class PlatformRoleName:
    """
    Role slugs used in code logic.
    These must match the 'name' column in the roles table.
    """ 
    PLATFORM_ADMIN = "platform_admin"
