from PIL import Image
import io
import config


def format_emote_for_discord(image_bytes, stretch: bool = True):
    image = Image.open(io.BytesIO(image_bytes))
    max_dim = max(image.size)
    target_size = config.EMOJI_SIZE_LIMIT
    resize_factor = 0.9  # Factor to progressively reduce dimensions if necessary

    def save_to_buffer(img, format="PNG", frames=None):
        with io.BytesIO() as output:
            if frames:
                frames[0].save(
                    output,
                    format=format,
                    save_all=True,
                    append_images=frames[1:],
                    duration=image.info.get("duration", 100),
                    loop=image.info.get("loop", 0),
                    disposal=2
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
            if stretch:
                frame_img = frame_img.resize((max_dim, max_dim), Image.LANCZOS)
            frames.append(frame_img)

        # Downscale loop for animated GIFs
        while True:
            image_bytes = save_to_buffer(image, format="GIF", frames=frames)
            if len(image_bytes) <= target_size:
                return image_bytes

            # Downscale each frame by resizing
            max_dim = int(max_dim * resize_factor)
            frames = [frame.resize((max_dim, max_dim), Image.LANCZOS) for frame in frames]
            if max_dim < 10:  # Prevent endless loop if images become too small
                break

    # Handle static images (non-animated)
    else:
        if stretch:
            image = image.resize((max_dim, max_dim), Image.LANCZOS)

        # Downscale loop for static images
        while True:
            image_bytes = save_to_buffer(image, format=image.format if image.format else "PNG")
            if len(image_bytes) <= target_size:
                return image_bytes

            # Downscale by resizing
            max_dim = int(max_dim * resize_factor)
            image = image.resize((max_dim, max_dim), Image.LANCZOS)
            if max_dim < 10:  # Prevent endless loop if image becomes too small
                break

    # Final fallback in case the image is still too large
    return None if len(image_bytes) > target_size else image_bytes
