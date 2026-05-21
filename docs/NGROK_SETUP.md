# Ngrok Public Demo Setup

This guide explains how to expose ParkSmart to the internet for demos using **ngrok**, without any code changes.

---

## What You Need

- [ngrok](https://ngrok.com/) account (free tier works)
- ParkSmart backend and frontend already working locally
- Your ngrok authtoken (from [dashboard.ngrok.com](https://dashboard.ngrok.com/get-started/your-authtoken))

---

## 1. Install ngrok

**Windows (via winget):**
```
winget install ngrok.ngrok
```

**Or download directly:** https://ngrok.com/download

Verify installation:
```
ngrok version
```

---

## 2. Authenticate ngrok

Run once to link your account:
```
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

---

## 3. Start the Demo (Recommended — Use the Script)

The easiest way is to use the included startup script:

```bat
start-demo.bat https://YOUR-NGROK-URL.ngrok-free.app
```

Or run it interactively — it will prompt for the URL:
```bat
start-demo.bat
```

> **Note:** You need to start the ngrok tunnel *first* to get the URL (see step 4), then pass it to the script.

---

## 4. Manual Setup (Step-by-Step)

### Step 4a — Start the backend

```
python -m uvicorn src.api.server:app --reload --port 8000
```

### Step 4b — Expose the backend via ngrok

In a **new terminal**:
```
ngrok http 8000
```

You will see output like:
```
Forwarding    https://abc123.ngrok-free.app -> http://localhost:8000
```

Copy the `https://abc123.ngrok-free.app` URL.

### Step 4c — Update the frontend environment

Edit `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=https://abc123.ngrok-free.app
NEXT_PUBLIC_APP_ENV=demo
```

### Step 4d — Add the ngrok URL to backend CORS

Edit the root `.env` file and add/update:
```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://abc123.ngrok-free.app
```

### Step 4e — Start the frontend

```
cd frontend
npm run dev
```

Your frontend at `http://localhost:3000` now routes API calls through the public ngrok URL.

### Step 4f — (Optional) Expose the frontend too

If you want to share the full UI publicly:

```
ngrok http 3000
```

You will get a second URL like `https://xyz789.ngrok-free.app`. Share this with your audience.

Remember to also add this frontend ngrok URL to `CORS_ORIGINS` in `.env`.

---

## 5. Environment Variables Reference

### Backend (root `.env`)

| Variable | Description | Default |
|---|---|---|
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins | `http://localhost:3000,http://127.0.0.1:3000` |

### Frontend (`frontend/.env.local`)

| Variable | Description | Local value | Demo value |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` | `https://xxx.ngrok-free.app` |
| `NEXT_PUBLIC_APP_ENV` | Enables demo banner | `local` | `demo` |

---

## 6. Demo Banner

When `NEXT_PUBLIC_APP_ENV=demo`, a yellow banner appears at the top of every page:

> 🚀 **ParkSmart AI — Public Demo Environment** · Backend: https://xxx.ngrok-free.app

This is automatically hidden in `local` mode. No code changes needed.

---

## 7. Switching Back to Local Development

Run:
```bat
start-local.bat
```

Or manually reset `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_ENV=local
```

---

## 8. Free Tier Limitations

- Ngrok free tier generates a **random URL** every time you restart the tunnel.
- Each restart requires updating `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS`.
- For stable URLs, upgrade to a paid ngrok plan or use a custom domain.

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `CORS error` in browser | Add the ngrok frontend URL to `CORS_ORIGINS` in `.env` and restart backend |
| `ERR_NGROK_3200` (tunnel not found) | Restart ngrok and update URLs |
| API calls returning 502 | Make sure the FastAPI backend is running on port 8000 |
| Banner not showing | Check `NEXT_PUBLIC_APP_ENV=demo` is set in `frontend/.env.local` and restart `npm run dev` |
