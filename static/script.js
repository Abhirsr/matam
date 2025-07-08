const video = document.getElementById('video');
const formSection = document.getElementById('form-section');

let storedEmail = null;
let emailSent = false;

// 🎥 Start camera
if (video) {
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            video.srcObject = stream;
        })
        .catch(err => {
            console.error("Camera access denied:", err);
            alert("Please allow camera access to continue.");
        });
}

// 📸 Capture face
function capture() {
    storedEmail = null;
    emailSent = false;

    showEmailForm();  // Prompt for email first

    fetch('/capture', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'no_face') {
                alert("❌ No face found. Try again.");
                return;
            }

            pollForResults();  // Start polling for results
        })
        .catch(err => {
            console.error("Error:", err);
            alert("⚠️ Failed to start capture. Try again.");
        });
}

// ✉️ Show email input immediately
function showEmailForm() {
    formSection.innerHTML = `
        <p style="text-align:center; font-size: 18px;">📸 Captured! Enter your email to receive matched images.</p>
        <input type="email" id="userEmail" placeholder="Enter your email" style="margin-top: 20px; padding: 10px; width: 100%; font-size: 16px;" required>
        <button onclick="storeEmail()" class="btn" style="margin-top: 15px;">✅ Confirm Email</button>
    `;
}

// ✅ Store email
function storeEmail() {
    const email = document.getElementById('userEmail').value;
    if (!email || !email.includes("@")) {
        alert("Please enter a valid email.");
        return;
    }

    storedEmail = email;

    fetch('/store_email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: storedEmail })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'ok') {
            formSection.innerHTML = `
                <p style="text-align:center; font-size: 18px; color: green;">
                    ✅ Email stored. You’ll receive your images once matching is ready.
                </p>
            `;
        } else {
            alert("❌ Failed to store email on server.");
        }
    })
    .catch(err => {
        console.error("Error storing email:", err);
        alert("⚠️ Could not store email.");
    });
}

// 🔄 Poll until match ready
function pollForResults() {
    const interval = setInterval(() => {
        fetch('/status')
            .then(res => res.json())
            .then(data => {
                if (data.status === 'ready' && storedEmail && !emailSent) {
                    clearInterval(interval);
                    sendEmailIfStored();
                }
            })
            .catch(err => {
                console.error("Polling error:", err);
            });
    }, 3000);
}

function clearGallery() {
    if (!confirm("⚠️ Are you sure you want to delete all images in the gallery folder?")) return;

    fetch('/clear_gallery', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                alert("✅ Gallery folder cleared.");
            } else {
                alert("❌ Failed to clear gallery: " + data.message);
            }
        })
        .catch(err => {
            console.error("Clear gallery error:", err);
            alert("⚠️ An error occurred while clearing the gallery.");
        });
}


// 📤 Send matched images via email
function sendEmailIfStored() {
    if (!storedEmail || emailSent) return;

    emailSent = true;

    fetch('/results')
        .then(res => res.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const checkboxes = doc.querySelectorAll('.image-checkbox');

            const matchedFiles = [];
            checkboxes.forEach(cb => matchedFiles.push(cb.getAttribute('data-filename')));

            fetch('/send_email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ images: matchedFiles, email: storedEmail })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'ok') {
                    formSection.innerHTML = `
                        <p style="text-align:center; font-size: 20px; color: green;">
                            ✅ Images sent to <b>${storedEmail}</b>!
                        </p>
                        <div style="text-align: center; margin-top: 20px;">
                            <button onclick="resetApp()" class="btn">🔁 Try Again</button>
                        </div>
                    `;
                    storedEmail = null;
                } else {
                    emailSent = false;
                    alert("❌ Failed to send email.");
                }
            })
            .catch(err => {
                emailSent = false;
                console.error("Send email error:", err);
                alert("⚠️ Error sending email.");
            });
        });
}

// 🔁 Reset
function resetApp() {
    fetch('/reset', { method: 'POST' })
        .then(() => {
            window.location.reload();
        });
}
/* particlesJS.load(@dom-id, @path-json, @callback (optional)); */
particlesJS.load('particles-js', '/static/particles.json', function() {
    console.log('callback - particles.js config loaded');
  });