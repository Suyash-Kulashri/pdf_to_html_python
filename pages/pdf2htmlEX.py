import streamlit as st
import subprocess
import tempfile
import os

st.set_page_config(page_title="PDF to Styled HTML", layout="wide")
st.title("📄➡️🌐 Convert PDF to Styled HTML (Exact Layout, Images & Tables)")

# Upload PDF file
pdf_file = st.file_uploader("📤 Upload your styled PDF", type=["pdf"])

if pdf_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_pdf_path = os.path.join(tmpdir, "input.pdf")
        output_html_path = os.path.join(tmpdir, "output.html")

        # Save the uploaded file
        with open(input_pdf_path, "wb") as f:
            f.write(pdf_file.read())

        with st.spinner("🔧 Converting PDF to HTML using pdf2htmlEX..."):
            try:
                # Run pdf2htmlEX
                subprocess.run([
                    "pdf2htmlEX",
                    "--embed", "cfijo",        # embed CSS, fonts, images, JS, outlines
                    "--zoom", "1.3",           # zoom factor for better fidelity
                    "--dest-dir", tmpdir,      # output directory
                    input_pdf_path,
                    "output.html"              # output file name
                ], check=True)

                # Load converted HTML
                with open(output_html_path, "r", encoding="utf-8") as f:
                    html = f.read()

                # Display results
                st.success("✅ PDF successfully converted to HTML!")
                st.subheader("🔍 Preview")
                st.components.v1.html(html, height=600, scrolling=True)

                # Download button
                st.download_button("⬇️ Download Styled HTML", html, file_name="styled_output.html", mime="text/html")

            except subprocess.CalledProcessError as e:
                st.error("❌ Error during conversion. Is pdf2htmlEX installed and on your PATH?")
                st.code(str(e))