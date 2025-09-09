# Eternal DJ — Auto-Playlist Bot

This GitHub Actions job keeps your YouTube station playlist fresh by pulling your **Liked videos** and optional **seed playlists**, filtering for embeddable tracks (90–540s), shuffling, and syncing to your target playlist.

**Your target playlist ID:** `PLWi0n_okuxCMfqrcUNl29Wdz6oi_BAPSC`

## Setup

1. **Create OAuth client**
   - Google Cloud Console → Create project → Enable **YouTube Data API v3**.
   - **Credentials → Create credentials → OAuth client ID → Desktop app.**
   - Note the **Client ID** and **Client Secret**.

2. **Get a Refresh Token (OAuth Playground)**
   - https://developers.google.com/oauthplayground
   - Gear icon → **Use your own OAuth credentials** → paste Client ID/Secret.
   - Select scope: `https://www.googleapis.com/auth/youtube` → **Authorize APIs**.
   - **Exchange authorization code for tokens** → copy the **Refresh token**.

3. **Add GitHub Secrets** (Repo → Settings → Secrets and variables → Actions)
   - `YT_CLIENT_ID` — your OAuth Client ID
   - `YT_CLIENT_SECRET` — your OAuth Client Secret
   - `YT_REFRESH_TOKEN` — refresh token from OAuth Playground
   - `TARGET_PLAYLIST_ID` — e.g. `PLWi0n_okuxCMfqrcUNl29Wdz6oi_BAPSC`
   - `SEED_PLAYLISTS` — (optional) comma-separated playlist IDs to mix in
   - `BANLIST_PLAYLIST_ID` — (optional) playlist ID; any video appearing here will be removed from the target

4. **Run it**
   - Repo → **Actions** → **Update YouTube Playlist** → **Run workflow**.
   - It also runs every 6 hours via cron.

## Notes
- Quota: `playlistItems.insert/delete` cost 50 units each; a handful per run is typical.
- Make the target playlist **Public or Unlisted** so embeds work everywhere.
- To change size, set secret `MAX_ITEMS` (default 150).
