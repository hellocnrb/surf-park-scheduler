# 🚀 Deployment Guide - Surf Park Scheduler to Streamlit Cloud

## 📋 Prerequisites Checklist

Before deploying, make sure you have:
- ✅ Google Cloud Project created
- ✅ Google Sheets API enabled
- ✅ Service account credentials (JSON file)
- ✅ 3 Google Sheets created and shared with service account
- ✅ Sheet IDs copied

---

## Step 4: Prepare Files for GitHub

### 4A: Organize Your Files

You need these files in one folder:
```
surf-park-scheduler/
├── schedule_manager_cloud.py
├── coaching_rules_engine.py
├── coaching_rules.yaml
├── requirements.txt
├── sample_sessions.csv (optional)
└── README.md (optional)
```

**Important:** Do NOT upload google_credentials.json to GitHub! We'll add it as a secret.

---

## Step 5: Create GitHub Repository

### 5A: Create GitHub Account
1. Go to: https://github.com
2. Click **Sign up**
3. Follow the steps to create a free account

### 5B: Create New Repository
1. Click the **+** icon (top right)
2. Select **New repository**
3. Name it: **surf-park-scheduler**
4. Make it **Public** (required for free Streamlit hosting)
5. Click **Create repository**

### 5C: Upload Files

**Option 1: Upload via Web (Easiest)**
1. On your new repository page, click **uploading an existing file**
2. Drag and drop all your files (except google_credentials.json!)
3. Add commit message: Initial commit
4. Click **Commit changes**

---

## Step 6: Deploy to Streamlit Cloud

### 6A: Create Streamlit Cloud Account
1. Go to: https://streamlit.io/cloud
2. Click **Sign up**
3. **Sign in with GitHub** (easiest)
4. Authorize Streamlit

### 6B: Deploy Your App
1. Click **New app**
2. Select your repository: **surf-park-scheduler**
3. Main file path: **schedule_manager_cloud.py**
4. Click **Advanced settings**

### 6C: Add Secrets
In the Secrets section, paste this (fill in YOUR values):
```toml
# Google Sheets Configuration
weekly_schedule_sheet_id = YOUR_WEEKLY_SHEET_ID_HERE
assignments_sheet_id = YOUR_ASSIGNMENTS_SHEET_ID_HERE
roster_sheet_id = YOUR_ROSTER_SHEET_ID_HERE

# Google Service Account Credentials
[gcp_service_account]
type = service_account
project_id = YOUR_PROJECT_ID
private_key_id = YOUR_PRIVATE_KEY_ID
private_key = YOUR_PRIVATE_KEY
client_email = YOUR_SERVICE_ACCOUNT_EMAIL
client_id = YOUR_CLIENT_ID
auth_uri = https://accounts.google.com/o/oauth2/auth
token_uri = https://oauth2.googleapis.com/token
auth_provider_x509_cert_url = https://www.googleapis.com/oauth2/v1/certs
client_x509_cert_url = YOUR_CERT_URL
```

**How to fill this in:**
1. Open your google_credentials.json file
2. Copy each value from the JSON into the corresponding field above
3. For private_key, copy the ENTIRE value including \\n characters

### 6D: Deploy!
1. Click **Deploy!**
2. Wait 2-3 minutes for deployment
3. Your app URL will be: https://YOUR-APP-NAME.streamlit.app

---

## Step 7: Test Your Deployment

### 7A: Initial Sync
1. Open your app URL
2. Click **🔄 Sync** button
3. Should see ✅ Synced!

---

## Step 8: Share with Your Team

Your URL will be: https://surf-park-scheduler.streamlit.app

Send this link to your team!

---

## 📱 Mobile Instructions

Tell your team:
1. Open the link in mobile browser
2. Tap the share icon
3. Select Add to Home Screen
4. Now it works like an app!

---

## 🔄 Updating Your App

When you need to make changes:
1. Go to your GitHub repository
2. Click on the file you want to edit
3. Click the pencil icon (edit)
4. Make changes
5. Commit changes
6. App auto-updates in ~2 minutes!

---

## 🐛 Troubleshooting

### Google Sheets credentials not found
**Fix:** Check your secrets configuration in Streamlit Cloud settings

### Error loading schedule
**Fix:** 
1. Make sure you shared all 3 Google Sheets with your service account email
2. Check that Sheet IDs are correct in secrets

### Data not persisting
**Fix:**
1. Click 🔄 Sync after making changes
2. Click 💾 Save to Cloud / 💾 Save Assignments
3. Check Google Sheets to verify data was saved

---

## 🎉 You're Done!

Your surf park scheduler is now:
✅ Accessible from anywhere
✅ Works on mobile and desktop
✅ Data persists in Google Sheets
✅ Multiple users can access

Share it with your team and start scheduling! 🏄
