import os

def replace_in_file(filepath, replacements):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        new_content = content
        for old, new in replacements.items():
            new_content = new_content.replace(old, new)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(new_content)
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

replacements = {
    "Complementary Shaders by EminGT": "Lumina Shader - Event Horizon",
    "Complementary Base by EminGT": "Lumina Shader - Event Horizon",
    "Complementary": "Lumina",
    "www.complementary.dev": "www.lumina-shader.dev",
    "EminGT": "Lumina Dev",
    "emingt": "luminadev"
}

root_dir = "/Users/benji10/code/Lumina_Event_Horizon/shaders"

for root, dirs, files in os.walk(root_dir):
    for file in files:
        if file.endswith((".glsl", ".lang", ".properties", ".json", ".txt")):
            replace_in_file(os.path.join(root, file), replacements)
