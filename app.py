from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, url_for, session, flash
import subprocess
import os
import shutil
from flask_mail import Mail, Message
from dotenv import load_dotenv
from drive_utils import upload_to_drive, download_drive_folder  # ⬅️ Defined in utils
from werkzeug.utils import secure_filename
from supabase import create_client, Client
from passlib.hash import bcrypt

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

app.secret_key = os.getenv('SECRET_KEY')  # Needed for session

# --- Admin Authentication ---
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

def is_admin_logged_in():
    return session.get('admin_logged_in', False)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    # Only allow POST (form submission) or explicit ?show=1 param to show login
    if request.method == 'GET' and not request.args.get('show'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = None
        try:
            admin = supabase.table("admins").select("username,password_hash").eq("username", username).single().execute().data
        except Exception as e:
            # If no admin found, show a friendly message
            flash('You do not have access.', 'danger')
            return render_template('admin_login.html')
        if admin and bcrypt.verify(password, admin["password_hash"]):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    credentials_exists = os.path.exists(os.path.join(os.path.dirname(__file__), 'credentials.json'))
    gallery_folder = os.path.join('static', 'gallery')
    gallery_images = []
    if os.path.exists(gallery_folder):
        gallery_images = [f for f in os.listdir(gallery_folder) if not f.startswith('.')]
    return render_template('admin_dashboard.html', credentials_exists=credentials_exists, gallery_images=gallery_images)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

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
        # Log to Supabase user_logs
        ip_address = request.remote_addr
        supabase.table('user_logs').insert({
            'email': email.strip(),
            'ip_address': ip_address
        }).execute()
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
    # If admin is logged in and using form, get from form
    if is_admin_logged_in() and request.form.get('link'):
        drive_link = request.form.get('link', '').strip()
        is_form = True
    else:
        data = request.get_json(silent=True) or {}
        drive_link = data.get('link', '').strip()
        is_form = False

    if not drive_link or "drive.google.com" not in drive_link:
        if is_form:
            flash('Invalid or missing Drive link.', 'danger')
            return redirect(url_for('admin_dashboard'))
        return jsonify(status='error', message='Invalid or missing Drive link.')

    try:
        if os.path.exists(GALLERY_FOLDER):
            shutil.rmtree(GALLERY_FOLDER)
        os.makedirs(GALLERY_FOLDER, exist_ok=True)

        success, msg = download_drive_folder(drive_link, GALLERY_FOLDER)
        if not success:
            if is_form:
                flash(f'Failed: {msg}', 'danger')
                return redirect(url_for('admin_dashboard'))
            return jsonify(status='error', message=msg)

        print("✅ Drive folder downloaded.")
        if is_form:
            flash('Drive images downloaded successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        return jsonify(status='ok')
    except Exception as e:
        print("❌ Drive download error:", e)
        if is_form:
            flash(f'Error: {e}', 'danger')
            return redirect(url_for('admin_dashboard'))
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

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'credentials.json')
ALLOWED_EXTENSIONS = {'json'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/admin/upload_credentials', methods=['POST'])
def upload_credentials():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    if 'credentials_file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('admin_dashboard'))
    file = request.files['credentials_file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('admin_dashboard'))
    if file and allowed_file(file.filename):
        filename = secure_filename('credentials.json')
        file.save(UPLOAD_FOLDER)
        flash('Credentials uploaded successfully.', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Invalid file type. Please upload a .json file.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_admin', methods=['POST'])
def add_admin():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    username = request.form.get('new_admin_username')
    password = request.form.get('new_admin_password')
    email = request.form.get('new_admin_email')
    if not username or not password:
        flash('Username and password are required.', 'danger')
        return redirect(url_for('admin_dashboard'))
    password_hash = bcrypt.hash(password)
    data = {
        "username": username,
        "password_hash": password_hash,
        "email": email
    }
    # Check if username already exists
    existing = supabase.table("admins").select("id").eq("username", username).execute()
    if existing.data:
        flash('Username already exists.', 'danger')
        return redirect(url_for('admin_dashboard'))
    result = supabase.table("admins").insert(data).execute()
    if result.data:
        flash('New admin added successfully!', 'success')
    else:
        flash('Failed to add new admin.', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/list_admins')
def list_admins():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    admins = supabase.table('admins').select('id,username,email,created_at').execute().data
    return jsonify(admins)

@app.route('/admin/delete_admin/<admin_id>', methods=['POST'])
def delete_admin(admin_id):
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    # Prevent deleting yourself (optional, can remove this check if not needed)
    # current_admin = session.get('admin_username')
    # admin = supabase.table('admins').select('username').eq('id', admin_id).single().execute().data
    # if admin and admin['username'] == current_admin:
    #     flash('You cannot delete yourself.', 'danger')
    #     return redirect(url_for('admin_dashboard'))
    result = supabase.table('admins').delete().eq('id', admin_id).execute()
    if result.data:
        flash('Admin deleted successfully.', 'success')
    else:
        flash('Failed to delete admin.', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_admin/<admin_id>', methods=['POST'])
def edit_admin(admin_id):
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    email = request.form.get('edit_admin_email')
    password = request.form.get('edit_admin_password')
    update_data = {}
    if email:
        update_data['email'] = email
    if password:
        update_data['password_hash'] = bcrypt.hash(password)
    if not update_data:
        flash('No changes provided.', 'warning')
        return redirect(url_for('admin_dashboard'))
    result = supabase.table('admins').update(update_data).eq('id', admin_id).execute()
    if result.data:
        flash('Admin updated successfully.', 'success')
    else:
        flash('Failed to update admin.', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/list_user_logs')
def list_user_logs():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    logs = supabase.table('user_logs').select('id,email,created_at,ip_address').order('created_at', desc=True).limit(100).execute().data
    return jsonify(logs)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# The following code was used to insert the initial admin user into Supabase.
# It is now commented out to avoid duplicate key errors.
'''
# Set your admin credentials
username = "admin"
password = "admin123"  # Change this to your desired password
email = "admin@example.com"

# Hash the password
password_hash = bcrypt.hash(password)

# Insert into Supabase
data = {
    "username": username,
    "password_hash": password_hash,
    "email": email
}
result = supabase.table("admins").insert(data).execute()
print(result)
'''

if __name__ == '__main__':
    app.run(debug=True)