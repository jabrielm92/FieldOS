# FieldOS Frontend - Vercel Deployment

## Quick Deploy

### 1. Deploy to Vercel
```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy (from frontend directory)
cd /path/to/frontend
vercel

# Set environment variable
vercel env add REACT_APP_BACKEND_URL
# Enter: https://your-railway-url.up.railway.app

# Redeploy with env
vercel --prod
```

### 2. Or Deploy via GitHub
1. Push code to GitHub
2. Go to vercel.com → New Project
3. Import your repo, select `frontend` as root directory
4. Add environment variable:
   - `REACT_APP_BACKEND_URL` = `https://your-railway-url.up.railway.app`
5. Deploy

## Environment Variables

| Variable | Description |
|----------|-------------|
| REACT_APP_BACKEND_URL | Railway backend URL |

## After Deployment
Update Railway's CORS_ORIGINS to include your Vercel URL:
```bash
railway variables set CORS_ORIGINS="https://your-app.vercel.app"
```
