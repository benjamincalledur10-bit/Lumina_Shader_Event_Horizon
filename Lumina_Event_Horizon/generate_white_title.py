from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

def create_white_title():
    # 2048x256 canvas to prevent cutoff and improve resolution (8:1 aspect ratio)
    width, height = 2048, 256
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Try to load a nice serif font (Times New Roman)
    font_path = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Helvetica.ttc"
        
    try:
        font = ImageFont.truetype(font_path, 120)
    except:
        font = ImageFont.load_default()

    text = "Lumina Event Horizon v1.3.4"
    
    x = width / 2
    y = height / 2
    
    # Create glow layer
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    
    # Draw dark glow/shadow multiple times with varying blur for effect
    glow_draw.text((x, y), text, font=font, fill=(0, 0, 0, 255), anchor="mm")
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    
    glow2 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow2_draw = ImageDraw.Draw(glow2)
    glow2_draw.text((x, y), text, font=font, fill=(0, 0, 0, 150), anchor="mm")
    glow2 = glow2.filter(ImageFilter.GaussianBlur(4))
    
    # Combine glows
    glow.alpha_composite(glow2)
    
    # Create text layer
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    text_draw.text((x, y), text, font=font, fill=(255, 255, 255, 255), anchor="mm")
    
    # Combine all
    final_img = Image.alpha_composite(img, glow)
    final_img = Image.alpha_composite(final_img, text_layer)
    
    out_path = "/Users/benji10/code/Lumina_Event_Horizon/shaders/lib/textures/title.png"
    final_img.save(out_path)
    print("Created title.png at", out_path)

if __name__ == "__main__":
    create_white_title()
