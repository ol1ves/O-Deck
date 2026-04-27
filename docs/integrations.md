# O-Deck Integration Setup

Each integration is optional. Missing credentials disable that integration gracefully; other widgets continue to work.

---

## Weather (Open-Meteo)

**Auth:** None. Completely free.

Configure in `~/.config/cyberdeck/config.yaml`:
```yaml
device:
  location:
    lat: 40.6926   # your latitude
    lon: -73.9869  # your longitude
```

---

## Transit (MTA GTFS-RT)

**Auth:** None required (free open data feed).

If you get 401 errors, register for a free MTA API key at:
https://api.mta.info/#/AccessKey

Then add to `~/.config/cyberdeck/.env`:
```
MTA_API_KEY=your-key-here
```

Configure stations in `config.yaml` → `transit.primary_stations` and `transit.secondary_stations`.

To find stop IDs for your stations:
1. Download GTFS static data: https://api-endpoint.mta.info/Feeds/http://realtime.mta.info/
2. Look up your station in `stops.txt`
3. Stop IDs end in `N` (Uptown) or `S` (Downtown)
4. Example: Jay St–MetroTech A/C/F/R uptown = `A41N`

---

## Google Calendar

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable **Google Calendar API**
4. OAuth consent screen → External → Add your email as test user
5. Credentials → Create OAuth client ID → Desktop application → Download JSON as `credentials.json`
6. Run OAuth flow from your laptop:
   ```bash
   pip install google-auth-oauthlib
   python3 scripts/auth/google-auth.py --credentials credentials.json
   ```
7. SCP files to Pi:
   ```bash
   scp google-token.json pi@<pi-ip>:~/.config/cyberdeck/google-token.json
   scp credentials.json pi@<pi-ip>:~/.config/cyberdeck/google-credentials.json
   ```
8. Add to `.env`:
   ```
   GOOGLE_CALENDAR_CREDENTIALS_PATH=/home/pi/.config/cyberdeck/google-credentials.json
   GOOGLE_CALENDAR_TOKEN_PATH=/home/pi/.config/cyberdeck/google-token.json
   ```

---

## Notion

1. Go to [Notion Integrations](https://www.notion.so/profile/integrations)
2. Create a new internal integration → Select workspace
3. Copy the **Internal Integration Token**
4. Share your todo databases with the integration (share button → invite → your integration)
5. Get database IDs from the URL: `notion.so/<workspace>/<database-id>?v=...`
6. Add to `.env`:
   ```
   NOTION_TOKEN=secret_xxx
   ```
7. Add database IDs to `config.yaml`:
   ```yaml
   calendar:
     notion:
       todo_database_ids:
         - your-database-id-here
   ```

---

## Spotify

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create an app → Settings → note Client ID and Client Secret
3. Add redirect URI: `http://localhost:8889/callback`
4. Run OAuth flow from your laptop:
   ```bash
   pip install requests
   SPOTIFY_CLIENT_ID=xxx SPOTIFY_CLIENT_SECRET=xxx python3 scripts/auth/spotify-auth.py
   ```
5. Copy the refresh token to `.env`:
   ```
   SPOTIFY_CLIENT_ID=xxx
   SPOTIFY_CLIENT_SECRET=xxx
   SPOTIFY_REFRESH_TOKEN=xxx
   ```

---

## GitHub

1. Go to GitHub → Settings → Developer settings → Fine-grained personal access tokens
2. Create new token → Repository access: Public Repositories only (read-only)
3. Permissions: Contents (read), Issues (read), Pull requests (read), Metadata (read)
4. Add to `.env`:
   ```
   GITHUB_TOKEN=ghp_xxx
   ```
5. Add to `config.yaml`:
   ```yaml
   github:
     username: your-github-username
   ```

---

## RSS

Configure feeds in `config.yaml`:
```yaml
rss:
  feeds:
    - name: "TLDR"
      url: "https://kill-the-newsletter.com/feeds/<your-id>.xml"
    - name: "Hacker News"
      url: "https://news.ycombinator.com/rss"
    - name: "r/nyc"
      url: "https://www.reddit.com/r/nyc/.rss"
```

For TLDR: subscribe at https://tldr.tech and use kill-the-newsletter.com to get an RSS URL.

---

## Photos

### Local folder (simplest)
```bash
mkdir ~/cyberdeck-photos
# Drop photos into this folder from laptop:
scp ~/Pictures/*.jpg pi@<pi-ip>:~/cyberdeck-photos/
```

In `config.yaml`:
```yaml
photos:
  source: "local"
  local_folder: "~/cyberdeck-photos"
  rotation_seconds: 30
```

### iCloud Shared Album
1. On iPhone: Photos → open album → Share → Create Shared Album → get the share URL
2. In `config.yaml`:
   ```yaml
   photos:
     source: "icloud_shared_album"
     icloud_share_url: "https://www.icloud.com/sharedalbum/#B0xxx"
   ```

Note: iCloud shared album API is unofficial and may break if Apple changes their CDN.
The fallback is always local folder.
