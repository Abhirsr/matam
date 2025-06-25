from flask import Flask, render_template, request, send_from_directory, jsonify
import subprocess
import os
import shutil
from flask_mail import Mail, Message
from dotenv import load_dotenv
from drive_utils import upload_to_drive  # New import for Drive upload

# Load environment variables
load_dotenv()

app = Flask(__name__)
MATCHED_FOLDER = 'static/matched'

# Mail configuration with correct types
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
    os.makedirs(MATCHED_FOLDER)

    try:
        subprocess.run(['python3', 'match_faces.py'], check=True)
    except subprocess.CalledProcessError:
        return jsonify(status='error', message="Face matching failed. Try again.")

    matched_files = [f for f in os.listdir(MATCHED_FOLDER) if f.startswith('clean_')]
    if not matched_files:
        return jsonify(status='no_face')

    return jsonify(status='ok', redirect_url='/results')

@app.route('/results')
def results():
    matched_files = [f for f in os.listdir(MATCHED_FOLDER) if f.startswith('clean_')]
    return render_template('results.html', images=matched_files)

@app.route('/static/matched/<filename>')
def matched_faces(filename):
    return send_from_directory(MATCHED_FOLDER, filename)

@app.route('/send_email', methods=['POST'])
def send_email():
    data = request.get_json()
    selected_images = data.get('images', [])
    recipient = data.get('email')

    print("📨 Email request received.")
    print("➡️ Selected images:", selected_images)
    print("📬 Recipient from frontend:", recipient)

    if not recipient:
        return jsonify(status='error', message='No recipient email provided.')

    if not selected_images:
        return jsonify(status='error', message='No images selected.')


    # Full paths to selected files
    image_paths = [os.path.join(MATCHED_FOLDER, filename) for filename in selected_images]

    try:
        drive_link = upload_to_drive("Matched_Faces", image_paths)
        msg = Message("Face Match Results", recipients=[recipient])
        msg.body = f"📁 Your matched images are available here:\n\n{drive_link}\n\n(Shared via Google Drive)"
        mail.send(msg)
        print("✅ Email with Drive link sent to:", recipient)
        return jsonify(status='ok')
    except Exception as e:
        print("❌ Email Error:", e)
        return jsonify(status='error', message='Email failed.')



if __name__ == '__main__':
    app.run(debug=True)