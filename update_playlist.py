import os, random, re, sys
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- Config via environment variables ---
SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]
TARGET = os.environ["TARGET_PLAYLIST_ID"]
SEED_PLAYLISTS = [s.strip() for s in os.environ.get("SEED_PLAYLISTS","").split(",") if s.strip()]
MAX_ITEMS = int(os.environ.get("MAX_ITEMS","150"))
BANLIST = os.environ.get("BANLIST_PLAYLIST_ID")  # optional

def creds():
    c = Credentials(token=None,
                    refresh_token=REFRESH_TOKEN,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET,
                    scopes=SCOPES)
    c.refresh(Request())
    return c

def yt():
    return build("youtube", "v3", credentials=creds(), cache_discovery=False)

def iso_to_seconds(iso):
    h = m = s = 0
    mobj = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", iso or "")
    if mobj:
        h = int(mobj.group(1) or 0); m = int(mobj.group(2) or 0); s = int(mobj.group(3) or 0)
    return h*3600 + m*60 + s

def get_my_liked_videos(y):
    items, page = [], None
    while True:
        resp = y.videos().list(
            part="id,snippet,contentDetails,status",
            myRating="like",
            maxResults=50,
            pageToken=page
        ).execute()
        items += resp.get("items", [])
        page = resp.get("nextPageToken")
        if not page: break
    return items

def get_videos_from_playlist(y, pid):
    vids, page = [], None
    while True:
        pl = y.playlistItems().list(
            part="contentDetails",
            playlistId=pid,
            maxResults=50,
            pageToken=page
        ).execute()
        ids = [i["contentDetails"]["videoId"] for i in pl.get("items",[])]
        if ids:
            v = y.videos().list(
                part="id,snippet,contentDetails,status",
                id=",".join(ids)
            ).execute()
            vids += v.get("items",[])
        page = pl.get("nextPageToken")
        if not page: break
    return vids

def filter_music(items, banned_ids=set()):
    OUT = []
    for it in items:
        vid = it["id"]
        if vid in banned_ids: continue
        sn, cd, st = it["snippet"], it["contentDetails"], it.get("status", {})
        dur = iso_to_seconds(cd.get("duration","PT0S"))
        title = (sn.get("title") or "").lower()
        if st.get("privacyStatus") != "public": continue
        if not st.get("embeddable", True): continue
        if "live" in title or dur < 90 or dur > 540: continue
        rr = cd.get("regionRestriction", {})
        if rr.get("blocked"): continue
        OUT.append(it)
    return OUT

def current_playlist_video_ids(y, pid):
    ids, map_id_to_item, page = [], {}, None
    while True:
        resp = y.playlistItems().list(
            part="id,contentDetails,snippet",
            playlistId=pid, maxResults=50, pageToken=page
        ).execute()
        for it in resp.get("items", []):
            vid = it["contentDetails"]["videoId"]
            ids.append(vid)
            map_id_to_item[vid] = it
        page = resp.get("nextPageToken")
        if not page: break
    return ids, map_id_to_item

def add_to_playlist(y, pid, video_id, pos=None):
    body = {"snippet":{"playlistId": pid, "resourceId":{"kind":"youtube#video","videoId":video_id}}}
    if pos is not None: body["snippet"]["position"] = pos
    y.playlistItems().insert(part="snippet", body=body).execute()

def delete_playlist_item(y, playlist_item_id):
    y.playlistItems().delete(id=playlist_item_id).execute()

def get_banlist_ids(y, pid):
    if not pid: return set()
    vids = get_videos_from_playlist(y, pid)
    return set(v["id"] for v in vids)

def main():
    y = yt()
    pool = []

    # 1) your liked videos
    try:
        pool += get_my_liked_videos(y)
    except Exception as e:
        print("Failed to fetch liked videos; check scope & OAuth:", e, file=sys.stderr)

    # 2) seed playlists (e.g., curated/recommended)
    for pid in SEED_PLAYLISTS:
        if pid and pid != TARGET:
            try:
                pool += get_videos_from_playlist(y, pid)
            except Exception as e:
                print(f"Failed to read seed playlist {pid}: {e}", file=sys.stderr)

    banned = get_banlist_ids(y, BANLIST)

    # Filter, dedupe
    pool = filter_music(pool, banned_ids=banned)
    uniq = {it["id"]: it for it in pool}
    pool = list(uniq.values())

    # Randomize & cap
    random.shuffle(pool)
    desired = [it["id"] for it in pool[:MAX_ITEMS]]

    # Sync with target playlist
    cur_ids, id_to_item = current_playlist_video_ids(y, TARGET)

    # Add missing
    to_add = [vid for vid in desired if vid not in cur_ids]
    for vid in to_add:
        add_to_playlist(y, TARGET, vid)

    # Trim overflow
    cur_ids, id_to_item = current_playlist_video_ids(y, TARGET)
    if len(cur_ids) > MAX_ITEMS:
        extra = cur_ids[MAX_ITEMS:]
        for vid in extra:
            delete_playlist_item(y, id_to_item[vid]["id"])

    print(f"Desired {len(desired)} | Added {len(to_add)} | Final size ~{min(len(cur_ids), MAX_ITEMS)}")

if __name__ == "__main__":
    main()
