from flask import Flask, jsonify
import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from guests_manager.count_guest import count

app = Flask(__name__)

@app.get("/api/count_guest")
def get_guest_count():
    try:
        total = count()
        return jsonify({"total": total})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def handler(request, *args, **kwargs):
    return app(request.environ, start_response=None)
