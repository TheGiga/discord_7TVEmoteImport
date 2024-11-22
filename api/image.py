import io
from PIL import Image


def format_emote_for_discord(initial_image_bytes, fit_to_square: bool = False):
    image = Image.open(io.BytesIO(initial_image_bytes))
    smaller_side = min(image.size)

    output = io.BytesIO()

    if image.format == "GIF":
        frames = []
        for frame in range(image.n_frames):
            image.seek(frame)
            frame_img = image.copy()

            if fit_to_square:
                frame_img = frame_img.resize((smaller_side, smaller_side))

            frames.append(frame_img)

        frames[0].save(
            output,
            format="GIF",
            append_images=frames[1:],
            disposal=2 if image.has_transparency_data else 0,
            save_all=True,
            optimize=True
        )

        return output.getvalue()

    else:
        if fit_to_square:
            image = image.resize((smaller_side, smaller_side))

        image.save(output, format="PNG")

        return output.getvalue()
