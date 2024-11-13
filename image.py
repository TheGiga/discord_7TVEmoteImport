from PIL import Image
import io
import config


def format_emote_for_discord(initial_image_bytes, stretch: bool = False):
    image = Image.open(io.BytesIO(initial_image_bytes))
    smaller_side = min(image.size)
    target_size = config.EMOJI_SIZE_LIMIT
    resize_factor = 0.9  # Factor to progressively reduce dimensions if necessary

    def save_to_buffer(img, l_frames=None):
        with io.BytesIO() as output:
            if l_frames:
                l_frames[0].save(
                    output,
                    format="GIF",
                    save_all=True,
                    append_images=l_frames[1:],
                    duration=image.info.get("duration", 100),
                    disposal=2,
                )
            else:
                img.save(output, format=format)
            return output.getvalue()

    # Handle animated GIFs
    if getattr(image, "is_animated", False):
        frames = []
        for frame in range(image.n_frames):
            image.seek(frame)
            frame_img = image.copy()
            frame_img.info.pop("background")

            if stretch:
                frame_img = frame_img.resize((smaller_side, smaller_side))

            frames.append(frame_img)

        # Downscale loop for animated GIFs
        while True:
            image_bytes = save_to_buffer(image, frames)
            if len(image_bytes) <= target_size:
                return image_bytes

            # Downscale each frame by resizing
            smaller_side = int(smaller_side * resize_factor)
            frames = [frame.resize((smaller_side, smaller_side)) for frame in frames]
            if smaller_side < 10:  # Prevent endless loop if images become too small
                break

    # Handle static images (non-animated)
    else:
        if stretch:
            image = image.resize((smaller_side, smaller_side))
            image_bytes = image.tobytes()
        else:
            image_bytes = initial_image_bytes

    return image_bytes
