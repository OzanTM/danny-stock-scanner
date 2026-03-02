# GitHub & Deployment Guide

## 📋 Prerequisites

- GitHub account (free at https://github.com)
- One of these deployment platforms (all have free tier):
  - **Render** (recommended, easiest)
  - **Railway**
  - **PythonAnywhere**
  - **Heroku** (limited free tier after Nov 2022)

---

## 1️⃣ GitHub Setup

### Create Repository on GitHub

1. Go to https://github.com/new
2. Fill in:
   - **Repository name:** `danny-stock-scanner`
   - **Description:** `BIST Stock Market Scanner with KDJ Indicator`
   - **Public** (required for free deployment)
3. **DO NOT** check "Initialize this repository with a README"
4. Click **Create repository**

### Get Repository URL

After creating, you'll see a URL like:
```
https://github.com/YOUR_USERNAME/danny-stock-scanner.git
```

Copy this URL.

### Push Code to GitHub

Run these commands in your project directory:

```bash
git remote add origin https://github.com/YOUR_USERNAME/danny-stock-scanner.git
git branch -M main
git push -u origin main
```

**Replace** `YOUR_USERNAME` with your actual GitHub username.

---

## 2️⃣ Deployment Options

### 🟢 Option A: **Render** (RECOMMENDED)

**Why Render?** Easiest, free tier is generous, auto-deploys from GitHub

1. Go to https://render.com
2. Sign up with GitHub account (click "Continue with GitHub")
3. Click **+ New +** → **Web Service**
4. Connect your GitHub account
5. Select `danny-stock-scanner` repository
6. Fill in:
   - **Name:** `danny-stock-scanner`
   - **Root Directory:** (leave empty)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
7. Click **Deploy**

**Your app will be live at:**
```
https://danny-stock-scanner.onrender.com
```

---

### 🟡 Option B: **Railway**

**Why Railway?** Modern, good free tier, nice dashboard

1. Go to https://railway.app
2. Sign up with GitHub
3. Click **New Project** → **Deploy from GitHub repo**
4. Select your `danny-stock-scanner` repo
5. Railway auto-detects Flask and configures it
6. Set environment variable:
   - **FLASK_ENV:** `production`
   - **FLASK_HOST:** `0.0.0.0`
   - **FLASK_PORT:** `8000`
7. Click **Deploy**

**Your app will be at:**
```
https://danny-stock-scanner-production.up.railway.app
```

---

### 🔵 Option C: **PythonAnywhere**

**Why PythonAnywhere?** Reliable, good for Python apps

1. Go to https://pythonanywhere.com
2. Create free account
3. Upload your code via Git in Web tab:
   - Click "Add a new web app"
   - Choose Flask
   - Choose Python 3.11
   - Create it
4. Go to **Web** tab → **Source code** → clone your GitHub repo
5. Set WSGI configuration to point to `app.py`
6. Reload your web app

---

## 3️⃣ Environment Variables

If deployed platform needs environment variables, set:

```
FLASK_ENV=production
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

The app uses SQLite (`data/scan_jobs.sqlite3`), which works on free tier.

---

## 4️⃣ Testing Deployed App

Once deployed, your app will be available at a public URL. You can:

1. Visit the homepage
2. Start a scan
3. View results in Signals panel
4. Download CSV exports
5. Check the Summary page

---

## ⚠️ Important Notes

- **Database:** SQLite stores scan results in `data/scan_jobs.sqlite3`
  - On free tier, this resets periodically
  - For persistent data, consider upgrading to paid or using PostgreSQL

- **Stock Data:** App downloads live BIST data on each scan
  - Scans may take 1-5 minutes depending on connection

- **First Deploy:** May take 2-5 minutes to start
  - Visit the URL, you might see a loading screen initially

---

## 📝 Next Steps

1. **Create GitHub repo** (see Section 1)
2. **Push code** to GitHub (see Section 1)
3. **Choose platform** (Render recommended)
4. **Deploy** (see your chosen option in Section 2)
5. **Test** your app at the provided URL

Need help? Check your chosen platform's documentation or feel free to ask!
