// ----------------------- Webcam + Matching -----------------------
const video = document.getElementById('video');
const loadingDiv = document.getElementById('loading');
const pickupLineP = document.getElementById('pickup-line');

const lines = [
    "You must be a magician — every time I look at you, everyone else disappears! ✨",
    "If beauty were time, you’d be an eternity. ⏳",
    "Your face just made our AI smile. 🤖😊",
    "You and this gallery are about to make history. 📸",
    "Are you a camera? Because every time I look at you, I smile! 📷",
    "Our AI is falling for your symmetry. ❤️🧠",
    "Hold tight! Matching your charm... 🔍💘"
];

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

function cyclePickupLines() {
    let i = 0;
    return setInterval(() => {
        pickupLineP.textContent = lines[i % lines.length];
        i++;
    }, 3000);
}

function capture() {
    loadingDiv.style.display = 'flex';
    const intervalId = cyclePickupLines();

    fetch('/capture', {
        method: 'POST'
    })
    .then(res => res.json())
    .then(data => {
        clearInterval(intervalId);
        if (data.status === 'no_face') {
            alert("❌ No face found. Try again.");
            loadingDiv.style.display = 'none';
        } else if (data.status === 'ok') {
            window.location.href = data.redirect_url;
        } else {
            alert("Something went wrong. Try again.");
            loadingDiv.style.display = 'none';
        }
    })
    .catch(err => {
        clearInterval(intervalId);
        console.error("Error:", err);
        alert("⚠️ Failed to start capture. Try again.");
        loadingDiv.style.display = 'none';
    });
}

// ----------------------- Select + Send Email -----------------------
function toggleSelectAll(source) {
    const checkboxes = document.querySelectorAll('input[name="selected_images"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = source.checked;
    });
}

const emailForm = document.getElementById('emailForm');
if (emailForm) {
    emailForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const selected = Array.from(document.querySelectorAll('input[name="selected_images"]:checked'))
                              .map(cb => cb.value);

        if (selected.length === 0) {
            alert("Please select at least one image.");
            return;
        }

        fetch('/send_email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ images: selected })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                alert("📧 Email sent successfully!");
            } else {
                alert("❌ Failed to send email.");
            }
        })
        .catch(err => {
            alert("⚠️ An error occurred while sending email.");
            console.error(err);
        });
    });
}