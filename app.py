import streamlit as st
import os
from PIL import Image, ImageDraw, ImageFont
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
    # Placeholder for AI-generated image integration
    # Just create a blank white image with a placeholder text
    img = Image.new("RGBA", size, (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((50,50), f"AI Image: {prompt}", fill=(0,0,0))
    return img

def generate_post_image(brand_config: BrandConfig, post_config: PostConfig) -> Image.Image:
    # Determine which image to use as background
    if post_config.user_image_path:
        base_img = load_image(post_config.user_image_path)
    else:
        prompt = f"{post_config.description} {post_config.occasion or ''}"
        base_img = generate_ai_image(prompt, post_config.desired_output_size)

    base_img = base_img.resize(post_config.desired_output_size, Resampling.LANCZOS)

    # Add the brand logo if provided
    if brand_config.brand_logo_path:
        logo_img = load_image(brand_config.brand_logo_path)
        logo_size = (int(post_config.desired_output_size[0]*0.2), int(post_config.desired_output_size[1]*0.2))
        logo_img = logo_img.resize(logo_size, Resampling.LANCZOS)
        # Place logo at top-right corner with some padding
        base_img.paste(logo_img, (post_config.desired_output_size[0]-logo_size[0]-30, 30), logo_img)

    # Add text overlays
    draw = ImageDraw.Draw(base_img)

    # Load fonts
    try:
        primary_font = ImageFont.truetype(brand_config.primary_font_path, size=60)
    except:
        primary_font = ImageFont.load_default()

    try:
        secondary_font = ImageFont.truetype(brand_config.secondary_font_path, size=30)
    except:
        secondary_font = ImageFont.load_default()

    text_color = brand_config.primary_colors[0] if brand_config.primary_colors else (0,0,0)
    description_text = f"{post_config.description}"
    draw.text((50, post_config.desired_output_size[1]-200), description_text, font=primary_font, fill=text_color)

    # If occasion is provided, add that text
    if post_config.occasion:
        occ_color = brand_config.secondary_colors[0] if brand_config.secondary_colors else (128,128,128)
        occ_text = f"{post_config.occasion}"
        draw.text((50, post_config.desired_output_size[1]-120), occ_text, font=secondary_font, fill=occ_color)

    return base_img

# Streamlit UI
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
description = st.text_area("Post Description:", "Announcing our new product line!")
occasion = st.text_input("Occasion (optional):", "")
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

    with st.spinner("Generating your post..."):
        final_image = generate_post_image(brand_config, post_config)
        st.image(final_image, caption="Your generated social media post")

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
