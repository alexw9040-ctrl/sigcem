import csv
import io
import json
import os
import shutil
import sqlite3
import tempfile
import unicodedata
import zipfile
from datetime import datetime, date
from functools import wraps
from pathlib import Path
from typing import Any, cast

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
BACKUP_DIR = DATA_DIR / "backups"
DB_PATH = DATA_DIR / "sigcem.db"
for folder in (DATA_DIR, UPLOAD_DIR, BACKUP_DIR, BASE_DIR / "public"):
    folder.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get("SIGCEM_SECRET", "sigcem-local-change-this-secret"), MAX_CONTENT_LENGTH=24 * 1024 * 1024)
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE, password_hash TEXT NOT NULL, nome TEXT NOT NULL, perfil TEXT NOT NULL DEFAULT 'Atendente administrativo', bloqueado INTEGER NOT NULL DEFAULT 0, tentativas INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS deceased (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE NOT NULL, nome TEXT NOT NULL, nome_social TEXT, sexo TEXT, nascimento TEXT, idade INTEGER, naturalidade TEXT, nacionalidade TEXT DEFAULT 'Brasileira', estado_civil TEXT, nome_mae TEXT, nome_pai TEXT, cpf TEXT, rg TEXT, certidao TEXT, declaracao_obito TEXT, data_falecimento TEXT, hora_falecimento TEXT, local_falecimento TEXT, municipio_falecimento TEXT, causa TEXT, cartorio TEXT, matricula_certidao TEXT, medico TEXT, funeraria TEXT, observacoes TEXT, status TEXT NOT NULL DEFAULT 'Ativo', deleted_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS relatives (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, cpf TEXT, rg TEXT, telefone TEXT, whatsapp TEXT, email TEXT, endereco TEXT, municipio TEXT, parentesco TEXT, observacoes TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cemeteries (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, endereco TEXT, ativo INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS graves (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE NOT NULL, cemetery_id INTEGER, quadra TEXT NOT NULL, rua TEXT, lote TEXT, numero TEXT NOT NULL, structure_type TEXT NOT NULL DEFAULT 'Sepultura', capacity INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL DEFAULT 'Disponível', titular_id INTEGER, responsavel_id INTEGER, observacoes TEXT, x INTEGER, y INTEGER, created_at TEXT NOT NULL, FOREIGN KEY(cemetery_id) REFERENCES cemeteries(id), FOREIGN KEY(titular_id) REFERENCES relatives(id), FOREIGN KEY(responsavel_id) REFERENCES relatives(id));
CREATE TABLE IF NOT EXISTS burials (id INTEGER PRIMARY KEY AUTOINCREMENT, deceased_id INTEGER NOT NULL, grave_id INTEGER NOT NULL, data_sepultamento TEXT NOT NULL, hora_sepultamento TEXT, tipo TEXT, relative_id INTEGER, funeraria TEXT, documentacao TEXT, funcionario_id INTEGER, observacoes TEXT, protocolo TEXT UNIQUE NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, FOREIGN KEY(deceased_id) REFERENCES deceased(id), FOREIGN KEY(grave_id) REFERENCES graves(id), FOREIGN KEY(relative_id) REFERENCES relatives(id), FOREIGN KEY(funcionario_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS movements (id INTEGER PRIMARY KEY AUTOINCREMENT, deceased_id INTEGER NOT NULL, kind TEXT NOT NULL, origin_grave_id INTEGER, destination_grave_id INTEGER, request_date TEXT, execution_date TEXT, requester TEXT, relationship TEXT, reason TEXT, authorization TEXT, destination_note TEXT, responsible_id INTEGER, documents TEXT, notes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(deceased_id) REFERENCES deceased(id), FOREIGN KEY(origin_grave_id) REFERENCES graves(id), FOREIGN KEY(destination_grave_id) REFERENCES graves(id), FOREIGN KEY(responsible_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, protocolo TEXT UNIQUE NOT NULL, data_abertura TEXT NOT NULL, requerente TEXT NOT NULL, cpf TEXT, telefone TEXT, tipo TEXT NOT NULL, descricao TEXT, status TEXT NOT NULL DEFAULT 'Recebida', despacho TEXT, data_conclusao TEXT, responsavel_id INTEGER, created_at TEXT NOT NULL, FOREIGN KEY(responsavel_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS reforms (id INTEGER PRIMARY KEY AUTOINCREMENT, protocolo TEXT UNIQUE NOT NULL, data_solicitacao TEXT NOT NULL, solicitante TEXT NOT NULL, cpf TEXT, telefone TEXT, deceased_id INTEGER, grave_id INTEGER, tipo TEXT NOT NULL, descricao TEXT, executor TEXT, status TEXT NOT NULL DEFAULT 'Recebida', data_inicio TEXT, data_conclusao TEXT, observacoes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(deceased_id) REFERENCES deceased(id), FOREIGN KEY(grave_id) REFERENCES graves(id));
CREATE TABLE IF NOT EXISTS services (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, valor REAL NOT NULL DEFAULT 0, vigencia TEXT, fundamento TEXT, ativo INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS charges (id INTEGER PRIMARY KEY AUTOINCREMENT, service_id INTEGER NOT NULL, responsavel TEXT NOT NULL, cpf TEXT, protocolo TEXT, valor REAL NOT NULL, status TEXT NOT NULL DEFAULT 'Pendente', data_lancamento TEXT NOT NULL, data_pagamento TEXT, fundamento TEXT, created_at TEXT NOT NULL, FOREIGN KEY(service_id) REFERENCES services(id));
CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id INTEGER, nome TEXT NOT NULL, tipo TEXT NOT NULL, path TEXT NOT NULL, descricao TEXT, uploaded_by INTEGER, created_at TEXT NOT NULL, deleted_at TEXT, FOREIGN KEY(uploaded_by) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS maintenance_assets (id INTEGER PRIMARY KEY AUTOINCREMENT, identificacao TEXT NOT NULL, tipo TEXT NOT NULL, localizacao TEXT, aquisicao TEXT, estado TEXT, responsavel TEXT, observacoes TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS work_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, numero TEXT UNIQUE NOT NULL, data_abertura TEXT NOT NULL, descricao TEXT NOT NULL, local TEXT, responsavel TEXT, prioridade TEXT DEFAULT 'Normal', prazo TEXT, status TEXT DEFAULT 'Aberta', data_conclusao TEXT, observacoes TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, operacao TEXT NOT NULL, entidade TEXT, entidade_id INTEGER, anterior TEXT, atual TEXT, justificativa TEXT, created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS backups (id INTEGER PRIMARY KEY AUTOINCREMENT, arquivo TEXT NOT NULL, tipo TEXT NOT NULL, tamanho INTEGER, responsavel_id INTEGER, resultado TEXT, created_at TEXT NOT NULL, FOREIGN KEY(responsavel_id) REFERENCES users(id));
CREATE INDEX IF NOT EXISTS idx_deceased_nome ON deceased(nome);
CREATE INDEX IF NOT EXISTS idx_deceased_cpf ON deceased(cpf);
CREATE INDEX IF NOT EXISTS idx_burials_date ON burials(data_sepultamento);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit(created_at);
"""

DEFAULT_SETTINGS = {
    "municipio": "Ararendá – Ceará",
    "prefeitura_nome": "Prefeitura Municipal de Ararendá",
    "cemiterio_nome": "Cemitério Municipal",
    "endereco": "Ararendá – CE",
    "setor_responsavel": "Administração do Cemitério",
    "email_institucional": "",
    "telefone_institucional": "",
    "status_personalizados": "Disponível, Ocupada, Parcialmente ocupada, Reservada, Interditada, Em manutenção, Abandonada, Em processo de regularização",
    "backup_auto": "0",
}


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today():
    return date.today().isoformat()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.create_function("unaccent", 1, lambda value: "".join(c for c in unicodedata.normalize("NFD", str(value or "")) if unicodedata.category(c) != "Mn").lower())
    return g.db


def query(sql, params=(), one=False) -> Any:
    cur = get_db().execute(sql, params)
    rows = cur.fetchone() if one else cur.fetchall()
    cur.close()
    return rows


def execute(sql, params=()):
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    return cur.lastrowid


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    for key, value in DEFAULT_SETTINGS.items():
        db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (key, value))
    db.execute("INSERT OR IGNORE INTO cemeteries(id,nome,endereco) VALUES(1,?,?)", (DEFAULT_SETTINGS["cemiterio_nome"], DEFAULT_SETTINGS["endereco"]))
    db.commit()
    db.close()


def settings_dict():
    return {r["key"]: r["value"] for r in query("SELECT key,value FROM settings")}


def audit(operation, entity=None, entity_id=None, before=None, after=None, justification=None):
    uid = session.get("user_id")
    execute("INSERT INTO audit(user_id,operacao,entidade,entidade_id,anterior,atual,justificativa,created_at) VALUES(?,?,?,?,?,?,?,?)", (uid, operation, entity, entity_id, json.dumps(before, ensure_ascii=False, default=str) if before is not None else None, json.dumps(after, ensure_ascii=False, default=str) if after is not None else None, justification, now()))


def current_user():
    uid = session.get("user_id")
    return query("SELECT * FROM users WHERE id=? AND bloqueado=0", (uid,), one=True) if uid else None


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login"))
            if user["perfil"] not in roles and user["perfil"] != "Administrador geral":
                flash("Seu perfil não possui permissão para esta operação.", "error")
                return redirect(request.referrer or url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapped
    return deco


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def next_number(prefix, table, column):
    row = query(f"SELECT COUNT(*) AS n FROM {table}", one=True)
    return f"{prefix}-{datetime.now().year}-{int(row['n']) + 1:05d}"


def status_class(status):
    if not status:
        return "gray"
    s = status.lower()
    if any(x in s for x in ("ocupada", "conclu", "paga", "deferida", "disponível", "recebida")) and "não" not in s:
        return "green" if "ocupada" not in s or "parcial" in s else "amber"
    if any(x in s for x in ("análise", "execução", "pendente", "reservada", "manutenção")):
        return "amber"
    if any(x in s for x in ("interdit", "indefer", "cancel", "abandon")):
        return "red"
    return "blue"


@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "settings": settings_dict(), "status_class": status_class, "today": today}


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/healthz")
def healthz():
    return jsonify({"ok": True, "service": "sigcem", "database": str(DB_PATH.name)})


@app.route("/manus-routes.json")
def manus_routes():
    return send_file(BASE_DIR / "public" / "manus-routes.json", mimetype="application/json")


@app.route("/")
def index():
    if not query("SELECT id FROM users LIMIT 1", one=True):
        return redirect(url_for("setup"))
    return redirect(url_for("dashboard" if current_user() else "login"))


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if query("SELECT id FROM users LIMIT 1", one=True):
        return redirect(url_for("login"))
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower() or None
        password = request.form.get("password", "")
        if not nome or not username or len(password) < 8:
            flash("Informe nome, usuário e uma senha com pelo menos 8 caracteres.", "error")
        else:
            uid = execute("INSERT INTO users(username,email,password_hash,nome,perfil,created_at) VALUES(?,?,?,?,?,?)", (username, email, generate_password_hash(password), nome, "Administrador geral", now()))
            session["user_id"] = uid
            audit("Administrador inicial criado", "users", uid, after={"username": username, "perfil": "Administrador geral"})
            flash("Administrador criado. O SIGCEM está pronto para iniciar a configuração.", "success")
            return redirect(url_for("dashboard"))
    return render_template("setup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        identity = request.form.get("identity", "").strip().lower()
        password = request.form.get("password", "")
        user = query("SELECT * FROM users WHERE lower(username)=? OR lower(email)=?", (identity, identity), one=True)
        if not user or user["bloqueado"] or not check_password_hash(user["password_hash"], password):
            if user:
                execute("UPDATE users SET tentativas=tentativas+1 WHERE id=?", (user["id"],))
            flash("Usuário, e-mail ou senha inválidos.", "error")
        else:
            execute("UPDATE users SET tentativas=0 WHERE id=?", (user["id"],))
            session.clear()
            session["user_id"] = user["id"]
            audit("Login realizado", "users", user["id"])
            return redirect(request.args.get("next") or url_for("dashboard"))
    if not query("SELECT id FROM users LIMIT 1", one=True):
        return redirect(url_for("setup"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    uid = session.get("user_id")
    if uid:
        audit("Logout realizado", "users", uid)
    session.clear()
    return redirect(url_for("login"))


@app.route("/api/dashboard")
@login_required
def api_dashboard():
    return jsonify(dashboard_data())


def dashboard_data():
    metrics = {
        "falecidos": query("SELECT COUNT(*) n FROM deceased WHERE deleted_at IS NULL", one=True)["n"],
        "sepultamentos": query("SELECT COUNT(*) n FROM burials WHERE active=1", one=True)["n"],
        "sepulturas": query("SELECT COUNT(*) n FROM graves", one=True)["n"],
        "ocupadas": query("SELECT COUNT(*) n FROM graves WHERE status IN ('Ocupada','Parcialmente ocupada')", one=True)["n"],
        "disponiveis": query("SELECT COUNT(*) n FROM graves WHERE status='Disponível'", one=True)["n"],
        "interditadas": query("SELECT COUNT(*) n FROM graves WHERE status='Interditada'", one=True)["n"],
        "jazigos": query("SELECT COUNT(*) n FROM graves WHERE lower(structure_type)='jazigo'", one=True)["n"],
        "catacumbas": query("SELECT COUNT(*) n FROM graves WHERE lower(structure_type)='catacumba'", one=True)["n"],
        "solicitacoes": query("SELECT COUNT(*) n FROM requests WHERE status NOT IN ('Concluída','Indeferida','Cancelada')", one=True)["n"],
        "exumacoes": query("SELECT COUNT(*) n FROM movements WHERE kind='Exumação'", one=True)["n"],
        "transferencias": query("SELECT COUNT(*) n FROM movements WHERE kind='Transferência'", one=True)["n"],
        "reformas": query("SELECT COUNT(*) n FROM reforms WHERE status IN ('Em execução','Deferida')", one=True)["n"],
        "manutencoes": query("SELECT COUNT(*) n FROM work_orders WHERE status NOT IN ('Concluída','Cancelada')", one=True)["n"],
    }
    chart = []
    for i in range(5, -1, -1):
        # SQLite date arithmetic is local and works without network.
        row = query("SELECT strftime('%Y-%m', date('now', ? || ' months')) mes", (f"-{i}",), one=True)
        mes = row["mes"]
        count = query("SELECT COUNT(*) n FROM burials WHERE substr(data_sepultamento,1,7)=?", (mes,), one=True)["n"]
        chart.append({"label": mes[5:7] + "/" + mes[2:4], "value": count})
    return {"metrics": metrics, "chart": chart}


@app.route("/dashboard")
@login_required
def dashboard():
    data = dashboard_data()
    latest_deceased = query("SELECT id,codigo,nome,data_falecimento,created_at FROM deceased WHERE deleted_at IS NULL ORDER BY id DESC LIMIT 5")
    latest_burials = query("SELECT b.id,b.protocolo,b.data_sepultamento,d.nome,g.codigo FROM burials b JOIN deceased d ON d.id=b.deceased_id JOIN graves g ON g.id=b.grave_id ORDER BY b.id DESC LIMIT 5")
    pending = query("SELECT protocolo,requerente,tipo,status FROM requests WHERE status NOT IN ('Concluída','Indeferida','Cancelada') ORDER BY id DESC LIMIT 5")
    alerts = []
    missing = query("SELECT COUNT(*) n FROM deceased WHERE deleted_at IS NULL AND (certidao IS NULL OR certidao='')", one=True)["n"]
    if missing:
        alerts.append(f"{missing} cadastro(s) de falecido sem número de certidão")
    if data["metrics"]["manutencoes"]:
        alerts.append(f"{data['metrics']['manutencoes']} ordem(ns) de serviço aguardam conclusão")
    return render_template("dashboard.html", data=data, latest_deceased=latest_deceased, latest_burials=latest_burials, pending=pending, alerts=alerts)


@app.route("/falecidos")
@login_required
def falecidos():
    q = request.args.get("q", "").strip()
    params = []
    sql = "SELECT d.*, (SELECT COUNT(*) FROM documents x WHERE x.entity_type='falecido' AND x.entity_id=d.id AND x.deleted_at IS NULL) doc_count, g.codigo grave_codigo, g.quadra FROM deceased d LEFT JOIN burials b ON b.deceased_id=d.id AND b.active=1 LEFT JOIN graves g ON g.id=b.grave_id WHERE d.deleted_at IS NULL"
    if q:
        like = f"%{q}%"
        sql += " AND (unaccent(d.nome) LIKE unaccent(?) OR unaccent(d.nome_social) LIKE unaccent(?) OR d.cpf LIKE ? OR unaccent(d.nome_mae) LIKE unaccent(?) OR d.certidao LIKE ? OR g.codigo LIKE ? OR g.quadra LIKE ?)"
        params += [like] * 7
    sql += " ORDER BY d.nome LIMIT 300"
    rows = query(sql, params)
    return render_template("falecidos.html", rows=rows, q=q)


DECEASED_FIELDS = [
    ("nome", "Nome completo", "text", True), ("nome_social", "Nome social", "text", False), ("sexo", "Sexo", "select:Não informado|Feminino|Masculino|Outro", False),
    ("nascimento", "Data de nascimento", "date", False), ("idade", "Idade no falecimento", "number", False), ("naturalidade", "Naturalidade", "text", False), ("nacionalidade", "Nacionalidade", "text", False), ("estado_civil", "Estado civil", "text", False),
    ("nome_mae", "Nome da mãe", "text", False), ("nome_pai", "Nome do pai", "text", False), ("cpf", "CPF", "text", False), ("rg", "RG", "text", False), ("certidao", "Nº da certidão de óbito", "text", False), ("declaracao_obito", "Nº da Declaração de Óbito", "text", False),
    ("data_falecimento", "Data do falecimento", "date", True), ("hora_falecimento", "Horário", "time", False), ("local_falecimento", "Local do falecimento", "text", False), ("municipio_falecimento", "Município do falecimento", "text", False), ("cartorio", "Cartório responsável", "text", False), ("matricula_certidao", "Matrícula da certidão", "text", False), ("medico", "Médico responsável", "text", False), ("funeraria", "Funerária", "text", False),
]


def deceased_form_data(form):
    return {key: (form.get(key, "").strip() or None) for key, _, _, _ in DECEASED_FIELDS}


@app.route("/falecidos/novo", methods=["GET", "POST"])
@login_required
def novo_falecido():
    if request.method == "POST":
        data = deceased_form_data(request.form)
        if not data["nome"] or not data["data_falecimento"]:
            flash("Nome e data do falecimento são obrigatórios.", "error")
        else:
            similar = query("SELECT id,nome FROM deceased WHERE deleted_at IS NULL AND lower(nome)=lower(?) AND (data_falecimento=? OR cpf=?)", (data["nome"], data["data_falecimento"], data.get("cpf") or "__none__"), one=True)
            if similar:
                flash(f"Possível duplicidade: já existe {similar['nome']} no cadastro. Revise antes de criar.", "warning")
            else:
                code = next_number("FAL", "deceased", "id")
                keys = ",".join(["codigo"] + list(data.keys()) + ["observacoes", "created_at", "updated_at"])
                marks = ",".join(["?"] * (len(data) + 4))
                did = execute(f"INSERT INTO deceased({keys}) VALUES({marks})", [code] + list(data.values()) + [request.form.get("observacoes") or None, now(), now()])
                audit("Cadastro de falecido criado", "deceased", did, after={"codigo": code, "nome": data["nome"]})
                flash(f"Falecido {code} cadastrado com sucesso.", "success")
                return redirect(url_for("falecido_detalhe", deceased_id=did))
    return render_template("falecido_form.html", fields=DECEASED_FIELDS, record=None, title="Novo falecido")


@app.route("/falecidos/<int:deceased_id>")
@login_required
def falecido_detalhe(deceased_id):
    record = query("SELECT * FROM deceased WHERE id=? AND deleted_at IS NULL", (deceased_id,), one=True)
    if not record:
        abort(404)
    docs = query("SELECT x.*,u.nome uploader FROM documents x LEFT JOIN users u ON u.id=x.uploaded_by WHERE x.entity_type='falecido' AND x.entity_id=? AND x.deleted_at IS NULL ORDER BY x.id DESC", (deceased_id,))
    burials = query("SELECT b.*,g.codigo,g.quadra,g.rua,g.numero FROM burials b JOIN graves g ON g.id=b.grave_id WHERE b.deceased_id=? ORDER BY b.id DESC", (deceased_id,))
    moves = query("SELECT m.*,og.codigo origem,dg.codigo destino FROM movements m LEFT JOIN graves og ON og.id=m.origin_grave_id LEFT JOIN graves dg ON dg.id=m.destination_grave_id WHERE m.deceased_id=? ORDER BY m.id DESC", (deceased_id,))
    relatives = query("SELECT r.* FROM relatives r JOIN burials b ON b.relative_id=r.id WHERE b.deceased_id=? GROUP BY r.id", (deceased_id,))
    return render_template("falecido_detail.html", record=record, docs=docs, burials=burials, moves=moves, relatives=relatives)


@app.route("/falecidos/<int:deceased_id>/editar", methods=["GET", "POST"])
@login_required
def editar_falecido(deceased_id):
    record = query("SELECT * FROM deceased WHERE id=? AND deleted_at IS NULL", (deceased_id,), one=True)
    if not record:
        abort(404)
    if request.method == "POST":
        data = deceased_form_data(request.form)
        data["observacoes"] = request.form.get("observacoes") or None
        sets = ",".join([f"{key}=?" for key in data]) + ",updated_at=?"
        execute(f"UPDATE deceased SET {sets} WHERE id=?", list(data.values()) + [now(), deceased_id])
        audit("Cadastro de falecido atualizado", "deceased", deceased_id, before=dict(record), after=data, justification=request.form.get("justificativa"))
        flash("Cadastro atualizado e alteração registrada no histórico.", "success")
        return redirect(url_for("falecido_detalhe", deceased_id=deceased_id))
    return render_template("falecido_form.html", fields=DECEASED_FIELDS, record=record, title="Editar falecido")


@app.route("/falecidos/<int:deceased_id>/excluir", methods=["POST"])
@roles_required("Administrador geral", "Administrador do cemitério")
def excluir_falecido(deceased_id):
    record = query("SELECT * FROM deceased WHERE id=? AND deleted_at IS NULL", (deceased_id,), one=True)
    if not record:
        abort(404)
    execute("UPDATE deceased SET deleted_at=?,status='Arquivado',updated_at=? WHERE id=?", (now(), now(), deceased_id))
    audit("Cadastro arquivado (exclusão lógica)", "deceased", deceased_id, before=dict(record), justification=request.form.get("justificativa"))
    flash("Registro arquivado; o histórico permanece preservado.", "success")
    return redirect(url_for("falecidos"))


@app.route("/sepulturas")
@login_required
def sepulturas():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    sql = "SELECT g.*,c.nome cemetery_name,r.nome responsavel_nome,(SELECT COUNT(*) FROM burials b WHERE b.grave_id=g.id AND b.active=1) used FROM graves g LEFT JOIN cemeteries c ON c.id=g.cemetery_id LEFT JOIN relatives r ON r.id=g.responsavel_id WHERE 1=1"
    params = []
    if q:
        sql += " AND (g.codigo LIKE ? OR g.quadra LIKE ? OR g.rua LIKE ? OR g.numero LIKE ?)"
        params += [f"%{q}%"] * 4
    if status:
        sql += " AND g.status=?"
        params.append(status)
    sql += " ORDER BY g.quadra,g.rua,g.numero LIMIT 500"
    rows = query(sql, params)
    return render_template("sepulturas.html", rows=rows, q=q, selected_status=status)


@app.route("/sepulturas/<int:grave_id>/editar", methods=["GET", "POST"])
@login_required
def editar_sepultura(grave_id):
    record = query("SELECT g.*,(SELECT COUNT(*) FROM burials b WHERE b.grave_id=g.id AND b.active=1) used FROM graves g WHERE g.id=?", (grave_id,), one=True)
    if not record:
        abort(404)
    if request.method == "POST":
        capacity = max(int(record["used"] or 0), int(request.form.get("capacity") or 1))
        before = dict(record)
        execute("UPDATE graves SET quadra=?,rua=?,lote=?,numero=?,structure_type=?,capacity=?,status=?,responsavel_id=?,observacoes=?,x=?,y=? WHERE id=?", (request.form.get("quadra"), request.form.get("rua"), request.form.get("lote"), request.form.get("numero"), request.form.get("structure_type"), capacity, request.form.get("status"), request.form.get("responsavel_id") or None, request.form.get("observacoes"), request.form.get("x") or None, request.form.get("y") or None, grave_id))
        audit("Unidade física atualizada", "graves", grave_id, before=before, after={"quadra": request.form.get("quadra"), "numero": request.form.get("numero"), "capacity": capacity, "status": request.form.get("status")}, justification=request.form.get("justificativa"))
        flash("Unidade física atualizada e registrada na auditoria.", "success")
        return redirect(url_for("sepulturas"))
    relatives = query("SELECT id,nome FROM relatives ORDER BY nome")
    statuses = [x.strip() for x in settings_dict().get("status_personalizados", "").split(",") if x.strip()]
    return render_template("sepultura_edit.html", record=record, relatives=relatives, statuses=statuses)
@app.route("/sepulturas/nova", methods=["GET", "POST"])
@login_required
def nova_sepultura():
    if request.method == "POST":
        quadra = request.form.get("quadra", "").strip()
        numero = request.form.get("numero", "").strip()
        if not quadra or not numero:
            flash("Quadra e número da unidade são obrigatórios.", "error")
        else:
            codigo = request.form.get("codigo", "").strip() or f"Q{quadra}-L{request.form.get('lote','').strip() or '0'}-S{numero}"
            try:
                gid = execute("INSERT INTO graves(codigo,cemetery_id,quadra,rua,lote,numero,structure_type,capacity,status,titular_id,responsavel_id,observacoes,x,y,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (codigo, 1, quadra, request.form.get("rua"), request.form.get("lote"), numero, request.form.get("structure_type") or "Sepultura", max(1, int(request.form.get("capacity") or 1)), request.form.get("status") or "Disponível", request.form.get("titular_id") or None, request.form.get("responsavel_id") or None, request.form.get("observacoes"), request.form.get("x") or None, request.form.get("y") or None, now()))
                audit("Unidade física criada", "graves", gid, after={"codigo": codigo, "quadra": quadra, "numero": numero})
                flash(f"Unidade {codigo} cadastrada.", "success")
                return redirect(url_for("sepulturas"))
            except sqlite3.IntegrityError:
                flash("O código da unidade já existe. Use uma identificação única.", "error")
    relatives = query("SELECT id,nome FROM relatives ORDER BY nome")
    statuses = [x.strip() for x in settings_dict().get("status_personalizados", "").split(",") if x.strip()]
    return render_template("sepultura_form.html", relatives=relatives, statuses=statuses)


@app.route("/mapa")
@login_required
def mapa():
    quadra = request.args.get("quadra", "")
    quads = query("SELECT DISTINCT quadra FROM graves ORDER BY quadra")
    sql = "SELECT g.*,(SELECT COUNT(*) FROM burials b WHERE b.grave_id=g.id AND b.active=1) used FROM graves g"
    params = []
    if quadra:
        sql += " WHERE g.quadra=?"
        params.append(quadra)
    sql += " ORDER BY g.quadra,g.rua,g.numero"
    cells = query(sql, params)
    return render_template("mapa.html", cells=cells, quads=quads, quadra=quadra)


@app.route("/sepultamentos/novo", methods=["GET", "POST"])
@login_required
def novo_sepultamento():
    if request.method == "POST":
        deceased_id = request.form.get("deceased_id")
        grave_id = request.form.get("grave_id")
        deceased = query("SELECT * FROM deceased WHERE id=? AND deleted_at IS NULL", (deceased_id,), one=True)
        grave = query("SELECT * FROM graves WHERE id=?", (grave_id,), one=True)
        used = query("SELECT COUNT(*) n FROM burials WHERE grave_id=? AND active=1", (grave_id,), one=True)["n"] if grave else 0
        if not deceased or not grave:
            flash("Selecione um falecido e uma unidade física válidos.", "error")
        elif grave["status"] in ("Interditada", "Em manutenção", "Abandonada") or used >= grave["capacity"]:
            flash("Esta unidade não está disponível ou não possui capacidade para receber o sepultamento.", "error")
        else:
            protocol = next_number("SEP", "burials", "id")
            bid = execute("INSERT INTO burials(deceased_id,grave_id,data_sepultamento,hora_sepultamento,tipo,relative_id,funeraria,documentacao,funcionario_id,observacoes,protocolo,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (deceased_id, grave_id, request.form.get("data_sepultamento") or today(), request.form.get("hora_sepultamento"), request.form.get("tipo"), request.form.get("relative_id") or None, request.form.get("funeraria"), request.form.get("documentacao"), session["user_id"], request.form.get("observacoes"), protocol, now()))
            new_status = "Ocupada" if used + 1 >= grave["capacity"] else "Parcialmente ocupada"
            execute("UPDATE graves SET status=? WHERE id=?", (new_status, grave_id))
            audit("Sepultamento registrado", "burials", bid, after={"protocolo": protocol, "falecido": deceased["nome"], "sepultura": grave["codigo"]})
            flash(f"Sepultamento registrado. Protocolo {protocol}.", "success")
            return redirect(url_for("falecido_detalhe", deceased_id=deceased_id))
    deceased_rows = query("SELECT id,codigo,nome FROM deceased WHERE deleted_at IS NULL ORDER BY nome")
    grave_rows = query("SELECT g.id,g.codigo,g.quadra,g.numero,g.capacity,g.status,(SELECT COUNT(*) FROM burials b WHERE b.grave_id=g.id AND b.active=1) used FROM graves g WHERE g.status NOT IN ('Interditada','Em manutenção','Abandonada') ORDER BY g.quadra,g.numero")
    relatives = query("SELECT id,nome FROM relatives ORDER BY nome")
    return render_template("sepultamento_form.html", deceased_rows=deceased_rows, grave_rows=grave_rows, relatives=relatives)


@app.route("/movimentacoes", methods=["GET", "POST"])
@login_required
def movimentacoes():
    if request.method == "POST":
        deceased_id = request.form.get("deceased_id")
        kind = request.form.get("kind") or "Exumação"
        origin = request.form.get("origin_grave_id") or None
        dest = request.form.get("destination_grave_id") or None
        mid = execute("INSERT INTO movements(deceased_id,kind,origin_grave_id,destination_grave_id,request_date,execution_date,requester,relationship,reason,authorization,destination_note,responsible_id,documents,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (deceased_id, kind, origin, dest, request.form.get("request_date") or today(), request.form.get("execution_date") or None, request.form.get("requester"), request.form.get("relationship"), request.form.get("reason"), request.form.get("authorization"), request.form.get("destination_note"), session["user_id"], request.form.get("documents"), request.form.get("notes"), now()))
        if kind in ("Exumação", "Transferência") and origin:
            execute("UPDATE burials SET active=0 WHERE deceased_id=? AND grave_id=?", (deceased_id, origin))
            remaining = query("SELECT COUNT(*) n FROM burials WHERE grave_id=? AND active=1", (origin,), one=True)["n"]
            origin_grave = query("SELECT capacity FROM graves WHERE id=?", (origin,), one=True)
            if origin_grave:
                new_origin_status = "Disponível" if remaining == 0 else ("Ocupada" if remaining >= origin_grave["capacity"] else "Parcialmente ocupada")
                execute("UPDATE graves SET status=? WHERE id=? AND status NOT IN ('Interditada','Em manutenção','Abandonada')", (new_origin_status, origin))
        if dest and kind in ("Transferência", "Reinumação"):
            grave = query("SELECT * FROM graves WHERE id=?", (dest,), one=True)
            used = query("SELECT COUNT(*) n FROM burials WHERE grave_id=? AND active=1", (dest,), one=True)["n"]
            if grave and used < grave["capacity"]:
                protocol = next_number("MOV", "burials", "id")
                execute("INSERT INTO burials(deceased_id,grave_id,data_sepultamento,tipo,funcionario_id,observacoes,protocolo,created_at) VALUES(?,?,?,?,?,?,?,?)", (deceased_id, dest, today(), kind, session["user_id"], "Movimentação vinculada ao histórico", protocol, now()))
                execute("UPDATE graves SET status=? WHERE id=?", ("Ocupada" if used + 1 >= grave["capacity"] else "Parcialmente ocupada", dest))
        audit(f"{kind} registrada", "movements", mid, after={"deceased_id": deceased_id, "origin": origin, "destination": dest})
        flash(f"{kind} registrada sem apagar o histórico anterior.", "success")
        return redirect(url_for("movimentacoes"))
    rows = query("SELECT m.*,d.nome,og.codigo origem,dg.codigo destino FROM movements m JOIN deceased d ON d.id=m.deceased_id LEFT JOIN graves og ON og.id=m.origin_grave_id LEFT JOIN graves dg ON dg.id=m.destination_grave_id ORDER BY m.id DESC")
    deceased_rows = query("SELECT id,nome FROM deceased WHERE deleted_at IS NULL ORDER BY nome")
    grave_rows = query("SELECT id,codigo FROM graves ORDER BY codigo")
    return render_template("movimentacoes.html", rows=rows, deceased_rows=deceased_rows, grave_rows=grave_rows)


@app.route("/familiares", methods=["GET", "POST"])
@login_required
def familiares():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("O nome do familiar é obrigatório.", "error")
        else:
            rid = execute("INSERT INTO relatives(nome,cpf,rg,telefone,whatsapp,email,endereco,municipio,parentesco,observacoes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (nome, request.form.get("cpf"), request.form.get("rg"), request.form.get("telefone"), request.form.get("whatsapp"), request.form.get("email"), request.form.get("endereco"), request.form.get("municipio"), request.form.get("parentesco"), request.form.get("observacoes"), now()))
            audit("Familiar/responsável criado", "relatives", rid, after={"nome": nome})
            flash("Familiar cadastrado.", "success")
    q = request.args.get("q", "").strip()
    rows = query("SELECT r.*,COUNT(DISTINCT b.deceased_id) vinculos FROM relatives r LEFT JOIN burials b ON b.relative_id=r.id WHERE r.nome LIKE ? GROUP BY r.id ORDER BY r.nome", (f"%{q}%",))
    return render_template("familiares.html", rows=rows, q=q)


@app.route("/solicitacoes", methods=["GET", "POST"])
@login_required
def solicitacoes():
    if request.method == "POST":
        protocolo = next_number("REQ", "requests", "id")
        rid = execute("INSERT INTO requests(protocolo,data_abertura,requerente,cpf,telefone,tipo,descricao,status,responsavel_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (protocolo, request.form.get("data_abertura") or today(), request.form.get("requerente"), request.form.get("cpf"), request.form.get("telefone"), request.form.get("tipo"), request.form.get("descricao"), "Recebida", session["user_id"], now()))
        audit("Solicitação protocolada", "requests", rid, after={"protocolo": protocolo})
        flash(f"Solicitação registrada com o protocolo {protocolo}.", "success")
        return redirect(url_for("solicitacoes"))
    rows = query("SELECT r.*,u.nome responsavel_nome FROM requests r LEFT JOIN users u ON u.id=r.responsavel_id ORDER BY r.id DESC")
    return render_template("solicitacoes.html", rows=rows)


@app.route("/familiares/<int:relative_id>/editar", methods=["GET", "POST"])
@login_required
def editar_familiar(relative_id):
    record = query("SELECT * FROM relatives WHERE id=?", (relative_id,), one=True)
    if not record:
        abort(404)
    if request.method == "POST":
        before = dict(record)
        execute("UPDATE relatives SET nome=?,cpf=?,rg=?,telefone=?,whatsapp=?,email=?,endereco=?,municipio=?,parentesco=?,observacoes=? WHERE id=?", tuple(request.form.get(k) for k in ("nome","cpf","rg","telefone","whatsapp","email","endereco","municipio","parentesco","observacoes")) + (relative_id,))
        audit("Familiar/responsável atualizado", "relatives", relative_id, before=before, after={"nome": request.form.get("nome")}, justification=request.form.get("justificativa"))
        flash("Familiar atualizado.", "success")
        return redirect(url_for("familiares"))
    return render_template("familiar_form.html", record=record)
@app.route("/solicitacoes/<int:req_id>/status", methods=["POST"])
@login_required
def atualizar_solicitacao(req_id):
    r = query("SELECT * FROM requests WHERE id=?", (req_id,), one=True)
    if not r:
        abort(404)
    status = request.form.get("status") or r["status"]
    execute("UPDATE requests SET status=?,despacho=?,data_conclusao=? WHERE id=?", (status, request.form.get("despacho"), today() if status in ("Concluída", "Indeferida", "Cancelada") else None, req_id))
    audit("Situação de solicitação atualizada", "requests", req_id, before=dict(r), after={"status": status})
    flash("Tramitação atualizada.", "success")
    return redirect(url_for("solicitacoes"))


@app.route("/solicitacoes/<int:req_id>/editar", methods=["GET", "POST"])
@login_required
def editar_solicitacao(req_id):
    record = query("SELECT * FROM requests WHERE id=?", (req_id,), one=True)
    if not record:
        abort(404)
    if request.method == "POST":
        before = dict(record)
        status = request.form.get("status") or record["status"]
        concluida = today() if status in ("Concluída", "Indeferida", "Cancelada") else None
        execute("UPDATE requests SET data_abertura=?,requerente=?,cpf=?,telefone=?,tipo=?,descricao=?,status=?,despacho=?,data_conclusao=? WHERE id=?", (request.form.get("data_abertura") or record["data_abertura"], request.form.get("requerente"), request.form.get("cpf"), request.form.get("telefone"), request.form.get("tipo"), request.form.get("descricao"), status, request.form.get("despacho"), concluida, req_id))
        audit("Solicitação editada", "requests", req_id, before=before, after={"status": status, "requerente": request.form.get("requerente")}, justification=request.form.get("justificativa"))
        flash("Solicitação atualizada.", "success")
        return redirect(url_for("solicitacoes"))
    tipos = ["Solicitação de sepultamento","Solicitação de exumação","Solicitação de transferência","Solicitação de declaração","Solicitação de localização de falecido","Atualização cadastral","Correção de informações","Regularização de sepultura","Outras solicitações"]
    statuses = ["Recebida","Em análise","Aguardando documentação","Concluída","Indeferida","Cancelada"]
    return render_template("solicitacao_form.html", record=record, tipos=tipos, statuses=statuses)
@app.route("/reformas", methods=["GET", "POST"])
@login_required
def reformas():
    if request.method == "POST":
        protocolo = next_number("OBR", "reforms", "id")
        rid = execute("INSERT INTO reforms(protocolo,data_solicitacao,solicitante,cpf,telefone,deceased_id,grave_id,tipo,descricao,executor,status,observacoes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (protocolo, request.form.get("data_solicitacao") or today(), request.form.get("solicitante"), request.form.get("cpf"), request.form.get("telefone"), request.form.get("deceased_id") or None, request.form.get("grave_id") or None, request.form.get("tipo"), request.form.get("descricao"), request.form.get("executor"), "Recebida", request.form.get("observacoes"), now()))
        audit("Solicitação de obra criada", "reforms", rid, after={"protocolo": protocolo, "tipo": request.form.get("tipo")})
        flash(f"Obra protocolada como {protocolo}.", "success")
        return redirect(url_for("reformas"))
    rows = query("SELECT r.*,d.nome falecido,g.codigo sepultura FROM reforms r LEFT JOIN deceased d ON d.id=r.deceased_id LEFT JOIN graves g ON g.id=r.grave_id ORDER BY r.id DESC")
    return render_template("reformas.html", rows=rows)


@app.route("/reformas/<int:reform_id>/editar", methods=["GET", "POST"])
@login_required
def editar_reforma(reform_id):
    record = query("SELECT * FROM reforms WHERE id=?", (reform_id,), one=True)
    if not record:
        abort(404)
    if request.method == "POST":
        before = dict(record)
        execute("UPDATE reforms SET data_solicitacao=?,solicitante=?,cpf=?,telefone=?,deceased_id=?,grave_id=?,tipo=?,descricao=?,executor=?,status=?,observacoes=? WHERE id=?", (request.form.get("data_solicitacao") or record["data_solicitacao"], request.form.get("solicitante"), request.form.get("cpf"), request.form.get("telefone"), request.form.get("deceased_id") or None, request.form.get("grave_id") or None, request.form.get("tipo"), request.form.get("descricao"), request.form.get("executor"), request.form.get("status") or record["status"], request.form.get("observacoes"), reform_id))
        audit("Solicitação de obra atualizada", "reforms", reform_id, before=before, after={"protocolo": record["protocolo"], "status": request.form.get("status")}, justification=request.form.get("justificativa"))
        flash("Obra atualizada e registrada na auditoria.", "success")
        return redirect(url_for("reformas"))
    tipos = ["Reforma de túmulo","Construção de jazigo","Construção de catacumba","Pintura","Revestimento","Ampliação","Substituição de lápide","Instalação de placa","Manutenção estrutural","Outra intervenção"]
    statuses = ["Recebida","Em análise","Aguardando documentação","Deferida","Indeferida","Em execução","Concluída","Cancelada"]
    return render_template("reforma_form.html", record=record, tipos=tipos, statuses=statuses, deceased_rows=query("SELECT id,nome FROM deceased WHERE deleted_at IS NULL ORDER BY nome"), grave_rows=query("SELECT id,codigo FROM graves ORDER BY codigo"))
@app.route("/manutencao", methods=["GET", "POST"])
@login_required
def manutencao():
    if request.method == "POST":
        if request.form.get("kind") == "asset":
            aid = execute("INSERT INTO maintenance_assets(identificacao,tipo,localizacao,aquisicao,estado,responsavel,observacoes,created_at) VALUES(?,?,?,?,?,?,?,?)", (request.form.get("identificacao"), request.form.get("tipo"), request.form.get("localizacao"), request.form.get("aquisicao"), request.form.get("estado"), request.form.get("responsavel"), request.form.get("observacoes"), now()))
            audit("Patrimônio cadastrado", "maintenance_assets", aid)
        else:
            num = next_number("OS", "work_orders", "id")
            oid = execute("INSERT INTO work_orders(numero,data_abertura,descricao,local,responsavel,prioridade,prazo,status,observacoes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (num, request.form.get("data_abertura") or today(), request.form.get("descricao"), request.form.get("local"), request.form.get("responsavel"), request.form.get("prioridade") or "Normal", request.form.get("prazo"), "Aberta", request.form.get("observacoes"), now()))
            audit("Ordem de serviço criada", "work_orders", oid, after={"numero": num})
            flash(f"Ordem de serviço {num} criada.", "success")
        return redirect(url_for("manutencao"))
    assets = query("SELECT * FROM maintenance_assets ORDER BY id DESC")
    orders = query("SELECT * FROM work_orders ORDER BY id DESC")
    return render_template("manutencao.html", assets=assets, orders=orders)


@app.route("/manutencao/<kind>/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
def editar_manutencao(kind, item_id):
    table = "work_orders" if kind == "order" else "maintenance_assets" if kind == "asset" else None
    if not table:
        abort(404)
    record = query(f"SELECT * FROM {table} WHERE id=?", (item_id,), one=True)
    if not record:
        abort(404)
    if request.method == "POST":
        before = dict(record)
        if kind == "order":
            execute("UPDATE work_orders SET data_abertura=?,descricao=?,local=?,responsavel=?,prioridade=?,prazo=?,status=?,observacoes=? WHERE id=?", (request.form.get("data_abertura") or record["data_abertura"], request.form.get("descricao"), request.form.get("local"), request.form.get("responsavel"), request.form.get("prioridade"), request.form.get("prazo") or None, request.form.get("status"), request.form.get("observacoes"), item_id))
        else:
            execute("UPDATE maintenance_assets SET identificacao=?,tipo=?,localizacao=?,aquisicao=?,estado=?,responsavel=?,observacoes=? WHERE id=?", tuple(request.form.get(k) for k in ("identificacao","tipo","localizacao","aquisicao","estado","responsavel","observacoes")) + (item_id,))
        audit("Registro de manutenção atualizado", table, item_id, before=before, after={"tipo": kind}, justification=request.form.get("justificativa"))
        flash("Registro de manutenção atualizado.", "success")
        return redirect(url_for("manutencao"))
    return render_template("manutencao_edit.html", record=record, kind=kind)
@app.route("/financeiro", methods=["GET", "POST"])
@login_required
def financeiro():
    if request.method == "POST":
        kind = request.form.get("kind")
        if kind == "service":
            sid = execute("INSERT INTO services(nome,valor,vigencia,fundamento,created_at) VALUES(?,?,?,?,?)", (request.form.get("nome"), float(request.form.get("valor") or 0), request.form.get("vigencia"), request.form.get("fundamento"), now()))
            audit("Serviço/taxa configurado", "services", sid)
            flash("Serviço configurado. Nenhuma cobrança automática foi criada.", "success")
        else:
            service = query("SELECT * FROM services WHERE id=?", (request.form.get("service_id"),), one=True)
            if not service:
                flash("Selecione um serviço válido.", "error")
            else:
                cid = execute("INSERT INTO charges(service_id,responsavel,cpf,protocolo,valor,status,data_lancamento,fundamento,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (service["id"], request.form.get("responsavel"), request.form.get("cpf"), request.form.get("protocolo"), service["valor"], request.form.get("status") or "Pendente", today(), request.form.get("fundamento"), now()))
                audit("Lançamento financeiro registrado", "charges", cid)
                flash("Lançamento registrado conforme a tabela vigente.", "success")
        return redirect(url_for("financeiro"))
    services = query("SELECT * FROM services ORDER BY nome")
    charges = query("SELECT c.*,s.nome servico FROM charges c JOIN services s ON s.id=c.service_id ORDER BY c.id DESC")
    return render_template("financeiro.html", services=services, charges=charges)


@app.route("/financeiro/servicos/<int:service_id>/editar", methods=["GET", "POST"])
@login_required
def editar_servico(service_id):
    record = query("SELECT * FROM services WHERE id=?", (service_id,), one=True)
    if not record:
        abort(404)
    if request.method == "POST":
        before = dict(record)
        execute("UPDATE services SET nome=?,valor=?,vigencia=?,fundamento=?,ativo=? WHERE id=?", (request.form.get("nome"), float(request.form.get("valor") or 0), request.form.get("vigencia") or None, request.form.get("fundamento"), int(request.form.get("ativo") or 0), service_id))
        audit("Serviço/taxa atualizado", "services", service_id, before=before, after={"nome": request.form.get("nome"), "valor": request.form.get("valor")}, justification=request.form.get("justificativa"))
        flash("Serviço/taxa atualizado.", "success")
        return redirect(url_for("financeiro"))
    return render_template("servico_form.html", record=record)

@app.route("/financeiro/lancamentos/<int:charge_id>/editar", methods=["GET", "POST"])
@login_required
def editar_lancamento(charge_id):
    record = query("SELECT * FROM charges WHERE id=?", (charge_id,), one=True)
    if not record:
        abort(404)
    if request.method == "POST":
        before = dict(record)
        execute("UPDATE charges SET responsavel=?,cpf=?,protocolo=?,status=?,data_pagamento=?,fundamento=? WHERE id=?", (request.form.get("responsavel"), request.form.get("cpf"), request.form.get("protocolo"), request.form.get("status"), request.form.get("data_pagamento") or None, request.form.get("fundamento"), charge_id))
        audit("Lançamento financeiro atualizado", "charges", charge_id, before=before, after={"status": request.form.get("status")}, justification=request.form.get("justificativa"))
        flash("Lançamento financeiro atualizado.", "success")
        return redirect(url_for("financeiro"))
    return render_template("lancamento_form.html", record=record)
@app.route("/documentos")
@login_required
def documentos():
    q = request.args.get("q", "").strip()
    rows = query("SELECT x.*,u.nome uploader,d.nome falecido FROM documents x LEFT JOIN users u ON u.id=x.uploaded_by LEFT JOIN deceased d ON x.entity_type='falecido' AND d.id=x.entity_id WHERE x.deleted_at IS NULL AND (x.nome LIKE ? OR x.tipo LIKE ? OR d.nome LIKE ?) ORDER BY x.id DESC", (f"%{q}%", f"%{q}%", f"%{q}%"))
    deceased_rows = query("SELECT id,nome FROM deceased WHERE deleted_at IS NULL ORDER BY nome")
    return render_template("documentos.html", rows=rows, deceased_rows=deceased_rows, q=q)


@app.route("/documentos/<int:doc_id>/editar", methods=["GET", "POST"])
@login_required
def editar_documento(doc_id):
    record = query("SELECT * FROM documents WHERE id=? AND deleted_at IS NULL", (doc_id,), one=True)
    if not record:
        abort(404)
    if request.method == "POST":
        before = dict(record)
        execute("UPDATE documents SET nome=?,tipo=?,descricao=? WHERE id=?", (request.form.get("nome"), request.form.get("tipo"), request.form.get("descricao"), doc_id))
        audit("Metadados de documento atualizados", "documents", doc_id, before=before, after={"nome": request.form.get("nome"), "tipo": request.form.get("tipo")}, justification=request.form.get("justificativa"))
        flash("Metadados atualizados; arquivo original preservado.", "success")
        return redirect(url_for("documentos"))
    return render_template("documento_edit.html", record=record)
@app.route("/documentos/upload", methods=["POST"])
@login_required
def upload_documento():
    file = request.files.get("arquivo")
    if not file or not file.filename or not allowed_file(file.filename):
        flash("Selecione um PDF, JPG, JPEG ou PNG válido.", "error")
        return redirect(request.referrer or url_for("documentos"))
    original = secure_filename(file.filename)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stored = f"{stamp}_{session['user_id']}_{original}"
    path = UPLOAD_DIR / stored
    file.save(path)
    entity_type = request.form.get("entity_type") or "falecido"
    entity_id = request.form.get("entity_id") or None
    doc_id = execute("INSERT INTO documents(entity_type,entity_id,nome,tipo,path,descricao,uploaded_by,created_at) VALUES(?,?,?,?,?,?,?,?)", (entity_type, entity_id, original, path.suffix.lower().replace(".", "").upper(), stored, request.form.get("descricao"), session["user_id"], now()))
    audit("Documento anexado", "documents", doc_id, after={"nome": original, "entity_type": entity_type, "entity_id": entity_id})
    flash("Documento arquivado com metadados e trilha de auditoria.", "success")
    return redirect(request.referrer or url_for("documentos"))


@app.route("/documentos/<int:doc_id>/download")
@login_required
def download_documento(doc_id):
    doc = query("SELECT * FROM documents WHERE id=? AND deleted_at IS NULL", (doc_id,), one=True)
    if not doc:
        abort(404)
    path = UPLOAD_DIR / doc["path"]
    if not path.exists():
        abort(404)
    audit("Documento consultado/baixado", "documents", doc_id)
    return send_file(path, as_attachment=False, download_name=doc["nome"])


OFFICIAL_DOCUMENTS = {
    "declaracao_sepultamento": "Declaração de sepultamento",
    "localizacao_restos": "Declaração de localização de restos mortais",
    "recebimento_restos": "Declaração de recebimento de restos mortais",
    "autorizacao_sepultamento": "Autorização de sepultamento",
    "autorizacao_exumacao": "Autorização de exumação",
    "autorizacao_transferencia": "Autorização de transferência",
    "autorizacao_reforma": "Autorização de reforma de sepultura",
    "certidao_informacoes": "Certidão de informações de sepultamento",
    "certidao_localizacao": "Certidão de localização de sepultura",
    "protocolo_atendimento": "Protocolo de atendimento",
    "termo_responsabilidade": "Termo de responsabilidade",
    "requerimento": "Requerimento administrativo",
}


@app.route("/documentos/oficiais", methods=["GET", "POST"])
@login_required
def documentos_oficiais():
    if request.method == "POST":
        tipo = request.form.get("tipo") or "declaracao_sepultamento"
        deceased_id = request.form.get("deceased_id") or None
        deceased = query("SELECT * FROM deceased WHERE id=?", (deceased_id,), one=True) if deceased_id else None
        title = OFFICIAL_DOCUMENTS.get(tipo, "Documento administrativo")
        numero = next_number("DOC", "documents", "id")
        filename = f"{numero.lower()}_{tipo}.pdf"
        path = UPLOAD_DIR / filename
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name="SigcemTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=colors.HexColor("#0b3139"), spaceAfter=8))
            styles.add(ParagraphStyle(name="SigcemBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=15, spaceAfter=7))
            doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=22 * mm, leftMargin=22 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
            story = [Paragraph(settings_dict().get("prefeitura_nome", "Prefeitura Municipal"), styles["Heading3"]), Paragraph(settings_dict().get("cemiterio_nome", "Cemitério Municipal"), styles["Heading4"]), Spacer(1, 8), Paragraph(title.upper(), styles["SigcemTitle"]), Paragraph(f"Número: {numero} &nbsp;&nbsp; Data de emissão: {datetime.now().strftime('%d/%m/%Y')}", styles["SigcemBody"])]
            if deceased:
                rows = [["Falecido", deceased["nome"]], ["Código", deceased["codigo"]], ["Data do falecimento", date_br(deceased["data_falecimento"])], ["Certidão", deceased["certidao"] or "Não informada"]]
                burial = query("SELECT b.*,g.codigo,g.quadra,g.rua,g.numero FROM burials b JOIN graves g ON g.id=b.grave_id WHERE b.deceased_id=? ORDER BY b.id DESC LIMIT 1", (deceased["id"],), one=True)
                if burial:
                    rows += [["Data do sepultamento", date_br(burial["data_sepultamento"])], ["Localização", f"{burial['codigo']} · Quadra {burial['quadra']} · Nº {burial['numero']}"]]
                table = Table(rows, colWidths=[45 * mm, 115 * mm])
                table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef4f2")), ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#cbd8d5")), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
                story.extend([table, Spacer(1, 14)])
            story.extend([Paragraph(request.form.get("observacoes") or "Documento emitido pelo SIGCEM para conferência e assinatura da autoridade competente.", styles["SigcemBody"]), Spacer(1, 28), Paragraph("____________________________________________", styles["SigcemBody"]), Paragraph(request.form.get("assinante") or "Servidor/autoridade responsável", styles["SigcemBody"])])
            doc.build(story)
        except Exception as exc:
            flash(f"Não foi possível gerar o PDF: {exc}", "error")
            return redirect(url_for("documentos_oficiais"))
        doc_id = execute("INSERT INTO documents(entity_type,entity_id,nome,tipo,path,descricao,uploaded_by,created_at) VALUES(?,?,?,?,?,?,?,?)", ("documento_oficial", deceased_id, filename, "PDF", filename, title, session["user_id"], now()))
        audit("Documento oficial emitido", "documents", doc_id, after={"numero": numero, "tipo": title, "deceased_id": deceased_id})
        flash(f"{title} emitida como {numero}. Revise e colha a assinatura competente.", "success")
        return redirect(url_for("documentos"))
    return render_template("documentos_oficiais.html", document_types=OFFICIAL_DOCUMENTS, deceased_rows=query("SELECT id,codigo,nome FROM deceased WHERE deleted_at IS NULL ORDER BY nome"))


@app.route("/importacao/falecidos", methods=["GET", "POST"])
@roles_required("Administrador geral", "Administrador do cemitério", "Atendente administrativo")
def importacao_falecidos():
    result = None
    if request.method == "POST":
        uploaded = request.files.get("arquivo")
        if not uploaded or not uploaded.filename or not uploaded.filename.lower().endswith((".csv", ".xlsx")):
            flash("Selecione uma planilha CSV ou XLSX.", "error")
        else:
            rows = []
            if uploaded.filename.lower().endswith(".csv"):
                text = uploaded.read().decode("utf-8-sig")
                rows = list(csv.DictReader(io.StringIO(text)))
            else:
                from openpyxl import load_workbook
                workbook = load_workbook(io.BytesIO(uploaded.read()), read_only=True, data_only=True)
                sheet = cast(Any, workbook.active)
                values = list(sheet.values)
                headers = [str(x or "").strip().lower() for x in (values[0] if values else [])]
                rows = [dict(zip(headers, row)) for row in values[1:]]
            created = 0
            duplicates = 0
            for row in rows:
                normalized = {str(k).strip().lower(): (str(v).strip() if v is not None else None) for k, v in row.items()}
                name = normalized.get("nome") or normalized.get("nome completo")
                death = normalized.get("data_falecimento") or normalized.get("data do falecimento")
                if not name or not death:
                    continue
                existing = query("SELECT id FROM deceased WHERE deleted_at IS NULL AND lower(nome)=lower(?) AND data_falecimento=?", (name, death), one=True)
                if existing:
                    duplicates += 1
                    continue
                code = next_number("FAL", "deceased", "id")
                execute("INSERT INTO deceased(codigo,nome,data_falecimento,cpf,certidao,naturalidade,nome_mae,observacoes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (code, name, death, normalized.get("cpf"), normalized.get("certidao") or normalized.get("numero da certidao"), normalized.get("naturalidade"), normalized.get("nome_mae") or normalized.get("nome da mae"), "Importado de planilha; revisar documentação", now(), now()))
                created += 1
            audit("Importação de falecidos executada", "deceased", None, after={"criados": created, "duplicidades": duplicates})
            result = {"criados": created, "duplicidades": duplicates, "linhas": len(rows)}
    return render_template("importacao.html", result=result)


@app.route("/relatorios")
@login_required
def relatorios():
    kind = request.args.get("tipo", "falecidos")
    start = request.args.get("inicio", "")
    end = request.args.get("fim", "")
    if kind == "sepultamentos":
        sql = "SELECT b.protocolo,b.data_sepultamento,d.nome,g.codigo,g.quadra,b.tipo FROM burials b JOIN deceased d ON d.id=b.deceased_id JOIN graves g ON g.id=b.grave_id WHERE 1=1"
        headers = ["Protocolo", "Data", "Falecido", "Sepultura", "Quadra", "Tipo"]
    elif kind == "movimentacoes":
        sql = "SELECT m.kind,m.request_date,m.execution_date,d.nome,og.codigo,dg.codigo FROM movements m JOIN deceased d ON d.id=m.deceased_id LEFT JOIN graves og ON og.id=m.origin_grave_id LEFT JOIN graves dg ON dg.id=m.destination_grave_id WHERE 1=1"
        headers = ["Tipo", "Solicitação", "Execução", "Falecido", "Origem", "Destino"]
    elif kind == "solicitacoes":
        sql = "SELECT protocolo,data_abertura,requerente,tipo,status,data_conclusao FROM requests WHERE 1=1"
        headers = ["Protocolo", "Abertura", "Requerente", "Tipo", "Situação", "Conclusão"]
    else:
        sql = "SELECT codigo,nome,data_falecimento,naturalidade,certidao FROM deceased WHERE deleted_at IS NULL"
        headers = ["Código", "Nome", "Falecimento", "Naturalidade", "Certidão"]
    params = []
    date_col = "b.data_sepultamento" if kind == "sepultamentos" else "m.request_date" if kind == "movimentacoes" else "data_abertura" if kind == "solicitacoes" else "data_falecimento"
    if start:
        sql += f" AND {date_col}>=?"
        params.append(start)
    if end:
        sql += f" AND {date_col}<=?"
        params.append(end)
    sql += " ORDER BY 2 DESC LIMIT 2000"
    rows = query(sql, params)
    return render_template("relatorios.html", rows=rows, headers=headers, kind=kind, start=start, end=end)


@app.route("/relatorios/export/<kind>")
@login_required
def export_relatorio(kind):
    if kind == "sepultamentos":
        rows = query("SELECT b.protocolo,b.data_sepultamento,d.nome,g.codigo,g.quadra,b.tipo FROM burials b JOIN deceased d ON d.id=b.deceased_id JOIN graves g ON g.id=b.grave_id ORDER BY b.id DESC")
        headers = ["Protocolo", "Data", "Falecido", "Sepultura", "Quadra", "Tipo"]
    elif kind == "movimentacoes":
        rows = query("SELECT m.kind,m.request_date,m.execution_date,d.nome,og.codigo,dg.codigo FROM movements m JOIN deceased d ON d.id=m.deceased_id LEFT JOIN graves og ON og.id=m.origin_grave_id LEFT JOIN graves dg ON dg.id=m.destination_grave_id ORDER BY m.id DESC")
        headers = ["Tipo", "Solicitação", "Execução", "Falecido", "Origem", "Destino"]
    elif kind == "solicitacoes":
        rows = query("SELECT protocolo,data_abertura,requerente,tipo,status,data_conclusao FROM requests ORDER BY id DESC")
        headers = ["Protocolo", "Abertura", "Requerente", "Tipo", "Situação", "Conclusão"]
    else:
        rows = query("SELECT codigo,nome,data_falecimento,naturalidade,certidao FROM deceased WHERE deleted_at IS NULL ORDER BY nome")
        headers = ["Código", "Nome", "Falecimento", "Naturalidade", "Certidão"]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row[i] for i in range(len(headers))])
    mem = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    audit("Relatório exportado", "report", None, after={"tipo": kind, "formato": "CSV"})
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name=f"sigcem_{kind}_{today()}.csv")


@app.route("/relatorios/export-xlsx/<kind>")
@login_required
def export_relatorio_xlsx(kind):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        flash("A exportação XLSX requer a dependência openpyxl.", "error")
        return redirect(url_for("relatorios", tipo=kind))
    if kind == "sepultamentos":
        rows = query("SELECT b.protocolo,b.data_sepultamento,d.nome,g.codigo,g.quadra,b.tipo FROM burials b JOIN deceased d ON d.id=b.deceased_id JOIN graves g ON g.id=b.grave_id ORDER BY b.id DESC")
        headers = ["Protocolo", "Data", "Falecido", "Sepultura", "Quadra", "Tipo"]
    elif kind == "movimentacoes":
        rows = query("SELECT m.kind,m.request_date,m.execution_date,d.nome,og.codigo,dg.codigo FROM movements m JOIN deceased d ON d.id=m.deceased_id LEFT JOIN graves og ON og.id=m.origin_grave_id LEFT JOIN graves dg ON dg.id=m.destination_grave_id ORDER BY m.id DESC")
        headers = ["Tipo", "Solicitação", "Execução", "Falecido", "Origem", "Destino"]
    elif kind == "solicitacoes":
        rows = query("SELECT protocolo,data_abertura,requerente,tipo,status,data_conclusao FROM requests ORDER BY id DESC")
        headers = ["Protocolo", "Abertura", "Requerente", "Tipo", "Situação", "Conclusão"]
    else:
        rows = query("SELECT codigo,nome,data_falecimento,naturalidade,certidao FROM deceased WHERE deleted_at IS NULL ORDER BY nome")
        headers = ["Código", "Nome", "Falecimento", "Naturalidade", "Certidão"]
    workbook = Workbook()
    sheet = cast(Any, workbook.active)
    sheet.title = "SIGCEM"
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0E5A63")
    for row in rows:
        sheet.append([row[i] for i in range(len(headers))])
    for column in sheet.columns:
        sheet.column_dimensions[column[0].column_letter].width = min(max(max(len(str(c.value or "")) for c in column) + 2, 12), 38)
    mem = io.BytesIO()
    workbook.save(mem)
    mem.seek(0)
    audit("Relatório exportado", "report", None, after={"tipo": kind, "formato": "XLSX"})
    return send_file(mem, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=f"sigcem_{kind}_{today()}.xlsx")


@app.route("/relatorios/export-pdf/<kind>")
@login_required
def export_relatorio_pdf(kind):
    if kind == "sepultamentos":
        rows = query("SELECT b.protocolo,b.data_sepultamento,d.nome,g.codigo,g.quadra,b.tipo FROM burials b JOIN deceased d ON d.id=b.deceased_id JOIN graves g ON g.id=b.grave_id ORDER BY b.id DESC")
        headers = ["Protocolo", "Data", "Falecido", "Sepultura", "Quadra", "Tipo"]
    elif kind == "movimentacoes":
        rows = query("SELECT m.kind,m.request_date,m.execution_date,d.nome,og.codigo,dg.codigo FROM movements m JOIN deceased d ON d.id=m.deceased_id LEFT JOIN graves og ON og.id=m.origin_grave_id LEFT JOIN graves dg ON dg.id=m.destination_grave_id ORDER BY m.id DESC")
        headers = ["Tipo", "Solicitação", "Execução", "Falecido", "Origem", "Destino"]
    elif kind == "solicitacoes":
        rows = query("SELECT protocolo,data_abertura,requerente,tipo,status,data_conclusao FROM requests ORDER BY id DESC")
        headers = ["Protocolo", "Abertura", "Requerente", "Tipo", "Situação", "Conclusão"]
    else:
        rows = query("SELECT codigo,nome,data_falecimento,naturalidade,certidao FROM deceased WHERE deleted_at IS NULL ORDER BY nome")
        headers = ["Código", "Nome", "Falecimento", "Naturalidade", "Certidão"]
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        mem = io.BytesIO()
        doc = SimpleDocTemplate(mem, pagesize=landscape(A4), rightMargin=12 * mm, leftMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
        styles = getSampleStyleSheet()
        story = [Paragraph(settings_dict().get("prefeitura_nome", "Prefeitura Municipal"), styles["Heading3"]), Paragraph(f"SIGCEM · Relatório de {kind.title()} · Emitido em {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Heading2"]), Spacer(1, 7)]
        table_data = [headers] + [[str(row[i] or "—") for i in range(len(headers))] for row in rows]
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0e5a63")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#cbd8d5")), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f6f4")]), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(table)
        doc.build(story)
        mem.seek(0)
        audit("Relatório exportado", "report", None, after={"tipo": kind, "formato": "PDF"})
        return send_file(mem, mimetype="application/pdf", as_attachment=True, download_name=f"sigcem_{kind}_{today()}.pdf")
    except Exception as exc:
        flash(f"Não foi possível gerar o PDF: {exc}", "error")
        return redirect(url_for("relatorios", tipo=kind))


@app.route("/usuarios", methods=["GET", "POST"])
@roles_required("Administrador geral")
def usuarios():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if not nome or not username or len(password) < 8:
            flash("Nome, usuário e senha de pelo menos 8 caracteres são obrigatórios.", "error")
        else:
            try:
                uid = execute("INSERT INTO users(username,email,password_hash,nome,perfil,created_at) VALUES(?,?,?,?,?,?)", (username, request.form.get("email") or None, generate_password_hash(password), nome, request.form.get("perfil") or "Atendente administrativo", now()))
                audit("Usuário criado", "users", uid, after={"username": username, "perfil": request.form.get("perfil")})
                flash("Usuário criado sem senha padrão.", "success")
            except sqlite3.IntegrityError:
                flash("Usuário ou e-mail já cadastrado.", "error")
        return redirect(url_for("usuarios"))
    rows = query("SELECT id,username,email,nome,perfil,bloqueado,tentativas,created_at FROM users ORDER BY nome")
    return render_template("usuarios.html", rows=rows)


@app.route("/usuarios/<int:user_id>/editar", methods=["GET", "POST"])
@roles_required("Administrador geral")
def editar_usuario(user_id):
    record = query("SELECT * FROM users WHERE id=?", (user_id,), one=True)
    if not record:
        abort(404)
    if request.method == "POST":
        before = dict(record)
        try:
            if request.form.get("password"):
                execute("UPDATE users SET nome=?,username=?,email=?,perfil=?,bloqueado=?,password_hash=?,tentativas=0 WHERE id=?", (request.form.get("nome"), request.form.get("username", "").lower(), request.form.get("email") or None, request.form.get("perfil"), int(request.form.get("bloqueado") or 0), generate_password_hash(request.form.get("password")), user_id))
            else:
                execute("UPDATE users SET nome=?,username=?,email=?,perfil=?,bloqueado=? WHERE id=?", (request.form.get("nome"), request.form.get("username", "").lower(), request.form.get("email") or None, request.form.get("perfil"), int(request.form.get("bloqueado") or 0), user_id))
            audit("Usuário atualizado", "users", user_id, before={"nome": before["nome"], "username": before["username"], "perfil": before["perfil"], "bloqueado": before["bloqueado"]}, after={"nome": request.form.get("nome"), "username": request.form.get("username"), "perfil": request.form.get("perfil"), "bloqueado": request.form.get("bloqueado")}, justification=request.form.get("justificativa"))
            flash("Usuário atualizado.", "success")
            return redirect(url_for("usuarios"))
        except sqlite3.IntegrityError:
            flash("Usuário ou e-mail já cadastrado.", "error")
    perfis = ["Administrador geral","Administrador do cemitério","Atendente administrativo","Operacional","Consulta e fiscalização"]
    return render_template("usuario_form.html", record=record, perfis=perfis)
@app.route("/usuarios/<int:user_id>/bloquear", methods=["POST"])
@roles_required("Administrador geral")
def bloquear_usuario(user_id):
    if user_id == session.get("user_id"):
        flash("Você não pode bloquear a própria sessão.", "error")
    else:
        user = query("SELECT * FROM users WHERE id=?", (user_id,), one=True)
        if user:
            value = 0 if user["bloqueado"] else 1
            execute("UPDATE users SET bloqueado=? WHERE id=?", (value, user_id))
            audit("Usuário bloqueado" if value else "Usuário desbloqueado", "users", user_id)
            flash("Status do usuário atualizado.", "success")
    return redirect(url_for("usuarios"))


@app.route("/auditoria")
@roles_required("Administrador geral", "Consulta e fiscalização")
def auditoria():
    rows = query("SELECT a.*,u.nome usuario FROM audit a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 500")
    return render_template("auditoria.html", rows=rows)


@app.route("/backup", methods=["GET", "POST"])
@roles_required("Administrador geral")
def backup():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            filename = f"sigcem_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            target = BACKUP_DIR / filename
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
                if DB_PATH.exists():
                    zf.write(DB_PATH, "sigcem.db")
                if UPLOAD_DIR.exists():
                    for path in UPLOAD_DIR.rglob("*"):
                        if path.is_file():
                            zf.write(path, str(Path("uploads") / path.relative_to(UPLOAD_DIR)))
            bid = execute("INSERT INTO backups(arquivo,tipo,tamanho,responsavel_id,resultado,created_at) VALUES(?,?,?,?,?,?)", (filename, "Completo", target.stat().st_size, session["user_id"], "Sucesso", now()))
            audit("Backup completo criado", "backups", bid, after={"arquivo": filename})
            flash(f"Backup criado: {filename}", "success")
        elif action == "restore":
            filename = secure_filename(request.form.get("arquivo", ""))
            confirm = request.form.get("confirmacao") == "RESTAURAR"
            source = BACKUP_DIR / filename
            if not confirm or not source.exists():
                flash("Informe RESTAURAR e selecione um backup existente. A restauração exige confirmação expressa.", "error")
            else:
                safety = BACKUP_DIR / f"antes_restauracao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                shutil.copy2(source, safety)
                with zipfile.ZipFile(source) as zf:
                    if "sigcem.db" not in zf.namelist():
                        flash("Backup inválido: banco não encontrado.", "error")
                    else:
                        tmp = BACKUP_DIR / "_restore_tmp.db"
                        with zf.open("sigcem.db") as src, open(tmp, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        get_db().close()
                        g.pop("db", None)
                        shutil.copy2(tmp, DB_PATH)
                        tmp.unlink(missing_ok=True)
                        audit("Backup restaurado após cópia de segurança", "backups", None, after={"arquivo": filename, "seguranca": safety.name})
                        flash("Backup restaurado. A cópia do estado anterior foi preservada.", "success")
        return redirect(url_for("backup"))
    rows = query("SELECT b.*,u.nome responsavel FROM backups b LEFT JOIN users u ON u.id=b.responsavel_id ORDER BY b.id DESC")
    files = sorted([p.name for p in BACKUP_DIR.glob("*.zip")], reverse=True)
    return render_template("backup.html", rows=rows, files=files)


@app.route("/configuracoes", methods=["GET", "POST"])
@roles_required("Administrador geral", "Administrador do cemitério")
def configuracoes():
    if request.method == "POST":
        for key in DEFAULT_SETTINGS:
            if key in request.form:
                old = settings_dict().get(key, "")
                value = request.form.get(key, "").strip()
                execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
                if old != value:
                    audit("Configuração institucional atualizada", "settings", None, before={key: old}, after={key: value})
        flash("Configurações salvas.", "success")
        return redirect(url_for("configuracoes"))
    return render_template("configuracoes.html", config=settings_dict())


@app.route("/buscar")
@login_required
def buscar():
    q = request.args.get("q", "").strip()
    if not q:
        return redirect(url_for("dashboard"))
    like = f"%{q}%"
    deceased_rows = query("SELECT id,codigo,nome,data_falecimento FROM deceased WHERE deleted_at IS NULL AND (unaccent(nome) LIKE unaccent(?) OR cpf LIKE ? OR codigo LIKE ?)", (like, like, like))
    grave_rows = query("SELECT id,codigo,quadra,rua,numero,status FROM graves WHERE codigo LIKE ? OR quadra LIKE ? OR numero LIKE ?", (like, like, like))
    request_rows = query("SELECT id,protocolo,requerente,tipo,status FROM requests WHERE protocolo LIKE ? OR requerente LIKE ?", (like, like))
    return render_template("buscar.html", q=q, deceased_rows=deceased_rows, grave_rows=grave_rows, request_rows=request_rows)


@app.template_filter("date_br")
def date_br(value):
    if not value:
        return ""
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(value)


@app.template_filter("datetime_br")
def datetime_br(value):
    if not value:
        return ""
    try:
        return datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(value)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "3000")), debug=False)
else:
    init_db()
