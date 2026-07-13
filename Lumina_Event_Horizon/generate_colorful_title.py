from PIL import Image, ImageDraw, ImageFont
import os

def create_title_image():
    # 1024x128
    width, height = 1024, 128
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Try to load a nice font
    font_path = "/System/Library/Fonts/Supplemental/Impact.ttf"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Helvetica.ttc"
        
    try:
        font = ImageFont.truetype(font_path, 80)
    except:
        font = ImageFont.load_default()

    text = "LUMINA EVENT HORIZON v1.3.4"
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    x = (width - text_w) // 2
    y = (height - text_h) // 2 - bbox[1]
    
    # Draw shadow
    shadow_color = (0, 0, 0, 180)
    draw.text((x + 4, y + 4), text, font=font, fill=shadow_color)
    
    # Draw gradient text
    # We can do this by drawing the text as a mask and then compositing a gradient
    text_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_img)
    text_draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    
    # Create gradient image
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)
    
    # Colorful gradient: Deep Purple to Bright Cyan
    color_start = (138, 43, 226) # BlueViolet
    color_end = (0, 255, 255) # Cyan
    
    for i in range(width):
        r = int(color_start[0] + (color_end[0] - color_start[0]) * (i / width))
        g = int(color_start[1] + (color_end[1] - color_start[1]) * (i / width))
        b = int(color_start[2] + (color_end[2] - color_start[2]) * (i / width))
        gradient_draw.line([(i, 0), (i, height)], fill=(r, g, b, 255))
        
    # Composite the text over the shadow
    gradient.putalpha(text_img.split()[3])
    img.alpha_composite(gradient)
    
    # Save the original image (not rotated, we'll fix the shader)
    out_path = "/Users/benji10/code/Lumina_Event_Horizon/shaders/lib/textures/title.png"
    img.save(out_path)
    print("Created title.png at", out_path)

if __name__ == "__main__":
    create_title_image()
