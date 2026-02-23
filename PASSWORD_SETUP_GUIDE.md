# 🔐 Password-Protected Schedule Manager Setup Guide

## 📦 What You Got

Two new apps with password protection:

1. **`schedule_manager_admin.py`** - Full admin access (you)
   - Edit schedules
   - Assign coaches
   - Save to Google Sheets
   - Password: Set in secrets

2. **`coach_view.py`** - View only (coaches)
   - See their schedule
   - See their assignments
   - Mobile-friendly
   - No edit buttons
   - Password: Set in secrets

---

## 🚀 Quick Setup (5 minutes)

### Step 1: Add Passwords to Secrets

Edit your `.streamlit/secrets.toml` file and add these lines at the top:

```toml
# Passwords
admin_password = "surfadmin2026"
coach_password = "wave2026"

# (Keep all your existing Google Sheets config below)
```

**Change these passwords to whatever you want!**

---

### Step 2: Copy Files to Your Folder

Download these 2 files and put them in:
```
C:\Users\17574\Downloads\surfparkfromclaudev1\
```

Files to download:
- `schedule_manager_admin.py`
- `coach_view.py`

---

### Step 3: Run the Apps

**For You (Admin):**
```bash
python -m streamlit run schedule_manager_admin.py
```
- Enter password: `surfadmin2026` (or whatever you set)
- Full access to edit everything

**For Coaches (View Only):**
```bash
python -m streamlit run coach_view.py
```
- Enter password: `wave2026` (or whatever you set)
- Select their name
- See their schedule and assignments

---

## 📱 How Coaches Use It

### Option A: On-Site (Same WiFi)
1. You run `coach_view.py` on your laptop
2. Look for the **Network URL**: `http://192.168.1.XXX:8501`
3. Share that URL with coaches
4. They open it on their phones
5. Enter coach password
6. Select their name
7. See their schedule!

### Option B: Share Your Computer
1. Run `coach_view.py` on your work computer
2. Coaches come to your desk
3. They enter password
4. Select their name
5. View schedule

---

## 🎨 Coach View Features

**What coaches see:**
- 👤 Select their name from dropdown
- 📅 Pick a date (shows next 7 days)
- ⏰ Their scheduled hours for that day
- 📋 All their assignments with times
- 🏄 Session details (LEFT/RIGHT, role)
- 📅 Whole week view in expandable section

**What coaches CAN'T do:**
- ❌ Edit assignments
- ❌ Change schedules
- ❌ See other coaches' info (unless they select that name)
- ❌ Save anything

**Mobile optimized:**
- Large buttons
- Easy to read cards
- Scrolls nicely on phones

---

## 🔒 Security Features

### Admin App:
- ✅ Password required to access
- ✅ Logout button (clears password)
- ✅ Full edit capabilities
- ✅ Syncs with Google Sheets

### Coach View:
- ✅ Password required to access
- ✅ Logout button
- ✅ Read-only access
- ✅ Can't modify anything
- ✅ No save buttons

---

## 💡 Daily Workflow

### Your Morning Routine (Admin):
1. Run: `python -m streamlit run schedule_manager_admin.py`
2. Enter admin password
3. Click "🔄 Sync" to load latest
4. Upload today's sessions CSV
5. Go to Daily tab
6. Make assignments
7. Click "💾 Save Assignments"
8. Keep app running

### Coach Access (Throughout the Day):
1. Run: `python -m streamlit run coach_view.py`
2. Share Network URL with team on WiFi
3. Coaches enter coach password
4. Select their name
5. View their schedule
6. They can refresh anytime to see updates

---

## 🔄 Updating Passwords

To change passwords, edit `.streamlit/secrets.toml`:

```toml
admin_password = "NEW_ADMIN_PASSWORD_HERE"
coach_password = "NEW_COACH_PASSWORD_HERE"
```

Restart the apps for changes to take effect.

---

## 📊 What Gets Synced

Both apps read from the same Google Sheets:
- ✅ Weekly schedules
- ✅ Coach assignments
- ✅ Coach roster

**Only admin app can WRITE** to Google Sheets.
**Coach view only READS** from Google Sheets.

---

## 🆘 Troubleshooting

### "Incorrect password"
- Check your `.streamlit/secrets.toml` file
- Make sure passwords match what you set
- No extra spaces or quotes

### "No coaches found"
- Click "🔄 Refresh" button
- Check that Google Sheets are shared
- Make sure roster sheet has coach names

### Coaches can't access on WiFi
- Make sure they're on same WiFi network
- Give them the **Network URL** (not localhost)
- Check your firewall isn't blocking port 8501

### Rate limit errors
- Wait 2-3 minutes
- Don't click Refresh/Sync repeatedly
- Sync once in morning, work from memory

---

## 🎯 Pro Tips

**For you:**
- Keep admin app running all day
- Only sync once in morning
- Save assignments periodically (not after every change)

**For coaches:**
- Bookmark the Network URL on phones
- Can check schedule anytime
- Updates when you save from admin

**Passwords:**
- Admin: Use strong password, keep private
- Coach: Simple password, share with whole team
- Change periodically for security

---

## 🚀 Next Steps

1. **Test locally first:**
   - Run both apps on your computer
   - Try logging in with each password
   - Make sure data syncs correctly

2. **Share with 1 coach:**
   - Have them test the coach view
   - Get feedback
   - Fix any issues

3. **Roll out to team:**
   - Share coach password with everyone
   - Show them how to use it
   - Collect feedback

4. **Optional: Deploy to cloud:**
   - Later you can deploy both to Streamlit Cloud
   - Give different URLs to admins vs coaches
   - Always accessible from anywhere

---

## 📞 Quick Reference

**Run Admin App:**
```bash
python -m streamlit run schedule_manager_admin.py
```

**Run Coach View:**
```bash
python -m streamlit run coach_view.py
```

**Both apps can run at the same time!** Just use different browser tabs or windows.

---

**Questions? Issues? Let me know!** 🏄
