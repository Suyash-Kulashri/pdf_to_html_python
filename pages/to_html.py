import streamlit as st
import os
import pdf2image
import img2pdf
import base64
from datetime import datetime
from pathlib import Path
import fitz  # PyMuPDF

# Create html folder if it doesn't exist
Path("html").mkdir(exist_ok=True)

def pdf_to_html(pdf_path):
    # Convert PDF to images
    images = pdf2image.convert_from_path(pdf_path)
    
    # Start HTML content
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF to HTML Conversion</title>
        <style>
            body { font-family: Arial, sans-serif; }
            .page { margin: 20px; padding: 20px; border: 1px solid #ccc; }
            img { max-width: 100%; height: auto; }
        </style>
    </head>
    <body>
    """
    
    # Convert each page image to base64 and add to HTML
    for i, image in enumerate(images):
        # Save image temporarily
        temp_img_path = f"temp_page_{i}.png"
        image.save(temp_img_path, "PNG")
        
        # Convert image to base64
        with open(temp_img_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode()
        
        # Add image to HTML
        html_content += f'<div class="page"><h2>Page {i+1}</h2><img src="data:image/png;base64,{img_data}"/></div>'
        
        # Clean up temporary image
        os.remove(temp_img_path)
    
    html_content += """
    </body>
    </html>
    """
    
    return html_content

def main():
    st.title("PDF to HTML Converter")
    
    # File uploader
    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    
    if uploaded_file is not None:
        # Save uploaded PDF temporarily
        temp_pdf_path = "temp.pdf"
        with open(temp_pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            # Convert PDF to HTML
            html_content = pdf_to_html(temp_pdf_path)
            
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"html/output_{timestamp}.html"
            
            # Save HTML file
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Provide download button
            with open(output_filename, "rb") as file:
                st.download_button(
                    label="Download HTML",
                    data=file,
                    file_name=output_filename,
                    mime="text/html"
                )
            
            st.success(f"HTML file generated and saved to {output_filename}")
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
        
        finally:
            # Clean up temporary PDF file
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

if __name__ == "__main__":
    main()