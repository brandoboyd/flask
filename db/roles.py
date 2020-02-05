# PREDEFINED CONSTANTS // Order based on priorities so we can quickly determine who has access to who
REVIEWER = 100
AGENT = 1000
ANALYST = 2000
ADMIN = 9000
SYSTEM = 9910
STAFF = 9999
# Available user roles
USER_ROLES = {REVIEWER: 'REVIEWER',
              AGENT: 'AGENT',
              ANALYST: 'ANALYST',
              ADMIN: 'ADMIN',
              STAFF: 'STAFF',
              SYSTEM: 'SYSTEM'}


def compute_main_role(user_roles):
    """ Since a user may have multiple roles, return the one which is
     the most relevant for UI display """
    if not user_roles:
        return None
    main_role = max(user_roles)
    return USER_ROLES[main_role]
