from flask import Flask, render_template, request, jsonify, send_file
import fitz
import os
import io

from PIL import Image
import pytesseract
from deep_translator import GoogleTranslator


app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "translated"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


# ==============================
# TRANSLATION
# ==============================

def translate_text(text):

    if not text or not text.strip():
        return ""

    try:
        translator = GoogleTranslator(
            source="auto",
            target="en"
        )

        # Avoid very large translation requests
        chunks = []
        current = ""

        for line in text.splitlines(True):

            if len(current) + len(line) > 4000:

                if current.strip():
                    chunks.append(current)

                current = line

            else:
                current += line

        if current.strip():
            chunks.append(current)

        translated_parts = []

        for chunk in chunks:

            try:
                translated_parts.append(
                    translator.translate(chunk)
                )

            except Exception:
                translated_parts.append(chunk)

        return "\n".join(translated_parts)

    except Exception as error:

        print("Translation error:", error)

        return text


# ==============================
# OCR
# ==============================

def extract_image_text(image):

    try:

        text = pytesseract.image_to_string(
            image,
            lang="eng"
        )

        return text

    except Exception as error:

        print("OCR error:", error)

        return ""


# ==============================
# CREATE TRANSLATED PDF
# ==============================

def create_translated_pdf(results, output_path):

    pdf = fitz.open()

    for result in results:

        page_number = result["page"]
        translated_text = result["translated"]

        page = pdf.new_page()

        page.insert_textbox(
            fitz.Rect(
                50,
                50,
                page.rect.width - 50,
                page.rect.height - 50
            ),
            f"Page {page_number}\n\n{translated_text}",
            fontsize=11,
            lineheight=1.5
        )

    pdf.save(output_path)

    pdf.close()


# ==============================
# PROCESS PDF
# ==============================

def process_pdf(filepath):

    pdf = fitz.open(filepath)

    results = []

    for page_number, page in enumerate(pdf):

        print(
            f"Processing page {page_number + 1}"
        )

        text = page.get_text("text")

        if text and text.strip():

            translated = translate_text(text)

            results.append({

                "page": page_number + 1,
                "type": "text",
                "original": text,
                "translated": translated

            })

        else:

            pix = page.get_pixmap(
                matrix=fitz.Matrix(2, 2)
            )

            image_bytes = pix.tobytes("png")

            image = Image.open(
                io.BytesIO(image_bytes)
            )

            detected_text = extract_image_text(
                image
            )

            translated = translate_text(
                detected_text
            )

            results.append({

                "page": page_number + 1,
                "type": "image / OCR",
                "original": detected_text,
                "translated": translated

            })

    pdf.close()

    return results


# ==============================
# HOME
# ==============================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==============================
# TRANSLATE
# ==============================

@app.route(
    "/translate",
    methods=["POST"]
)
def translate_pdf():

    if "pdf" not in request.files:

        return jsonify({
            "success": False,
            "error": "PDF file was not uploaded."
        }), 400

    file = request.files["pdf"]

    if file.filename == "":

        return jsonify({
            "success": False,
            "error": "Please select a PDF."
        }), 400

    if not file.filename.lower().endswith(".pdf"):

        return jsonify({
            "success": False,
            "error": "Only PDF files are supported."
        }), 400

    filepath = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    file.save(filepath)

    try:

        results = process_pdf(
            filepath
        )

        # Create output filename
        base_name = os.path.splitext(
            file.filename
        )[0]

        output_filename = (
            base_name +
            "_English.pdf"
        )

        output_path = os.path.join(
            OUTPUT_FOLDER,
            output_filename
        )

        create_translated_pdf(
            results,
            output_path
        )

        return jsonify({

            "success": True,

            "filename": file.filename,

            "download": (
                "/download/" +
                output_filename
            ),

            "pages": results

        })

    except Exception as error:

        print(
            "PDF processing error:",
            error
        )

        return jsonify({

            "success": False,

            "error": "Unable to process this PDF."

        }), 500

    finally:

        if os.path.exists(filepath):

            os.remove(filepath)


# ==============================
# DOWNLOAD
# ==============================

@app.route(
    "/download/<filename>"
)
def download_pdf(filename):

    filepath = os.path.join(
        OUTPUT_FOLDER,
        filename
    )

    if not os.path.exists(filepath):

        return "File not found", 404

    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename
    )


# ==============================
# START SERVER
# ==============================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )