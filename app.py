from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory
import os
import json
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Cloudinary bağlantısı
cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("CLOUD_API_KEY"),  # ← burası değişti
    api_secret=os.getenv("CLOUD_API_SECRET"),  # ← burası değişti
    secure=True
)

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

USERS_FILE = "users.json"
FILES_JSON = "files.json"

# Kullanıcı verisi dosyası yoksa oluştur
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

# Dosya açıklama verisi dosyası yoksa oluştur
if not os.path.exists(FILES_JSON):
    with open(FILES_JSON, "w") as f:
        json.dump([], f)

# HTML Template
BASE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Dosya Paylaşım</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    {% if page == 'login' %}
        <div class="login-container">
            <h2>Giriş Yap</h2>
            <form method="POST" action="{{ url_for('login') }}">
                <input type="text" name="username" placeholder="Kullanıcı adı" required>
                <input type="password" name="password" placeholder="Şifre" required>
                <button type="submit">Giriş</button>
            </form>
            <p>Hesabın yok mu? <a href="{{ url_for('register') }}">Kayıt Ol</a></p>
            {% if error %}<p class="error">{{ error }}</p>{% endif %}
        </div>

    {% elif page == 'register' %}
        <div class="login-container">
            <h2>Kayıt Ol</h2>
            <form method="POST" action="{{ url_for('register') }}">
                <input type="text" name="username" placeholder="Kullanıcı adı" required>
                <input type="password" name="password" placeholder="Şifre" required>
                <button type="submit">Kayıt Ol</button>
            </form>
            <p>Zaten hesabın var mı? <a href="{{ url_for('login') }}">Giriş Yap</a></p>
            {% if error %}<p class="error">{{ error }}</p>{% endif %}
        </div>

    {% elif page == 'files' %}
        <div class="container">
            <div class="header">
                <h1>📁 Dosya Paylaşım Alanı</h1>
                <p>Hoşgeldin, <strong>{{ session['username'] }}</strong></p>
                <a href="{{ url_for('logout') }}" class="logout-btn">Çıkış Yap</a>
            </div>

            <form method="POST" enctype="multipart/form-data" action="{{ url_for('upload') }}" class="upload-form">
                <input type="file" name="file" required>
                <input type="text" name="description" placeholder="Dosya açıklaması" required>
                <button type="submit">Yükle</button>
            </form>
            <div id="progress-container" style="width: 100%; background: #ddd; border-radius: 5px; margin-top: 10px; display: none;">
    <div id="progress-bar" style="width: 0%; height: 20px; background: #4caf50; border-radius: 5px;"></div>
</div>

<script>
document.querySelector('.upload-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const form = e.target;
    const fileInput = form.querySelector('input[name="file"]');
    const descInput = form.querySelector('input[name="description"]');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');

    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('description', descInput.value);

    xhr.open('POST', form.action, true);

    xhr.upload.addEventListener('loadstart', () => {
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
    });

    xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
            const percent = (e.loaded / e.total) * 100;
            progressBar.style.width = percent + '%';
        }
    });

    xhr.addEventListener('load', () => {
        progressBar.style.width = '100%';
        setTimeout(() => {
            window.location.reload();
        }, 500);
    });

    xhr.send(formData);
});
</script>


            <h2>Yüklenen Dosyalar</h2>
            <ul class="file-list">
                {% for file in files %}
                    <li>
                        <a href="{{ file.url }}" target="_blank">{{ file.filename }}</a><br>
                        <small>Açıklama: {{ file.description }} | Yükleyen: {{ file.uploaded_by }}</small>
                    </li>
                {% else %}
                    <li>Henüz dosya yüklenmemiş.</li>
                {% endfor %}
            </ul>
        </div>
    {% endif %}
</body>
</html>
"""

# Anasayfa
@app.route("/")
def home():
    if "username" in session:
        if os.path.exists(FILES_JSON):
            with open(FILES_JSON) as f:
                file_data = json.load(f)
        else:
            file_data = []
        return render_template_string(BASE_HTML, page="files", files=file_data)
    return redirect(url_for("login"))

# Giriş
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        with open(USERS_FILE) as f:
            users = json.load(f)
        if username in users and users[username] == password:
            session["username"] = username
            return redirect(url_for("home"))
        else:
            return render_template_string(BASE_HTML, page="login", error="Hatalı giriş bilgisi!")
    return render_template_string(BASE_HTML, page="login")

# Kayıt
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        with open(USERS_FILE) as f:
            users = json.load(f)
        if username in users:
            return render_template_string(BASE_HTML, page="register", error="Bu kullanıcı adı zaten var!")
        users[username] = password
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
        session["username"] = username
        return redirect(url_for("home"))
    return render_template_string(BASE_HTML, page="register")

# Çıkış
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# Dosya yükleme (Cloudinary)
@app.route("/upload", methods=["POST"])
def upload():
    if "username" not in session:
        return redirect(url_for("login"))
    
    file = request.files["file"]
    description = request.form["description"]

    if file:
        # Cloudinary'ye yükle
        upload_result = cloudinary.uploader.upload(file)
        file_url = upload_result["secure_url"]

        # Dosya bilgilerini JSON'a ekle
        with open(FILES_JSON) as f:
            file_data = json.load(f)

        file_data.append({
            "filename": file.filename,
            "url": file_url,
            "description": description,
            "uploaded_by": session["username"]
        })

        with open(FILES_JSON, "w") as f:
            json.dump(file_data, f)

    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
