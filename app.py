import streamlit as st
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
import requests
from PIL.Image import Resampling

class BrandConfig:
    def __init__(self, brand_logo_path: str, primary_colors: list, secondary_colors: list, primary_font_path: str, secondary_font_path: str):
        self.brand_logo_path = brand_logo_path
        self.primary_colors = primary_colors
        self.secondary_colors = secondary_colors
        self.primary_font_path = primary_font_path
        self.secondary_font_path = secondary_font_path

class PostConfig:
    def __init__(self, 
                 description: str, 
                 occasion: str = None, 
                 user_image_path: str = None,
                 desired_output_size: tuple = (1080, 1080)):
        self.description = description
        self.occasion = occasion
        self.user_image_path = user_image_path
        self.desired_output_size = desired_output_size

def load_image(image_path: str) -> Image.Image:
    return Image.open(image_path).convert("RGBA")

def generate_ai_image(prompt: str, size: tuple=(1080,1080)):
    # Placeholder: Replace with a real AI image generation integration
    img = Image.new("RGBA", size, (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((50,50), f"AI Image:\n{prompt}", fill=(0,0,0))
    return img

def add_stylized_overlay(base_img: Image.Image, brand_config: BrandConfig):
    draw = ImageDraw.Draw(base_img, "RGBA")
    shape_color = brand_config.primary_colors[0] if brand_config.primary_colors else "#FF0000"
    secondary_color = brand_config.secondary_colors[0] if brand_config.secondary_colors else "#000000"

    width, height = base_img.size
    wave_height = int(height * 0.3)
    wave_img = Image.new("RGBA", (width, wave_height), (0,0,0,0))
    wdraw = ImageDraw.Draw(wave_img, "RGBA")

    # Create a wave-like shape at the bottom using ellipses and rectangles
    wdraw.rectangle([0, wave_height//2, width, wave_height], fill=secondary_color)
    wdraw.ellipse([-(wave_height), 0, wave_height, wave_height], fill=secondary_color)
    wdraw.ellipse([width-wave_height, 0, width+wave_height, wave_height], fill=secondary_color)

    # Paste the wave onto the base image
    base_img.alpha_composite(wave_img, (0, height - wave_height))

    # Add a rounded rectangle for text background
    text_bg_margin = 50
    text_bg_width = width - text_bg_margin*2
    text_bg_height = 200
    text_bg_x0 = text_bg_margin
    text_bg_y0 = height - wave_height + (wave_height//2 - text_bg_height//2)
    text_bg_x1 = text_bg_x0 + text_bg_width
    text_bg_y1 = text_bg_y0 + text_bg_height
    corner_radius = 50

    text_bg = Image.new("RGBA", (text_bg_width, text_bg_height), (0,0,0,0))
    tb_draw = ImageDraw.Draw(text_bg, "RGBA")
    tb_draw.rounded_rectangle([0,0,text_bg_width,text_bg_height], corner_radius, fill=shape_color)
    base_img.alpha_composite(text_bg, (text_bg_x0, text_bg_y0))

    return (text_bg_x0, text_bg_y0, text_bg_width, text_bg_height)

def generate_post_image(brand_config: BrandConfig, post_config: PostConfig) -> Image.Image:
    # Determine background image
    if post_config.user_image_path:
        base_img = load_image(post_config.user_image_path)
    else:
        prompt = f"{post_config.description} {post_config.occasion or ''}"
        base_img = generate_ai_image(prompt, post_config.desired_output_size)

    base_img = base_img.resize(post_config.desired_output_size, Resampling.LANCZOS)

    # Add stylized overlay
    text_area = add_stylized_overlay(base_img, brand_config)

    # Add brand logo if available
    if brand_config.brand_logo_path:
        logo_img = load_image(brand_config.brand_logo_path)
        logo_size = (int(post_config.desired_output_size[0]*0.15), int(post_config.desired_output_size[1]*0.15))
        logo_img = logo_img.resize(logo_size, Resampling.LANCZOS)

        # Add subtle shadow behind logo
        shadow_offset = 5
        logo_shadow = Image.new("RGBA", logo_size, (0,0,0,0))
        ls_draw = ImageDraw.Draw(logo_shadow)
        ls_draw.rectangle([0,0,logo_size[0],logo_size[1]], fill=(0,0,0,100))
        logo_shadow = logo_shadow.filter(ImageFilter.GaussianBlur(5))
        base_img.alpha_composite(logo_shadow, (30+shadow_offset,30+shadow_offset))
        base_img.alpha_composite(logo_img, (30,30))

    draw = ImageDraw.Draw(base_img)

    # Load fonts, fallback to default if not found
    try:
        primary_font = ImageFont.truetype(brand_config.primary_font_path, size=60)
    except:
        primary_font = ImageFont.load_default()

    try:
        secondary_font = ImageFont.truetype(brand_config.secondary_font_path, size=40)
    except:
        secondary_font = ImageFont.load_default()

    text_color = (255,255,255)
    description_text = post_config.description
    w = text_area[2]
    h = text_area[3]

    # Measure text using textbbox instead of textsize
    desc_bbox = draw.textbbox((0,0), description_text, font=primary_font)
    desc_w = desc_bbox[2] - desc_bbox[0]
    desc_h = desc_bbox[3] - desc_bbox[1]

    desc_x = text_area[0] + (w - desc_w)//2
    desc_y = text_area[1] + (h - desc_h)//2 - 20

    occ_text = post_config.occasion if post_config.occasion else ""
    occ_bbox = draw.textbbox((0,0), occ_text, font=secondary_font) if occ_text else (0,0,0,0)
    occ_w = occ_bbox[2] - occ_bbox[0]
    occ_h = occ_bbox[3] - occ_bbox[1]

    # If there's occasion text, place it below the description
    if occ_text:
        desc_y = desc_y - (occ_h//2)  # Move description up a bit so both lines fit nicely
        occ_x = text_area[0] + (w - occ_w)//2
        occ_y = desc_y + desc_h + 20

    # Draw drop shadows behind text
    for offset in [(2,2), (2,-2), (-2,2), (-2,-2)]:
        draw.text((desc_x+offset[0], desc_y+offset[1]), description_text, font=primary_font, fill=(0,0,0,128))
        if occ_text:
            draw.text((occ_x+offset[0], occ_y+offset[1]), occ_text, font=secondary_font, fill=(0,0,0,128))

    # Draw actual text
    draw.text((desc_x, desc_y), description_text, font=primary_font, fill=text_color)
    if occ_text:
        draw.text((occ_x, occ_y), occ_text, font=secondary_font, fill=text_color)

    return base_img

# ---------- STREAMLIT UI ---------- #
st.title("Social Media Post Generator")

st.header("Brand Configuration")
uploaded_logo = st.file_uploader("Upload Brand Logo (.png)", type=["png"])
if uploaded_logo:
    brand_logo_path = "temp_brand_logo.png"
    with open(brand_logo_path, "wb") as f:
        f.write(uploaded_logo.read())
else:
    brand_logo_path = None

primary_colors = st.text_input("Primary Colors (comma separated hex):", "#FF0000,#FFFFFF")
secondary_colors = st.text_input("Secondary Colors (comma separated hex):", "#000000,#CCCCCC")
primary_font_path = st.text_input("Primary Font Path:", "arial.ttf")
secondary_font_path = st.text_input("Secondary Font Path:", "arial.ttf")

brand_config = BrandConfig(
    brand_logo_path=brand_logo_path,
    primary_colors=[c.strip() for c in primary_colors.split(",") if c.strip()],
    secondary_colors=[c.strip() for c in secondary_colors.split(",") if c.strip()],
    primary_font_path=primary_font_path,
    secondary_font_path=secondary_font_path
)

st.header("Post Configuration")
description = st.text_area("Post Description:", "Craving Authentic Indian Flavours?")
occasion = st.text_input("Occasion (optional):", "Delivering straight to your doorstep")
user_image_option = st.radio("Upload a background image?", ("No", "Yes"))
user_image_path = None
if user_image_option == "Yes":
    uploaded_image = st.file_uploader("Upload background image", type=["png", "jpg", "jpeg"])
    if uploaded_image:
        user_image_path = f"temp_uploaded_image.{uploaded_image.name.split('.')[-1]}"
        with open(user_image_path, "wb") as f:
            f.write(uploaded_image.read())

if st.button("Generate Post"):
    post_config = PostConfig(
        description=description,
        occasion=occasion,
        user_image_path=user_image_path
    )

    with st.spinner("Generating your post with a stylized layout..."):
        final_image = generate_post_image(brand_config, post_config)
        st.image(final_image, caption="Your stylized social media post")

        # Provide a download button
        buf = BytesIO()
        final_image.convert("RGB").save(buf, format="JPEG")
        byte_im = buf.getvalue()
        st.download_button(label="Download Image", data=byte_im, file_name="generated_post.jpg", mime="image/jpeg")

    # Clean up temporary files
    if user_image_path and os.path.exists(user_image_path):
        os.remove(user_image_path)
    if brand_logo_path and os.path.exists(brand_logo_path):
        os.remove(brand_logo_path)
