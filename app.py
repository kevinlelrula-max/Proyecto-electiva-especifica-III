from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import hashlib
import secrets
import os
import resend
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = "climalink_pesquera_2026_secure"

# ─── BASE DE DATOS ───────────────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://climalink:rTzY0aKIvu9f1MHUQVT0ZXo3t0xoXBhj@dpg-d7rqlv7avr4c73a43k70-a.oregon-postgres.render.com/climalink"
)

NODE_RED_URL = os.environ.get("NODE_RED_URL", "http://localhost:1880/ui")

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id SERIAL PRIMARY KEY,
            congelador TEXT,
            temperatura REAL,
            humedad REAL,
            especie TEXT,
            tiempo INTEGER,
            estado TEXT,
            fecha TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email_alerta TEXT,
            app_password TEXT,
            reset_token TEXT,
            activo INTEGER DEFAULT 1
        )
    """)

    password_hash = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute("""
        INSERT INTO usuarios (nombre, username, password)
        VALUES (%s, %s, %s)
        ON CONFLICT (username) DO NOTHING
    """, ("Administrador", "admin", password_hash))

    conn.commit()
    cursor.close()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ─── LOGIN ───────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM usuarios WHERE username = %s AND password = %s AND activo = 1",
            (username, hash_password(password))
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session["usuario"] = username
            session["nombre"] = user["nombre"]
            return redirect(NODE_RED_URL)
        else:
            flash("error|Usuario o contraseña incorrectos.")

    return render_template("login.html")

# ─── REGISTRO ────────────────────────────────────────────

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre       = request.form.get("nombre", "").strip()
        username     = request.form.get("username", "").strip()
        password     = request.form.get("password", "").strip()
        confirm      = request.form.get("confirm", "").strip()
        email_alerta = request.form.get("email_alerta", "").strip()
        app_password = request.form.get("app_password", "").strip()

        if not nombre or not username or not password:
            flash("error|Todos los campos son obligatorios.")
            return render_template("registro.html")
        if len(password) < 6:
            flash("error|La contraseña debe tener al menos 6 caracteres.")
            return render_template("registro.html")
        if password != confirm:
            flash("error|Las contraseñas no coinciden.")
            return render_template("registro.html")

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (nombre, username, password, email_alerta, app_password) VALUES (%s, %s, %s, %s, %s)",
                (nombre, username, hash_password(password), email_alerta or None, app_password or None)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash("success|Cuenta creada correctamente.")
            return redirect(url_for("login"))
        except psycopg2.errors.UniqueViolation:
            flash("error|Usuario ya existe.")

    return render_template("registro.html")

# ─── RECUPERAR ───────────────────────────────────────────

@app.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        username = request.form.get("username", "").strip()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user:
            token = secrets.token_hex(16)
            cursor.execute(
                "UPDATE usuarios SET reset_token = %s WHERE username = %s",
                (token, username)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for("reset", token=token))
        else:
            cursor.close()
            conn.close()
            flash("error|Usuario no encontrado.")

    return render_template("recuperar.html")

# ─── RESET ───────────────────────────────────────────────

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE reset_token = %s", (token,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        flash("error|Token inválido.")
        return redirect(url_for("login"))

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm", "").strip()

        if password != confirm:
            flash("error|Las contraseñas no coinciden.")
            return render_template("reset.html", token=token)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuarios SET password = %s, reset_token = NULL WHERE reset_token = %s",
            (hash_password(password), token)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash("success|Contraseña actualizada.")
        return redirect(url_for("login"))

    return render_template("reset.html", token=token)

# ─── HISTORIAL ───────────────────────────────────────────

@app.route("/historial")
def historial():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    congelador = request.args.get("congelador", "")
    especie    = request.args.get("especie", "")
    estado     = request.args.get("estado", "")

    query  = "SELECT * FROM registros WHERE 1=1"
    params = []

    if congelador:
        query += " AND congelador = %s"
        params.append(congelador)
    if especie:
        query += " AND especie = %s"
        params.append(especie)
    if estado:
        query += " AND estado = %s"
        params.append(estado)

    query += " ORDER BY id DESC LIMIT 200"

    cursor.execute(query, params)
    registros = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM registros")
    total = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) FROM registros WHERE estado='RIESGO'")
    riesgos = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) FROM registros WHERE estado='OPTIMO'")
    optimos = cursor.fetchone()["count"]

    cursor.close()
    conn.close()

    return render_template(
        "historial.html",
        registros=registros,
        total=total,
        riesgos=riesgos,
        optimos=optimos,
        filtro_congelador=congelador,
        filtro_especie=especie,
        filtro_estado=estado
    )

# ─── ALERTA EMAIL ────────────────────────────────────────

@app.route("/alerta-email", methods=["POST"])
def alerta_email():
    try:
        data = request.get_json()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT email_alerta, app_password FROM usuarios WHERE activo = 1 AND email_alerta IS NOT NULL ORDER BY id DESC LIMIT 1"
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user or not user["email_alerta"] or not user["app_password"]:
            return jsonify({"error": "No hay credenciales de email configuradas"}), 400

        destinatario = user["email_alerta"]
        resend_api_key = os.environ.get("RESEND_API_KEY", "")

        if not resend_api_key:
            return jsonify({"error": "RESEND_API_KEY no configurada"}), 400

        congelador  = data.get("congelador", "?")
        alerta_tipo = data.get("alerta_tipo", "")
        temperatura = data.get("temperatura", "N/A")
        especie     = data.get("especie", "N/A")
        alerta_msg  = data.get("alerta_msg", "")

        emoji = "🔴" if alerta_tipo == "TEMP_CRÍTICA" else "🟠" if alerta_tipo == "TEMP_ELEVADA" else "⛔"

        asunto = f"{emoji} ALERTA Congelador {congelador} — {alerta_tipo}"
        cuerpo = f"""
        <html><body style="font-family:Arial,sans-serif;color:#333;">
        <h2 style="color:#c0392b;">{emoji} Alerta detectada — Congelador {congelador}</h2>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;">
            <tr><td><b>Congelador</b></td><td>{congelador}</td></tr>
            <tr><td><b>Tipo de alerta</b></td><td>{alerta_tipo}</td></tr>
            <tr><td><b>Temperatura</b></td><td>{temperatura} °C</td></tr>
            <tr><td><b>Especie</b></td><td>{especie}</td></tr>
            <tr><td><b>Mensaje</b></td><td>{alerta_msg}</td></tr>
        </table>
        <p style="margin-top:16px;">Revisa el sistema ClimaLink Station para más detalles.</p>
        </body></html>
        """

        resend.api_key = resend_api_key
        resend.Emails.send({
            "from": "ClimaLink <onboarding@resend.dev>",
            "to": [destinatario],
            "subject": asunto,
            "html": cuerpo
        })

        return jsonify({"ok": True}), 200

    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        return jsonify({"error": str(e)}), 500

# ─── LOGOUT ──────────────────────────────────────────────

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── MAIN ────────────────────────────────────────────────

init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5001)