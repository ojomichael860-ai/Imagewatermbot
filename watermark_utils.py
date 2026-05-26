import os
from PIL import Image, ImageDraw, ImageFont

def apply_text_watermark(base_img_path, output_path, text="SAMPLE"):
    """Adds semi-transparent center text watermark to an image."""
    try:
        base_img = Image.open(base_img_path).convert("RGBA")
        txt_img = Image.new("RGBA", base_img.size, (255, 255, 255, 0))

        # 1. Choose font and scale size based on image width
        font_size = int(base_img.width * 0.08)  # Text width will be ~8% of image width
        try:
            # Render usually uses a default DejaVu/Liberation font
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except OSError:
            # Fallback if specific font not found on Render
            font = ImageFont.load_default()

        d = ImageDraw.Draw(txt_img)
        
        # 2. Calculate Text Position (Centered)
        # Using bbox instead of obsolete textsize for newer Pillow versions
        bbox = d.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (base_img.width - text_width) // 2
        y = (base_img.height - text_height) // 2

        # 3. Draw text with white color and low opacity (50)
        # Position slightly offset if fallback font is used for centering
        draw_y = y if hasattr(font, 'getbbox') else y - (text_height // 2)
        d.text((x, draw_y), text, fill=(255, 255, 255, 128), font=font)

        # 4. Composite original image and text layer
        watermarked = Image.alpha_composite(base_img, txt_img)
        watermarked.convert("RGB").save(output_path, "JPEG", quality=90)
        return True, None
    except Exception as e:
        return False, str(e)

def apply_logo_watermark(base_img_path, logo_img_path, output_path):
    """Adds a semi-transparent logo overlay to the main image."""
    try:
        base_img = Image.open(base_img_path).convert("RGBA")
        logo_img = Image.open(logo_img_path).convert("RGBA")

        # 1. Rescale Logo Size (make logo width ~15% of the main image width)
        scale_ratio = (base_img.width * 0.15) / logo_img.width
        new_size = (int(logo_img.width * scale_ratio), int(logo_img.height * scale_ratio))
        logo_img = logo_img.resize(new_size, Image.Resampling.LANCZOS)

        # 2. Adjust Logo Transparency (Opacity)
        # Modify the alpha channel directly
        r, g, b, alpha = logo_img.split()
        alpha = alpha.point(lambda p: int(p * 0.6))  # 60% of original opacity
        logo_img = Image.merge("RGBA", (r, g, b, alpha))

        # 3. Create a blank overlay layer same size as original
        overlay_img = Image.new("RGBA", base_img.size, (255, 255, 255, 0))

        # 4. Calculate Position (Center the scaled logo)
        x = (base_img.width - logo_img.width) // 2
        y = (base_img.height - logo_img.height) // 2

        # 5. Paste the logo onto the overlay
        overlay_img.paste(logo_img, (x, y))

        # 6. Composite final image
        watermarked = Image.alpha_composite(base_img, overlay_img)
        watermarked.convert("RGB").save(output_path, "JPEG", quality=90)
        return True, None
    except Exception as e:
        return False, str(e)
