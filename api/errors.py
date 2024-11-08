class EmoteNotFound(Exception):
    def __init__(self, emote_id: str):
        super().__init__(f"Emote `{emote_id}` not found.")


class EmoteBytesReadFail(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class EmoteJSONReadFail(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class FailedToFindFittingEmote(Exception):
    pass
