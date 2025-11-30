import json
import os
import sys
import asyncio
import httpx
import time
import binascii

# tambahkan root path agar bisa import file original
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from get_jwt import create_jwt
from encrypt_like_body import create_like_payload
from count_likes import GetAccountInformation

# load guest file
GUEST_FILE = os.path.join(ROOT, "guests_manager", "guests_converted.json")
with open(GUEST_FILE, "r") as f:
    GUESTS = json.load(f)

# memory sementara (serverless tidak menyimpan file)
usage_temp = {}

def ensure_target(uid):
    if uid not in usage_temp:
        usage_temp[uid] = {"used": set()}

def base_url(server):
    server = server.upper()
    if server == "IND":
        return "https://client.ind.freefiremobile.com"
    if server in {"BR", "US", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com"
    return "https://clientbp.ggblueshark.com"

async def like_single(guest, target_uid, BASE_URL, semaphore):
    guest_uid = str(guest["uid"])
    guest_pw = guest["password"]

    if guest_uid in usage_temp[target_uid]["used"]:
        return False

    async with semaphore:
        try:
            jwt, region, server_from_jwt = await create_jwt(guest_uid, guest_pw)
            payload = create_like_payload(target_uid, region)
            if isinstance(payload, str):
                payload = binascii.unhexlify(payload)

            headers = {
                "User-Agent": "Dalvik/2.1.0 (Linux; Android 14)",
                "Content-Type": "application/octet-stream",
                "Authorization": f"Bearer {jwt}",
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{BASE_URL}/LikeProfile", data=payload, headers=headers)
                resp.raise_for_status()

            usage_temp[target_uid]["used"].add(guest_uid)
            return True

        except Exception:
            return False

async def process_likes(uid, server, likes, max_concurrent):
    BASE_URL = base_url(server)
    ensure_target(uid)

    available = [
        g for g in GUESTS 
        if str(g["uid"]) not in usage_temp[uid]["used"]
    ]

    likes = min(len(available), likes)

    sem = asyncio.Semaphore(max_concurrent)
    tasks = [
        like_single(g, uid, BASE_URL, sem)
        for g in available[:likes]
    ]

    results = await asyncio.gather(*tasks)
    success = sum(1 for r in results if r)

    info_after = await GetAccountInformation(uid, "0", server, "/GetPlayerPersonalShow")

    return {
        "attempted": likes,
        "success": success,
        "after_info": info_after
    }

def handler(request):
    try:
        uid = request.args.get("uid")
        server = request.args.get("server", "IND")
        likes = int(request.args.get("likes", 100))
        max_concurrent = int(request.args.get("max_concurrent", 20))
    except:
        return {"statusCode": 400, "body": json.dumps({"error": "invalid parameters"})}

    if not uid:
        return {"statusCode": 400, "body": json.dumps({"error": "uid is required"})}

    result = asyncio.run(process_likes(uid, server, likes, max_concurrent))

    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
