from flask import Flask, render_template, request, send_from_directory, jsonify
import subprocess
import os
import shutil
from flask_mail import Mail, Message
from dotenv import load_dotenv
from drive_utils import upload_to_drive, download_drive_folder  # ⬅️ Defined in utils

load_dotenv()

app = Flask(__name__)

MATCHED_FOLDER = 'static/matched'
GALLERY_FOLDER = 'static/gallery'
EMAIL_FLAG_FILE = 'stored_email.txt'
EMAIL_SENT_FLAG = 'email_sent.flag'

# 🔧 Mail configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/capture', methods=['POST'])
def capture():
    if os.path.exists(MATCHED_FOLDER):
        shutil.rmtree(MATCHED_FOLDER)
    os.makedirs(MATCHED_FOLDER, exist_ok=True)

    if os.path.exists(EMAIL_SENT_FLAG):
        os.remove(EMAIL_SENT_FLAG)

    try:
        subprocess.run(['python3', 'match_faces.py'], check=True)
    except subprocess.CalledProcessError:
        return jsonify(status='error', message="Face matching failed.")

    matched_files = [f for f in os.listdir(MATCHED_FOLDER) if f.startswith('clean_')]
    if not matched_files:
        return jsonify(status='no_face')

    return jsonify(status='ok')

@app.route('/results')
def results():
    matched_files = [f for f in os.listdir(MATCHED_FOLDER) if f.startswith('clean_')]
    return render_template('results.html', images=matched_files)

@app.route('/static/matched/<filename>')
def matched_faces(filename):
    return send_from_directory(MATCHED_FOLDER, filename)

@app.route('/store_email', methods=['POST'])
def store_email():
    email = request.get_json().get('email')
    if not email:
        return jsonify(status='error', message='No email provided.')
    try:
        with open(EMAIL_FLAG_FILE, "w") as f:
            f.write(email.strip())
        print("📩 Email stored for later:", email)
        return jsonify(status='ok')
    except Exception as e:
        return jsonify(status='error', message=str(e))

@app.route('/status')
def status():
    matched_files = [f for f in os.listdir(MATCHED_FOLDER) if f.startswith('clean_')]
    return jsonify(status='ready' if matched_files else 'processing')

@app.route('/send_email', methods=['POST'])
def send_email():
    if os.path.exists(EMAIL_SENT_FLAG):
        print("⚠️ Email already sent. Skipping.")
        return jsonify(status='ok')

    data = request.get_json()
    selected_images = data.get('images', [])

    recipient = data.get('email')
    if not recipient and os.path.exists(EMAIL_FLAG_FILE):
        with open(EMAIL_FLAG_FILE) as f:
            recipient = f.read().strip()

    print("📨 Email request received.")
    print("➡️ Selected images:", selected_images)
    print("📬 Recipient:", recipient)

    if not recipient or not selected_images:
        return jsonify(status='error', message='Missing data.')

    image_paths = [os.path.join(MATCHED_FOLDER, f) for f in selected_images]

    try:
        drive_link = upload_to_drive("Matched_Faces", image_paths)
        msg = Message("Face Match Results", recipients=[recipient])
        msg.body = f"📁 Your matched images are here:\n\n{drive_link}"
        mail.send(msg)
        print("✅ Email sent to", recipient)

        with open(EMAIL_SENT_FLAG, "w") as flag:
            flag.write("sent")

        if os.path.exists(EMAIL_FLAG_FILE):
            os.remove(EMAIL_FLAG_FILE)

        return jsonify(status='ok')
    except Exception as e:
        print("❌ Email error:", e)
        return jsonify(status='error', message=str(e))

@app.route('/download_drive_images', methods=['POST'])
def download_drive_images():
    data = request.get_json()
    drive_link = data.get('link', '').strip()

    if not drive_link or "drive.google.com" not in drive_link:
        return jsonify(status='error', message='Invalid or missing Drive link.')

    try:
        if os.path.exists(GALLERY_FOLDER):
            shutil.rmtree(GALLERY_FOLDER)
        os.makedirs(GALLERY_FOLDER, exist_ok=True)

        success, msg = download_drive_folder(drive_link, GALLERY_FOLDER)
        if not success:
            return jsonify(status='error', message=msg)

        print("✅ Drive folder downloaded.")
        return jsonify(status='ok')
    except Exception as e:
        print("❌ Drive download error:", e)
        return jsonify(status='error', message=str(e))

@app.route('/clear_gallery', methods=['POST'])
def clear_gallery():
    try:
        if os.path.exists(GALLERY_FOLDER):
            shutil.rmtree(GALLERY_FOLDER)
        os.makedirs(GALLERY_FOLDER, exist_ok=True)
        print("🧹 Gallery cleared.")
        return jsonify(status='ok')
    except Exception as e:
        print("❌ Clear gallery error:", e)
        return jsonify(status='error', message=str(e))

@app.route('/reset', methods=['POST'])
def reset():
    try:
        if os.path.exists(MATCHED_FOLDER):
            shutil.rmtree(MATCHED_FOLDER)
        os.makedirs(MATCHED_FOLDER, exist_ok=True)

        if os.path.exists(EMAIL_FLAG_FILE):
            os.remove(EMAIL_FLAG_FILE)

        if os.path.exists(EMAIL_SENT_FLAG):
            os.remove(EMAIL_SENT_FLAG)

        return jsonify(status='ok')
    except Exception as e:
        print("❌ Reset error:", e)
        return jsonify(status='error', message=str(e))

if __name__ == '__main__':
    app.run(debug=True)