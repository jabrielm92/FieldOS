# FieldOS Backend - Railway Deployment

## Prerequisites
- Railway account (https://railway.app)
- MongoDB Atlas account (https://mongodb.com/atlas)
- Twilio account with phone number

## Quick Deploy

### 1. Create MongoDB Atlas Cluster
1. Go to MongoDB Atlas → Create Free Cluster
2. Create database user with password
3. Whitelist IP: `0.0.0.0/0` (allow all for Railway)
4. Get connection string: `mongodb+srv://user:pass@cluster.mongodb.net/fieldos`

### 2. Deploy Backend to Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create new project
railway init

# Link to this directory
cd /path/to/backend
railway link

# Set environment variables
railway variables set MONGO_URL="mongodb+srv://user:pass@cluster.mongodb.net/fieldos"
railway variables set DB_NAME="fieldos"
railway variables set JWT_SECRET="your-secure-secret-key"
railway variables set EMERGENT_LLM_KEY="sk-emergent-xxx"
railway variables set TWILIO_ACCOUNT_SID="ACxxx"
railway variables set TWILIO_AUTH_TOKEN="xxx"
railway variables set TWILIO_MESSAGING_SERVICE_SID="MGxxx"
railway variables set CORS_ORIGINS="https://your-vercel-app.vercel.app"

# Deploy
railway up

# Get your URL (e.g., https://fieldos-backend.up.railway.app)
railway domain
```

### 3. Set APP_BASE_URL
After getting your Railway URL:
```bash
railway variables set APP_BASE_URL="https://your-railway-url.up.railway.app"
```

### 4. Configure Twilio Webhook
1. Go to Twilio Console → Phone Numbers → Your Number
2. Set Voice webhook to: `https://your-railway-url.up.railway.app/api/v1/voice/inbound`
3. Method: POST

## Environment Variables Reference

| Variable | Description |
|----------|-------------|
| MONGO_URL | MongoDB Atlas connection string |
| DB_NAME | Database name (fieldos) |
| JWT_SECRET | Secret for JWT tokens |
| EMERGENT_LLM_KEY | Emergent universal LLM key |
| TWILIO_ACCOUNT_SID | Twilio Account SID |
| TWILIO_AUTH_TOKEN | Twilio Auth Token |
| TWILIO_MESSAGING_SERVICE_SID | Twilio Messaging Service |
| APP_BASE_URL | Your Railway app URL |
| CORS_ORIGINS | Frontend URL for CORS |
