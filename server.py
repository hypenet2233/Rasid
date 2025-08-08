import os
import json
from flask import Flask, jsonify, Response, send_file
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# اختيار مجلد النتائج تلقائي
def resolve_results_dir():
    # أولوية 1: متغير بيئة RESULTS_DIR (للمنصات مثل Render)
    env_dir = os.environ.get("RESULTS_DIR")
    if env_dir and os.path.isdir(env_dir):
        return env_dir
    
    # أولوية 2: متغير بيئة مخصص RESULTS_DIR_CUSTOM (لتشغيل محلي أو بيئات أخرى)
    custom_dir = os.environ.get("RESULTS_DIR_CUSTOM")
    if custom_dir and os.path.isdir(custom_dir):
        return custom_dir
    
    # أولوية 3: مجلد data داخل المشروع
    local_dir = os.path.join(os.path.dirname(__file__), "data")
    if os.path.isdir(local_dir):
        return local_dir
    
    # إذا لم يوجد أي من أعلاه، نرجع المجلد المحلي حتى لو غير موجود
    return local_dir

DIRECTORY = resolve_results_dir()
HTML_FILE = os.path.join(DIRECTORY, "wep.html")

latest_json = None
latest_txt = ""

app = Flask(__name__)

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('utf-8', errors='replace').decode('utf-8'))

def find_latest_file(extension):
    try:
        files = [
            os.path.join(DIRECTORY, f)
            for f in os.listdir(DIRECTORY)
            if f.lower().endswith(extension.lower())
        ]
    except FileNotFoundError:
        return None
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def load_latest_files():
    global latest_json, latest_txt
    json_path = find_latest_file('.json')
    txt_path  = find_latest_file('.txt')

    if json_path:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                latest_json = json.load(f)
            safe_print(f"[تم التحميل] JSON: {os.path.basename(json_path)}")
        except Exception as e:
            safe_print(f"[خطأ] قراءة JSON: {e}")
            latest_json = None
    else:
        latest_json = None

    if txt_path:
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                latest_txt = f.read()
            safe_print(f"[تم التحميل] TXT: {os.path.basename(txt_path)}")
        except Exception as e:
            safe_print(f"[خطأ] قراءة TXT: {e}")
            latest_txt = ""
    else:
        latest_txt = ""

class FileChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        if event.event_type in ('created', 'modified'):
            if event.src_path.endswith(('.json', '.txt')):
                safe_print(f"[تحديث]: {event.src_path}")
                load_latest_files()

@app.route("/")
def index():
    if os.path.exists(HTML_FILE):
        return send_file(HTML_FILE, mimetype='text/html')
    else:
        return "<h2>❌ لم يتم العثور على الملف wep.html</h2>", 404

@app.route("/data/json")
def get_json():
    if latest_json is not None:
        return jsonify(latest_json)
    else:
        return jsonify({"error": "لم يتم العثور على ملف JSON"}), 404

@app.route("/data/text")
def get_text():
    if latest_txt:
        return Response(latest_txt, mimetype='text/plain; charset=utf-8')
    else:
        return Response("⚠️ لم يتم العثور على تقرير TXT", mimetype='text/plain; charset=utf-8'), 404

def run_server():
    load_latest_files()
    if os.path.isdir(DIRECTORY):
        observer = Observer()
        observer.schedule(FileChangeHandler(), DIRECTORY, recursive=False)
        observer.start()
    else:
        observer = None
        safe_print(f"⚠️ مجلد النتائج غير موجود: {DIRECTORY}")

    port = int(os.environ.get("PORT", 5000))
    safe_print(f"🚀 Server running at http://0.0.0.0:{port}")
    try:
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    finally:
        if observer:
            observer.stop()
            observer.join()

if __name__ == "__main__":
    run_server()
