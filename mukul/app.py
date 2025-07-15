from spire.doc import *
from spire.doc.common import *

# Create a Document instance
document = Document()

# Load a Word document
document.LoadFromFile("ENG-LCM300-235-02-11-06-24.docx")

# Embed css styles
document.HtmlExportOptions.CssStyleSheetFileName = "sample.css"
document.HtmlExportOptions.CssStyleSheetType = CssStyleSheetType.External

# Set whether to embed images
document.HtmlExportOptions.ImageEmbedded = False
document.HtmlExportOptions.ImagesPath = "Images/"

# Set whether to export form fields as plain text
document.HtmlExportOptions.IsTextInputFormFieldAsText = True

# Save the document as an html file
document.SaveToFile("ToHtmlExportOption.html", FileFormat.Html)
document.Close()