import os
import json
from flask import Flask, jsonify, Response, send_file

# --------- إعداد مسار البيانات ----------
def resolve_results_dir():
    env_dir = os.environ.get("RESULTS_DIR")
    if env_dir and os.path.isdir(env_dir):
        return env_dir

    render_dir = "/opt/render/project/src/data"
    if os.path.isdir(render_dir):
        return render_dir

    custom_dir = os.environ.get("RESULTS_DIR_CUSTOM")
    if custom_dir and os.path.isdir(custom_dir):
        return custom_dir

    local_dir = os.path.join(os.path.dirname(__file__), "data")
    return local_dir

DIRECTORY = resolve_results_dir()
HTML_FILE = os.path.join(DIRECTORY, "wep.html")

latest_json = None
latest_txt = ""

app = Flask(__name__)

def safe_print(msg):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(str(msg).encode("utf-8", errors="replace").decode("utf-8"), flush=True)

def find_latest_file(extension):
    try:
        files = [
            os.path.join(DIRECTORY, f)
            for f in os.listdir(DIRECTORY)
            if f.lower().endswith(extension.lower())
        ]
    except Exception as e:
        safe_print(f"[WARN] listdir({DIRECTORY}) failed: {e}")
        return None
    if not files:
        safe_print(f"[INFO] No *{extension} files in {DIRECTORY}")
        return None
    chosen = max(files, key=os.path.getmtime)
    safe_print(f"[INFO] latest {extension}: {os.path.basename(chosen)}")
    return chosen

def load_latest_files():
    global latest_json, latest_txt
    safe_print(f"[BOOT] Scanning dir: {DIRECTORY}")

    json_path = find_latest_file(".json")
    txt_path  = find_latest_file(".txt")

    if json_path:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                latest_json = json.load(f)
            safe_print(f"[OK] JSON loaded: {os.path.basename(json_path)}")
        except Exception as e:
            safe_print(f"[ERR] Reading JSON: {e}")
            latest_json = None
    else:
        latest_json = None

    if txt_path:
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                latest_txt = f.read()
            safe_print(f"[OK] TXT loaded: {os.path.basename(txt_path)}")
        except Exception as e:
            safe_print(f"[ERR] Reading TXT: {e}")
            latest_txt = ""
    else:
        latest_txt = ""

# 🔥 حمّل البيانات مرة واحدة عند الاستيراد (متوافق مع Flask 3.1 + Gunicorn)
load_latest_files()

# --------- المسارات ----------
@app.route("/")
def index():
    if os.path.exists(HTML_FILE):
        return send_file(HTML_FILE, mimetype="text/html")
    else:
        return f"<h2>❌ لم يتم العثور على الملف wep.html في {HTML_FILE}</h2>", 404

@app.route("/data/json")
def get_json():
    if latest_json is not None:
        return jsonify(latest_json)
    else:
        return jsonify({"error": f"لم يتم العثور على ملف JSON داخل {DIRECTORY}"}), 404

@app.route("/data/text")
def get_text():
    if latest_txt:
        return Response(latest_txt, mimetype="text/plain; charset=utf-8")
    else:
        return Response(f"⚠️ لم يتم العثور على تقرير TXT داخل {DIRECTORY}", mimetype="text/plain; charset=utf-8"), 404

# فحص ونشِر معلومات مفيدة
@app.route("/debug/list")
def debug_list():
    try:
        items = os.listdir(DIRECTORY)
    except Exception as e:
        return jsonify({"version": "v4", "directory": DIRECTORY, "error": str(e)}), 500

    commit = os.environ.get("RENDER_GIT_COMMIT", "UNKNOWN")
    return jsonify({
        "version": "v4",
        "directory": DIRECTORY,
        "items": items,
        "render_git_commit": commit
    })

def run_server_dev():
    port = int(os.environ.get("PORT", 5000))
    safe_print(f"🚀 Dev server at http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    run_server_dev()
