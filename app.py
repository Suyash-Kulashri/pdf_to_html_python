import streamlit as st
import pdf2image
import pdfminer
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams, LTTextBox, LTFigure
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
import os
import base64
from PIL import Image
import io
import openai
import uuid
# load environment variables if needed
from dotenv import load_dotenv
load_dotenv()

# Set up Open AI API key
openai.api_key = os.getenv("OPENAI_API_KEY") or st.text_input("Enter your Open AI API key", type="password")

# Function to extract text and layout from PDF
def extract_text_and_layout(pdf_path):
    text = extract_text(pdf_path)
    resource_manager = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(resource_manager, laparams=laparams)
    interpreter = PDFPageInterpreter(resource_manager, device)
    layout_info = []

    with open(pdf_path, 'rb') as fp:
        for page in PDFPage.get_pages(fp):
            interpreter.process_page(page)
            layout = device.get_result()
            for element in layout:
                if isinstance(element, LTTextBox):
                    layout_info.append({
                        'type': 'text',
                        'content': element.get_text(),
                        'bbox': element.bbox,  # (x0, y0, x1, y1)
                        'font_size': element.height  # Approximate font size
                    })
                elif isinstance(element, LTFigure):
                    layout_info.append({
                        'type': 'image',
                        'bbox': element.bbox
                    })
    return text, layout_info

# Function to extract images from PDF
def extract_images(pdf_path, output_dir):
    images = pdf2image.convert_from_path(pdf_path)
    image_paths = []
    for i, image in enumerate(images):
        image_path = os.path.join(output_dir, f'image_{i}.png')
        image.save(image_path, 'PNG')
        image_paths.append(image_path)
    return image_paths

# Function to structure text using Open AI
def structure_text_with_openai(text):
    if not openai.api_key:
        return text, []  # Fallback if no API key
    prompt = f"""
    You are an expert in HTML structuring. Convert the following raw text into structured HTML with appropriate tags (title, h1, h2, h3, p, etc.) based on context and formatting cues. Preserve the content exactly as provided. Return only the HTML content within the body tag, and list the used tags separately.

    Text:
    {text}

    Output format:
    ```html
    <!-- HTML content here -->
    ```
    Used tags: [list of tags]
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    response_text = response.choices[0].message.content
    html_content = response_text.split('```html\n')[1].split('\n```')[0]
    used_tags = response_text.split('Used tags: ')[1].strip('[]').split(', ')
    return html_content, used_tags

# Function to generate CSS mimicking PDF
def generate_css():
    return """
    body {
        font-family: 'Times New Roman', Times, serif;
        margin: 1in;
        width: 8.5in; /* A4 width */
        line-height: 1.6;
    }
    h1 {
        font-size: 24pt;
        font-weight: bold;
        margin-bottom: 0.5em;
    }
    h2 {
        font-size: 18pt;
        font-weight: bold;
        margin-bottom: 0.4em;
    }
    h3 {
        font-size: 14pt;
        font-weight: bold;
        margin-bottom: 0.3em;
    }
    p {
        font-size: 12pt;
        margin-bottom: 1em;
    }
    img {
        max-width: 100%;
        height: auto;
        margin: 0.5em 0;
    }
    """

# Function to generate HTML with images
def generate_html(html_content, image_paths, layout_info, output_dir):
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Converted PDF</title>
        <style>
        {generate_css()}
        </style>
    </head>
    <body>
    {html_content}
    """
    # Insert images based on layout information
    for i, info in enumerate(layout_info):
        if info['type'] == 'image' and i < len(image_paths):
            img_tag = f'<img src="{image_paths[i]}" style="position: relative; left: {info["bbox"][0]}px; top: {info["bbox"][1]}px;">'
            html += img_tag
    html += """
    </body>
    </html>
    """
    return html

# Streamlit app
st.title("PDF to HTML Converter")
uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

if uploaded_file:
    # Save uploaded PDF
    pdf_path = "temp.pdf"
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Create output directory for images
    output_dir = "images"
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract text and images
    text, layout_info = extract_text_and_layout(pdf_path)
    image_paths = extract_images(pdf_path, output_dir)
    
    # Structure text using Open AI
    html_content, used_tags = structure_text_with_openai(text)
    
    # Generate HTML
    html_output = generate_html(html_content, image_paths, layout_info, output_dir)
    
    # Save HTML and images
    html_path = "output.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_output)
    
    # Save images in a zip file
    import zipfile
    zip_path = "output.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(html_path)
        for image_path in image_paths:
            zipf.write(image_path)
    
    # Display HTML and download link
    st.write("### Generated HTML Preview")
    st.markdown(html_output, unsafe_allow_html=True)
    with open(zip_path, "rb") as f:
        st.download_button(
            label="Download HTML and Images",
            data=f,
            file_name="output.zip",
            mime="application/zip"
        )
    
    # Clean up
    os.remove(pdf_path)
    for image_path in image_paths:
        os.remove(image_path)
    os.remove(html_path)
    os.remove(zip_path)
    os.rmdir(output_dir)