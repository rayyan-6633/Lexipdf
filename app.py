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
# HINDI TO NATURAL ROMAN HINDI
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

        replacements = [
            ("RR^i", "ri"),
            ("R^i", "ri"),
            ("RRi", "ri"),
            ("R^I", "ri"),
            ("Ri", "ri"),

            ("Chh", "chh"),
            ("chh", "chh"),

            ("kh", "kh"),
            ("gh", "gh"),
            ("jh", "jh"),
            ("th", "th"),
            ("dh", "dh"),
            ("ph", "ph"),
            ("bh", "bh"),

            ("Sh", "sh"),
            ("sh", "sh"),

            ("GY", "gy"),
            ("JN", "gy"),

            ("~N", "n"),
            ("~n", "n"),
            (".N", "n"),
            (".n", "n"),

            ("~m", "m"),

            ("T", "t"),
            ("D", "d"),
            ("N", "n"),

            ("M", "n"),

            ("^", ""),
            ("'", ""),
        ]

        for old, new in replacements:
            roman = roman.replace(old, new)

        roman = roman.replace("||", ".")
        roman = roman.replace("|", ".")
        roman = roman.replace("~", "")

        roman = re.sub(
            r"\s+",
            " ",
            roman
        ).strip()

        corrections = {

            "eka": "ek",
            "EkA": "Ek",

            "vyasta": "vyast",
            "Vyasta": "Vyast",

            "dina": "din",
            "Dina": "Din",

            "hara": "har",
            "Hara": "Har",

            "subaha": "subah",
            "Subaha": "Subah",

            "jaldI": "jaldi",
            "jaldi": "jaldi",

            "uthatA": "uthta",
            "uthata": "uthta",
            "UthatA": "Uthta",

            "vaha": "woh",
            "Vaha": "Woh",

            "vah": "woh",
            "Vah": "Woh",

            "usakA": "uska",
            "usak": "uska",

            "apane": "apne",
            "Apane": "Apne",

            "apani": "apni",
            "apanI": "apni",
            "Apani": "Apni",

            "lie": "liye",
            "liye": "liye",

            "tAIyAra": "taiyar",
            "taiyAra": "taiyar",
            "taiyara": "taiyar",
            "TaiyAra": "Taiyar",

            "nAshtA": "nashta",
            "nashta": "nashta",
            "Nashta": "Nashta",

            "karatA": "karta",
            "karata": "karta",
            "KaratA": "Karta",

            "aura": "aur",
            "Aura": "Aur",

            "chalA": "chala",
            "chala": "chala",

            "ghara": "ghar",
            "Ghara": "Ghar",

            "kAryAlaya": "office",
            "karyalaya": "office",
            "Karyalaya": "office",

            "kArya": "kaam",
            "karya": "kaam",

            "vyasta": "vyast",

            "kAryadivasa": "workday",
            "karyadivasa": "workday",

            "rahatA": "rehta",
            "rahata": "rehta",

            "kAryon": "kaamon",
            "karyon": "kaamon",

            "pUrA": "poora",
            "pUra": "poora",
            "pura": "poora",

            "karane": "karne",

            "men": "mein",
            "meM": "mein",

            "kaI": "kai",
            "kai": "kai",

            "ghaMTe": "ghante",
            "ghante": "ghante",

            "bitAtA": "bitaata",
            "bitata": "bitata",

            "baithakon": "meetings",

            "bhAga": "bhaag",
            "bhaga": "bhaag",

            "lenA": "lena",
            "lena": "lena",

            "sahayogiyon": "colleagues",

            "madada": "madad",
            "Madada": "Madad",

            "karanA": "karna",
            "karana": "karna",

            "bhara": "bhar",
            "Bhara": "Bhar",

            "kAma": "kaam",
            "kama": "kaam",

            "shAma": "shaam",
            "shama": "shaam",

            "taka": "tak",

            "thakAna": "thakan",

            "mahasUsa": "mehsoos",
            "mahasusa": "mehsoos",

            "jimmedAriyAn": "zimmedariyan",
            "jimmedariyan": "zimmedariyan",

            "pUrI": "poori",
            "puri": "poori",

            "vApasa": "wapas",
            "vapasa": "wapas",

            "yAtrA": "yatra",
            "yatra": "yatra",

            "jaba": "jab",
            "Jaba": "Jab",

            "AtA": "aata",
            "ata": "aata",

            "patnI": "patni",
            "patni": "patni",

            "sAtha": "saath",
            "satha": "saath",

            "kuCha": "kuchh",
            "kucha": "kuchh",

            "shAnta": "shaant",
            "shanta": "shaant",

            "samaya": "samay",

            "bItAtA": "bitaata",
            "bitata": "bitaata",

            "unake": "unke",
            "Unake": "Unke",

            "bAre": "baare",
            "bare": "baare",

            "bAta": "baat",
            "bata": "baat",

            "ArAma": "aaraam",
            "arama": "aaraam",

            "rAta": "raat",
            "Rata": "Raat",

            "khAne": "khaane",
            "khane": "khaane",

            "shAntipUrNa": "shaantipoorn",
            "shantipurna": "shaantipoorn",

            "taiyArI": "taiyari",
            "taiyari": "taiyari",

            "ahasAsa": "ehsaas",
            "ahasaasa": "ehsaas",

            "thakA": "thaka",
            "thaka": "thaka",

            "huA": "hua",
            "hua": "hua",

            "lekina": "lekin",
            "Lekin": "Lekin",

            "santuShta": "santusht",
            "santushta": "santusht",

            "bistara": "bistar",
            "Bistara": "Bistar",

            "jAtA": "jaata",
            "jata": "jaata",

            "so": "so",

            "shurU": "shuru",
            "shuru": "shuru",

            "agale": "agle",
            "Agale": "Agle",

            "taiyAra": "taiyar",

            "hone": "hone",

            "mujhe": "mujhe",
            "Mujhe": "Mujhe",

            "tumhe": "tumhein",
            "Tumhe": "Tumhein",

            "tumhE": "tumhein",

            "ham": "hum",
            "Ham": "Hum",

            "hama": "hamara",

            "haii": "hai",
            "haia": "hai",

            "nahin": "nahi",
            "Nahin": "Nahi",

            "kyon": "kyun",
            "Kyon": "Kyun",

            "mai": "main",
            "Mai": "Main",

            "mE": "main",

            "mErA": "mera",
            "mera": "mera",

            "mErI": "meri",
            "meri": "meri",

            "usakI": "uski",

            "kevala": "sirf",
            "sirf": "sirf",

            "isalie": "isliye",
            "isliye": "isliye",

            "bAda": "baad",
            "bada": "baad",

            "sA": "sa",
        }

        words = roman.split()
        cleaned = []

        for word in words:

            punctuation = ""

            while word and word[-1] in ".,!?;:":

                punctuation = (
                    word[-1]
                    + punctuation
                )

                word = word[:-1]

            word = word.replace("^", "")
            word = word.replace("'", "")

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

        phrase_corrections = [

            ("ke lie", "ke liye"),
            ("ke liye ghar", "ghar se"),

            ("ghara ke", "ghar ke"),

            ("dina ke lie", "din ke liye"),

            ("taiyara hota", "taiyar hota"),

            ("nashta karata", "nashta karta"),

            ("office ke lie", "office ke liye"),

            ("kaI ghaMTe", "kai ghante"),
            ("kai ghante", "kai ghante"),

            ("bitata hai", "bitaata hai"),

            ("pUrA karane", "poora karne"),
            ("poora karane", "poora karne"),

            ("sAtha", "saath"),
            ("shAnta", "shaant"),
            ("shAntipUrNa", "shaantipoorn"),

            ("rAta ke", "raat ke"),

            ("ghara vApasa", "ghar wapas"),
            ("ghar vapasa", "ghar wapas"),

            ("agale dina", "agle din"),
            ("agale din", "agle din"),

            ("eka aura", "ek aur"),
            ("eka", "ek"),

            ("vyasta dina", "vyast din"),

            ("hara subaha", "har subah"),

            ("jaldI uthatA", "jaldi uthta"),
            ("jaldI", "jaldi"),

            ("vaha", "woh"),
            ("Vaha", "Woh"),

            ("apane", "apne"),
            ("apanI", "apni"),

            ("karatA", "karta"),
            ("aura", "aur"),

            ("ghara", "ghar"),
            ("kAma", "kaam"),
            ("shAma", "shaam"),

            ("mahasUsa", "mehsoos"),
            ("jimmedAriyAn", "zimmedariyan"),
        ]

        for old, new in phrase_corrections:

            roman = roman.replace(
                old,
                new
            )

        roman = re.sub(
            r"\s+",
            " ",
            roman
        ).strip()

        return roman

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
  
