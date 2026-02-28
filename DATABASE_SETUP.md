# 🗄️ Database Setup Guide

## What Changed?

Your app now uses **PostgreSQL database** instead of in-memory storage. This means:
- ✅ Reports persist forever (even when Railway restarts)
- ✅ Can handle thousands of reports
- ✅ Production-ready and scalable
- ✅ Automatic backups (on Railway)

## 🚀 Setting Up on Railway

### Step 1: Add PostgreSQL to Your Railway Project

1. Go to your Railway dashboard: https://railway.app/dashboard
2. Open your **roadwatch-kerala project**
3. Click **"+ New"** button
4. Select **"Database"**
5. Choose **"PostgreSQL"**
6. Railway creates the database instantly!

### Step 2: Connect Backend to Database

Railway automatically sets the `DATABASE_URL` environment variable. Your backend code already handles this!

**No manual configuration needed** - it just works! 🎉

### Step 3: Deploy Updated Code

Upload these 3 new/updated files to Railway:

**Method A: Via Railway Dashboard**
1. Click your backend service
2. Go to "Deployments" tab
3. Click "Deploy" → "Redeploy"
4. Or manually upload the files

**Method B: Via GitHub (Recommended)**
1. Commit the new files to your GitHub repo:
   ```bash
   cd ~/Desktop/roadwatch
   git add .
   git commit -m "Add PostgreSQL database"
   git push
   ```
2. Railway auto-deploys!

### Step 4: Verify Database is Working

Once deployed, check Railway logs:
```
✅ Database tables created successfully
🚦 RoadWatch Kerala Backend Starting...
```

Test it:
1. Submit a report from your frontend
2. Check Railway logs - should see: `POST /api/reports HTTP/1.1 201`
3. Restart your Railway service (Settings → Restart)
4. Submit another report
5. Check `/api/stats` - you should see BOTH reports still there!

## 🧪 Testing Locally with SQLite

Before deploying, test locally:

```bash
cd ~/Desktop/roadwatch
source venv/bin/activate

# Install new dependencies
pip install flask-sqlalchemy psycopg2-binary

# Run locally (uses SQLite by default)
export ANTHROPIC_API_KEY="your-key"
python backend.py
```

You'll see: `✅ Database tables created successfully`

A file called `roadwatch.db` will be created - this is your local SQLite database.

## 📊 Database Schema

The `reports` table has these columns:

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key (auto-increment) |
| plate_number | String | Vehicle plate (indexed for fast lookup) |
| violations | Text | JSON array of violations |
| location | String | Where incident occurred |
| description | Text | Optional details |
| photo_url | String | URL to photo (for future use) |
| user_id | String | Reporter's ID or IP |
| status | String | pending/approved/rejected |
| moderation_approved | Boolean | AI decision |
| moderation_reason | Text | Why approved/rejected |
| moderation_confidence | Float | AI confidence 0-1 |
| moderation_flags | Text | JSON array of issues found |
| moderation_reviewed_at | DateTime | When AI reviewed it |
| created_at | DateTime | When submitted |
| updated_at | DateTime | Last modified |

## 🔧 Troubleshooting

**"No module named 'models'"**
- Make sure you uploaded `models.py` to Railway
- Check Railway file list includes `models.py`

**"DATABASE_URL not set"**
- Make sure PostgreSQL service is running in Railway
- Both services (backend + database) should be in same project
- Railway auto-connects them

**"Table doesn't exist"**
- Check Railway logs for `✅ Database tables created successfully`
- If missing, the `db.create_all()` didn't run
- Try redeploying

**Local testing shows "operational error"**
- Install dependencies: `pip install flask-sqlalchemy psycopg2-binary`
- Make sure you're in virtual environment: `source venv/bin/activate`

## 📈 Database Management

**View your data in Railway:**
1. Go to Railway dashboard
2. Click your PostgreSQL service
3. Click "Data" tab
4. See all reports in real-time!

**Query your database:**
Railway provides a SQL editor where you can run queries like:
```sql
-- See all approved reports
SELECT * FROM reports WHERE status = 'approved' ORDER BY created_at DESC;

-- Count reports by plate
SELECT plate_number, COUNT(*) as count 
FROM reports 
WHERE status = 'approved' 
GROUP BY plate_number 
ORDER BY count DESC;

-- Today's reports
SELECT COUNT(*) FROM reports WHERE DATE(created_at) = CURRENT_DATE;
```

## 🎯 What's Next?

Now that you have a database, you can add:

1. **Admin Dashboard** - View/moderate reports manually
2. **User Accounts** - Track who reports what
3. **Analytics** - Violation hotspots, trends over time
4. **Export Data** - Send CSV to Kerala Traffic Police
5. **API for Authorities** - Let them query your database

Your infrastructure is now production-ready! 🚀
