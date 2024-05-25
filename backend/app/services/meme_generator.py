import pathlib
import textwrap
from IPython.display import display
from IPython.display import Markdown
import PIL.Image
import urllib.request 
import os
import json
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from fastapi import UploadFile
import tempfile
import shutil
import textwrap

gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("A chave de API GEMINI_API_KEY não foi configurada.")

genai.configure(api_key=gemini_api_key)

model = genai.GenerativeModel("gemini-pro-vision")

def extract_subtitle_from_response(response_text):
    try:
        response_text = response_text.strip('```json').strip('```')
        response_json = json.loads(response_text)
        legenda = response_json.get("legenda", "Legenda não encontrada.")
    except json.JSONDecodeError as e:
        print(response_text)
        legenda = "Legenda não encontrada."
        print(f"Failed to decode JSON from response: {str(e)}")
    return {"legenda": legenda}

def generate_subtitle(file: UploadFile) -> dict:
    image_url = f"https://dummyimage.com/{file.filename}"
    prompt = (
        f"Quero criar um meme. Crie uma legenda engraçada, e nao tão grande, para caber bem na imagem. Por favor, responda no seguinte formato JSON: 'legenda': 'sua_legenda_aqui.'"
    )

    response = model.generate_content(
        ["Quero criar um meme. Crie uma legenda engraçada, e nao tão grande, para caber bem na imagem. Por favor, responda no seguinte formato JSON: 'legenda': 'sua_legenda_aqui.", image_url],
        stream=True
        )
    response.resolve()

    meme_subtitles = extract_subtitle_from_response(response.text)
    
    return meme_subtitles

def apply_subtitles_to_image(file: UploadFile, caption):
    try:
        image = Image.open(file.file)
    except UnidentifiedImageError:
        raise ValueError("O arquivo fornecido não é uma imagem válida.")

    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", size=36)
    
    max_width = image.width - 20 
    char_width, _ = draw.textbbox((0, 0), 'A', font=font)[2:]
    wrapped_caption = textwrap.fill(caption, width=max_width // char_width)
    
    text_size = draw.textbbox((0, 0), wrapped_caption, font=font)
    text_width, text_height = text_size[2], text_size[3]
    width, height = image.size
    x = (width - text_width) / 2
    y = height - text_height - 10 

    outline_range = 2  
    for adj in range(-outline_range, outline_range + 1):
        if adj != 0:
            draw.text((x + adj, y), wrapped_caption, font=font, fill="black")
            draw.text((x, y + adj), wrapped_caption, font=font, fill="black")
            draw.text((x + adj, y + adj), wrapped_caption, font=font, fill="black")
            draw.text((x - adj, y - adj), wrapped_caption, font=font, fill="black")

    draw.text((x, y), wrapped_caption, font=font, fill="white")

    return image

def generate_meme_with_subtitles(file: UploadFile) -> str:
    meme_subtitles = generate_subtitle(file)
    subtitles = meme_subtitles.get("legenda", "Sem legenda")
    image_with_subtitles = apply_subtitles_to_image(file, subtitles)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_image_path = os.path.join(temp_dir, "temp_image_with_caption.png")
        image_with_subtitles.save(temp_image_path, format="PNG")
        meme_png = os.path.join(tempfile.gettempdir(), "temp_image_with_caption.png")
        shutil.move(temp_image_path, meme_png)
    
    return meme_png