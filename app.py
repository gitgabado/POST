import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os

# Title and description
st.title("Social Media Post Generator")
st.markdown(
    "Generate visually appealing social media posts using AI for text and image generation."
)

# User inputs
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
brand_logo = st.sidebar.file_uploader("Upload Brand Logo (PNG)", type=["png"])
primary_color = st.sidebar.color_picker("Primary Color")
secondary_color = st.sidebar.color_picker("Secondary Color")


font_path = st.sidebar.text_input("Font Path (optional, leave blank for default font)", "")
post_size = st.sidebar.selectbox(
    "Select Post Size",
    ["1080x1080", "1200x628", "1080x1920"],
    index=0,
)

background_image = st.sidebar.file_uploader(
    "Upload Background Image (optional)", type=["png", "jpg", "jpeg"]
)

post_description = st.text_area("Post Description", "Enter the content of the post here.")
occession = st.text_input("Occasion (optional)")

# Post size mapping
size_mapping = {
    "1080x1080": (1080, 1080),
    "1200x628": (1200, 628),
    "1080x1920": (1080, 1920),
}
selected_size = size_mapping[post_size]

# Generate refined prompt
if st.button("Generate Post"):
    if not api_key:
        st.error("Please provide your OpenAI API key.")
    else:
        headers = {"Authorization": f"Bearer {api_key}"}

        # Refine the prompt
        prompt = f"Create a social media post for the following: {post_description}"
        if occession:
            prompt += f". Occasion: {occession}"

        try:
            completion_response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json={
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            completion_response.raise_for_status()
            refined_prompt = completion_response.json()["choices"][0]["message"]["content"]
            st.success("Refined prompt generated successfully.")
        except Exception as e:
            st.error(f"Error generating text: {str(e)}")
            refined_prompt = prompt

        # Generate background image if not uploaded
        if not background_image:
            try:
                image_response = requests.post(
                    "https://api.openai.com/v1/images/generations",
                    headers=headers,
                    json={"prompt": refined_prompt, "n": 1, "size": "1024x1024"},
                )
                image_response.raise_for_status()
                image_url = image_response.json()["data"][0]["url"]
                response = requests.get(image_url)
                generated_image = Image.open(io.BytesIO(response.content))
                st.success("Background image generated successfully.")
            except Exception as e:
                st.error(f"Error generating image: {str(e)}")
                generated_image = None
        else:
            generated_image = Image.open(background_image)

        # Compose final image
        final_image = Image.new("RGB", selected_size, primary_color)
        if generated_image:
            generated_image = generated_image.resize(selected_size)
            final_image.paste(generated_image)

        draw = ImageDraw.Draw(final_image)

        # Load font
        try:
            font = ImageFont.truetype(font_path, 40) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
            st.warning("Could not load the specified font. Using default font.")

        # Add text overlay
        text_overlay_height = int(selected_size[1] * 0.25)
        overlay = Image.new("RGBA", (selected_size[0], text_overlay_height), (0, 0, 0, 128))
        final_image.paste(overlay, (0, selected_size[1] - text_overlay_height))

        text_position = (
            20,
            selected_size[1] - text_overlay_height + 20,
        )
        draw.text(text_position, f"{post_description}\n{occession}", fill="white", font=font)

        # Add brand logo if provided
        if brand_logo:
            logo = Image.open(brand_logo).convert("RGBA")
            logo_width = int(selected_size[0] * 0.2)
            logo.thumbnail((logo_width, logo_width))
            final_image.paste(logo, (20, 20), logo)

        st.image(final_image, caption="Generated Post")
        # Save final image
        output_buffer = io.BytesIO()
        final_image.save(output_buffer, format="JPEG")
        st.download_button(
            label="Download Image",
            data=output_buffer.getvalue(),
            file_name="social_media_post.jpg",
            mime="image/jpeg",
        )
