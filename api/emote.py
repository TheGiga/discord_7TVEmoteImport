from dataclasses import dataclass


@dataclass
class Emote:
    id: str
    name: str
    animated: bool
    format: str
    width: int
    height: int

    emote_url: str
    emote_bytes: bytes

    def __repr__(self):
        return f"Emote({self.id=}, {self.name=}, {self.animated=}, {self.emote_url})"
