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
# HINDI TO NATURAL ROMAN HINDI
# ==========================================

def hindi_to_roman(text):

    if not text:
        return ""

    # This function converts Devanagari Hindi into
    # simple readable Roman Hindi without ITRANS
    # symbols such as A, I, U, ^ etc.

    devanagari_map = {
        "अ": "a", "आ": "aa", "इ": "i", "ई": "ee",
        "उ": "u", "ऊ": "oo", "ऋ": "ri",
        "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",

        "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
        "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
        "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
        "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
        "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
        "य": "y", "र": "r", "ल": "l", "व": "v",
        "श": "sh", "ष": "sh", "स": "s", "ह": "h",

        "ड़": "d", "ढ़": "dh",
        "ज़": "z", "फ़": "f", "क़": "q",
        "ख़": "kh", "ग़": "gh",

        "०": "0", "१": "1", "२": "2", "३": "3",
        "४": "4", "५": "5", "६": "6", "७": "7",
        "८": "8", "९": "9",

        "।": ".",
        "॥": ".",
        "ँ": "n",
        "ं": "n",
        "ः": "h",
    }

    vowel_signs = {
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
        "ॉ": "o",
        "ॅ": "e",
    }

    output = []
    i = 0

    while i < len(text):

        char = text[i]

        # Virama / halant
        if char == "्":
            i += 1
            continue

        # Vowel signs
        if char in vowel_signs:
            output.append(vowel_signs[char])
            i += 1
            continue

        # Nukta
        if char == "़":
            i += 1
            continue

        # Consonant
        if char in devanagari_map:

            roman = devanagari_map[char]

            # Check next character
            if i + 1 < len(text):

                next_char = text[i + 1]

                # If next character is a vowel sign
                if next_char in vowel_signs:
                    output.append(
                        roman + vowel_signs[next_char]
                    )
                    i += 2
                    continue

                # If next character is halant,
                # don't add inherent "a"
                if next_char == "्":
                    output.append(roman)
                    i += 2
                    continue

            # Consonants normally carry "a"
            consonants = {
                "क", "ख", "ग", "घ", "ङ",
                "च", "छ", "ज", "झ", "ञ",
                "ट", "ठ", "ड", "ढ", "ण",
                "त", "थ", "द", "ध", "न",
                "प", "फ", "ब", "भ", "म",
                "य", "र", "ल", "व",
                "श", "ष", "स", "ह",
                "ड़", "ढ़", "ज़", "फ़",
                "क़", "ख़", "ग़"
            }

            if char in consonants:
                output.append(roman + "a")
            else:
                output.append(roman)

            i += 1
            continue

        # Keep Latin letters, numbers and punctuation
        output.append(char)
        i += 1

    roman = "".join(output)

    # ==========================================
    # CLEAN COMMON ROMAN HINDI FORMS
    # ==========================================

    corrections = {
        "vaha": "woh",
        "vah": "woh",

        "yeha": "yeh",
        "yaha": "yahaan",

        "kaha": "kahan",
        "kahana": "kehna",

        "eka": "ek",

        "hara": "har",
        "sabhi": "sab",

        "dina": "din",
        "samaya": "samay",

        "ghara": "ghar",
        "ghare": "ghar",
        "gharo": "gharon",

        "subaha": "subah",
        "jaldii": "jaldi",

        "uthtaa": "uthta",
        "uthataa": "uthta",

        "karataa": "karta",
        "karata": "karta",

        "jaataa": "jaata",
        "jata": "jaata",

        "aataa": "aata",
        "aata": "aata",

        "jaataa": "jaata",

        "apanaa": "apna",
        "apane": "apne",
        "apani": "apni",

        "usakaa": "uska",
        "usake": "uske",
        "usaki": "uski",

        "unake": "unke",
        "unaki": "unki",

        "auraa": "aur",
        "aura": "aur",

        "karyaalaya": "office",
        "kaarya": "kaam",

        "kaama": "kaam",
        "kaamon": "kaamon",

        "shaama": "shaam",
        "raata": "raat",

        "khaanaa": "khaana",
        "khaane": "khaane",

        "puraa": "poora",
        "poori": "poori",

        "karane": "karne",
        "karanaa": "karna",

        "hone": "hone",
        "hote": "hote",

        "mein": "mein",
        "men": "mein",

        "nahina": "nahi",
        "nahin": "nahi",

        "kyona": "kyun",
        "kyon": "kyun",

        "maina": "main",
        "mai": "main",

        "meraa": "mera",
        "meree": "meri",

        "tumhe": "tumhein",
        "tumahen": "tumhein",

        "ham": "hum",

        "baata": "baat",
        "baare": "baare",

        "aaraama": "aaraam",

        "thakaana": "thakan",
        "thakaa": "thaka",

        "mehsoosa": "mehsoos",

        "madada": "madad",
        "karanaa": "karna",

        "leinaa": "lena",
        "lenaa": "lena",

        "saathe": "saath",
        "saatha": "saath",

        "kuchha": "kuchh",

        "shaanta": "shaant",

        "shurua": "shuru",

        "agale": "agle",
    }

    words = roman.split()
    cleaned_words = []

    for word in words:

        if not word:
            continue

        # Separate punctuation
        beginning = ""
        ending = ""

        while word and word[0] in "\"'([{":
            beginning += word[0]
            word = word[1:]

        while word and word[-1] in ".,!?;:)]}\"'":
            ending = word[-1] + ending
            word = word[:-1]

        lower_word = word.lower()

        if lower_word in corrections:

            replacement = corrections[lower_word]

            # Preserve first-letter capitalization
            if word and word[0].isupper():
                replacement = replacement.capitalize()

            word = replacement

        cleaned_words.append(
            beginning + word + ending
        )

    roman = " ".join(cleaned_words)

    # ==========================================
    # PHRASE CORRECTIONS
    # ==========================================

    phrase_corrections = [
        ("ke lie", "ke liye"),
        ("ke liye ghar", "ghar ke liye"),

        ("har subah", "har subah"),
        ("jaldi uthta", "jaldi uthta"),

        ("nashta karata", "nashta karta"),
        ("nashta karta", "nashta karta"),

        ("office ke lie", "office ke liye"),

        ("ghar vapas", "ghar wapas"),
        ("ghara vapas", "ghar wapas"),

        ("agle dina", "agle din"),
        ("agle din", "agle din"),

        ("ek aura", "ek aur"),
        ("ek aur", "ek aur"),

        ("vyasta dina", "vyast din"),
        ("vyast dina", "vyast din"),

        ("poora karane", "poora karne"),

        ("raat ke", "raat ke"),

        ("ghar ke", "ghar ke"),

        ("din ke lie", "din ke liye"),

        ("din ke liye", "din ke liye"),
    ]

    for old, new in phrase_corrections:
        roman = roman.replace(old, new)

    # ==========================================
    # GENERAL CLEANUP
    # ==========================================

    roman = re.sub(
        r"\s+",
        " ",
        roman
    ).strip()

    # Remove accidental repeated vowels
    roman = re.sub(
        r"\baaa+\b",
        "aa",
        roman,
        flags=re.IGNORECASE
    )

    return roman


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

            result = translator.translate(text)

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

    result = google_translate_chunk(
        text,
        target
    )

    if result:
        return result

    print(
        "Google failed. Using MyMemory..."
    )

    result = mymemory_translate_chunk(
        text,
        target
    )

    if result:
        return result

    print(
        "All translation services failed."
    )

    return text


# ==========================================
# TRANSLATE TEXT
# ==========================================

def translate_text(text, target_language):

    if not text or not text.strip():
        return ""

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
            "Processing page "
            + str(page_number + 1)
        )

        text = page.get_text("text")

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

        else:

            pix = page.get_pixmap(
                matrix=fitz.Matrix(
                    2,
                    2
                )
            )

            image_bytes = pix.tobytes("png")

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

    if not file.filename.lower().endswith(".pdf"):

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

    file.save(filepath)

    try:

        results = process_pdf(
            filepath,
            target_language
        )

        output_filename = (
            os.path.splitext(
                file.filename
            )[0]
            + "_"
            + target_language
            + ".pdf"
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

            "pages":
                results,

            "download":
                "/download/"
                + output_filename

        })

    except Exception as error:

        print(
            "Processing error:",
            error
        )

        return jsonify({

            "success":
                False,

            "error":
                str(error)

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
def download_file(filename):

    filepath = os.path.join(
        OUTPUT_FOLDER,
        filename
    )

    if not os.path.exists(filepath):

        return jsonify({

            "success":
                False,

            "error":
                "File not found."

        }), 404

    return send_file(
        filepath,
        as_attachment=True
    )


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )
    )
