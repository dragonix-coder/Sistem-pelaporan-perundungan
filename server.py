# path: server.py
import http.server
import socketserver
import json
import sqlite3
import random
import string
from urllib.parse import parse_qs, urlparse

# MENGGUNAKAN PORT 8000 AGAR TIDAK BENTROK DENGAN LIVE SERVER (5500)
PORT = 8000
DB_NAME = "sigap_bully.db"
MAX_BODY_SIZE = 15 * 1024 * 1024  # BARU: ~15MB, batas ukuran request (anti payload raksasa)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS laporan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_tiket TEXT UNIQUE NOT NULL,
            nama TEXT NOT NULL,
            kelas TEXT NOT NULL,
            kategori TEXT NOT NULL,
            cerita TEXT NOT NULL,
            bukti TEXT DEFAULT '[]',
            status TEXT DEFAULT 'Menunggu Tinjauan',
            pesan_bk TEXT DEFAULT 'Belum ada pesan dari Guru BK.',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # BARU: migrasi otomatis — kalau sigap_bully.db lama sudah ada tapi belum punya kolom 'bukti'
    cursor.execute("PRAGMA table_info(laporan)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    if "bukti" not in existing_columns:
        cursor.execute("ALTER TABLE laporan ADD COLUMN bukti TEXT DEFAULT '[]'")

    conn.commit()
    conn.close()

def generate_kode_tiket():
    chars = string.ascii_uppercase + string.digits
    kode_acak = ''.join(random.choices(chars, k=4))
    return f"BULLY-{kode_acak}"

class SigapRequestHandler(http.server.SimpleHTTPRequestHandler):

    def _set_headers(self, status_code=200, content_type="application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed_path = urlparse(self.path)

        # 1. Cek Status Siswa
        if parsed_path.path == "/api/cek-status":
            query = parse_qs(parsed_path.query)
            kode_tiket = query.get("tiket", [None])[0]

            if not kode_tiket:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Kode tiket wajib diisi"}).encode())
                return

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT kode_tiket, status, pesan_bk FROM laporan WHERE kode_tiket = ?", (kode_tiket,))
            row = cursor.fetchone()
            conn.close()

            if row:
                res = {"kode_tiket": row[0], "status": row[1], "pesan_bk": row[2]}
                self._set_headers(200)
                self.wfile.write(json.dumps(res).encode())
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Tiket tidak ditemukan"}).encode())
            return

        # 2. Ambil Semua Laporan (Admin)
        elif parsed_path.path == "/api/admin/laporan":
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, kode_tiket, nama, kelas, kategori, cerita, status, pesan_bk, created_at, bukti FROM laporan ORDER BY id DESC"
            )  # BARU: tambah kolom 'bukti' di SELECT
            rows = cursor.fetchall()
            conn.close()

            laporan_list = []
            for r in rows:
                # BARU: parse kolom bukti (JSON text) jadi list
                try:
                    bukti_parsed = json.loads(r[9]) if r[9] else []
                except (json.JSONDecodeError, TypeError):
                    bukti_parsed = []

                laporan_list.append({
                    "id": r[0],
                    "kode_tiket": r[1],
                    "nama_pelapor": r[2],
                    "kelas": r[3],
                    "kategori": r[4],
                    "kronologi": r[5],
                    "status_penanganan": r[6],
                    "pesan_balasan": r[7],
                    "tanggal": r[8],
                    "bukti": bukti_parsed  # BARU
                })

            self._set_headers(200)
            self.wfile.write(json.dumps(laporan_list).encode())
            return

        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))

        # BARU: proteksi dasar — tolak body yang kelewat besar (anti resource-exhaustion)
        if content_length > MAX_BODY_SIZE:
            self._set_headers(413)
            self.wfile.write(json.dumps({"error": "Ukuran data terlalu besar (maks 15MB)."}).encode())
            return

        post_data = self.rfile.read(content_length)

        try:
            body = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Data JSON tidak valid"}).encode())
            return

        # 1. Kirim Laporan (Siswa)
        if self.path == "/api/lapor":
            nama = body.get("nama", "Anonim")
            kelas = body.get("kelas", "-")
            kategori = body.get("kategori", "")
            cerita = body.get("cerita", "")
            bukti_list = body.get("bukti", [])  # BARU: list data-URL base64 (gambar/video)

            if not isinstance(bukti_list, list):
                bukti_list = []

            kode_tiket = generate_kode_tiket()

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO laporan (kode_tiket, nama, kelas, kategori, cerita, bukti) VALUES (?, ?, ?, ?, ?, ?)",
                (kode_tiket, nama, kelas, kategori, cerita, json.dumps(bukti_list))  # BARU: simpan bukti
            )
            conn.commit()
            conn.close()

            self._set_headers(201)
            self.wfile.write(json.dumps({"success": True, "kode_tiket": kode_tiket}).encode())
            return

        # 2. Update Status (Admin)
        elif self.path == "/api/admin/update-status":
            kode_tiket = body.get("kode_tiket")
            status = body.get("status_penanganan")
            pesan_bk = body.get("pesan_balasan", "")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE laporan SET status = ?, pesan_bk = ? WHERE kode_tiket = ?",
                (status, pesan_bk, kode_tiket)
            )
            conn.commit()
            updated = cursor.rowcount
            conn.close()

            if updated > 0:
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True}).encode())
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Tiket tidak ditemukan"}).encode())
            return

        self._set_headers(404)
        self.wfile.write(json.dumps({"error": "Endpoint tidak ditemukan"}).encode())

    # FUNGSI UNTUK MENGHAPUS DATA
    def do_DELETE(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path.startswith("/api/admin/laporan/"):
            kode_tiket = parsed_path.path.split("/")[-1]

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM laporan WHERE kode_tiket = ?", (kode_tiket,))
            conn.commit()
            deleted = cursor.rowcount
            conn.close()

            if deleted > 0:
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True}).encode())
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Data tidak ditemukan"}).encode())
            return

        self._set_headers(404)
        self.wfile.write(json.dumps({"error": "Endpoint DELETE tidak ditemukan"}).encode())

if __name__ == "__main__":
    init_db()
    print(f"🚀 Server SIGAP-BULLY aktif di http://localhost:{PORT}")
    with socketserver.TCPServer(("", PORT), SigapRequestHandler) as httpd:
        httpd.serve_forever()