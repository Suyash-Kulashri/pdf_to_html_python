import fitz  # PyMuPDF
import os
import pymupdf4llm
import pathlib
import re
from markdown import markdown

def extract_images(pdf_path, output_folder):
    """
    Extract images from a PDF and save them to the output folder.
    """
    try:
        os.makedirs(output_folder, exist_ok=True)
        pdf_document = fitz.open(pdf_path)
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            image_list = page.get_images(full=True)
            
            for image_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    image_filename = f"image_{page_num + 1}_{image_index + 1}.{image_ext}"
                    image_path = os.path.join(output_folder, image_filename)
                    
                    with open(image_path, "wb") as image_file:
                        image_file.write(image_bytes)
                except Exception as e:
                    print(f"Error extracting image {image_index + 1} on page {page_num + 1}: {e}")
        
        pdf_document.close()
    except Exception as e:
        print(f"Error processing PDF {pdf_path}: {e}")
        raise

def replace_images_with_placeholders(pdf_path, output_pdf_path, image_positions):
    """
    Replace images in the PDF with text placeholders.
    """
    try:
        pdf_document = fitz.open(pdf_path)
        
        for page_number, images in image_positions.items():
            try:
                page = pdf_document[page_number]
                images.sort(key=lambda x: (x[0].y0, x[0].x0))
                
                for rect, image_filename in images:
                    placeholder_text = f"[{image_filename}]"
                    page.insert_textbox(
                        rect,
                        placeholder_text,
                        fontsize=12,
                        color=(0, 0, 0),
                        align=0
                    )
            except Exception as e:
                print(f"Error processing page {page_number}: {e}")
        
        pdf_document.save(output_pdf_path, garbage=4, deflate=True)
        pdf_document.close()
    except Exception as e:
        print(f"Error saving modified PDF {output_pdf_path}: {e}")
        raise

def convert_pdf_to_markdown(pdf_path, image_folder):
    """
    Convert PDF to Markdown with image references.
    """
    try:
        output_markdown_path = "output.md"
        # Convert PDF to Markdown and get the content as a string
        markdown_content = pymupdf4llm.to_markdown(
            pdf_path,
            write_images=True,
            image_path=image_folder
        )
        # Write the Markdown content to a file
        with open(output_markdown_path, "w", encoding="utf-8") as md_file:
            md_file.write(markdown_content)
        return output_markdown_path
    except Exception as e:
        print(f"Error converting PDF to Markdown: {e}")
        raise

def convert_into_markdownimages(markdown_path, output_folder):
    """
    Replace image placeholders in Markdown with proper image Markdown syntax.
    """
    try:
        with open(markdown_path, "r", encoding="utf-8") as md_file:
            lines = md_file.readlines()

        image_pattern = re.compile(r'\[([^\]]+\.(?:png|jpg|jpeg|gif))\]')
        new_lines = []

        for line in lines:
            matches = image_pattern.findall(line)
            if matches:
                for match in matches:
                    image_filename = match
                    image_path = os.path.join(output_folder, image_filename)
                    if os.path.exists(image_path):
                        image_markdown = f"![{image_filename}]({image_path})"
                        line = line.replace(f'[{image_filename}]', image_markdown)
                    else:
                        print(f"Warning: Image {image_path} not found.")
            new_lines.append(line)

        with open(markdown_path, "w", encoding="utf-8") as md_file:
            md_file.writelines(new_lines)
    except Exception as e:
        print(f"Error processing Markdown file {markdown_path}: {e}")
        raise

def convert_markdown_to_html(markdown_path, html_output_path):
    """
    Convert Markdown file to HTML with proper HTML structure.
    """
    try:
        with open(markdown_path, "r", encoding="utf-8", errors="ignore") as md_file:
            markdown_content = md_file.read()
        
        html_content = markdown(markdown_content)
        
        # Wrap the HTML content in proper HTML structure
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF to HTML Conversion</title>
</head>
<body>
    {html_content}
</body>
</html>"""
        
        with open(html_output_path, "w", encoding="utf-8") as html_file:
            html_file.write(html_template)
    except Exception as e:
        print(f"Error converting Markdown to HTML: {e}")
        raise

# Example usage
if __name__ == "__main__":
    pdf_path = "../ENG-LCM300-235-02-11-06-24 (Copy).pdf"
    image_folder = "images"
    output_pdf_path = "modified.pdf"
    html_output_path = "output.html"
    
    image_positions = {
        0: [(fitz.Rect(100, 100, 200, 200), "image_1_1.png")]
    }
    
    try:
        extract_images(pdf_path, image_folder)
        replace_images_with_placeholders(pdf_path, output_pdf_path, image_positions)
        markdown_path = convert_pdf_to_markdown(pdf_path, image_folder)
        convert_into_markdownimages(markdown_path, image_folder)
        convert_markdown_to_html(markdown_path, html_output_path)
        print("Conversion completed successfully.")
    except Exception as e:
        print(f"Pipeline failed: {e}")