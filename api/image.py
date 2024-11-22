from PIL import Image
import io
import config
from api.errors import FailedToFindFittingEmote


def format_emote_for_discord(initial_image_bytes, fit_to_square: bool = False):
    image = Image.open(io.BytesIO(initial_image_bytes))
    smaller_side = min(image.size)
    target_size = config.EMOJI_SIZE_LIMIT

    def save_to_buffer(img, l_frames=None):
        with io.BytesIO() as l_output:
            if l_frames:
                l_frames[0].save(
                    l_output,
                    format="GIF",
                    save_all=True,
                    append_images=l_frames[1:],
                    disposal=2
                )
            else:
                img.save(l_output, format="GIF")
            return l_output.getvalue()

    if getattr(image, "is_animated", False):
        frames = []
        for frame in range(image.n_frames):
            image.seek(frame)
            frame_img = image.copy()
            frame_img.info.pop("background")

            if fit_to_square:
                frame_img = frame_img.resize((smaller_side, smaller_side))

            frames.append(frame_img)

        image_bytes = save_to_buffer(image, frames)
        if len(image_bytes) > target_size:
            raise FailedToFindFittingEmote

        return image_bytes


    else:
        output = io.BytesIO()

        if fit_to_square:
            image = image.resize((smaller_side, smaller_side))

        image.save(output, format="PNG")

        return output.getvalue()
