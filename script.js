let mediaRecorder;
let recordedChunks = [];

function showPopup() {
        document.getElementById("popup").style.display = "block";
        document.getElementById("overlay").style.display = "block";
    }

    function closePopup() {
        document.getElementById("popup").style.display = "none";
        document.getElementById("overlay").style.display = "none";
    }

    function updateFileLabel() {
        document.getElementById("audioLabel").innerText = "Uploaded ✅";
    }

async function uploadAudio(endpoint) {
    let fileInput = document.getElementById("audioFile");
    let inputLang = document.getElementById("inputLangAudio").value;
    let targetLang = document.getElementById("targetLangAudio");

    if (fileInput.files.length === 0) {
        alert("Please upload or record an audio file");
        return;
    }

    let formData = new FormData();
    formData.append("audio", fileInput.files[0]);
    formData.append("input_lang", inputLang);

    if (endpoint === "translate_audio") {
        formData.append("target_lang", targetLang.value);
    }

    showLoading();
    let response = await fetch(`/${endpoint}`, { method: "POST", body: formData });
    let result = await response.json();
    hideLoading();

    displayResult(result);
}

async function translateText() {
    let text = document.getElementById("textInput").value;
    let targetLang = document.getElementById("targetLangText").value;

    if (!text) {
        alert("Please enter text to translate");
        return;
    }

    showLoading();
    let response = await fetch("/translate_text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text, target_lang: targetLang })
    });

    let result = await response.json();
    hideLoading();

    displayResult(result);
}

function displayResult(result) {
    let table = document.getElementById("resultTable");
    table.innerHTML = "";

    let headerRow = table.insertRow();
    let headerCell1 = headerRow.insertCell(0);
    let headerCell2 = headerRow.insertCell(1);
    headerCell1.textContent = "Speaker";
    headerCell2.textContent = "Text";

    for (let key in result) {
        let row = table.insertRow();
        let cell1 = row.insertCell(0);
        let cell2 = row.insertCell(1);
        cell1.textContent = key;
        cell2.textContent = result[key];
    }
}

function showLoading() {
    let loadingDiv = document.createElement("div");
    loadingDiv.id = "loading";
    loadingDiv.className = "loading show";
    loadingDiv.textContent = "Loading...⌛";
    document.body.appendChild(loadingDiv);
}

function hideLoading() {
    let loadingDiv = document.getElementById("loading");
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

async function startRecording() {
    recordedChunks = [];
    let stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = handleDataAvailable;
    mediaRecorder.start();
    document.getElementById("recordButton").textContent = "Stop Recording";
    document.getElementById("recordButton").onclick = stopRecording;
}

function stopRecording() {
    mediaRecorder.stop();
    document.getElementById("recordButton").textContent = "Start Recording";
    document.getElementById("recordButton").onclick = startRecording;
}

function handleDataAvailable(event) {
    if (event.data.size > 0) {
        recordedChunks.push(event.data);
        let blob = new Blob(recordedChunks, { type: 'audio/wav' });
        let file = new File([blob], "recording.wav", { type: 'audio/wav' });
        let fileInput = document.getElementById("audioFile");
        let dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;
        updateFileLabel();
    }
}

function logout() {
    // Perform logout actions here, such as clearing session data or redirecting to a logout endpoint
    alert("You have been logged out.");
    window.location.href = "/logout"; // Redirect to logout endpoint or login page
}