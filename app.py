from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory
import os
import json

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

            <form id="uploadForm" enctype="multipart/form-data" class="upload-form">
    <input type="file" name="file" required>
    <input type="text" name="description" placeholder="Dosya açıklaması" required>
    <button type="submit">Yükle</button>
</form>

<div id="progressContainer" style="display:none;">
    <div id="progressBar"></div>
    <p id="progressText">0%</p>
</div>


            <h2>Yüklenen Dosyalar</h2>
            <ul class="file-list">
                {% for file in files %}
                    <li>
                        <a href="{{ url_for('download', filename=file.filename) }}">{{ file.filename }}</a><br>
                        <small>Açıklama: {{ file.description }} | Yükleyen: {{ file.uploaded_by }}</small>
                    </li>
                {% else %}
                    <li>Henüz dosya yüklenmemiş.</li>
                {% endfor %}
            </ul>
        </div>
    {% endif %}
    <script>
document.getElementById("uploadForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "{{ url_for('upload') }}", true);

    const progressContainer = document.getElementById("progressContainer");
    const progressBar = document.getElementById("progressBar");
    const progressText = document.getElementById("progressText");

    progressContainer.style.display = "block";
    progressBar.style.width = "0%";
    progressText.textContent = "0%";

    xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            progressBar.style.width = percent + "%";
            progressText.textContent = percent + "%";
        }
    });

    xhr.onload = function() {
        if (xhr.status === 200) {
            progressBar.style.width = "100%";
            progressText.textContent = "Yükleme tamamlandı!";
            setTimeout(() => window.location.reload(), 1000);
        } else {
            progressText.textContent = "Yükleme hatası!";
        }
    };

    xhr.send(formData);
});
</script>

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

# Dosya yükleme
@app.route("/upload", methods=["POST"])
def upload():
    if "username" not in session:
        return redirect(url_for("login"))
    
    file = request.files["file"]
    description = request.form["description"]

    if file:
        filename = file.filename
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        # Dosya bilgilerini JSON'a ekle
        with open(FILES_JSON) as f:
            file_data = json.load(f)

        file_data.append({
            "filename": filename,
            "description": description,
            "uploaded_by": session["username"]
        })

        with open(FILES_JSON, "w") as f:
            json.dump(file_data, f)

    return redirect(url_for("home"))

# Dosya indirme
@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
