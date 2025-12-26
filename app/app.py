import platform
import subprocess
import mysql.connector
import google.generativeai as genai
import os
import time
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    flash,
)
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)


# --- DECORATOR CEK LOGIN ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


# Ambil Secret Key dari .env
app.secret_key = os.environ.get("SECRET_KEY", "default_secret_key")


# --- KONFIGURASI GEMINI ---


# Ambil API Key dari Environment Variable (diset di docker-compose)
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)
else:
    print("PERINGATAN: GEMINI_API_KEY belum diset!")


# Inisialisasi Model Gemini Pro
model = genai.GenerativeModel("gemini-2.5-flash")


# --- KONEKSI DATABASE ---
def get_db_connection():
    # Retry logic sederhana
    retries = 5
    while retries > 0:
        try:
            conn = mysql.connector.connect(
                host=os.environ.get("DB_HOST", ""),
                user=os.environ.get("DB_USER", ""),
                password=os.environ.get("DB_PASSWORD", ""),
                database=os.environ.get("DB_NAME", ""),
            )
            return conn
        except mysql.connector.Error as err:
            time.sleep(2)
            retries -= 1
    raise Exception("Gagal konek ke Database")


def init_db():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()

        # 1. Tabel Devices (Sudah ada)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100),
                ip_address VARCHAR(50),
                last_status VARCHAR(10) DEFAULT 'UNKNOWN',
                last_checked DATETIME
            )
        """
        )

        # 2. Tabel Logs (Sudah ada)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS device_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                device_id INT,
                status VARCHAR(10),
                event_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
            )
        """
        )

        # 3. Tabel Users (BARU)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL
            )
        """
        )

        # 4. Buat User Admin Default (Jika tabel kosong)
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            # Password default: admin123
            hashed_pw = generate_password_hash("admin123", method="pbkdf2:sha256")
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                ("admin", hashed_pw),
            )
            print("User 'admin' berhasil dibuat (Pass: admin123)")

        conn.commit()
        cursor.close()
        conn.close()


# --- FUNGSI PING (Sama seperti sebelumnya) ---
def ping_host(host):
    param = "-c"
    timeout_param = "-W"
    timeout_val = "1"
    command = ["ping", param, "1", timeout_param, timeout_val, host]
    try:
        response = subprocess.call(
            command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return response == 0
    except Exception:
        return False


# --- HELPER: FORMAT TANGGAL INDONESIA ---
def format_indo(dt_obj):
    if not dt_obj:
        return "-"

    # Mapping Hari dan Bulan
    hari = {
        "Sunday": "Minggu",
        "Monday": "Senin",
        "Tuesday": "Selasa",
        "Wednesday": "Rabu",
        "Thursday": "Kamis",
        "Friday": "Jumat",
        "Saturday": "Sabtu",
    }
    bulan = {
        "January": "Januari",
        "February": "Februari",
        "March": "Maret",
        "April": "April",
        "May": "Mei",
        "June": "Juni",
        "July": "Juli",
        "August": "Agustus",
        "September": "September",
        "October": "Oktober",
        "November": "November",
        "December": "Desember",
    }

    # Ambil nama hari dan bulan dalam inggris
    nama_hari = hari[dt_obj.strftime("%A")]
    nama_bulan = bulan[dt_obj.strftime("%B")]
    tanggal = dt_obj.strftime("%d")
    tahun = dt_obj.strftime("%Y")
    jam = dt_obj.strftime("%H:%M")

    return f"{nama_hari}, {tanggal} {nama_bulan} {tahun} {jam} WIB"


# --- ROUTES ---


@app.route("/")
@login_required
def index():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM devices ORDER BY id DESC"
        )  # Urutkan dari yang terbaru
        devices = cursor.fetchall()
        # Format tanggal last_checked agar cantik
        for d in devices:
            if d["last_checked"]:
                # Pastikan format datetime object, lalu format ke text Indo
                d["last_checked_str"] = format_indo(d["last_checked"])
            else:
                d["last_checked_str"] = "Belum dicek"

        cursor.close()
        conn.close()
        return render_template("index.html", hosts=devices)
    except Exception as e:
        return str(e)


# API: Ping Perangkat
# @app.route("/api/ping", methods=["POST"])
# def api_ping():
#     data = request.json
#     id_device = data.get("id")
#     ip_address = data.get("ip")

#     is_up = ping_host(ip_address)
#     status_str = "UP" if is_up else "DOWN"

#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "UPDATE devices SET last_status = %s, last_checked = NOW() WHERE id = %s"
#         cursor.execute(sql, (status_str, id_device))
#         conn.commit()
#         cursor.close()
#         conn.close()
#     except Exception as e:
#         print("Error DB:", e)


#     return jsonify(
#         {
#             "id": id_device,
#             "ip": ip_address,
#             "status": "up" if is_up else "down",
#             "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#         }
#     )
@app.route("/api/ping", methods=["POST"])
def api_ping():
    data = request.json
    id_device = data.get("id")
    ip_address = data.get("ip")

    # 1. Lakukan Ping
    is_up = ping_host(ip_address)
    new_status = "UP" if is_up else "DOWN"

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)  # Pakai dictionary cursor biar gampang

        # 2. Ambil Status Lama dari DB
        cursor.execute("SELECT last_status FROM devices WHERE id = %s", (id_device,))
        result = cursor.fetchone()
        old_status = result["last_status"] if result else None

        # 3. Cek Perubahan Status (CHANGE DETECTION)
        # Catat ke log HANYA jika status berubah (misal UP -> DOWN)
        # Atau jika ini ping pertama kali (old_status None)
        if old_status != new_status:
            print(
                f"Status Change Detected for {ip_address}: {old_status} -> {new_status}"
            )
            cursor.execute(
                "INSERT INTO device_logs (device_id, status, event_time) VALUES (%s, %s, NOW())",
                (id_device, new_status),
            )

        # 4. Update Status Terkini di tabel devices
        sql_update = (
            "UPDATE devices SET last_status = %s, last_checked = NOW() WHERE id = %s"
        )
        cursor.execute(sql_update, (new_status, id_device))

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error DB Ping:", e)

    # Format waktu untuk respon JSON
    current_time_str = datetime.now().strftime("%H:%M:%S")  # Jam simpel untuk UI

    return jsonify(
        {
            "id": id_device,
            "ip": ip_address,
            "status": "up" if is_up else "down",
            "last_checked": current_time_str,
        }
    )


# API: Tambah Perangkat (Create)
@app.route("/api/add", methods=["POST"])
def add_device():
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO devices (name, ip_address) VALUES (%s, %s)"
        cursor.execute(sql, (data["name"], data["ip"]))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# API: Edit Perangkat (Update)
@app.route("/api/edit", methods=["POST"])
def edit_device():
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "UPDATE devices SET name = %s, ip_address = %s WHERE id = %s"
        cursor.execute(sql, (data["name"], data["ip"], data["id"]))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# API: Hapus Perangkat (Delete)
@app.route("/api/delete", methods=["POST"])
def delete_device():
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM devices WHERE id = %s"
        cursor.execute(sql, (data["id"],))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/analyze", methods=["GET"])
def analyze_network():
    # Cek apakah API Key ada
    if not GENAI_API_KEY:
        return jsonify(
            {
                "success": False,
                "error": "API Key Gemini belum dipasang di docker-compose.",
            }
        )

    try:
        # 1. Ambil Data dari Database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT name, ip_address, last_status, last_checked FROM devices"
        )
        devices = cursor.fetchall()
        cursor.close()
        conn.close()

        # 2. Siapkan Data JSON string untuk dikirim ke Gemini
        import json

        devices_json = json.dumps(devices, default=str)

        # 3. Buat Prompt (Instruksi ke AI)
        prompt = f"""
        Bertindaklah sebagai Senior Network Engineer. Analisa data status jaringan berikut dalam format JSON:
        {devices_json}

        Instruksi:
        1. Berikan kesimpulan status jaringan saat ini (AMAN, WASPADA, atau KRITIS).
        2. Jika ada device status 'DOWN', jelaskan potensi dampaknya dan berikan langkah troubleshooting teknis yang spesifik.
        3. Jika semua 'UP', berikan satu tips maintenance singkat.
        4. Gunakan bahasa Indonesia yang santai tapi profesional. Jangan gunakan markdown bold (**) terlalu banyak.
        
        Jawablah dengan ringkas.
        """

        # 4. Kirim ke Gemini
        response = model.generate_content(prompt)

        # Ambil text hasilnya
        ai_analysis = response.text

        return jsonify({"success": True, "analysis": ai_analysis})

    except Exception as e:
        print("Error Gemini:", e)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/chat", methods=["POST"])
def chat_network():
    if not GENAI_API_KEY:
        return jsonify({"success": False, "error": "API Key belum diset."})

    data = request.json
    user_message = data.get("message", "")
    history = data.get(
        "history", []
    )  # Kita terima history chat dari frontend jika perlu

    try:
        # 1. Ambil Data Realtime (Supaya AI tahu kondisi TERBARU saat ditanya)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT name, ip_address, last_status, last_checked FROM devices"
        )
        devices = cursor.fetchall()
        cursor.close()
        conn.close()

        # Konversi ke JSON string
        import json

        devices_json = json.dumps(devices, default=str)

        # 2. Definisikan Persona & Konteks
        # Kita masukkan data jaringan ke dalam 'System Instruction'
        system_instruction = f"""
        Kamu adalah 'Network AI Assistant', asisten cerdas untuk monitoring jaringan.
        DATA LIVE JARINGAN SAAT INI (JSON):
        {devices_json}

        TUGAS KAMU:
        1. Jawab pertanyaan user berdasarkan data jaringan di atas.
        2. Jika user bertanya "Analisa", berikan ringkasan status, perangkat yang DOWN, dan solusi.
        3. Jika user bertanya teknis (misal: "Apa itu ICMP?"), jelaskan dengan singkat.
        4. Gaya bahasa: Profesional, membantu, dan berbahasa Indonesia.
        5. Jangan mengarang data. Jika status UP bilang UP, jika DOWN bilang DOWN.
        """

        # 3. Siapkan Model
        # Catatan: Kita mengirim 'history' manual atau one-shot prompt agar stateless & ringan
        # model = genai.GenerativeModel("gemini-1.5-flash")

        # Buat Chat Session (Simplifikasi: Kita kirim prompt gabungan untuk hemat token)
        # Format: System Context + User Question
        final_prompt = f"{system_instruction}\n\nUser bertanya: {user_message}\nJawab:"

        response = model.generate_content(final_prompt)
        ai_reply = response.text

        return jsonify({"success": True, "reply": ai_reply})

    except Exception as e:
        print("Error Chat:", e)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/history", methods=["GET"])
def get_history():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Join tabel logs dengan devices untuk dapat nama device-nya
        # Urutkan dari kejadian paling baru
        query = """
            SELECT l.status, l.event_time, d.name, d.ip_address 
            FROM device_logs l
            JOIN devices d ON l.device_id = d.id
            ORDER BY l.event_time DESC
            LIMIT 50
        """
        cursor.execute(query)
        logs = cursor.fetchall()

        # Format tanggal biar cantik (pakai fungsi format_indo yg kita buat sebelumnya)
        for log in logs:
            if log["event_time"]:
                log["event_time"] = format_indo(log["event_time"])

        cursor.close()
        conn.close()
        return jsonify({"success": True, "logs": logs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# --- ROUTE LOGIN ---
@app.route("/login", methods=["GET", "POST"])
def login():
    # Jika sudah login, lempar ke dashboard
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        # Cek Password Hash
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))
        else:
            flash("Username atau Password salah!", "danger")

    return render_template("login.html")


# --- ROUTE LOGOUT ---
@app.route("/logout")
def logout():
    session.clear()  # Hapus sesi
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
