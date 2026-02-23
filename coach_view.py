"""
Surf Park Coach View - VIEW ONLY
Password protected - Coaches can view their schedules
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from collections import defaultdict
import os

st.set_page_config(page_title="Coach Schedule", page_icon="🏄", layout="wide")

# Password protection
def check_password():
    """Returns True if user has entered correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets.get("coach_password", "coach123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Coach Password", type="password", on_change=password_entered, key="password")
        st.caption("Enter coach password to view your schedule")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Coach Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Incorrect password")
        return False
    else:
        return True

if not check_password():
    st.stop()

st.markdown('''
<style>
@media (max-width: 768px) {
    .main-header { font-size: 1.8rem !important; }
    .stButton>button { width: 100%; padding: 0.75rem; font-size: 1rem; }
    .session-card { font-size: 0.9rem; }
}
.main-header { 
    font-size: 2.5rem; 
    font-weight: bold; 
    color: #1f77b4; 
    text-align: center; 
    margin-bottom: 1rem; 
}
.coach-name {
    font-size: 2rem;
    font-weight: bold;
    color: #2c3e50;
    text-align: center;
    margin: 1rem 0;
}
.session-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1.5rem;
    border-radius: 1rem;
    margin: 1rem 0;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.session-time {
    font-size: 1.5rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
}
.session-details {
    font-size: 1.1rem;
    opacity: 0.95;
}
.day-off {
    background: #95a5a6;
    color: white;
    padding: 2rem;
    border-radius: 1rem;
    text-align: center;
    font-size: 1.5rem;
}
.no-assignments {
    background: #3498db;
    color: white;
    padding: 2rem;
    border-radius: 1rem;
    text-align: center;
    font-size: 1.2rem;
}
</style>
''', unsafe_allow_html=True)

def get_google_sheets_client():
    try:
        if 'gcp_service_account' in os.environ:
            import json
            creds_dict = json.loads(os.environ['gcp_service_account'])
        elif hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets['gcp_service_account'])
        else:
            st.error("No credentials found")
            return None
        
        from google.oauth2.service_account import Credentials
        import gspread
        
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def load_weekly_schedule_from_sheets(gc, sheet_id):
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        data = sheet.get_all_values()
        if len(data) < 2:
            return {}
        dates = []
        for col in data[0][1:]:
            try:
                dates.append(datetime.strptime(col, '%Y-%m-%d').date())
            except:
                continue
        schedule = {}
        for row in data[1:]:
            if not row or not row[0]:
                continue
            coach = row[0]
            schedule[coach] = {}
            for i, date_val in enumerate(dates):
                try:
                    val = row[i + 1] if i + 1 < len(row) else 'available'
                    schedule[coach][date_val] = val if val else 'available'
                except:
                    schedule[coach][date_val] = 'available'
        return schedule
    except Exception as e:
        st.error(f"Error loading schedule: {e}")
        return {}

def load_coach_assignments_from_sheets(gc, sheet_id):
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        data = sheet.get_all_values()
        if len(data) < 2:
            return {}
        assignments = {}
        for row in data[1:]:
            if len(row) >= 4:
                try:
                    dt = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                    assignments[(dt, row[1], row[2])] = row[3]
                except:
                    continue
        return assignments
    except Exception as e:
        st.error(f"Error loading assignments: {e}")
        return {}

def load_coach_roster_from_sheets(gc, sheet_id):
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        data = sheet.get_all_values()
        return [row[0] for row in data[1:] if row and row[0]]
    except:
        return []

# Initialize
gc = get_google_sheets_client()

if 'weekly_schedule' not in st.session_state:
    st.session_state.weekly_schedule = {}
if 'coach_assignments' not in st.session_state:
    st.session_state.coach_assignments = {}
if 'coach_roster' not in st.session_state:
    st.session_state.coach_roster = []
if 'last_sync' not in st.session_state:
    st.session_state.last_sync = None

try:
    if 'weekly_schedule_sheet_id' in os.environ:
        WEEKLY_SHEET_ID = os.environ['weekly_schedule_sheet_id']
        ASSIGNMENTS_SHEET_ID = os.environ['assignments_sheet_id']
        ROSTER_SHEET_ID = os.environ['roster_sheet_id']
    else:
        WEEKLY_SHEET_ID = st.secrets.get('weekly_schedule_sheet_id', '')
        ASSIGNMENTS_SHEET_ID = st.secrets.get('assignments_sheet_id', '')
        ROSTER_SHEET_ID = st.secrets.get('roster_sheet_id', '')
except:
    WEEKLY_SHEET_ID = ASSIGNMENTS_SHEET_ID = ROSTER_SHEET_ID = ''

st.markdown('<div class="main-header">🏄 My Schedule</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    if st.session_state.last_sync:
        st.caption(f"📡 Last updated: {st.session_state.last_sync.strftime('%I:%M %p')}")
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        if gc and WEEKLY_SHEET_ID:
            with st.spinner("Loading..."):
                try:
                    st.session_state.weekly_schedule = load_weekly_schedule_from_sheets(gc, WEEKLY_SHEET_ID)
                    st.session_state.coach_assignments = load_coach_assignments_from_sheets(gc, ASSIGNMENTS_SHEET_ID)
                    st.session_state.coach_roster = load_coach_roster_from_sheets(gc, ROSTER_SHEET_ID)
                    st.session_state.last_sync = datetime.now()
                    st.success("✅ Updated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Update failed: {e}")
with col3:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

# Coach selection
if not st.session_state.coach_roster:
    st.warning("⚠️ No coaches found. Click 'Refresh' to load data.")
    st.stop()

selected_coach = st.selectbox(
    "👤 Select Your Name",
    st.session_state.coach_roster,
    key='coach_select'
)

if selected_coach:
    st.markdown(f'<div class="coach-name">👋 Hi, {selected_coach}!</div>', unsafe_allow_html=True)
    
    # Date selection
    today = date.today()
    dates_range = [today + timedelta(days=i) for i in range(7)]
    
    selected_date = st.selectbox(
        "📅 Select Date",
        dates_range,
        format_func=lambda d: d.strftime('%A, %B %d, %Y') + (' (Today)' if d == today else ''),
        key='date_select'
    )
    
    # Check if working today
    schedule = st.session_state.weekly_schedule.get(selected_coach, {})
    day_status = schedule.get(selected_date, 'available')
    
    if day_status == 'off':
        st.markdown('<div class="day-off">🌴 Day Off - Enjoy!</div>', unsafe_allow_html=True)
    else:
        # Show schedule hours
        if day_status != 'available':
            st.info(f"⏰ Scheduled Hours: {day_status}")
        else:
            st.info(f"⏰ Available to work")
        
        # Get assignments for this coach on this date
        my_assignments = []
        for (dt, side, role), coach in st.session_state.coach_assignments.items():
            if coach == selected_coach and dt.date() == selected_date:
                my_assignments.append({
                    'time': dt,
                    'side': side,
                    'role': role
                })
        
        if my_assignments:
            st.subheader(f"📋 Your Assignments ({len(my_assignments)})")
            
            # Group by time
            by_time = defaultdict(list)
            for assignment in my_assignments:
                by_time[assignment['time']].append(assignment)
            
            for time in sorted(by_time.keys()):
                assignments = by_time[time]
                time_str = time.strftime('%I:%M %p')
                
                roles_str = ', '.join([f"{a['side']} - {a['role']}" for a in assignments])
                
                st.markdown(f'''
                <div class="session-card">
                    <div class="session-time">⏰ {time_str}</div>
                    <div class="session-details">📍 {roles_str}</div>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-assignments">📭 No assignments yet for this day</div>', unsafe_allow_html=True)
    
    st.markdown('---')
    
    # Week view
    with st.expander("📅 View My Whole Week", expanded=False):
        week_data = []
        for d in dates_range:
            status = schedule.get(d, 'available')
            
            # Count assignments for this day
            day_assignments = sum(1 for (dt, side, role), coach in st.session_state.coach_assignments.items() 
                                if coach == selected_coach and dt.date() == d)
            
            week_data.append({
                'Date': d.strftime('%a %m/%d'),
                'Status': status,
                'Assignments': day_assignments if day_assignments > 0 else '-'
            })
        
        st.table(pd.DataFrame(week_data))

st.markdown('---')
st.caption('🏄 Coach View | View Only | v2.0')
