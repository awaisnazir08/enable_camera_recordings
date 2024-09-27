document.addEventListener("DOMContentLoaded", function() {
    const recordButton = document.getElementById("recordButton");
    const filenameInput = document.getElementById("filename");
    const recordLocalCheckbox = document.getElementById("recordLocal");

    // Function to update the button state
    function updateButtonState() {
        const isFilenameValid = filenameInput.value.trim() !== '';
        const isRecordLocalChecked = recordLocalCheckbox.checked;

        recordButton.disabled = !(isFilenameValid && isRecordLocalChecked);
        recordButton.style.backgroundColor = recordButton.disabled ? 'lightgray' : (recordButton.innerText.includes("Start") ? 'green' : 'red');
    }

    // Event listeners
    filenameInput.addEventListener("input", updateButtonState);
    recordLocalCheckbox.addEventListener("change", updateButtonState);

    // Handle button click to start/stop recording
    recordButton.addEventListener("click", async () => {
        if (recordButton.innerText === "Start Recording") {
            const filename = filenameInput.value.trim();
            const recordLocal = recordLocalCheckbox.checked;

            const response = await fetch("/start_recording", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ filename: filename, record_local: recordLocal })
            });
            // const responseData = await response.json();
            // console.log(responseData.status); // Should print: "Recording started"

            if (response.ok) {
                recordButton.innerText = "Stop Recording";
                updateButtonState();
            }
        } else {
            const response = await fetch("/stop_recording", {
                method: "POST"
            });

            if (response.ok) {
                recordButton.innerText = "Start Recording";
                updateButtonState();
            }
        }
    });
});
