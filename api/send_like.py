from flask import Flask, request, jsonify
import os, sys, json, asyncio, binascii, httpx

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from get_jwt import create_jwt
from encrypt_like_body import create_like_payload
from count_likes import GetAccountInformation

app = Flask(__name__)

# load guests
GUEST_FILE = os.path.join(ROOT, "guests_manager", "guests_converted.json")
with open(GUEST_FILE, "r") as f:
    GUESTS = json.load(f)

temp_used = {}

def base_url(server):
    server = server.upper()
    if server == "IND":
        return "https://client.ind.freefiremobile.com"
    if server in {"BR","US","SAC","NA"}:
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
        if str(g["uid"]) not in temp_used.get(uid, set())
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


@app.get("/api/send_like")
def send_like():
    uid = request.args.get("uid")
    server = request.args.get("server", "IND")
    likes = int(request.args.get("likes", 50))
    max_conc = int(request.args.get("max_conc", 10))

    if not uid:
        return jsonify({"error": "uid required"}), 400

    result = asyncio.run(do_likes(uid, server, likes, max_conc))
    return jsonify(result)


# export app for Vercel
def handler(request, *args, **kwargs):
    return app(request.environ, start_response=None)
