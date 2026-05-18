# NICS Employee Time Monitoring System

Web-based attendance tracking for NICS Call Centre.

## Quick Deploy

### Step 1 — Supabase (database)
1. Go to https://supabase.com and sign up free
2. Create a new project (remember your password)
3. Go to **SQL Editor** and paste the contents of `supabase_setup.sql` and click **Run**
4. Go to **Settings → API** and copy:
   - Project URL
   - anon/public key

### Step 2 — GitHub
1. Create a new repository on GitHub (name it `nics-monitoring`)
2. Upload all these files to it

### Step 3 — Streamlit Cloud
1. Go to https://share.streamlit.io
2. Click **New app**
3. Connect your GitHub repo
4. Set **Main file path** to `app.py`
5. Go to **Advanced settings → Secrets** and add:
```
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_KEY = "your-anon-public-key"
```
6. Click **Deploy**

Your app will be live at:
`https://your-app-name.streamlit.app`

## Credentials
| Role | Username | Password |
|------|----------|----------|
| Admin | edgart | Admin@2025 |
| Admin | mabokop | Admin@2025 |
| Supervisor | nomsa, tmodise, jramahlo, tshepom, bmohau | nics1068 |
| Agent | (their username) | no password |
