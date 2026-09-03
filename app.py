from flask import Flask, render_template, request, jsonify, send_file
import fitz
import os
import io
import re
import time

from PIL import Image
import pytesseract

from deep_translator import GoogleTranslator, MyMemoryTranslator
from indic_transliteration import sanscript


app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "translated"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


# ==========================================
# HINDI TO ROMAN HINDI
# ==========================================

def hindi_to_roman(text):

    if not text:
        return ""

    try:

        roman = sanscript.transliterate(
            text,
            sanscript.DEVANAGARI,
            sanscript.ITRANS
        )

        # ITRANS -> simple readable Roman Hindi
        replacements = [
            ("RR^i", "ri"),
            ("R^i", "ri"),
            ("RRi", "ri"),
            ("Ri", "ri"),

            ("ai", "ai"),
            ("au", "au"),

            ("chh", "chh"),
            ("Chh", "chh"),

            ("kh", "kh"),
            ("gh", "gh"),
            ("jh", "jh"),
            ("th", "th"),
            ("dh", "dh"),
            ("ph", "ph"),
            ("bh", "bh"),
            ("sh", "sh"),

            ("~N", "n"),
            ("~n", "n"),
            (".N", "n"),
            (".n", "n"),
            ("M", "n"),

            ("~m", "m"),

            ("GY", "gy"),
            ("JN", "gy"),

            ("Sh", "sh"),
            ("S", "sh"),

            ("T", "t"),
            ("D", "d"),
            ("N", "n"),

            ("^", ""),
            ("'", ""),
        ]

        for old, new in replacements:
            roman = roman.replace(old, new)

        # Remove common ITRANS punctuation
        roman = roman.replace("||", ".")
        roman = roman.replace("|", ".")
        roman = roman.replace("~", "")

        # Spaces clean
        roman = re.sub(
            r"\s+",
            " ",
            roman
        )

        # Natural Roman Hindi corrections
        corrections = {
            "mai": "main",
            "Main": "Main",
            "mein": "mein",

            "haii": "hai",
            "haia": "hai",

            "nahin": "nahi",
            "Nahin": "Nahi",

            "kyon": "kyun",
            "Kyon": "Kyun",

            "tumhe": "tumhein",
            "Tumhe": "Tumhein",

            "mujhe": "mujhe",
            "Mujhe": "Mujhe",
        }

        words = roman.split()

        cleaned = []

        for word in words:

            punctuation = ""

            while word and word[-1] in ".,!?;:":

                punctuation = word[-1] + punctuation
                word = word[:-1]

            if word in corrections:
                word = corrections[word]

            elif word.lower() in corrections:
                replacement = corrections[word.lower()]

                if word and word[0].isupper():
                    replacement = replacement.capitalize()

                word = replacement

            cleaned.append(
                word + punctuation
            )

        roman = " ".join(cleaned)

        return roman.strip()

    except Exception as error:

        print(
            "Roman Hindi conversion error:",
            error
        )

        return text


# ==========================================
# CHECK BAD TRANSLATION RESPONSE
# ==========================================

def is_bad_translation(text):

    if not text:
        return True

    bad_phrases = [
        "error 500",
        "server error",
        "internal server error",
        "please try again later",
        "something went wrong",
        "an error occurred",
        "error occurred",
    ]

    lower_text = text.lower()

    for phrase in bad_phrases:

        if phrase in lower_text:
            return True

    return False


# ==========================================
# SPLIT TEXT
# ==========================================

def split_text(text, max_length=2500):

    chunks = []

    current = ""

    for line in text.splitlines(True):

        if len(current) + len(line) > max_length:

            if current.strip():
                chunks.append(current)

            current = line

        else:

            current += line

    if current.strip():
        chunks.append(current)

    return chunks


# ==========================================
# GOOGLE TRANSLATION
# ==========================================

def google_translate_chunk(text, target):

    for attempt in range(3):

        try:

            translator = GoogleTranslator(
                source="auto",
                target=target
            )

            result = translator.translate(
                text
            )

            if result and not is_bad_translation(result):

                return result

        except Exception as error:

            print(
                "Google translation attempt "
                + str(attempt + 1)
                + " failed:",
                error
            )

        time.sleep(1)

    return None


# ==========================================
# MYMEMORY FALLBACK
# ==========================================

def mymemory_translate_chunk(text, target):

    try:

        translator = MyMemoryTranslator(
            source="auto",
            target=target
        )

        result = translator.translate(
            text
        )

        if result and not is_bad_translation(result):

            return result

    except Exception as error:

        print(
            "MyMemory translation failed:",
            error
        )

    return None


# ==========================================
# TRANSLATE ONE CHUNK
# ==========================================

def translate_chunk(text, target):

    if not text or not text.strip():
        return ""

    # Google
    result = google_translate_chunk(
        text,
        target
    )

    if result:
        return result

    print(
        "Google failed. Using MyMemory..."
    )

    # MyMemory
    result = mymemory_translate_chunk(
        text,
        target
    )

    if result:
        return result

    print(
        "All translation services failed."
    )

    # Never put an error message into PDF
    return text


# ==========================================
# TRANSLATE TEXT
# ==========================================

def translate_text(text, target_language):

    if not text or not text.strip():
        return ""

    # Target language
    if target_language == "roman_hindi":

        target = "hi"

    elif target_language == "hindi":

        target = "hi"

    else:

        target = "en"

    chunks = split_text(
        text,
        max_length=2500
    )

    translated_parts = []

    for chunk in chunks:

        translated = translate_chunk(
            chunk,
            target
        )

        translated_parts.append(
            translated
        )

    result = "\n".join(
        translated_parts
    )

    # Hindi -> Roman Hindi
    if target_language == "roman_hindi":

        result = hindi_to_roman(
            result
        )

    return result


# ==========================================
# OCR
# ==========================================

def extract_image_text(image):

    try:

        text = pytesseract.image_to_string(
            image,
            lang="eng"
        )

        return text

    except Exception as error:

        print(
            "OCR error:",
            error
        )

        return ""


# ==========================================
# CREATE TRANSLATED PDF
# ==========================================

def create_translated_pdf(
    results,
    output_path,
    target_language
):

    pdf = fitz.open()

    if target_language == "english":

        title = "English Translation"

    elif target_language == "hindi":

        title = "Hindi Translation"

    else:

        title = "Roman Hindi Translation"

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

            "Page "
            + str(page_number)
            + "\n\n"
            + title
            + "\n\n"
            + translated_text,

            fontsize=11,

            lineheight=1.5
        )

    pdf.save(
        output_path
    )

    pdf.close()


# ==========================================
# PROCESS PDF
# ==========================================

def process_pdf(
    filepath,
    target_language
):

    pdf = fitz.open(
        filepath
    )

    results = []

    for page_number, page in enumerate(pdf):

        print(
            "Processing page "
            + str(page_number + 1)
        )

        text = page.get_text(
            "text"
        )

        # Selectable text
        if text and text.strip():

            translated = translate_text(
                text,
                target_language
            )

            results.append({

                "page":
                    page_number + 1,

                "type":
                    "text",

                "original":
                    text,

                "translated":
                    translated

            })

        # Scanned PDF
        else:

            pix = page.get_pixmap(
                matrix=fitz.Matrix(
                    2,
                    2
                )
            )

            image_bytes = pix.tobytes(
                "png"
            )

            image = Image.open(
                io.BytesIO(
                    image_bytes
                )
            )

            detected_text = extract_image_text(
                image
            )

            translated = translate_text(
                detected_text,
                target_language
            )

            results.append({

                "page":
                    page_number + 1,

                "type":
                    "image / OCR",

                "original":
                    detected_text,

                "translated":
                    translated

            })

    pdf.close()

    return results


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==========================================
# TRANSLATE PDF
# ==========================================

@app.route(
    "/translate",
    methods=["POST"]
)
def translate_pdf():

    if "pdf" not in request.files:

        return jsonify({

            "success":
                False,

            "error":
                "PDF file was not uploaded."

        }), 400

    file = request.files["pdf"]

    if file.filename == "":

        return jsonify({

            "success":
                False,

            "error":
                "Please select a PDF."

        }), 400

    if not file.filename.lower().endswith(
        ".pdf"
    ):

        return jsonify({

            "success":
                False,

            "error":
                "Only PDF files are supported."

        }), 400

    target_language = request.form.get(
        "target_language",
        "english"
    )

    allowed_languages = [
        "english",
        "hindi",
        "roman_hindi"
    ]

    if target_language not in allowed_languages:

        target_language = "english"

    filepath = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    file.save(
        filepath
    )

    try:

        results = process_pdf(
            filepath,
            target_language
        )

        base_name = os.path.splitext(
            file.filename
        )[0]

        if target_language == "english":

            suffix = "_English.pdf"

        elif target_language == "hindi":

            suffix = "_Hindi.pdf"

        else:

            suffix = "_RomanHindi.pdf"

        output_filename = (
            base_name
            + suffix
        )

        output_path = os.path.join(
            OUTPUT_FOLDER,
            output_filename
        )

        create_translated_pdf(
            results,
            output_path,
            target_language
        )

        return jsonify({

            "success":
                True,

            "filename":
                file.filename,

            "download":
                "/download/"
                + output_filename,

            "pages":
                results

        })

    except Exception as error:

        print(
            "PDF processing error:",
            error
        )

        return jsonify({

            "success":
                False,

            "error":
                "Unable to process this PDF."

        }), 500

    finally:

        if os.path.exists(
            filepath
        ):

            os.remove(
                filepath
            )


# ==========================================
# DOWNLOAD
# ==========================================

@app.route(
    "/download/<filename>"
)
def download_pdf(filename):

    filepath = os.path.join(
        OUTPUT_FOLDER,
        filename
    )

    if not os.path.exists(
        filepath
    ):

        return "File not found", 404

    return send_file(

        filepath,

        as_attachment=True,

        download_name=filename

    )


# ==========================================
# START SERVER
# ==========================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

        )
