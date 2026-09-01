const pdfInput = document.getElementById("pdfInput");
const dropZone = document.getElementById("dropZone");
const translateBtn = document.getElementById("translateBtn");

const fileInfo = document.getElementById("fileInfo");

const progressBox = document.getElementById("progressBox");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const progressPercent = document.getElementById("progressPercent");

const resultSection = document.getElementById("resultSection");
const resultsBox = document.getElementById("results");


let selectedFile = null;


// ==============================
// FILE SELECT
// ==============================

pdfInput.addEventListener("change", function () {

    if (this.files.length > 0) {

        handleFile(this.files[0]);

    }

});


// ==============================
// HANDLE FILE
// ==============================

function handleFile(file) {

    if (file.type !== "application/pdf") {

        alert("Please select a PDF file.");

        return;

    }


    if (file.size > 50 * 1024 * 1024) {

        alert("Maximum file size is 50 MB.");

        return;

    }


    selectedFile = file;


    fileInfo.textContent =
        file.name +
        " • " +
        formatSize(file.size);


    translateBtn.disabled = false;

}


// ==============================
// FILE SIZE
// ==============================

function formatSize(bytes) {

    const mb = bytes / (1024 * 1024);

    return mb.toFixed(2) + " MB";

}


// ==============================
// DRAG & DROP
// ==============================

dropZone.addEventListener(
    "dragover",
    function (event) {

        event.preventDefault();

        dropZone.classList.add("dragging");

    }
);


dropZone.addEventListener(
    "dragleave",
    function () {

        dropZone.classList.remove("dragging");

    }
);


dropZone.addEventListener(
    "drop",
    function (event) {

        event.preventDefault();

        dropZone.classList.remove("dragging");


        if (event.dataTransfer.files.length > 0) {

            handleFile(
                event.dataTransfer.files[0]
            );

        }

    }
);


// ==============================
// TRANSLATE
// ==============================

translateBtn.addEventListener(
    "click",
    async function () {

        if (!selectedFile) {

            alert("Please select a PDF first.");

            return;

        }


        const formData = new FormData();

        formData.append(
            "pdf",
            selectedFile
        );


        // Show progress

        progressBox.classList.remove("hidden");

        resultSection.classList.add("hidden");

        translateBtn.disabled = true;


        setProgress(
            10,
            "Uploading PDF..."
        );


        try {

            setProgress(
                30,
                "Reading PDF..."
            );


            const response = await fetch(
                "/translate",
                {
                    method: "POST",
                    body: formData
                }
            );


            setProgress(
                60,
                "Translating content..."
            );


            const data = await response.json();


            if (!data.success) {

                throw new Error(
                    data.error ||
                    "Translation failed."
                );

            }


            setProgress(
                85,
                "Creating English PDF..."
            );


            displayResults(
                data.pages
            );


            setProgress(
                100,
                "Translation complete!"
            );


            // ==========================
            // DOWNLOAD BUTTON
            // ==========================

            addDownloadButton(
                data.download
            );


            translateBtn.disabled = false;

        }

        catch (error) {

            console.error(error);

            alert(
                error.message ||
                "Something went wrong."
            );


            progressBox.classList.add(
                "hidden"
            );


            translateBtn.disabled = false;

        }

    }
);


// ==============================
// PROGRESS
// ==============================

function setProgress(
    percent,
    message
) {

    progressBar.style.width =
        percent + "%";


    progressPercent.textContent =
        percent + "%";


    progressText.textContent =
        message;

}


// ==============================
// SHOW RESULTS
// ==============================

function displayResults(pages) {

    resultsBox.innerHTML = "";


    pages.forEach(function (page) {

        const card =
            document.createElement("div");


        card.className =
            "result-card";


        const title =
            document.createElement("h3");


        title.textContent =
            "Page " +
            page.page +
            " • " +
            page.type;


        const original =
            document.createElement("div");


        original.className =
            "result-original";


        original.innerHTML =
            "<strong>Original</strong><br>" +
            escapeHtml(
                page.original
            );


        const translated =
            document.createElement("div");


        translated.className =
            "result-translated";


        translated.innerHTML =
            "<strong>English Translation</strong><br>" +
            escapeHtml(
                page.translated
            );


        card.appendChild(title);

        card.appendChild(original);

        card.appendChild(translated);


        resultsBox.appendChild(card);

    });


    resultSection.classList.remove(
        "hidden"
    );

}


// ==============================
// DOWNLOAD BUTTON
// ==============================

function addDownloadButton(url) {

    const oldButton =
        document.getElementById(
            "downloadPdfBtn"
        );


    if (oldButton) {

        oldButton.remove();

    }


    const button =
        document.createElement("a");


    button.id =
        "downloadPdfBtn";


    button.href =
        url;


    button.textContent =
        "⬇ Download English PDF";


    button.className =
        "download-pdf-btn";


    button.setAttribute(
        "download",
        ""
    );


    resultSection
        .querySelector(".section-title")
        .appendChild(button);

}


// ==============================
// HTML SECURITY
// ==============================

function escapeHtml(text) {

    if (!text) {

        return "";

    }


    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}
