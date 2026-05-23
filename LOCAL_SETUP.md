# 🚀 Quick Setup Guide - Run Locally with Gemini API

## Step 1: Get Your Free Gemini API Key

1. Visit: **https://aistudio.google.com/apikey**
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the generated key

## Step 2: Configure Your .env File

1. Open `.env` file in the project root
2. Find the line: `GOOGLE_API_KEY=your-gemini-api-key-here`
3. Replace `your-gemini-api-key-here` with your actual Gemini API key
4. Save the file

Example:
```env
GOOGLE_API_KEY=AIzaSyBqL8ZxYNf4K9mP2Xr3Wt5Hj6Vd8Gc1Ea0
```

## Step 3: Install Dependencies (if not already done)

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

## Step 4: Initialize Database (first time only)

```bash
python main.py --setup
```

This will:
- Create SQLite database at `data/parking_dynamic.db`
- Seed parking types, slots, prices, and hours
- Initialize Pinecone vector store with parking info

## Step 5: Start the Backend API

```bash
python -m uvicorn src.api.server:app --reload --port 8000
```

The backend will be available at: **http://localhost:8000**

## Step 6: Test the API

Open your browser and visit:
- **Health check**: http://localhost:8000/
- **API docs**: http://localhost:8000/docs

Or use the terminal chatbot:
```bash
python main.py
```

## Step 7 (Optional): Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at: **http://localhost:3000**

## Troubleshooting

### Issue: "Invalid API key" or "401 Unauthorized"
- Double-check your GOOGLE_API_KEY in `.env`
- Make sure there are no extra spaces or quotes
- Verify the key is active at https://aistudio.google.com/apikey

### Issue: "Pinecone connection failed"
- Verify PINECONE_API_KEY in `.env`
- Check that index name is `parking` (not `parking-info`)
- Make sure Pinecone index exists with 384 dimensions

### Issue: "No module named 'xxx'"
- Run: `pip install -r requirements.txt`
- Make sure virtual environment is activated

### Issue: Database errors
- Delete `data/parking_dynamic.db` and run `python main.py --setup` again

## LLM Provider Priority

The app uses LLMs in this order:
1. **Gemini 2.5 Flash** (if GOOGLE_API_KEY is set) ← Recommended for local
2. **Groq Llama 3.3** (if GROQ_API_KEY is set)
3. **EPAM DIAL** (if DIAL_API_KEY is set, requires EPAM network)

To use a different provider, just set the corresponding API key in `.env`.

## What's Working

✅ Backend API with Gemini LLM  
✅ SQLite database with auto-seeding  
✅ Pinecone vector store for RAG  
✅ Email notifications (Gmail SMTP)  
✅ Payment workflow with unique tokens  
✅ Admin approval system  
✅ Frontend (Next.js + shadcn/ui)  
✅ 250 tests passing  

## Need Help?

Check the logs:
- Backend logs appear in the terminal running uvicorn
- Test the /api/chat endpoint with curl:
  ```bash
  curl -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "Hello", "session_id": "test123"}'
  ```

Enjoy! 🎉
