import os
from PIL import Image, ImageDraw, ImageFont

def apply_text_watermark(base_img_path, output_path, text="SAMPLE"):
    """Adds semi-transparent center text watermark to an image."""
    try:
        base_img = Image.open(base_img_path).convert("RGBA")
        txt_img = Image.new("RGBA", base_img.size, (255, 255, 255, 0))

        # Choose font and scale size based on image width (~8% of width)
        font_size = int(base_img.width * 0.08)  
        try:
            # Render systems default paths for Linux standard fonts
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        d = ImageDraw.Draw(txt_img)
        
        # Calculate Text Position (Centered) using modern syntax
        bbox = d.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (base_img.width - text_width) // 2
        y = (base_img.height - text_height) // 2

        # Draw text with white color and 50% opacity
        d.text((x, y), text, fill=(255, 255, 255, 128), font=font)

        # Composite original image and text layer
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

        # Rescale Logo Size (make logo width ~15% of the main image width)
        scale_ratio = (base_img.width * 0.15) / logo_img.width
        new_size = (int(logo_img.width * scale_ratio), int(logo_img.height * scale_ratio))
        
        # Modern Resampling call for Pillow 10+ / 11+ / 12+
        logo_img = logo_img.resize(new_size, Image.Resampling.LANCZOS)

        # Adjust Logo Transparency (Opacity) to 60%
        r, g, b, alpha = logo_img.split()
        alpha = alpha.point(lambda p: int(p * 0.6))  
        logo_img = Image.merge("RGBA", (r, g, b, alpha))

        # Create blank canvas layer
        overlay_img = Image.new("RGBA", base_img.size, (255, 255, 255, 0))

        # Calculate Center Position
        x = (base_img.width - logo_img.width) // 2
        y = (base_img.height - logo_img.height) // 2

        # Paste logo overlay
        overlay_img.paste(logo_img, (x, y))

        # Composite final image
        watermarked = Image.alpha_composite(base_img, overlay_img)
        watermarked.convert("RGB").save(output_path, "JPEG", quality=90)
        return True, None
    except Exception as e:
        return False, str(e)
