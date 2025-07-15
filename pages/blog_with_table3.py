import streamlit as st
import tempfile
import fitz  # PyMuPDF
import os
import pathlib
import re
import pymupdf4llm
from markdown import markdown
from bs4 import BeautifulSoup
from io import BytesIO

def extract_images_from_stream(pdf_stream, image_folder):
    os.makedirs(image_folder, exist_ok=True)
    doc = fitz.open(stream=pdf_stream, filetype="pdf")
    for page_num in range(len(doc)):
        page = doc[page_num]
        for img_index, img in enumerate(page.get_images(full=True), start=1):
            xref = img[0]
            base = doc.extract_image(xref)
            ext = base["ext"]
            data = base["image"]
            img_name = f"image_{page_num+1}_{img_index}.{ext}"
            img_path = os.path.join(image_folder, img_name)
            with open(img_path, "wb") as f:
                f.write(data)
    doc.close()

def replace_images_with_placeholders(pdf_stream, modified_pdf_path, image_folder):
    doc = fitz.open(stream=pdf_stream, filetype="pdf")
    img_map = {}
    for page_num in range(len(doc)):
        page = doc[page_num]
        images = page.get_images(full=True)
        for img_index, img in enumerate(images, start=1):
            xref = img[0]
            # PyMuPDF does not provide get_image_bbox; use a default rectangle or skip bounding box
            rect = fitz.Rect(72, 72, 200, 200)  # Example rectangle; adjust as needed
            img_name = f"image_{page_num+1}_{img_index}.{doc.extract_image(xref)['ext']}"
            img_map.setdefault(page_num, []).append((rect, img_name))

    for pnum, items in img_map.items():
        page = doc[pnum]
        for rect, name in items:
            page.insert_textbox(rect, f"[{name}]", fontsize=12, color=(0, 0, 0))

    doc.save(modified_pdf_path)
    doc.close()

def convert_pdf_to_markdown(pdf_path, md_path, image_folder):
    pymupdf4llm.convert(pdf_path, md_path, image_folder=image_folder)
    return md_path

def markdown_to_html(md_path, html_path):
    with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
        md = f.read()
    html = markdown(md, extensions=["tables", "fenced_code"])
    soup = BeautifulSoup(html, "html.parser")
    formatted_html = soup.prettify()
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(formatted_html)
    return formatted_html

def extract_tables_with_placeholders_from_stream(pdf_stream, modified_pdf_path, table_folder):
    doc = fitz.open(stream=pdf_stream, filetype="pdf")
    os.makedirs(table_folder, exist_ok=True)

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("blocks")
        tables_found = 0
        for i, block in enumerate(text):
            x0, y0, x1, y1, content, _, _, _ = block
            if "|" in content or ("----" in content):
                tables_found += 1
                table_name = f"table_{page_num+1}_{tables_found}.csv"
                table_path = os.path.join(table_folder, table_name)
                with open(table_path, "w", encoding="utf-8") as tf:
                    tf.write(content.strip())
                rect = fitz.Rect(x0, y0, x1, y1)
                page.insert_textbox(rect, f"[{table_name}]", fontsize=10, color=(0, 0, 1))

    doc.save(modified_pdf_path)
    doc.close()

def convert_csv_to_html(csv_path):
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            cells = [cell.strip() for cell in line.strip().split("|") if cell.strip()]
            if cells:
                rows.append(cells)

    if not rows:
        return ""

    html = "<table border='1' style='border-collapse: collapse; width: 100%;'>\n"
    for i, row in enumerate(rows):
        tag = "th" if i == 0 else "td"
        html += "  <tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in row) + "</tr>\n"
    html += "</table>"
    return html

def fix_markdown_placeholders(md_path, image_folder, table_folder):
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    img_pat = re.compile(r'\[([^\]]+\.(?:png|jpg|jpeg|gif))\]')
    tbl_pat = re.compile(r'\[([^\]]+\.csv)\]')

    out = []
    for line in lines:
        line = img_pat.sub(lambda m: f"<img src='images/{m.group(1)}' alt='{m.group(1)}' style='max-width: 100%; height: auto;'>", line)
        line = tbl_pat.sub(lambda m: convert_csv_to_html(os.path.join(table_folder, m.group(1))), line)
        out.append(line)

    with open(md_path, "w", encoding="utf-8") as f:
        f.writelines(out)

# Streamlit Interface
st.set_page_config(page_title="PDF to Styled HTML", layout="wide")
st.title("📄➡️🌐 Convert PDF to Styled HTML (Images + Tables)")

pdf_file = st.file_uploader("Upload your PDF file", type=["pdf"])

if pdf_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_bytes = pdf_file.read()
        pdf_stream = BytesIO(pdf_bytes)

        image_dir = os.path.join(tmpdir, "images")
        table_dir = os.path.join(tmpdir, "tables")
        modified_pdf = os.path.join(tmpdir, "mod.pdf")
        markdown_path = os.path.join(tmpdir, "output.md")
        html_path = os.path.join(tmpdir, "output.html")

        with st.spinner("Extracting images..."):
            extract_images_from_stream(pdf_bytes, image_dir)

        with st.spinner("Replacing images with placeholders..."):
            replace_images_with_placeholders(pdf_stream, modified_pdf, image_dir)

        with st.spinner("Extracting tables and replacing with placeholders..."):
            extract_tables_with_placeholders_from_stream(BytesIO(pdf_bytes), modified_pdf, table_dir)

        with st.spinner("Converting to markdown..."):
            convert_pdf_to_markdown(modified_pdf, markdown_path, image_dir)

        with st.spinner("Fixing image and table placeholders..."):
            fix_markdown_placeholders(markdown_path, image_dir, table_dir)

        with st.spinner("Converting markdown to HTML..."):
            final_html = markdown_to_html(markdown_path, html_path)

        st.success("✅ Conversion complete!")
        st.subheader("🔍 HTML Preview")
        st.components.v1.html(final_html, height=600, scrolling=True)

        st.download_button("⬇️ Download HTML", final_html, file_name="converted.html", mime="text/html")
