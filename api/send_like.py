import json
import os
import sys
import asyncio
import binascii
import httpx

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from get_jwt import create_jwt
from encrypt_like_body import create_like_payload
from count_likes import GetAccountInformation

# load guest data (OK di serverless)
GUESTS_FILE = os.path.join(ROOT, "guests_manager", "guests_converted.json")
with open(GUESTS_FILE, "r") as f:
    GUESTS = json.load(f)

# temporary RAM storage for this request (serverless OK)
temp_used = {}

def base_url(server):
    s = server.upper()
    if s == "IND": return "https://client.ind.freefiremobile.com"
    if s in {"BR","US","SAC","NA"}:
        return "https://client.us.freefiremobile.com"
    return "https://clientbp.ggblueshark.com"


async def like_one(guest, target_uid, BASE_URL, semaphore):
    guest_uid = str(guest["uid"])
    guest_pw = guest["password"]

    if guest_uid in temp_used.get(target_uid, set()):
        return False

    async with semaphore:
        try:
            jwt, region, _ = await create_jwt(guest_uid, guest_pw)
            payload = create_like_payload(target_uid, region)
            if isinstance(payload, str):
                payload = binascii.unhexlify(payload)

            headers = {
                "User-Agent": "Dalvik FF",
                "Content-Type": "application/octet-stream",
                "Authorization": f"Bearer {jwt}"
            }

            async with httpx.AsyncClient() as c:
                r = await c.post(f"{BASE_URL}/LikeProfile", data=payload, headers=headers)
                r.raise_for_status()

            temp_used.setdefault(target_uid, set()).add(guest_uid)
            return True

        except:
            return False


async def do_likes(uid, server, likes, max_conc):
    BASE_URL = base_url(server)
    sem = asyncio.Semaphore(max_conc)

    available = [
        g for g in GUESTS 
        if g["uid"] not in temp_used.get(uid, set())
    ]

    likes = min(likes, len(available))
    tasks = [like_one(g, uid, BASE_URL, sem) for g in available[:likes]]

    results = await asyncio.gather(*tasks)
    success = sum(1 for r in results if r)

    info = await GetAccountInformation(uid, "0", server, "/GetPlayerPersonalShow")

    return {
        "attempted": likes,
        "success": success,
        "after": info
    }


def handler(request):
    """
    Vercel Python expected sync handler
    """
    try:
        uid = request.get("query", {}).get("uid")
        server = request.get("query", {}).get("server", "IND")
        likes = int(request.get("query", {}).get("likes", 50))
        max_conc = int(request.get("query", {}).get("max_conc", 10))
    except:
        return {
            "status": 400,
            "headers": { "Content-Type": "application/json" },
            "body": json.dumps({"error": "invalid parameters"})
        }

    if not uid:
        return {
            "status": 400,
            "headers": { "Content-Type": "application/json" },
            "body": json.dumps({"error": "uid required"})
        }

    result = asyncio.run(do_likes(uid, server, likes, max_conc))

    return {
        "status": 200,
        "headers": { "Content-Type": "application/json" },
        "body": json.dumps(result)
    }
