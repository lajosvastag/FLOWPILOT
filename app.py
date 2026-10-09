import json
import os
import queue
import random
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
PUBLIC = ROOT / "public"
DB_PATH = ROOT / "data" / "flowpilot.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
PORT = int(os.environ.get("PORT", "3000"))

JOB_QUEUE = queue.Queue()
DB_LOCK = threading.Lock()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with DB_LOCK:
        conn = db()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS automations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL,
                schedule TEXT NOT NULL,
                icon TEXT NOT NULL,
                color TEXT NOT NULL,
                runs INTEGER NOT NULL DEFAULT 0,
                success_rate REAL NOT NULL DEFAULT 100,
                avg_duration INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                automation_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                duration INTEGER,
                triggered_by TEXT NOT NULL,
                error_step TEXT,
                error_message TEXT,
                payload TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(automation_id) REFERENCES automations(id)
            );
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(execution_id) REFERENCES executions(id)
            );
            """
        )
        if conn.execute("SELECT COUNT(*) FROM automations").fetchone()[0] == 0:
            seed(conn)
        conn.commit()
        conn.close()


def seed(conn):
    automations = [
        ("file-sorter", "Organizador de arquivos", "Move arquivos para pastas por tipo e projeto.", "Arquivos", "active", "A cada 1 hora", "folder", "violet", 128, 99.2, 42),
        ("sales-report", "Relatório de vendas", "Consolida pedidos e envia um resumo para a equipe.", "Relatórios", "active", "Diariamente às 08:00", "chart", "amber", 84, 97.6, 118),
        ("data-cleanup", "Limpeza de dados", "Remove duplicidades e normaliza campos do CRM.", "Dados", "paused", "Toda segunda-feira", "monkey", "cyan", 46, 94.1, 86),
        ("invoice-check", "Validador de notas", "Confere campos obrigatórios antes do processamento fiscal.", "Financeiro", "active", "Quando um arquivo chegar", "shield", "pink", 212, 98.7, 31),
    ]
    for item in automations:
        conn.execute(
            "INSERT INTO automations (id,name,description,category,status,schedule,icon,color,runs,success_rate,avg_duration,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (*item, now_iso()),
        )
    base = datetime.now(timezone.utc)
    samples = [
        ("file-sorter", "success", 42, "manual", None, None),
        ("sales-report", "success", 118, "schedule", None, None),
        ("invoice-check", "success", 31, "webhook", None, None),
        ("data-cleanup", "error", 86, "schedule", "Normalização", "Campo 'customer_id' ausente no lote recebido."),
        ("file-sorter", "success", 37, "schedule", None, None),
        ("invoice-check", "success", 28, "webhook", None, None),
        ("sales-report", "success", 124, "manual", None, None),
        ("data-cleanup", "success", 79, "manual", None, None),
        ("file-sorter", "success", 45, "schedule", None, None),
        ("invoice-check", "error", 22, "webhook", "Validação de schema", "O arquivo não contém a coluna 'invoice_number'."),
    ]
    for idx, (automation_id, status, duration, triggered_by, error_step, error_message) in enumerate(samples):
        started = (base - timedelta(minutes=(idx + 1) * 38)).isoformat(timespec="seconds").replace("+00:00", "Z")
        finished = (base - timedelta(minutes=(idx + 1) * 38) + timedelta(seconds=duration)).isoformat(timespec="seconds").replace("+00:00", "Z")
        execution_id = f"exec-{uuid.uuid4().hex[:10]}"
        conn.execute(
            "INSERT INTO executions (id,automation_id,status,started_at,finished_at,duration,triggered_by,error_step,error_message,payload) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (execution_id, automation_id, status, started, finished, duration, triggered_by, error_step, error_message, json.dumps({"source": "seed", "batch": idx + 1})),
        )
        log_messages = ["Execução iniciada", "Dados recebidos", "Processamento concluído" if status == "success" else f"Erro em {error_step}"]
        for message in log_messages:
            conn.execute("INSERT INTO execution_logs (execution_id,level,message,created_at) VALUES (?,?,?,?)", (execution_id, "error" if status == "error" and message.startswith("Erro") else "info", message, finished))


def row_dict(row):
    return dict(row) if row else None


def get_automation(conn, automation_id):
    return conn.execute("SELECT * FROM automations WHERE id = ?", (automation_id,)).fetchone()


def execution_dict(conn, row):
    data = row_dict(row)
    if not data:
        return None
    automation = get_automation(conn, data["automation_id"])
    data["automation_name"] = automation["name"] if automation else "Automação removida"
    data["payload"] = json.loads(data["payload"] or "{}")
    data["logs"] = [row_dict(log) for log in conn.execute("SELECT level,message,created_at FROM execution_logs WHERE execution_id = ? ORDER BY id", (data["id"],)).fetchall()]
    return data


def run_job(execution_id, automation_id):
    time.sleep(0.9)
    with DB_LOCK:
        conn = db()
        automation = get_automation(conn, automation_id)
        if not automation:
            conn.close()
            return
        should_fail = automation_id in {"data-cleanup", "invoice-check"} and random.random() < 0.16
        duration = random.randint(28, 140)
        finished = now_iso()
        status = "error" if should_fail else "success"
        error_step = "Validação de schema" if should_fail else None
        error_message = "O lote recebido não possui o campo obrigatório esperado." if should_fail else None
        conn.execute("UPDATE executions SET status=?,finished_at=?,duration=?,error_step=?,error_message=? WHERE id=?", (status, finished, duration, error_step, error_message, execution_id))
        if should_fail:
            conn.execute("INSERT INTO execution_logs (execution_id,level,message,created_at) VALUES (?,?,?,?)", (execution_id, "error", f"Erro em {error_step}: {error_message}", finished))
        else:
            conn.execute("INSERT INTO execution_logs (execution_id,level,message,created_at) VALUES (?,?,?,?)", (execution_id, "info", "Processamento concluído com sucesso", finished))
        conn.execute("UPDATE automations SET runs=runs+1,updated_at=? WHERE id=?", (finished, automation_id))
        conn.commit()
        conn.close()


def worker():
    while True:
        item = JOB_QUEUE.get()
        if item is None:
            break
        run_job(*item)
        JOB_QUEUE.task_done()


class Handler(BaseHTTPRequestHandler):
    server_version = "FlowPilot/1.0"

    def log_message(self, format, *args):
        return

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            return self.send_json({"ok": True, "service": "flowpilot", "time": now_iso()})
        if path.startswith("/api/"):
            return self.api_get(path, parse_qs(parsed.query))
        self.serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            return self.api_post(parsed.path)
        self.send_json({"error": "Rota não encontrada"}, 404)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            return self.api_patch(parsed.path)
        self.send_json({"error": "Rota não encontrada"}, 404)

    def api_get(self, path, query):
        with DB_LOCK:
            conn = db()
            if path == "/api/summary":
                total = conn.execute("SELECT COUNT(*) FROM automations").fetchone()[0]
                active = conn.execute("SELECT COUNT(*) FROM automations WHERE status='active'").fetchone()[0]
                executions = conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0]
                successes = conn.execute("SELECT COUNT(*) FROM executions WHERE status='success'").fetchone()[0]
                failed = conn.execute("SELECT COUNT(*) FROM executions WHERE status='error'").fetchone()[0]
                avg = conn.execute("SELECT COALESCE(AVG(duration),0) FROM executions WHERE status='success'").fetchone()[0]
                return self.send_json({"automations": total, "active": active, "executions": executions, "successes": successes, "failed": failed, "success_rate": round((successes / executions) * 100, 1) if executions else 0, "time_saved": "18h 42m", "avg_duration": round(avg or 0)})
            if path == "/api/automations":
                rows = conn.execute("SELECT * FROM automations ORDER BY status='active' DESC, updated_at DESC").fetchall()
                self.send_json({"items": [row_dict(row) for row in rows]})
                conn.close()
                return
            if path == "/api/executions":
                status = query.get("status", [""])[0]
                search = query.get("q", [""])[0].lower()
                sql = "SELECT e.*, a.name AS automation_name FROM executions e JOIN automations a ON a.id=e.automation_id WHERE 1=1"
                params = []
                if status and status != "all":
                    sql += " AND e.status=?"
                    params.append(status)
                if search:
                    sql += " AND (LOWER(a.name) LIKE ? OR LOWER(e.id) LIKE ?)"
                    params.extend([f"%{search}%", f"%{search}%"])
                sql += " ORDER BY e.started_at DESC LIMIT 100"
                rows = conn.execute(sql, params).fetchall()
                self.send_json({"items": [row_dict(row) for row in rows]})
                conn.close()
                return
            if path.startswith("/api/executions/"):
                execution_id = path.split("/")[-1]
                row = conn.execute("SELECT * FROM executions WHERE id=?", (execution_id,)).fetchone()
                if not row:
                    conn.close()
                    return self.send_json({"error": "Execução não encontrada"}, 404)
                data = execution_dict(conn, row)
                conn.close()
                return self.send_json(data)
            conn.close()
        self.send_json({"error": "Rota não encontrada"}, 404)

    def api_post(self, path):
        with DB_LOCK:
            conn = db()
            if path == "/api/automations":
                body = self.read_json()
                name = str(body.get("name", "Nova automação")).strip() or "Nova automação"
                automation_id = f"auto-{uuid.uuid4().hex[:8]}"
                conn.execute("INSERT INTO automations (id,name,description,category,status,schedule,icon,color,runs,success_rate,avg_duration,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (automation_id, name, body.get("description", "Automação criada pelo painel."), body.get("category", "Operações"), "active", body.get("schedule", "Manual"), body.get("icon", "monkey"), "violet", 0, 100, 0, now_iso()))
                conn.commit()
                data = row_dict(get_automation(conn, automation_id))
                conn.close()
                return self.send_json(data, 201)
            if path.startswith("/api/automations/") and path.endswith("/run"):
                automation_id = path.split("/")[-2]
                automation = get_automation(conn, automation_id)
                if not automation:
                    conn.close()
                    return self.send_json({"error": "Automação não encontrada"}, 404)
                execution_id = f"exec-{uuid.uuid4().hex[:10]}"
                started = now_iso()
                conn.execute("INSERT INTO executions (id,automation_id,status,started_at,triggered_by,payload) VALUES (?,?,?,?,?,?)", (execution_id, automation_id, "running", started, "manual", json.dumps({"source": "dashboard", "requested_at": started})))
                conn.execute("INSERT INTO execution_logs (execution_id,level,message,created_at) VALUES (?,?,?,?)", (execution_id, "info", "Execução adicionada à fila", started))
                conn.commit()
                conn.close()
                JOB_QUEUE.put((execution_id, automation_id))
                return self.send_json({"id": execution_id, "status": "running", "message": "Execução adicionada à fila."}, 202)
            if path.startswith("/api/executions/") and path.endswith("/retry"):
                execution_id = path.split("/")[-2]
                row = conn.execute("SELECT automation_id FROM executions WHERE id=?", (execution_id,)).fetchone()
                if not row:
                    conn.close()
                    return self.send_json({"error": "Execução não encontrada"}, 404)
                automation_id = row["automation_id"]
                new_id = f"exec-{uuid.uuid4().hex[:10]}"
                started = now_iso()
                conn.execute("INSERT INTO executions (id,automation_id,status,started_at,triggered_by,payload) VALUES (?,?,?,?,?,?)", (new_id, automation_id, "running", started, "retry", json.dumps({"retry_of": execution_id})))
                conn.execute("INSERT INTO execution_logs (execution_id,level,message,created_at) VALUES (?,?,?,?)", (new_id, "info", f"Reexecução criada a partir de {execution_id}", started))
                conn.commit()
                conn.close()
                JOB_QUEUE.put((new_id, automation_id))
                return self.send_json({"id": new_id, "status": "running"}, 202)
            conn.close()
        self.send_json({"error": "Rota não encontrada"}, 404)

    def api_patch(self, path):
        if not path.startswith("/api/automations/"):
            return self.send_json({"error": "Rota não encontrada"}, 404)
        automation_id = path.split("/")[-1]
        body = self.read_json()
        with DB_LOCK:
            conn = db()
            if not get_automation(conn, automation_id):
                conn.close()
                return self.send_json({"error": "Automação não encontrada"}, 404)
            allowed = {key: body[key] for key in ("name", "description", "schedule", "status") if key in body}
            if allowed:
                fields = ", ".join(f"{key}=?" for key in allowed)
                conn.execute(f"UPDATE automations SET {fields},updated_at=? WHERE id=?", (*allowed.values(), now_iso(), automation_id))
                conn.commit()
            data = row_dict(get_automation(conn, automation_id))
            conn.close()
        self.send_json(data)

    def serve_static(self, path):
        relative = "index.html" if path in ("/", "") else path.lstrip("/")
        candidate = (PUBLIC / relative).resolve()
        try:
            candidate.relative_to(PUBLIC.resolve())
        except ValueError:
            return self.send_json({"error": "Arquivo não encontrado"}, 404)
        if not candidate.exists() or not candidate.is_file():
            candidate = PUBLIC / "index.html"
        content = candidate.read_bytes()
        types = {".html": "text/html", ".css": "text/css", ".js": "application/javascript", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png"}
        self.send_response(200)
        self.send_header("Content-Type", types.get(candidate.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    init_db()
    threading.Thread(target=worker, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"FlowPilot running at http://0.0.0.0:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
