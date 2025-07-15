import fitz  # PyMuPDF
import os
import pymupdf4llm
import re
from markdown import markdown
import camelot
import pandas as pd

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

def extract_tables(pdf_path, output_folder):
    """
    Extract tables from PDF using Camelot and save as HTML files.
    Returns a dictionary mapping page numbers to list of table HTML strings and their positions.
    """
    try:
        os.makedirs(output_folder, exist_ok=True)
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
        table_positions = {}
        
        print(f"Total tables extracted: {tables.n}")
        
        for table_idx, table in enumerate(tables, start=1):
            page_num = table.page - 1  # Camelot pages are 1-based, convert to 0-based
            # Convert table to HTML
            table_html = table.df.to_html(index=False, header=True, classes="pdf-table")
            # Get table bounding box (approximate position)
            if table._bbox:
                rect = fitz.Rect(table._bbox)
            else:
                rect = fitz.Rect(50, 50, 550, 350)
            table_filename = f"table_{table_idx}_page_{table.page}.html"
            table_path = os.path.join(output_folder, table_filename)
            
            # Save table HTML
            with open(table_path, "w", encoding="utf-8") as table_file:
                table_file.write(table_html)
            
            # Store table info
            if page_num not in table_positions:
                table_positions[page_num] = []
            table_positions[page_num].append((rect, table_filename, table_html))
            
            print(f"Saved table {table_idx} to {table_path}")
        
        return table_positions
    except Exception as e:
        print(f"Error extracting tables from PDF: {e}")
        raise

def replace_tables_with_placeholders(pdf_path, output_pdf_path, table_positions):
    """
    Replace tables in the PDF with text placeholders.
    """
    try:
        pdf_document = fitz.open(pdf_path)
        
        for page_number, tables in table_positions.items():
            try:
                page = pdf_document[page_number]
                tables.sort(key=lambda x: (x[0].y0, x[0].x0))
                
                for rect, table_filename, _ in tables:
                    placeholder_text = f"[TABLE:{table_filename}]"
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

def convert_pdf_to_markdown(pdf_path, image_folder, table_folder, table_positions):
    """
    Convert PDF to Markdown with image and table references.
    """
    try:
        output_markdown_path = "output.md"
        # Convert the modified PDF with placeholders
        markdown_content = pymupdf4llm.to_markdown(
            pdf_path,
            write_images=True,
            image_path=image_folder
        )
        
        with open(output_markdown_path, "w", encoding="utf-8") as md_file:
            md_file.write(markdown_content)
        
        return output_markdown_path
    except Exception as e:
        print(f"Error converting PDF to Markdown: {e}")
        raise

def convert_into_markdownimages_and_tables(markdown_path, image_folder, table_folder):
    """
    Replace image and table placeholders in Markdown with proper syntax (images as Markdown, tables as placeholders for HTML).
    """
    try:
        with open(markdown_path, "r", encoding="utf-8") as md_file:
            lines = md_file.readlines()

        image_pattern = re.compile(r'\[([^\]]+\.(?:png|jpg|jpeg|gif))\]')
        table_pattern = re.compile(r'\[TABLE:([^\]]+\.html)\]')
        new_lines = []

        for line in lines:
            # Replace image placeholders
            image_matches = image_pattern.findall(line)
            for image_filename in image_matches:
                image_path = os.path.join(image_folder, image_filename)
                if os.path.exists(image_path):
                    image_markdown = f"![{image_filename}]({image_path})"
                    line = line.replace(f'[{image_filename}]', image_markdown)
                else:
                    print(f"Warning: Image {image_path} not found.")
            
            # Keep table placeholders as is for HTML replacement
            table_matches = table_pattern.findall(line)
            for table_filename in table_matches:
                table_path = os.path.join(table_folder, table_filename)
                if not os.path.exists(table_path):
                    print(f"Warning: Table {table_path} not found.")
            
            new_lines.append(line)

        with open(markdown_path, "w", encoding="utf-8") as md_file:
            md_file.writelines(new_lines)
    except Exception as e:
        print(f"Error processing Markdown file {markdown_path}: {e}")
        raise

def save_css_file(css_path):
    """
    Save the CSS file to style the HTML output like a PDF.
    """
    css_content = """/* Setting up page size and margins to mimic A4 PDF layout */
@page {
    size: A4; /* 210mm x 297mm */
    margin: 2cm; /* Standard PDF margins */
    margin-inside: 2.5cm; /* Slightly larger for binding, if needed */
    margin-outside: 1.5cm;
}

/* Ensure the body respects the page layout */
body {
    font-family: "Times New Roman", Times, serif; /* Common PDF font */
    font-size: 12pt; /* Standard PDF font size */
    line-height: 1.2; /* Typical line spacing in PDFs */
    color: #000000; /* Black text for print-like appearance */
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    width: 210mm; /* A4 width */
    max-width: 210mm;
    margin-left: auto;
    margin-right: auto;
    background: #ffffff; /* White background like a PDF */
}

/* Style headings to match typical PDF document structure */
h1, h2, h3, h4, h5, h6 {
    font-family: "Helvetica", Arial, sans-serif; /* Common PDF heading font */
    font-weight: bold;
    margin: 0.5cm 0;
    page-break-after: avoid; /* Prevent page breaks after headings */
}

h1 {
    font-size: 16pt;
}

h2 {
    font-size: 14pt;
}

h3 {
    font-size: 12pt;
}

/* Paragraph styling for consistent text flow */
p {
    margin: 0 0 0.5cm 0;
    text-align: justify; /* Common in PDFs for clean text alignment */
}

/* Image styling to ensure proper sizing and placement */
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0.5cm auto; /* Center images with PDF-like spacing */
    page-break-inside: avoid; /* Prevent images from breaking across pages */
}

/* Iframe styling to match PDF appearance */
iframe {
    border: none;
    margin: 0.5cm 0;
    page-break-inside: avoid;
    width: 100%; /* Adjust as needed */
    min-height: 200px; /* Minimum height to ensure visibility */
}

/* Handle lists to match PDF formatting */
ul, ol {
    margin: 0.5cm 0;
    padding-left: 1cm;
}

li {
    margin-bottom: 0.2cm;
}

/* Page break control to avoid widows and orphans */
p, li, div {
    orphans: 3; /* Prevent single lines at the bottom of a page */
    widows: 3; /* Prevent single lines at the top of a page */
}

/* Optional: Add page numbers in the footer */
@page {
    @bottom-center {
        content: counter(page); /* Add page number */
        font-family: "Helvetica", Arial, sans-serif;
        font-size: 10pt;
        color: #000000;
    }
}

/* Print-specific media query to ensure compatibility */
@media print {
    body {
        margin: 0;
        width: 210mm;
    }
    img {
        max-width: 100%;
    }
    iframe {
        max-width: 100%;
        height: auto;
    }
    /* Hide unnecessary elements for printing */
    nav, footer, aside {
        display: none;
    }
}
"""
    try:
        with open(css_path, "w", encoding="utf-8") as css_file:
            css_file.write(css_content)
    except Exception as e:
        print(f"Error saving CSS file {css_path}: {e}")
        raise

def convert_markdown_to_html(markdown_path, html_output_path, table_folder, table_positions):
    """
    Convert Markdown file to HTML with proper HTML structure, CSS, and iframe for tables.
    """
    try:
        with open(markdown_path, "r", encoding="utf-8", errors="ignore") as md_file:
            markdown_content = md_file.read()
        
        html_content = markdown(markdown_content)
        
        # Replace table placeholders with iframe tags
        table_pattern = re.compile(r'\[TABLE:([^\]]+\.html)\]')
        def replace_table(match):
            table_filename = match.group(1)
            table_path = os.path.join(table_folder, table_filename).replace("\\", "/")
            # Use a default size or calculate based on context if needed
            return f'<iframe src="{table_path}" width="100%" height="300px" style="border:none;"></iframe>'
        
        html_content = table_pattern.sub(replace_table, html_content)
        
        # Wrap the HTML content in proper HTML structure with CSS link
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF to HTML Conversion</title>
    <link rel="stylesheet" href="pdf_styles.css">
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
    table_folder = "tables_output"
    output_pdf_path = "modified.pdf"
    html_output_path = "output.html"
    css_path = "pdf_styles.css"
    
    image_positions = {
        0: [(fitz.Rect(100, 100, 200, 200), "image_1_1.png")]
    }
    
    try:
        # Ensure the PDF file exists
        if not os.path.exists(pdf_path):
            print(f"Error: The file {pdf_path} does not exist.")
            exit(1)
        
        extract_images(pdf_path, image_folder)
        replace_images_with_placeholders(pdf_path, output_pdf_path, image_positions)
        table_positions = extract_tables(pdf_path, table_folder)
        replace_tables_with_placeholders(pdf_path, output_pdf_path, table_positions)
        markdown_path = convert_pdf_to_markdown(pdf_path, image_folder, table_folder, table_positions)
        convert_into_markdownimages_and_tables(markdown_path, image_folder, table_folder)
        save_css_file(css_path)
        convert_markdown_to_html(markdown_path, html_output_path, table_folder, table_positions)
        print("Conversion completed successfully.")
    except Exception as e:
        print(f"Pipeline failed: {e}")