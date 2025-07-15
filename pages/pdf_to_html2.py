import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI
from bs4 import BeautifulSoup
import tempfile
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---- Streamlit Page Config ----
st.set_page_config(page_title="PDF Style to HTML", layout="wide")
st.title("📄➡️🌐 Apply PDF Layout & Styling to HTML Using GPT-4o")

# ---- Initialize OpenAI client ----
def initialize_openai():
    api_key = os.getenv("OPENAI_API_KEY_NEW")
    if not api_key:
        st.error("Please provide a valid OpenAI API key in the .env file (OPENAI_API_KEY_NEW).")
        return None
    return OpenAI(api_key=api_key)

# ---- Extract layout summary from PDF ----
def extract_pdf_layout_description(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        layout = []

        for page_num, page in enumerate(doc):
            layout.append(f"--- Page {page_num+1} ---")
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue
                        font = span["font"]
                        size = round(span["size"], 1)
                        bbox = span["bbox"]
                        color = span.get("color", 0)
                        hex_color = f"#{color:06x}" if isinstance(color, int) else color
                        layout.append(f"Text: '{text}' | Font: {font}, Size: {size}pt, Color: {hex_color}, Position: {bbox}")
            for i, img in enumerate(page.get_images(full=True), start=1):
                layout.append(f"Image {i} on page {page_num+1}")
            if "Table" in page.get_text("text"):
                layout.append(f"Detected Table on page {page_num+1}")

        doc.close()
        return "\n".join(layout)
    except Exception as e:
        st.error(f"Error extracting PDF layout: {e}")
        return None

# ---- Call GPT with layout + HTML ----
def call_openai(layout_summary, html_content, client):
    try:
        system_prompt = "You are a professional front-end developer. Convert plain HTML into visually styled HTML based on the layout extracted from a PDF. Reconstruct layout accurately: heading alignment, fonts, image placements, table locations, and spacing."
        user_prompt = f"""
Here is the layout and style extracted from the PDF:

{layout_summary}

Here is the HTML content with the same text but no layout or styling:

```
{html_content}
```

### Instructions:
1. Analyze the PDF layout summary to understand text, fonts, sizes, colors, positions (bbox: [x0, y0, x1, y1]), images, and tables.
2. Rewrite the HTML to match the PDF's layout and design, including:
   - Font families (use web-safe fonts or closest matches, e.g., Arial for Helvetica).
   - Text sizes (convert PDF points to CSS pixels, 1pt ≈ 1.333px).
   - Colors (use hex codes from the PDF).
   - Positioning (use absolute or relative positioning to mimic PDF layout).
   - Image placements (approximate based on page and order).
   - Tables (reconstruct based on detected table information).
   - Spacing and alignment (e.g., margins, padding, text alignment).
3. Embed the CSS in the HTML using a <style> tag or inline styles.
4. Ensure the HTML structure remains intact, only adding CSS to match the PDF's appearance.
5. If exact font matches are unavailable, use the closest web-safe font.
6. Return the full styled HTML file with CSS included.
"""
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error generating styled HTML with OpenAI: {e}")
        return None

# ---- Main Logic ----
def main():
    # Initialize OpenAI client
    client = initialize_openai()
    if not client:
        return

    # File uploaders
    pdf_file = st.file_uploader("📄 Upload PDF file (with styling)", type=["pdf"])
    html_file = st.file_uploader("🌐 Upload HTML file (unstyled, same content)", type=["html", "htm"])

    # Process button
    if st.button("✨ Apply Styling"):
        if pdf_file and html_file:
            # Save uploaded files temporarily
            pdf_path = None
            html_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tf_pdf:
                    tf_pdf.write(pdf_file.read())
                    pdf_path = tf_pdf.name

                with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tf_html:
                    tf_html.write(html_file.read())
                    html_path = tf_html.name

                # Extract HTML content
                with open(html_path, "r", encoding="utf-8") as f:
                    html_content = BeautifulSoup(f.read(), "html.parser").prettify()

                with st.spinner("🔍 Extracting layout from PDF..."):
                    layout_summary = extract_pdf_layout_description(pdf_path)
                    if not layout_summary:
                        return

                st.success("✅ Layout extracted!")
                st.text_area("📐 PDF Layout Summary", layout_summary, height=300)

                with st.spinner("🤖 Applying styling with GPT-4o..."):
                    styled_html = call_openai(layout_summary, html_content, client)
                    if not styled_html:
                        return

                st.success("✅ Styling complete!")

                # Display output
                st.subheader("💡 Styled HTML Preview")
                st.components.v1.html(styled_html, height=600, scrolling=True)

                # Download
                st.download_button(
                    "⬇️ Download Styled HTML",
                    styled_html,
                    file_name="styled_output.html",
                    mime="text/html"
                )

            except Exception as e:
                st.error(f"❌ An error occurred: {e}")
            finally:
                # Clean up temporary files
                for path in [pdf_path, html_path]:
                    if path and os.path.exists(path):
                        os.remove(path)
        else:
            st.error("Please upload both a PDF and an HTML file before processing.")

    # Footer
    st.markdown("---")
    st.caption("Built with ❤️ using OpenAI + Streamlit + PyMuPDF")

if __name__ == "__main__":
    main()