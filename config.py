import logging

SEVEN_TV_API_URL: str = "https://7tv.io"
SEVEN_TV_API_VERSION: str = "v3"

LOGGING_LEVEL = logging.INFO

# Discord emoji size limit, it *should* be 256kb
EMOJI_SIZE_LIMIT: int = 262144  # in bytes

# These commands cannot be assigned custom permissions. Discord-based (based on role and user perms) perms are used.
IGNORED_COMMANDS_FOR_PERMISSIONS_OVERRIDES: list[str] = ["permissions remove", "permissions allow", "permissions list"]

# Either or not the command should be available for everyone, ignoring any overrides
# (p.s all the commands that are not in this list are defaulted to False)
DEFAULT_PERMISSIONS: dict[str: bool] = {
    "7tv emote add": False,
    "permissions list": True
}

# Should permission overrides be ignored if the user has administrator permissions.
IGNORE_OVERRIDES_IF_ADMINISTRATOR: bool = True

DEFAULT_PERMISSIONS_VALUE_JSON = {
    "role": [],  # ID of the role
    "user": []  # same as above, but user
}

COGS: list[str] = ["permissions", "emotes"]
