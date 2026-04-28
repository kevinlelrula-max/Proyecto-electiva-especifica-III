from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import hashlib
import secrets

app = Flask(__name__)
app.secret_key = "climalink_pesquera_2026_secure"

DB_PATH = "datos.db"

# ───────────────────────── DB ─────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            reset_token TEXT,
            activo INTEGER DEFAULT 1
        )
    """)

    password_hash = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute("""
        INSERT OR IGNORE INTO usuarios (nombre, username, password)
        VALUES (?, ?, ?)
    """, ("Administrador", "admin", password_hash))

    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ───────────────────────── LOGIN ─────────────────────────

@app.route("/", methods=["GET", "POST"])
def login():

    # ❌ IMPORTANTE: YA NO AUTO-REDIRECT A NODE-RED

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM usuarios WHERE username = ? AND password = ? AND activo = 1",
            (username, hash_password(password))
        ).fetchone()
        conn.close()

        if user:
            session["usuario"] = username
            session["nombre"] = user["nombre"]

            # ✔ SOLO AQUÍ ENTRAS AL DASHBOARD IoT
            return redirect("http://localhost:1880/ui")
        else:
            flash("error|Usuario o contraseña incorrectos.")

    return render_template("login.html")


# ───────────────────────── REGISTRO ─────────────────────────

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()

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
            conn.execute(
                "INSERT INTO usuarios (nombre, username, password) VALUES (?, ?, ?)",
                (nombre, username, hash_password(password))
            )
            conn.commit()
            conn.close()

            flash("success|Cuenta creada correctamente.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("error|Usuario ya existe.")

    return render_template("registro.html")


# ───────────────────────── RECUPERAR ─────────────────────────

@app.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        username = request.form.get("username", "").strip()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM usuarios WHERE username = ?",
            (username,)
        ).fetchone()

        if user:
            token = secrets.token_hex(16)
            conn.execute(
                "UPDATE usuarios SET reset_token = ? WHERE username = ?",
                (token, username)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("reset", token=token))
        else:
            conn.close()
            flash("error|Usuario no encontrado.")

    return render_template("recuperar.html")


# ───────────────────────── RESET ─────────────────────────

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM usuarios WHERE reset_token = ?",
        (token,)
    ).fetchone()
    conn.close()

    if not user:
        flash("error|Token inválido.")
        return redirect(url_for("login"))

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()

        if password != confirm:
            flash("error|Las contraseñas no coinciden.")
            return render_template("reset.html", token=token)

        conn = get_db()
        conn.execute(
            "UPDATE usuarios SET password = ?, reset_token = NULL WHERE reset_token = ?",
            (hash_password(password), token)
        )
        conn.commit()
        conn.close()

        flash("success|Contraseña actualizada.")
        return redirect(url_for("login"))

    return render_template("reset.html", token=token)


# ───────────────────────── HISTORIAL ─────────────────────────

@app.route("/historial")
def historial():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    congelador = request.args.get("congelador", "")
    especie = request.args.get("especie", "")
    estado = request.args.get("estado", "")

    query = "SELECT * FROM registros WHERE 1=1"
    params = []

    if congelador:
        query += " AND congelador = ?"
        params.append(congelador)

    if especie:
        query += " AND especie = ?"
        params.append(especie)

    if estado:
        query += " AND estado = ?"
        params.append(estado)

    query += " ORDER BY id DESC LIMIT 200"

    registros = conn.execute(query, params).fetchall()

    total = conn.execute("SELECT COUNT(*) FROM registros").fetchone()[0]
    riesgos = conn.execute("SELECT COUNT(*) FROM registros WHERE estado='RIESGO'").fetchone()[0]
    optimos = conn.execute("SELECT COUNT(*) FROM registros WHERE estado='OPTIMO'").fetchone()[0]

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


# ───────────────────────── LOGOUT ─────────────────────────

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ───────────────────────── MAIN ─────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001)