import streamlit as st
import fitz  # PyMuPDF
import os
from openai import OpenAI
from lxml import html
import re
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
def initialize_openai():
    api_key = os.getenv("OPENAI_API_KEY_NEW")
    if not api_key:
        st.error("Please provide a valid OpenAI API key in the .env file (OPENAI_API_KEY_NEW).")
        return None
    return OpenAI(api_key=api_key)

# Extract PDF details (text, fonts, colors, layout)
def extract_pdf_details(pdf_path):
    try:
        pdf_document = fitz.open(pdf_path)
        details = []
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            page_text = page.get_text("dict")
            blocks = page_text.get("blocks", [])
            
            page_info = {
                "page_number": page_num + 1,
                "text_blocks": [],
                "fonts": set(),
                "colors": set(),
                "layout": []
            }
            
            for block in blocks:
                if block["type"] == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "")
                            font = span.get("font", "unknown")
                            size = span.get("size", 12)
                            color = span.get("color", 0)
                            # Convert color to hex
                            color_hex = f"#{color:06x}" if isinstance(color, int) else color
                            bbox = span.get("bbox", [0, 0, 0, 0])
                            
                            page_info["text_blocks"].append({
                                "text": text,
                                "font": font,
                                "size": size,
                                "color": color_hex,
                                "position": bbox
                            })
                            page_info["fonts"].add(font)
                            page_info["colors"].add(color_hex)
                            page_info["layout"].append({
                                "text": text,
                                "bbox": bbox
                            })
            details.append(page_info)
        
        pdf_document.close()
        return details
    except Exception as e:
        st.error(f"Error extracting PDF details: {e}")
        return None

# Parse HTML content
def parse_html(html_content):
    try:
        tree = html.fromstring(html_content)
        elements = []
        for elem in tree.iter():
            if elem.text:
                elements.append({
                    "tag": elem.tag,
                    "text": elem.text.strip(),
                    "attributes": elem.attrib
                })
        return elements
    except Exception as e:
        st.error(f"Error parsing HTML: {e}")
        return None

# Use LLM to generate CSS and modify HTML
def generate_css_and_modify_html(pdf_details, html_content, client):
    try:
        # Prepare prompt for LLM
        prompt = f"""
You are an expert in web design and CSS. I have extracted details from a PDF and an HTML file. Your task is to generate CSS styles to make the HTML visually match the PDF as closely as possible, including fonts, colors, text sizes, and layout. The modified HTML should include the CSS inline or in a <style> tag.

### PDF Details:
{pdf_details}

### Original HTML:
{html_content}

### Instructions:
1. Analyze the PDF details to understand fonts, colors, text sizes, and layout (positions in bbox: [x0, y0, x1, y1]).
2. Parse the HTML to identify its structure and content.
3. Generate CSS to match the PDF's appearance, including:
   - Font families (use web-safe fonts or closest matches to PDF fonts).
   - Text sizes (convert PDF points to CSS pixels, 1pt ≈ 1.333px).
   - Colors (use hex codes from PDF).
   - Positioning (use absolute or relative positioning to mimic PDF layout).
4. Embed the CSS in the HTML using a <style> tag or inline styles.
5. Ensure the HTML structure remains intact, only add CSS to match the PDF's appearance.
6. If exact font matches are unavailable, suggest the closest web-safe font (e.g., Arial for Helvetica).
7. Return the complete modified HTML with CSS included.

### Output:
Provide the complete modified HTML content with embedded CSS.
"""
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a web design expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.3
        )
        modified_html = response.choices[0].message.content.strip()
        return modified_html
    except Exception as e:
        st.error(f"Error generating CSS with LLM: {e}")
        return None

# Convert file to base64 for download
def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">Download {file_label}</a>'
    return href

# Streamlit app
def main():
    st.title("PDF-to-HTML Style Matcher")
    st.write("Upload a PDF and HTML file, then click 'Process' to modify the HTML with CSS to match the PDF's appearance.")

    # Initialize OpenAI client
    client = initialize_openai()
    if not client:
        return

    # File uploaders
    pdf_file = st.file_uploader("Upload PDF file", type=["pdf"])
    html_file = st.file_uploader("Upload HTML file", type=["html", "htm"])

    # Process button
    if st.button("Process"):
        if pdf_file and html_file:
            # Save uploaded files temporarily
            pdf_path = "temp.pdf"
            html_path = "temp.html"
            output_html_path = "modified.html"

            try:
                with open(pdf_path, "wb") as f:
                    f.write(pdf_file.read())
                with open(html_path, "wb") as f:
                    f.write(html_file.read())

                # Extract PDF details
                pdf_details = extract_pdf_details(pdf_path)
                if not pdf_details:
                    return

                # Read HTML content
                with open(html_path, "r", encoding="utf-8") as f:
                    html_content = f.read()

                # Parse HTML
                html_elements = parse_html(html_content)
                if not html_elements:
                    return

                # Generate CSS and modify HTML using LLM
                modified_html = generate_css_and_modify_html(pdf_details, html_content, client)
                if not modified_html:
                    return

                # Save modified HTML
                with open(output_html_path, "w", encoding="utf-8") as f:
                    f.write(modified_html)

                # Display modified HTML
                st.subheader("Modified HTML Preview")
                st.markdown(modified_html, unsafe_allow_html=True)

                # Provide download link
                st.subheader("Download Modified HTML")
                st.markdown(get_binary_file_downloader_html(output_html_path, "Modified HTML"), unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Error processing files: {e}")
            finally:
                # Clean up temporary files
                for path in [pdf_path, html_path, output_html_path]:
                    if os.path.exists(path):
                        os.remove(path)
        else:
            st.error("Please upload both a PDF and an HTML file before processing.")

if __name__ == "__main__":
    main()
