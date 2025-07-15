import streamlit as st
import os
import base64
import PyPDF2
from openai import OpenAI
import asyncio
import platform
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Open AI client with API key from environment
openai_api_key = os.getenv("OPENAI_API_KEY_MY")
if not openai_api_key:
    st.error("Open AI API key not found. Please set OPENAI_API_KEY_NEW in your environment.")
else:
    client = OpenAI(api_key=openai_api_key)

# Function to encode PDF images to base64
def encode_pdf_images(pdf_file):
    images = []
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            # Placeholder for image extraction (PyPDF2 doesn't extract images directly)
            images.append("Placeholder: Image extraction not implemented in PyPDF2")
    except Exception as e:
        st.error(f"Error processing PDF images: {e}")
    return images

# Function to extract text from PDF
def extract_pdf_text(pdf_file):
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        st.error(f"Error extracting PDF text: {e}")
    return text

# Function to generate CSS and modified HTML using Open AI
async def generate_css_and_html(html_content, pdf_text, pdf_images):
    if not openai_api_key:
        return "", ""
    prompt = f"""
    You are an expert in web development and document formatting. I have an HTML file and a PDF document. Your task is to generate a CSS file and a modified HTML file that makes the HTML visually match the PDF's layout, typography, and formatting. Below are the inputs:

    **HTML Content:**
    ```html
    {html_content}
    ```

    **PDF Text Content:**
    ```
    {pdf_text}
    ```

    **PDF Images (Base64 or Descriptions):**
    {pdf_images}

    **Instructions:**
    - Analyze the PDF text and HTML content to identify layout, fonts, colors, spacing, and other styling elements.
    - Generate a CSS file that styles the HTML to closely resemble the PDF's appearance.
    - Modify the HTML to ensure proper structure, including tables, sections, and images, to match the PDF.
    - Return the CSS content and modified HTML content in the following format:
      - CSS: Wrapped in ```css\n<css_content>\n```
      - HTML: Wrapped in ```html\n<html_content>\n```
    - Ensure the CSS uses standard web fonts (e.g., Arial) and is compatible with browser rendering.
    - Include page breaks for multi-page PDF replication if applicable.
    - Do not alter image sources; assume they are correctly referenced in the HTML.
    - If specific formatting details are unclear, make reasonable assumptions based on typical datasheet styles.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a web development assistant specializing in CSS and HTML."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000
        )
        response_content = response.choices[0].message.content
        # Extract CSS and HTML from response
        css_start = response_content.find("```css\n") + 7
        css_end = response_content.find("\n```", css_start)
        html_start = response_content.find("```html\n") + 8
        html_end = response_content.find("\n```", html_start)
        css_content = response_content[css_start:css_end] if css_start != 6 and css_end != -1 else ""
        html_content = response_content[html_start:html_end] if html_start != 7 and html_end != -1 else ""
        return css_content, html_content
    except Exception as e:
        st.error(f"Error calling Open AI API: {e}")
        return "", ""

# Streamlit app
async def main():
    st.title("HTML to PDF Formatter")
    st.write("Upload an HTML file and a PDF file to generate CSS and modified HTML that matches the PDF's formatting.")

    # File uploaders
    html_file = st.file_uploader("Upload HTML File", type=["html"])
    pdf_file = st.file_uploader("Upload PDF File", type=["pdf"])

    if html_file and pdf_file:
        # Read HTML content
        html_content = html_file.read().decode("utf-8")
        # Extract PDF text
        pdf_text = extract_pdf_text(pdf_file)
        # Encode PDF images (placeholder for now)
        pdf_images = encode_pdf_images(pdf_file)
        pdf_images_str = "\n".join(pdf_images)

        if st.button("Generate CSS and HTML"):
            with st.spinner("Generating CSS and modified HTML..."):
                css_content, modified_html = await generate_css_and_html(html_content, pdf_text, pdf_images_str)
                
                if css_content and modified_html:
                    # Display generated files
                    st.subheader("Generated CSS")
                    st.code(css_content, language="css")
                    st.subheader("Modified HTML")
                    st.code(modified_html, language="html")

                    # Provide download buttons
                    st.download_button(
                        label="Download CSS File",
                        data=css_content,
                        file_name="pdf_styles.css",
                        mime="text/css"
                    )
                    st.download_button(
                        label="Download Modified HTML File",
                        data=modified_html,
                        file_name="index.html",
                        mime="text/html"
                    )
                else:
                    st.error("Failed to generate CSS or HTML. Please check the inputs and try again.")

# Run the app
if platform.system() == "Emscripten":
    asyncio.run_coroutine_threadsafe(main(), asyncio.get_event_loop())
else:
    if __name__ == "__main__":
        asyncio.run(main())