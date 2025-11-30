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
            "statusCode": 200,
            "body": json.dumps({"total_guests": total})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
