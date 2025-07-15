import camelot
import fitz  # PyMuPDF
import os
import pymupdf4llm
import re
from markdown import markdown

def extract_images(pdf_path, image_folder):
    """
    Extract images from a PDF and save them to the output folder, returning their positions.
    """
    image_positions = {}
    try:
        os.makedirs(image_folder, exist_ok=True)
        pdf_document = fitz.open(pdf_path)
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            image_list = page.get_images(full=True)
            image_positions[page_num] = []
            
            for image_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    image_filename = f"image_{page_num + 1}_{image_index + 1}.{image_ext}"
                    image_path = os.path.join(image_folder, image_filename)
                    
                    with open(image_path, "wb") as image_file:
                        image_file.write(image_bytes)
                    
                    # Get image rectangle for positioning
                    image_info = page.get_image_info()[image_index]
                    rect = image_info["bbox"]  # (x0, y0, x1, y1)
                    image_positions[page_num].append((fitz.Rect(rect), image_filename))
                except Exception as e:
                    print(f"Error extracting image {image_index + 1} on page {page_num + 1}: {e}")
        
        pdf_document.close()
        return image_positions
    except Exception as e:
        print(f"Error processing PDF {pdf_path} for images: {e}")
        raise

def extract_tables(pdf_path, table_folder):
    """
    Extract tables from a PDF using Camelot and save as HTML, returning their positions.
    """
    table_positions = {}
    try:
        os.makedirs(table_folder, exist_ok=True)
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
        print(f"Total tables extracted: {tables.n}")
        
        if tables.n == 0:
            print("No tables found in the PDF. Try adjusting Camelot settings (e.g., flavor='stream').")
        
        for table_idx, table in enumerate(tables, start=1):
            html_file = os.path.join(table_folder, f"table_{table_idx}_page_{table.page}.html")
            table.to_html(html_file)
            print(f"Saved table {table_idx} to {html_file}")
            
            # Get table bounding box (x0, y0, x1, y1)
            if table.page not in table_positions:
                table_positions[table.page] = []
            table_positions[table.page].append((table._bbox, f"table_{table_idx}_page_{table.page}.html"))
        
        return table_positions
    except Exception as e:
        print(f"Error processing PDF for tables: {e}")
        raise

def replace_images_and_tables_with_placeholders(pdf_path, output_pdf_path, image_positions, table_positions):
    """
    Replace images and tables in the PDF with text placeholders.
    """
    try:
        pdf_document = fitz.open(pdf_path)
        
        for page_number in range(len(pdf_document)):
            page = pdf_document[page_number]
            
            # Replace images
            if page_number in image_positions:
                images = image_positions[page_number]
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
            
            # Replace tables
            if page_number + 1 in table_positions:  # Camelot uses 1-based page numbers
                tables = table_positions[page_number + 1]
                tables.sort(key=lambda x: (x[0][1], x[0][0]))  # Sort by y0, x0
                for bbox, table_filename in tables:
                    placeholder_text = f"[{table_filename}]"
                    rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                    page.insert_textbox(
                        rect,
                        placeholder_text,
                        fontsize=12,
                        color=(0, 0, 0),
                        align=0
                    )
        
        pdf_document.save(output_pdf_path, garbage=4, deflate=True)
        pdf_document.close()
    except Exception as e:
        print(f"Error saving modified PDF {output_pdf_path}: {e}")
        raise

def convert_pdf_to_markdown(pdf_path, image_folder, table_folder):
    """
    Convert PDF to Markdown with image and table placeholders.
    """
    try:
        output_markdown_path = "output.md"
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

def convert_into_markdown_elements(markdown_path, image_folder, table_folder, image_positions, table_positions):
    """
    Replace image and table placeholders in Markdown with proper Markdown syntax and store positioning.
    """
    try:
        with open(markdown_path, "r", encoding="utf-8") as md_file:
            lines = md_file.readlines()

        image_pattern = re.compile(r'\[([^\]]+\.(?:png|jpg|jpeg|gif))\]')
        table_pattern = re.compile(r'\[([^\]]+\.html)\]')
        new_lines = []
        html_elements = []

        for line in lines:
            # Handle images
            image_matches = image_pattern.findall(line)
            for image_filename in image_matches:
                image_path = os.path.join(image_folder, image_filename)
                if os.path.exists(image_path):
                    image_markdown = f"![{image_filename}]({image_path})"
                    line = line.replace(f'[{image_filename}]', image_markdown)
                    # Find position for this image
                    for page, images in image_positions.items():
                        for rect, fname in images:
                            if fname == image_filename:
                                html_elements.append({
                                    'type': 'image',
                                    'content': f'<img src="{image_path}" alt="{image_filename}">',
                                    'rect': rect,
                                    'page': page
                                })
                else:
                    print(f"Warning: Image {image_path} not found.")

            # Handle tables
            table_matches = table_pattern.findall(line)
            for table_filename in table_matches:
                table_path = os.path.join(table_folder, table_filename)
                if os.path.exists(table_path):
                    with open(table_path, "r", encoding="utf-8") as table_file:
                        table_html = table_file.read()
                    line = line.replace(f'[{table_filename}]', f"<!-- TABLE:{table_filename} -->")
                    # Find position for this table
                    for page, tables in table_positions.items():
                        for bbox, fname in tables:
                            if fname == table_filename:
                                html_elements.append({
                                    'type': 'table',
                                    'content': table_html,
                                    'rect': fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3]),
                                    'page': page - 1  # Adjust for 0-based indexing
                                })
                else:
                    print(f"Warning: Table {table_path} not found.")
            
            new_lines.append(line)

        with open(markdown_path, "w", encoding="utf-8") as md_file:
            md_file.writelines(new_lines)
        
        return html_elements
    except Exception as e:
        print(f"Error processing Markdown file {markdown_path}: {e}")
        raise

def save_css_file(css_path):
    """
    Save the CSS file to style the HTML output like a PDF with absolute positioning.
    """
    css_content = """/* Setting up page size and margins to mimic A4 PDF layout */
@page {
    size: A4; /* 210mm x 297mm */
    margin: 2cm;
    margin-inside: 2.5cm;
    margin-outside: 1.5cm;
}

body {
    font-family: "Times New Roman", Times, serif;
    font-size: 12pt;
    line-height: 1.2;
    color: #000000;
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    width: 210mm;
    max-width: 210mm;
    margin-left: auto;
    margin-right: auto;
    background: #ffffff;
}

/* Page container to simulate A4 pages */
.page {
    width: 210mm;
    height: 297mm;
    position: relative;
    margin-bottom: 1cm;
    page-break-after: always;
    background: #ffffff;
    border: 1px solid #e0e0e0; /* Optional for visibility */
}

/* Absolute positioning for elements */
.element {
    position: absolute;
}

/* Style images */
.element img {
    max-width: 100%;
    height: auto;
    display: block;
}

/* Style tables */
.element table {
    width: 100%;
    border-collapse: collapse;
}

.element th, .element td {
    border: 1px solid #000000;
    padding: 0.2cm;
    text-align: left;
}

.element thead {
    display: table-header-group;
}

/* Headings */
h1, h2, h3 {
    font-family: "Helvetica", Arial, sans-serif;
    font-weight: bold;
    margin: 0.5cm 0;
}

h1 { font-size: 16pt; }
h2 { font-size: 14pt; }
h3 { font-size: 12pt; }

/* Paragraphs and lists */
p {
    margin: 0 0 0.5cm 0;
    text-align: justify;
}

ul, ol {
    margin: 0.5cm 0;
    padding-left: 1cm;
}

li {
    margin-bottom: 0.2cm;
}

/* Page break control */
p, li, div {
    orphans: 3;
    widows: 3;
}

/* Page numbers */
@page {
    @bottom-center {
        content: counter(page);
        font-family: "Helvetica", Arial, sans-serif;
        font-size: 10pt;
        color: #000000;
    }
}

@media print {
    body {
        margin: 0;
        width: 210mm;
    }
    .page {
        margin: 0;
        border: none;
    }
}
"""
    try:
        with open(css_path, "w", encoding="utf-8") as css_file:
            css_file.write(css_content)
    except Exception as e:
        print(f"Error saving CSS file {css_path}: {e}")
        raise

def convert_markdown_to_html(markdown_path, html_output_path, html_elements):
    """
    Convert Markdown to HTML, placing images and tables at their exact PDF positions.
    """
    try:
        with open(markdown_path, "r", encoding="utf-8") as md_file:
            markdown_content = md_file.read()
        
        html_content = markdown(markdown_content)
        
        # Create page containers
        max_page = max([elem['page'] for elem in html_elements], default=0) + 1
        pages = [[] for _ in range(max_page)]
        for elem in html_elements:
            pages[elem['page']].append(elem)
        
        # Generate HTML with page structure
        html_pages = []
        for page_num in range(max_page):
            page_content = []
            # Add regular content (split by table placeholders)
            page_html = html_content
            for elem in pages[page_num]:
                if elem['type'] == 'table':
                    page_html = page_html.replace(f'<!-- TABLE:{os.path.basename(elem["content"])} -->', '')
            
            page_content.append(page_html)
            
            # Add positioned elements
            for elem in pages[page_num]:
                rect = elem['rect']
                style = (f'left: {rect.x0}px; top: {rect.y0}px; '
                        f'width: {rect.x1 - rect.x0}px; height: {rect.y1 - rect.y0}px;')
                page_content.append(f'<div class="element" style="{style}">{elem["content"]}</div>')
            
            html_pages.append(f'<div class="page">{"".join(page_content)}</div>')
        
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF to HTML Conversion</title>
    <link rel="stylesheet" href="pdf_styles.css">
</head>
<body>
    {"".join(html_pages)}
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
    
    try:
        image_positions = extract_images(pdf_path, image_folder)
        table_positions = extract_tables(pdf_path, table_folder)
        replace_images_and_tables_with_placeholders(pdf_path, output_pdf_path, image_positions, table_positions)
        markdown_path = convert_pdf_to_markdown(output_pdf_path, image_folder, table_folder)
        html_elements = convert_into_markdown_elements(markdown_path, image_folder, table_folder, image_positions, table_positions)
        save_css_file(css_path)
        convert_markdown_to_html(markdown_path, html_output_path, html_elements)
        print("Conversion completed successfully.")
    except Exception as e:
        print(f"Pipeline failed: {e}")