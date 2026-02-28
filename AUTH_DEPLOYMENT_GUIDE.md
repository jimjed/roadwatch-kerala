# 🔐 User Authentication - Complete Deployment Guide

## What You're Getting

✅ **Email/Password & Google Sign-In** via Firebase  
✅ **User Profiles** with display name, photo, stats  
✅ **Reputation System** (increases with good reports, decreases with rejected ones)  
✅ **Auto-ban** for users with low reputation (<20 points)  
✅ **Report History** per user  
✅ **Backwards compatible** - anonymous reports still work  

---

## 📦 New Files Overview

1. **backend.py** - Updated with auth endpoints
2. **models.py** - Updated Report model with user relationships
3. **user_model.py** - NEW: User table schema
4. **auth.py** - NEW: Firebase token verification
5. **requirements.txt** - Added `requests` library
6. **FIREBASE_SETUP.md** - Firebase project setup

---

## 🚀 Deployment Steps

### Step 1: Set Up Firebase (10 minutes)

Follow **FIREBASE_SETUP.md** to:
1. Create Firebase project
2. Enable Email/Password & Google auth
3. Register web app
4. Copy your Firebase config

### Step 2: Add Firebase Config to Railway

In Railway dashboard:

1. Click your **backend service**
2. Go to **Variables** tab
3. Add these new environment variables:

```
FIREBASE_PROJECT_ID=roadwatch-kerala
FIREBASE_API_KEY=AIza... (from Firebase console)
```

To find these values:
- Go to Firebase Console → Project Settings
- Under "General" tab, see "Web API Key"
- Project ID is at the top

### Step 3: Deploy Updated Backend

**Via GitHub:**
```bash
cd ~/Desktop/roadwatch

# Download all 5 new files from above and replace/add them:
# - backend.py (updated)
# - models.py (updated)
# - user_model.py (NEW)
# - auth.py (NEW)
# - requirements.txt (updated)

git add .
git commit -m "Add user authentication with Firebase"
git push
```

**Or manually upload** all 5 files to Railway.

### Step 4: Database Migration

The database needs a new `users` table. Railway will create it automatically on first deploy.

Watch the logs for:
```
✅ Database tables created successfully
```

If you see errors about columns, you may need to drop and recreate tables:

**Option A - Fresh Start (if no important data):**
In Railway PostgreSQL dashboard → Data tab → Run SQL:
```sql
DROP TABLE IF EXISTS reports CASCADE;
DROP TABLE IF EXISTS users CASCADE;
```

Then redeploy the backend - tables will be recreated.

**Option B - Keep Data (advanced):**
Use migrations (contact me if you need this).

### Step 5: Update Frontend (I'll provide this next)

You'll need an updated HTML file with Firebase auth UI.

Tell me when you've completed Steps 1-4, and I'll give you the frontend code!

---

## 🎯 New API Endpoints

### POST /api/auth/register
Register/update user after Firebase login
- Headers: `Authorization: Bearer <firebase_token>`
- Returns: User profile

### GET /api/auth/profile
Get current user's profile
- Headers: `Authorization: Bearer <firebase_token>`
- Returns: User stats, reputation, ban status

### GET /api/auth/reports
Get user's report history
- Headers: `Authorization: Bearer <firebase_token>`
- Returns: All reports by this user

### POST /api/reports (Updated)
Submit report - now works with or without auth
- Optional header: `Authorization: Bearer <firebase_token>`
- If authenticated: saves user info, tracks reputation
- If anonymous: saves IP address (old behavior)

---

## 🏆 Reputation System

**Starting Score:** 100 points

**Points Changes:**
- Approved report: +0.5 points (max 100)
- Rejected report: -2 points
- Auto-ban at: <20 points

**Ban Logic:**
- User can't submit reports
- Returns 403 error with ban reason
- Requires manual unban (admin feature coming later)

---

## 🧪 Testing Checklist

Once deployed, test:

1. **Anonymous submission still works**
   - Submit without logging in
   - Should work as before

2. **Email signup**
   - Create account
   - Submit report
   - Check user appears in database

3. **Google sign-in**
   - Sign in with Google
   - Submit report
   - Verify profile saved

4. **Reputation tracking**
   - Submit good report → check reputation increased
   - Submit spam report → check reputation decreased

5. **Ban system**
   - Create test user
   - Submit 40 spam reports (reputation drops to 20)
   - Try submitting again → should get 403 banned error

---

## 📊 Database Schema Changes

### New `users` Table:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    firebase_uid VARCHAR(128) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    photo_url VARCHAR(500),
    total_reports INTEGER DEFAULT 0,
    approved_reports INTEGER DEFAULT 0,
    rejected_reports INTEGER DEFAULT 0,
    reputation_score FLOAT DEFAULT 100.0,
    is_banned BOOLEAN DEFAULT FALSE,
    ban_reason TEXT,
    created_at TIMESTAMP,
    last_login TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Updated `reports` Table:
```sql
ALTER TABLE reports 
ADD COLUMN user_id INTEGER REFERENCES users(id),
ADD COLUMN user_ip VARCHAR(50);
```

Old `user_id` (string) → Split into:
- `user_id` (integer, foreign key to users)
- `user_ip` (string, for anonymous reports)

---

## 🔧 Troubleshooting

**"Firebase token invalid"**
- Check FIREBASE_API_KEY is set correctly in Railway
- Verify token isn't expired (tokens last 1 hour)
- Frontend must send token in Authorization header

**"User not found after login"**
- User might not have called `/api/auth/register` after Firebase login
- Frontend needs to call this endpoint after successful Firebase auth

**"Column 'user_id' does not exist"**
- Database migration didn't run
- Drop tables and redeploy (see Step 4)

**"Import error: user_model"**
- Make sure you uploaded user_model.py
- Check Railway file list includes all 3 new Python files

---

## ✅ What's Next

After backend is deployed:

**Immediate:**
- Updated frontend HTML with Firebase UI (I'll provide)
- Test authentication flow

**Soon:**
- Admin dashboard to view users and unban
- Email verification requirement
- User reputation badges
- Report upvoting by other users

---

**Ready to proceed?** Complete Steps 1-4 above, then let me know and I'll give you the updated frontend!
