import io
import config
from PIL import Image, GifImagePlugin
GifImagePlugin.LOADING_STRATEGY = GifImagePlugin.LoadingStrategy.RGB_AFTER_DIFFERENT_PALETTE_ONLY

async def process_gif(image: Image, compress_factor: int = 1, fit_to_square: bool = False, speed_up: bool = False):
    frames = []
    output = io.BytesIO()
    smaller_side = min(image.size)

    for n_frame in range(0, image.n_frames, compress_factor):
        image.seek(n_frame)
        frame_img = image.copy()

        if fit_to_square:
            frame_img = frame_img.resize((smaller_side, smaller_side))

        frames.append(frame_img)

    duration = image.info.get('duration', 100)
    if not speed_up:
        duration = duration * compress_factor

    frames[0].save(
        output,
        format="GIF",
        append_images=frames[1:],
        disposal=2 if image.has_transparency_data else 1,
        save_all=True,
        optimize=True,
        interlace=False,
        duration=duration
    )

    return output.getvalue()

async def format_emote_for_discord(initial_image_bytes, fit_to_square: bool = False, speed_up: bool = False):
    image = Image.open(io.BytesIO(initial_image_bytes))

    if image.format == "GIF":
        result = None
        compress_factor = 1

        while True and compress_factor <= 4:
            result = await process_gif(
                image, compress_factor=compress_factor, fit_to_square=fit_to_square, speed_up=speed_up
            )
            if len(result) < config.EMOJI_SIZE_LIMIT:
                return result

            compress_factor += 1

        return result


    else:
        output = io.BytesIO()
        smaller_side = min(image.size)
        if fit_to_square:
            image = image.resize((smaller_side, smaller_side))

        image.save(output, format="PNG")

        return output.getvalue()
