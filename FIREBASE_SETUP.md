# 🔐 Firebase Authentication Setup Guide

## Step 1: Create Firebase Project (5 minutes)

1. Go to: https://console.firebase.google.com/
2. Click **"Add project"**
3. Name it: `roadwatch-kerala`
4. Disable Google Analytics (optional for now)
5. Click **"Create project"**

## Step 2: Enable Authentication Methods

1. In Firebase console, click **"Authentication"** in left sidebar
2. Click **"Get started"**
3. Go to **"Sign-in method"** tab
4. Enable these providers:
   - **Email/Password** - Click, toggle Enable, Save
   - **Google** - Click, toggle Enable, add support email, Save

## Step 3: Register Your Web App

1. Click the **gear icon** (⚙️) next to "Project Overview"
2. Click **"Project settings"**
3. Scroll down to **"Your apps"**
4. Click the **web icon** (</>) to add a web app
5. Nickname: `RoadWatch Web`
6. Check ✅ **"Also set up Firebase Hosting"** (optional)
7. Click **"Register app"**

## Step 4: Copy Your Config

You'll see a code snippet like this:

```javascript
const firebaseConfig = {
  apiKey: "AIza...",
  authDomain: "roadwatch-kerala.firebaseapp.com",
  projectId: "roadwatch-kerala",
  storageBucket: "roadwatch-kerala.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123"
};
```

**Save this! You'll need it in Step 5.**

## Step 5: Update Your Frontend HTML

I'll provide you an updated `roadwatch-kerala.html` with Firebase integrated.

## Step 6: Update Backend for User Tokens

I'll provide an updated `backend.py` that verifies Firebase tokens.

---

## What You'll Get

**User Features:**
- ✅ Email/password signup
- ✅ Google Sign-In
- ✅ User profiles
- ✅ Report history per user
- ✅ Logout functionality

**Backend Features:**
- ✅ Verify user identity via Firebase tokens
- ✅ Store reports with real user IDs (not IP addresses)
- ✅ Track user reputation
- ✅ Ban abusive users

---

**Ready?** Complete Steps 1-4 above, then tell me when you have your Firebase config. I'll give you the updated code with everything integrated.
