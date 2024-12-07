import streamlit as st
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import requests
import openai
from PIL.Image import Resampling

st.set_page_config(page_title="Social Media Post Generator", layout="wide")

# Predefined sizes for social media posts (width, height)
SOCIAL_SIZES = {
    "Post Size (1080x1080)": (1080, 1080),
    "Landscape Size (1200x628)": (1200, 628),
    "Story Size (1080x1920)": (1080, 1920),
    "Portrait Size (1080x1350)": (1080, 1350),
    "Pin (1000x1500)": (1000, 1500)
}

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

def generate_prompt_with_openai(api_key: str, description: str, occasion: str) -> str:
    """
    Use OpenAI's ChatCompletion to generate a more creative and descriptive prompt
    based on user input. This prompt will then be used to generate the DALL·E image.
    """
    openai.api_key = api_key
    messages = [
        {"role": "system", "content": "You are a creative marketing assistant that crafts imaginative and visual prompts for AI image generation."},
        {"role": "user", "content": f"Create a highly visual, detailed, and aesthetically appealing prompt for an AI image generation model. The user wants a social media post. Description: '{description}' Occasion: '{occasion}'. Focus on making the image attractive and unique."}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.8
    )
    prompt = response.choices[0].message.content.strip()
    return prompt

def generate_ai_image(api_key: str, prompt: str):
    """
    Use OpenAI's Image.create to generate an image from a prompt.
    DALL·E images are by default 1024x1024. We will have to resize/crop to desired aspect ratio later.
    """
    openai.api_key = api_key
    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response['data'][0]['url']
    # Download the image
    resp = requests.get(image_url)
    img = Image.open(BytesIO(resp.content)).convert("RGBA")
    return img

def fit_image_to_size(img: Image.Image, target_size: tuple) -> Image.Image:
    """
    Resize and possibly pad the generated image to match the target_size exactly,
    without excessive distortion.
    """
    tw, th = target_size
    # Calculate aspect ratios
    w, h = img.size
    img_aspect = w / h
    target_aspect = tw / th

    # If image aspect > target aspect, match width and crop/pad height
    # Otherwise, match height and crop/pad width
    if img_aspect > target_aspect:
        # Image is wider than target. Fit width, crop/pad height
        new_width = tw
        new_height = int(tw / img_aspect)
        img = img.resize((new_width, new_height), Resampling.LANCZOS)
        # Pad if needed
        if new_height < th:
            padding = (0, (th - new_height)//2, 0, (th - new_height)-(th - new_height)//2)
            img = ImageOps.expand(img, padding, fill=(255,255,255,0))
        elif new_height > th:
            # Crop vertical center
            top = (new_height - th)//2
            img = img.crop((0, top, tw, top+th))
    else:
        # Image is taller. Fit height, crop/pad width
        new_height = th
        new_width = int(th * img_aspect)
        img = img.resize((new_width, new_height), Resampling.LANCZOS)
        if new_width < tw:
            padding = ((tw - new_width)//2, 0, (tw - new_width)-(tw - new_width)//2, 0)
            img = ImageOps.expand(img, padding, fill=(255,255,255,0))
        elif new_width > tw:
            # Crop horizontal center
            left = (new_width - tw)//2
            img = img.crop((left, 0, left+tw, th))

    return img

def add_brand_logo(base_img: Image.Image, logo_path: str):
    """
    Add the brand logo in the top-left corner with a small margin.
    """
    logo_img = load_image(logo_path)
    # Resize logo to a smaller portion of image height
    w, h = base_img.size
    logo_height = int(h * 0.15)
    aspect = logo_img.width / logo_img.height
    logo_width = int(logo_height * aspect)
    logo_img = logo_img.resize((logo_width, logo_height), Resampling.LANCZOS)

    # Paste with alpha
    base_img.alpha_composite(logo_img, (30,30))

def add_text_overlays(base_img: Image.Image, brand_config: BrandConfig, description: str, occasion: str):
    """
    Add text overlays (description and occasion) at the bottom area of the image.
    We'll overlay a semi-transparent box for text visibility.
    """
    draw = ImageDraw.Draw(base_img)
    try:
        primary_font = ImageFont.truetype(brand_config.primary_font_path, size=60)
    except:
        primary_font = ImageFont.load_default()

    try:
        secondary_font = ImageFont.truetype(brand_config.secondary_font_path, size=40)
    except:
        secondary_font = ImageFont.load_default()

    # Text color (white)
    text_color = (255,255,255,255)
    w, h = base_img.size

    # Prepare text
    top_text = description
    bottom_text = occasion if occasion else ""

    # Measure text
    def text_bbox(txt, font):
        return draw.textbbox((0,0), txt, font=font)

    # We'll place texts at bottom area
    padding = 50
    total_area_height = 250
    overlay = Image.new("RGBA", (w, total_area_height), (0,0,0,100))
    base_img.alpha_composite(overlay, (0, h - total_area_height - padding))

    # Draw top text centered
    top_box = text_bbox(top_text, primary_font)
    tw = top_box[2]-top_box[0]
    th = top_box[3]-top_box[1]

    tx = (w - tw)//2
    ty = h - total_area_height - padding + (total_area_height//2 - th) - 20
    draw.text((tx, ty), top_text, font=primary_font, fill=text_color)

    if bottom_text:
        bottom_box = text_bbox(bottom_text, secondary_font)
        btw = bottom_box[2]-bottom_box[0]
        bth = bottom_box[3]-bottom_box[1]
        bx = (w - btw)//2
        by = ty + th + 20
        draw.text((bx, by), bottom_text, font=secondary_font, fill=text_color)

def generate_post_image(brand_config: BrandConfig, post_config: PostConfig, openai_key: str, no_user_image: bool) -> Image.Image:
    if no_user_image:
        # Generate prompt
        prompt = generate_prompt_with_openai(openai_key, post_config.description, post_config.occasion)
        # Generate AI image
        ai_img = generate_ai_image(openai_key, prompt)
        # Fit to desired size
        base_img = fit_image_to_size(ai_img, post_config.desired_output_size)
    else:
        # Use user image directly
        base_img = load_image(post_config.user_image_path)
        base_img = base_img.resize(post_config.desired_output_size, Resampling.LANCZOS)

    # Add brand logo if provided
    if brand_config.brand_logo_path:
        add_brand_logo(base_img, brand_config.brand_logo_path)

    # Add text overlays
    add_text_overlays(base_img, brand_config, post_config.description, post_config.occasion)

    return base_img

# ---------- STREAMLIT UI ---------- #
st.title("Generate Social Creatives")

st.write("Generate engagement-focused social media post creatives using AI.")

openai_key = st.text_input("OpenAI API Key:", type="password", help="Enter your OpenAI API key to enable AI generation.")
if not openai_key:
    st.warning("Please provide your OpenAI API key to proceed.")
    st.stop()

# Select creative size
st.subheader("Select Creative Size")
size_choice = st.radio("Social Media Sizes", list(SOCIAL_SIZES.keys()), index=0)
desired_size = SOCIAL_SIZES[size_choice]

# Brand Configuration
st.subheader("Brand Configuration")
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

# Post Configuration
st.subheader("Post Configuration")
description = st.text_area("Post Description:", "Craving Authentic Indian Flavours?")
occasion = st.text_input("Occasion (optional):", "Delivering straight to your doorstep")

user_image_option = st.radio("Choose Background Image:", ("Use AI Generated Image", "Upload My Own"))
user_image_path = None
no_user_image = True
if user_image_option == "Upload My Own":
    uploaded_image = st.file_uploader("Upload background image", type=["png", "jpg", "jpeg"])
    if uploaded_image:
        user_image_path = f"temp_uploaded_image.{uploaded_image.name.split('.')[-1]}"
        with open(user_image_path, "wb") as f:
            f.write(uploaded_image.read())
        no_user_image = False

if st.button("Generate Post"):
    post_config = PostConfig(
        description=description,
        occasion=occasion,
        user_image_path=user_image_path,
        desired_output_size=desired_size
    )

    with st.spinner("Generating your unique, high-quality AI-powered social media post..."):
        final_image = generate_post_image(brand_config, post_config, openai_key, no_user_image)
        st.image(final_image, caption="Your AI-Generated Social Media Post")

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
