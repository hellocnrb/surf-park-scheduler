"""
Surf Park Schedule Manager - ADMIN VERSION
Password protected - Full editing capabilities
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from collections import defaultdict
import yaml
import io
import os

from coaching_rules_engine import CoachingRulesEngine

st.set_page_config(page_title="Admin Schedule", page_icon="🏄", layout="wide", initial_sidebar_state="collapsed")

# Password protection
def check_password():
    """Returns True if user has entered correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets.get("admin_password", "admin123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Admin Password", type="password", on_change=password_entered, key="password")
        st.caption("Enter admin password to access schedule manager")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Admin Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Incorrect password")
        return False
    else:
        return True

if not check_password():
    st.stop()

st.markdown('''
<style>
@media (max-width: 768px) {
    .main-header { font-size: 1.5rem !important; }
    .stButton>button { width: 100%; padding: 0.75rem; }
}
.main-header { font-size: 2rem; font-weight: bold; color: #1f77b4; text-align: center; margin-bottom: 1rem; }
.left-side { background-color: #8B4513; color: white; padding: 1rem; border-radius: 0.5rem; margin-bottom: 0.5rem; }
.right-side { background-color: #2F4F4F; color: white; padding: 1rem; border-radius: 0.5rem; margin-bottom: 0.5rem; }
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
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error initializing Google Sheets: {e}")
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

def save_weekly_schedule_to_sheets(gc, sheet_id, schedule, week_start):
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        dates = [week_start + timedelta(days=i) for i in range(7)]
        header = ['Coach'] + [d.strftime('%Y-%m-%d') for d in dates]
        rows = [header]
        for coach in sorted(schedule.keys()):
            row = [coach]
            for d in dates:
                row.append(schedule[coach].get(d, 'available'))
            rows.append(row)
        sheet.clear()
        sheet.update('A1', rows)
        return True
    except Exception as e:
        st.error(f"Error saving: {e}")
        return False

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

def save_coach_assignments_to_sheets(gc, sheet_id, assignments):
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        rows = [['DateTime', 'Side', 'Role', 'Coach']]
        for (dt, side, role), coach in assignments.items():
            rows.append([dt.strftime('%Y-%m-%d %H:%M:%S'), side, role, coach])
        sheet.clear()
        sheet.update('A1', rows)
        return True
    except Exception as e:
        st.error(f"Error saving assignments: {e}")
        return False

def load_coach_roster_from_sheets(gc, sheet_id):
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        data = sheet.get_all_values()
        return [row[0] for row in data[1:] if row and row[0]]
    except:
        return ['Conner', 'Jake B', 'Kai', 'Brady', 'Jack', 'Laird']

def save_coach_roster_to_sheets(gc, sheet_id, roster):
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        rows = [['Coach Name']] + [[coach] for coach in roster]
        sheet.clear()
        sheet.update('A1', rows)
        return True
    except Exception as e:
        st.error(f"Error saving roster: {e}")
        return False

def load_engine():
    with open('coaching_rules.yaml') as f:
        return CoachingRulesEngine(yaml.safe_load(f))

def process_csv(f):
    df = pd.read_csv(f)
    return [{'datetime_start': pd.to_datetime(r['datetime_start']), 'side': r['side'], 
             'session_type': r['session_type'], 'booked_guests': int(r['booked_guests']),
             'private_lessons_count': int(r.get('private_lessons_count', 0))} for _, r in df.iterrows()]

# Initialize
gc = get_google_sheets_client()

if 'processed_sessions' not in st.session_state:
    st.session_state.processed_sessions = None
if 'weekly_schedule' not in st.session_state:
    st.session_state.weekly_schedule = {}
if 'coach_assignments' not in st.session_state:
    st.session_state.coach_assignments = {}
if 'coach_roster' not in st.session_state:
    st.session_state.coach_roster = ['Conner', 'Jake B', 'Kai', 'Brady', 'Jack', 'Laird']
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

st.markdown('<div class="main-header">🏄 Schedule Manager (ADMIN)</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    if st.session_state.last_sync:
        st.caption(f"📡 Last synced: {st.session_state.last_sync.strftime('%I:%M %p')}")
    else:
        st.caption("📡 Not synced yet")
with col2:
    if st.button("🔄 Sync", use_container_width=True):
        if gc and WEEKLY_SHEET_ID:
            with st.spinner("Syncing..."):
                try:
                    st.session_state.weekly_schedule = load_weekly_schedule_from_sheets(gc, WEEKLY_SHEET_ID)
                    st.session_state.coach_assignments = load_coach_assignments_from_sheets(gc, ASSIGNMENTS_SHEET_ID)
                    st.session_state.coach_roster = load_coach_roster_from_sheets(gc, ROSTER_SHEET_ID)
                    st.session_state.last_sync = datetime.now()
                    st.success("✅ Synced!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Sync failed: {e}")
        else:
            st.error("Google Sheets not configured")
with col3:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

with st.sidebar:
    st.header('📁 Upload')
    up = st.file_uploader('Sessions CSV', type=['csv'])
    if up:
        eng = load_engine()
        proc, _ = eng.process_csv_data(process_csv(up))
        if proc:
            st.session_state.processed_sessions = proc
            st.success(f'✅ {len(proc)} sessions')
    
    if st.button('📊 Load Sample'):
        try:
            eng = load_engine()
            proc, _ = eng.process_csv_data(process_csv(open('sample_sessions.csv', 'rb')))
            st.session_state.processed_sessions = proc
            st.success('✅ Loaded')
        except:
            st.error('Sample not found')

tab1, tab2 = st.tabs(['📅 Weekly', '📋 Daily'])

with tab1:
    st.header('📅 Weekly Schedule')
    with st.expander("👥 Manage Coaches"):
        new = st.text_input('Add Coach')
        if st.button('➕ Add') and new:
            if new not in st.session_state.coach_roster:
                st.session_state.coach_roster.append(new)
                if gc and ROSTER_SHEET_ID:
                    save_coach_roster_to_sheets(gc, ROSTER_SHEET_ID, st.session_state.coach_roster)
                st.success(f'Added {new}')
                st.rerun()
        if st.session_state.coach_roster:
            st.info(f'📋 {", ".join(st.session_state.coach_roster)}')
    
    ws = st.date_input('Week Starting', value=date.today())
    dates = [ws + timedelta(days=i) for i in range(7)]
    st.caption('💡 Enter time ranges (e.g., "9-5"), "off", or "available"')
    
    data = []
    for coach in st.session_state.coach_roster:
        row = {'Coach': coach}
        for d in dates:
            row[d.strftime('%a %m/%d')] = st.session_state.weekly_schedule.get(coach, {}).get(d, 'available')
        data.append(row)
    
    df = pd.DataFrame(data)
    edited = st.data_editor(df, use_container_width=True, num_rows='fixed', hide_index=True)
    
    if st.button('💾 Save to Cloud', type='primary'):
        for _, row in edited.iterrows():
            coach = row['Coach']
            if coach not in st.session_state.weekly_schedule:
                st.session_state.weekly_schedule[coach] = {}
            for d in dates:
                st.session_state.weekly_schedule[coach][d] = row[d.strftime('%a %m/%d')]
        if gc and WEEKLY_SHEET_ID:
            if save_weekly_schedule_to_sheets(gc, WEEKLY_SHEET_ID, st.session_state.weekly_schedule, ws):
                st.success('✅ Saved!')
                st.session_state.last_sync = datetime.now()

with tab2:
    st.header('📋 Daily')
    if not st.session_state.processed_sessions:
        st.info('👈 Upload sessions CSV or load sample')
    else:
        sess = st.session_state.processed_sessions
        dates_avail = sorted(set(s.datetime_start.date() for s in sess))
        sel_date = st.selectbox('Date', dates_avail, format_func=lambda d: d.strftime('%A, %B %d'))
        
        with st.expander("👥 Staff Today", expanded=True):
            staff = []
            for coach, schedule in st.session_state.weekly_schedule.items():
                if sel_date in schedule and schedule[sel_date] != 'off':
                    staff.append({'Staff': coach, 'Hours': schedule[sel_date]})
            if staff:
                st.table(pd.DataFrame(staff))
        
        day_sess = [s for s in sess if s.datetime_start.date() == sel_date]
        by_hour = defaultdict(list)
        for s in day_sess:
            by_hour[s.datetime_start.hour].append(s)
        
        for hour in sorted(by_hour.keys()):
            main = by_hour[hour][0]
            st.markdown(f"### {main.datetime_start.strftime('%I:%M%p').lower()} - {main.session_type}")
            
            for s in by_hour[hour]:
                with st.container():
                    st.markdown(f'''<div class='{"left-side" if s.side == "LEFT" else "right-side"}'>
                        <strong>{s.side}</strong> - {s.booked_guests} guests
                    </div>''', unsafe_allow_html=True)
                    
                    roles = []
                    if s.session_type in ['Beginner', 'Novice'] and s.baseline_coaches >= 2:
                        roles = ['Pusher', 'Tutor']
                        if s.baseline_coaches >= 3:
                            roles.append('Flowter')
                    elif s.session_type == 'Progressive' and s.baseline_coaches >= 1:
                        roles = ['Coach']
                        if s.baseline_coaches >= 2:
                            roles.append('Flowter')
                    for i in range(s.private_lessons_count):
                        roles.append(f'Private {i+1}')
                    
                    if roles:
                        for role in roles:
                            key = (s.datetime_start, s.side, role)
                            assigned = st.session_state.coach_assignments.get(key, '')
                            opts = ['-- Unassigned --'] + st.session_state.coach_roster
                            idx = opts.index(assigned) if assigned in st.session_state.coach_roster else 0
                            new = st.selectbox(role, opts, index=idx, key=f'{hour}_{s.side}_{role}')
                            if new != '-- Unassigned --':
                                st.session_state.coach_assignments[key] = new
                            elif key in st.session_state.coach_assignments:
                                del st.session_state.coach_assignments[key]
                    else:
                        st.caption('*No coaches needed*')
            st.markdown('---')
        
        if st.button('💾 Save Assignments', type='primary'):
            if gc and ASSIGNMENTS_SHEET_ID:
                if save_coach_assignments_to_sheets(gc, ASSIGNMENTS_SHEET_ID, st.session_state.coach_assignments):
                    st.success('✅ Saved!')
                    st.session_state.last_sync = datetime.now()

st.markdown('---')
st.caption('🏄 Admin Schedule Manager | v2.0 | Password Protected')
