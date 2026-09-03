from flask import Flask, render_template, request, jsonify, send_file
import fitz
import os
import io
import re
import time

from PIL import Image
import pytesseract

from deep_translator import GoogleTranslator, MyMemoryTranslator


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

    replacements = {
        "क्ष": "ksh",
        "त्र": "tr",
        "ज्ञ": "gy",
        "श्र": "shr",
        "त्त": "tt",
        "द्ध": "ddh",
        "द्व": "dv",
        "प्र": "pr",
        "क्र": "kr",
        "ग्र": "gr",
        "ब्र": "br",
        "भ्र": "bhr",
        "म्र": "mr",
        "व्र": "vr",
        "स्त्र": "str",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    consonants = {
        "क": "k",
        "ख": "kh",
        "ग": "g",
        "घ": "gh",
        "ङ": "ng",
        "च": "ch",
        "छ": "chh",
        "ज": "j",
        "झ": "jh",
        "ञ": "ny",
        "ट": "t",
        "ठ": "th",
        "ड": "d",
        "ढ": "dh",
        "ण": "n",
        "त": "t",
        "थ": "th",
        "द": "d",
        "ध": "dh",
        "न": "n",
        "प": "p",
        "फ": "ph",
        "ब": "b",
        "भ": "bh",
        "म": "m",
        "य": "y",
        "र": "r",
        "ल": "l",
        "व": "v",
        "श": "sh",
        "ष": "sh",
        "स": "s",
        "ह": "h",
        "ड़": "d",
        "ढ़": "dh",
    }

    vowels = {
        "अ": "a",
        "आ": "aa",
        "इ": "i",
        "ई": "ee",
        "उ": "u",
        "ऊ": "oo",
        "ऋ": "ri",
        "ए": "e",
        "ऐ": "ai",
        "ओ": "o",
        "औ": "au",
    }

    matras = {
        "ा": "aa",
        "ि": "i",
        "ी": "ee",
        "ु": "u",
        "ू": "oo",
        "ृ": "ri",
        "े": "e",
        "ै": "ai",
        "ो": "o",
        "ौ": "au",
    }

    special = {
        "ं": "n",
        "ँ": "n",
        "ः": "h",
        "़": "",
        "।": ".",
        "॥": ".",
        "ऽ": "'",
    }

    digits = {
        "०": "0",
        "१": "1",
        "२": "2",
        "३": "3",
        "४": "4",
        "५": "5",
        "६": "6",
        "७": "7",
        "८": "8",
        "९": "9",
    }

    result = []
    i = 0

    while i < len(text):

        char = text[i]

        if char in consonants:

            base = consonants[char]

            if i + 1 < len(text) and text[i + 1] == "्":
                result.append(base)
                i += 2
                continue

            if i + 1 < len(text) and text[i + 1] in matras:
                result.append(
                    base + matras[text[i + 1]]
                )
                i += 2
                continue

            result.append(base + "a")
            i += 1
            continue

        if char in vowels:
            result.append(vowels[char])
            i += 1
            continue

        if char in special:
            result.append(special[char])
            i += 1
            continue

        if char in digits:
            result.append(digits[char])
            i += 1
            continue

        result.append(char)
        i += 1

    roman = "".join(result)

    roman = re.sub(r"\baaa\b", "aa", roman)
    roman = re.sub(r"\s+", " ", roman)

    corrections = {
        "mai": "main",
        "hain": "hain",
        "haia": "hai",
        "haii": "hai",
        "mujhe": "mujhe",
        "tumhe": "tumhe",
        "kya": "kya",
        "kyon": "kyun",
        "nahi": "nahi",
        "nahin": "nahi",
    }

    words = roman.split(" ")

    cleaned_words = []

    for word in words:
        cleaned_words.append(
            corrections.get(word.lower(), word)
        )

    return " ".join(cleaned_words)


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
# SPLIT TEXT INTO SMALL CHUNKS
# ==========================================

def split_text(text, max_length=3000):

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

            result = translator.translate(text)

            if result and not is_bad_translation(result):
                return result

        except Exception as error:

            print(
                f"Google translation attempt "
                f"{attempt + 1} failed:",
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

        result = translator.translate(text)

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

    # First try Google
    result = google_translate_chunk(
        text,
        target
    )

    if result:
        return result

    # If Google fails, use MyMemory
    print("Using MyMemory fallback...")

    result = mymemory_translate_chunk(
        text,
        target
    )

    if result:
        return result

    # Do NOT put an API error inside the PDF.
    # Return original text instead.
    print("All translation services failed.")

    return text


# ==========================================
# TRANSLATE TEXT
# ==========================================

def translate_text(text, target_language):

    if not text or not text.strip():
        return ""

    if target_language == "roman_hindi":
        intermediate_language = "hi"

    elif target_language == "hindi":
        intermediate_language = "hi"

    else:
        intermediate_language = "en"

    chunks = split_text(
        text,
        max_length=3000
    )

    translated_parts = []

    for chunk in chunks:

        translated = translate_chunk(
            chunk,
            intermediate_language
        )

        translated_parts.append(
            translated
        )

    result = "\n".join(
        translated_parts
    )

    # Roman Hindi conversion
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

            f"Page {page_number}\n\n"
            f"{title}\n\n"
            f"{translated_text}",

            fontsize=11,

            lineheight=1.5
        )

    pdf.save(output_path)

    pdf.close()


# ==========================================
# PROCESS PDF
# ==========================================

def process_pdf(
    filepath,
    target_language
):

    pdf = fitz.open(filepath)

    results = []

    for page_number, page in enumerate(pdf):

        print(
            f"Processing page {page_number + 1}"
        )

        text = page.get_text("text")

        if text and text.strip():

            translated = translate_text(
                text,
                target_language
            )

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

            image_bytes = pix.tobytes(
                "png"
            )

            image = Image.open(
                io.BytesIO(image_bytes)
            )

            detected_text = extract_image_text(
                image
            )

            translated = translate_text(
                detected_text,
                target_language
            )

            results.append({

                "page": page_number + 1,

                "type": "image / OCR",

                "original": detected_text,

                "translated": translated

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

            "success": False,

            "error":
            "PDF file was not uploaded."

        }), 400

    file = request.files["pdf"]

    if file.filename == "":

        return jsonify({

            "success": False,

            "error":
            "Please select a PDF."

        }), 400

    if not file.filename.lower().endswith(
        ".pdf"
    ):

        return jsonify({

            "success": False,

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

    file.save(filepath)

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
            base_name + suffix
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

            "success": True,

            "filename":
            file.filename,

            "download":
            "/download/" +
            output_filename,

            "pages":
            results

        })

    except Exception as error:

        print(
            "PDF processing error:",
            error
        )

        return jsonify({

            "success": False,

            "error":
            "Unable to process this PDF."

        }), 500

    finally:

        if os.path.exists(filepath):

            os.remove(filepath)


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

    if not os.path.exists(filepath):

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
