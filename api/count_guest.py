import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from guests_manager.count_guest import count

def handler(request):

    try:
        total = count()
        return {
            "status": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"total": total})
        }
    except Exception as e:
        return {
            "status": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
