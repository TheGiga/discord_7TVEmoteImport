import aiohttp
import config
from api import Emote
from api.errors import *
from api.image import format_emote_for_discord

_api_endpoint = f"{config.SEVEN_TV_API_URL}/{config.SEVEN_TV_API_VERSION}"


class EmotesAPI:
    def __init__(self):
        self._session: aiohttp.ClientSession = None  # type: ignore

    @staticmethod
    def _get_fitting_emote(files: dict, animated: bool) -> dict | None:
        for i in reversed(range(1, 5)):
            search_for = f"{i}x.png" if not animated else f"{i}x.gif"

            for file in files:
                if not file.get("name") == search_for:
                    continue

                if int(file.get("size")) > config.EMOJI_SIZE_LIMIT:
                    continue

                return file

            continue
        else:
            return None

    async def create_session(self):
        self._session = aiohttp.ClientSession()

    async def _emote_get(self, emote_id: str) -> dict | None:
        try:
            response = await self._session.get(f"{_api_endpoint}/emotes/{emote_id}")

        except aiohttp.InvalidURL:
            raise aiohttp.InvalidURL(url=f"{_api_endpoint}/emotes/{emote_id}", description="No Such URL")

        match response.status:
            case 404:
                raise EmoteNotFound(emote_id)

            case 200:
                response_json = await response.json()
                if response_json.get('status') == "Not Found":
                    raise EmoteNotFound(emote_id)

                return response_json

    async def emote_get(self, emote_id: str, square_aspect_ratio=False) -> Emote:
        emote_json = await self._emote_get(emote_id=emote_id)

        if not emote_json:
            raise EmoteJSONReadFail(f"Failed to read JSON for emote `{emote_id}`, most likely Invalid URL!")

        animated = emote_json.get("animated", False)

        fitting_emote = self._get_fitting_emote(emote_json["host"]["files"], animated)
        if not fitting_emote:
            raise FailedToFindFittingEmote

        fitting_emote_url = f"https:{emote_json['host']['url']}/{fitting_emote.get('name')}"

        r = await self._session.get(fitting_emote_url)

        if r.status == 200:
            emote_bytes = await r.read()
        else:
            raise EmoteBytesReadFail(f"Failed reading bytes from {fitting_emote_url}")

        width, height = int(fitting_emote.get('width')), int(fitting_emote.get('height'))

        emote_bytes = format_emote_for_discord(
            emote_bytes,
            square_aspect_ratio
        )

        return Emote(
            id=emote_json.get('id'),
            name=emote_json.get('name')[:32],
            format="gif" if animated else "png",
            animated=animated,
            width=width,
            height=height,
            emote_url=fitting_emote_url,
            emote_bytes=emote_bytes
        )
