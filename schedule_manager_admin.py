"""
Surf Park Daily Schedule Builder
For Head Coaches - Multi-day scheduling with role assignment
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
from collections import defaultdict
import yaml
import io
import os

st.set_page_config(page_title="Schedule Builder", page_icon="🏄", layout="wide")

# Password protection
def check_password():
    """Returns True if user has entered correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets.get("head_coach_password", "coach2026"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Head Coach Password", type="password", on_change=password_entered, key="password")
        st.caption("Enter password to access schedule builder")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Head Coach Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Incorrect password")
        return False
    else:
        return True

if not check_password():
    st.stop()

st.markdown('''
<style>
.main-header { font-size: 2rem; font-weight: bold; color: #1f77b4; text-align: center; margin: 1rem 0; }
.date-badge { background: #1f77b4; color: white; padding: 0.5rem 1rem; border-radius: 0.5rem; display: inline-block; margin: 0.5rem 0; font-weight: bold; font-size: 1.2rem; }
.session-card { background: #f0f2f6; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0; border-left: 4px solid #1f77b4; }
.left-side { background-color: #8B4513; color: white; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0; }
.right-side { background-color: #2F4F4F; color: white; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0; }
</style>
''', unsafe_allow_html=True)

# Load coaching rules
def load_coaching_rules():
    try:
        with open('coaching_rules.yaml') as f:
            return yaml.safe_load(f)
    except:
        return {
            'session_types': {
                'Beginner': {'baseline_rules': [
                    {'guest_range': [0, 0], 'baseline_coaches': 0},
                    {'guest_range': [1, 14], 'baseline_coaches': 2},
                    {'guest_range': [15, 999], 'baseline_coaches': 3}
                ]},
                'Novice': {'baseline_rules': [
                    {'guest_range': [0, 0], 'baseline_coaches': 0},
                    {'guest_range': [1, 14], 'baseline_coaches': 2},
                    {'guest_range': [15, 999], 'baseline_coaches': 3}
                ]},
                'Progressive': {'baseline_rules': [
                    {'guest_range': [0, 0], 'baseline_coaches': 0},
                    {'guest_range': [1, 9], 'baseline_coaches': 1},
                    {'guest_range': [10, 999], 'baseline_coaches': 2}
                ]},
                'Intermediate': {'baseline_rules': [{'guest_range': [0, 999], 'baseline_coaches': 0}]},
                'Advanced': {'baseline_rules': [{'guest_range': [0, 999], 'baseline_coaches': 0}]},
                'Expert': {'baseline_rules': [{'guest_range': [0, 999], 'baseline_coaches': 0}]},
                'Pro': {'baseline_rules': [{'guest_range': [0, 999], 'baseline_coaches': 0}]},
                'Pro_Barrel': {'baseline_rules': [{'guest_range': [0, 999], 'baseline_coaches': 0}]}
            }
        }

def calculate_baseline_coaches(session_type, guest_count, rules):
    """Calculate how many baseline coaches are needed"""
    if session_type not in rules['session_types']:
        return 0
    
    for rule in rules['session_types'][session_type]['baseline_rules']:
        min_guests, max_guests = rule['guest_range']
        if min_guests <= guest_count <= max_guests:
            return rule['baseline_coaches']
    return 0

def get_required_roles(session_type, baseline_coaches, private_lessons):
    """Determine which roles are needed for a session"""
    roles = []
    
    if session_type in ['Beginner', 'Novice']:
        if baseline_coaches >= 2:
            roles = ['Pusher', 'Tutor']
        if baseline_coaches >= 3:
            roles.append('Flowter')
    elif session_type == 'Progressive':
        if baseline_coaches >= 1:
            roles = ['Coach']
        if baseline_coaches >= 2:
            roles.append('Flowter')
    
    for i in range(private_lessons):
        roles.append(f'Private {i+1}')
    
    return roles

def load_from_google_sheets(gc, sheet_id):
    """Load all schedules, rosters, and rental info from Google Sheets"""
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        data = sheet.get_all_values()
        
        if len(data) < 2:
            return {}, {}, [], [], {}, {}
        
        sessions_by_date = defaultdict(list)
        assignments = {}
        seen_sessions = set()
        coach_roster = []
        rental_roster = []
        rental_assignments = {}
        opening_closing_times = {}
        
        for row in data[1:]:  # Skip header
            # Check for coach roster row
            if len(row) >= 9 and row[0] == 'COACH_ROSTER' and row[8]:
                coach_roster = [c.strip() for c in row[8].split(',') if c.strip()]
                continue
            
            # Check for rental roster row
            if len(row) >= 10 and row[0] == 'RENTAL_ROSTER' and row[9]:
                rental_roster = [c.strip() for c in row[9].split(',') if c.strip()]
                continue
            
            # Check for opening/closing rental assignments
            if len(row) >= 12 and row[0] in ['OPENING', 'CLOSING']:
                try:
                    date_obj = datetime.strptime(row[7], "%Y-%m-%d").date()
                    rental_assignments[(date_obj, row[0])] = row[10]
                    if date_obj not in opening_closing_times:
                        opening_closing_times[date_obj] = {}
                    # Load the actual time from column 11 (OpenCloseTime)
                    if row[11]:
                        time_obj = datetime.strptime(row[11], "%I:%M %p").time()
                        if row[0] == 'OPENING':
                            opening_closing_times[date_obj]['opening'] = time_obj
                        else:  # CLOSING
                            opening_closing_times[date_obj]['closing'] = time_obj
                    continue
                except:
                    continue
            
            # Check for session rental assignments
            if len(row) >= 11 and row[1] == 'RENTAL' and row[10]:
                try:
                    time_str = row[0]
                    date_str = row[7]
                    session_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %I:%M %p")
                    rental_assignments[(session_datetime, 'SESSION')] = row[10]
                    continue
                except:
                    continue
            
            if len(row) >= 7:
                try:
                    time_str = row[0]
                    session_datetime = datetime.strptime(f"{row[7]} {time_str}", "%Y-%m-%d %I:%M %p")
                    session_date = session_datetime.date()
                    
                    # Create unique identifier for this session
                    session_key = (session_datetime, row[2], row[1], int(row[3]), int(row[4]))
                    
                    # Only create session if we haven't seen this exact session before
                    if session_key not in seen_sessions:
                        session = {
                            'time': session_datetime,
                            'session_type': row[1],
                            'side': row[2],
                            'guests': int(row[3]),
                            'private_lessons': int(row[4]),
                            'baseline_coaches': 0,
                            'roles': []
                        }
                        
                        # Recalculate roles based on current rules
                        baseline = calculate_baseline_coaches(
                            session['session_type'],
                            session['guests'],
                            load_coaching_rules()
                        )
                        session['baseline_coaches'] = baseline
                        session['roles'] = get_required_roles(
                            session['session_type'],
                            baseline,
                            session['private_lessons']
                        )
                        
                        sessions_by_date[session_date].append(session)
                        seen_sessions.add(session_key)
                    
                    # Load assignment (this happens for each role row)
                    if row[5] != 'N/A' and row[6] != 'No coaches needed' and row[6] != 'Unassigned':
                        key = (session_datetime, row[2], row[5])
                        assignments[key] = row[6]
                
                except Exception as e:
                    continue
        
        # If no rosters loaded, use defaults
        if not coach_roster:
            coach_roster = ['Conner', 'Jake B', 'Kai', 'Brady', 'Jack', 'Laird']
        if not rental_roster:
            rental_roster = ['Ella', 'Sarah', 'Mike', 'Alex']
        
        return dict(sessions_by_date), assignments, coach_roster, rental_roster, rental_assignments, opening_closing_times
    
    except Exception as e:
        st.error(f"Error loading: {e}")
        return {}, {}, [], [], {}, {}

def save_to_google_sheets(gc, sheet_id, all_sessions, assignments, coach_roster, rental_roster, rental_assignments, opening_closing_times):
    """Save all schedules, rosters, and rental info to Google Sheets"""
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        
        rows = [['Time', 'Session Type', 'Side', 'Guests', 'Private', 'Role', 'Coach', 'Date', 'CoachRoster', 'RentalRoster', 'RentalPerson', 'OpenCloseTime']]
        
        # Row 2: Save coach roster
        if coach_roster:
            rows.append(['COACH_ROSTER', '', '', '', '', '', '', '', ','.join(coach_roster), '', '', ''])
        
        # Row 3: Save rental roster
        if rental_roster:
            rows.append(['RENTAL_ROSTER', '', '', '', '', '', '', '', '', ','.join(rental_roster), '', ''])
        
        # Save rental assignments (Opening/Closing and sessions)
        for (key, rental_type), person in rental_assignments.items():
            if rental_type == 'OPENING':
                date_key = key
                time_obj = opening_closing_times.get(date_key, {}).get('opening', time(8, 0))
                time_str = time_obj.strftime('%I:%M %p')
                rows.append(['OPENING', '', '', '', '', '', '', date_key.strftime('%Y-%m-%d'), '', '', person, time_str])
            elif rental_type == 'CLOSING':
                date_key = key
                time_obj = opening_closing_times.get(date_key, {}).get('closing', time(18, 0))
                time_str = time_obj.strftime('%I:%M %p')
                rows.append(['CLOSING', '', '', '', '', '', '', date_key.strftime('%Y-%m-%d'), '', '', person, time_str])
            elif rental_type == 'SESSION':
                time_dt = key
                rows.append([time_dt.strftime('%I:%M %p'), 'RENTAL', '', '', '', '', '', time_dt.date().strftime('%Y-%m-%d'), '', '', person, ''])
        
        # Flatten all sessions across all dates
        for session_date, sessions in sorted(all_sessions.items()):
            for session in sessions:
                roles = session.get('roles', [])
                if roles:
                    for role in roles:
                        key = (session['time'], session['side'], role)
                        coach = assignments.get(key, 'Unassigned')
                        rows.append([
                            session['time'].strftime('%I:%M %p'),
                            session['session_type'],
                            session['side'],
                            session['guests'],
                            session['private_lessons'],
                            role,
                            coach,
                            session_date.strftime('%Y-%m-%d'),
                            '', '', '', ''
                        ])
                else:
                    rows.append([
                        session['time'].strftime('%I:%M %p'),
                        session['session_type'],
                        session['side'],
                        session['guests'],
                        session['private_lessons'],
                        'N/A',
                        'No coaches needed',
                        session_date.strftime('%Y-%m-%d'),
                        '', '', '', ''
                    ])
        
        sheet.clear()
        sheet.update('A1', rows)
        return True
    except Exception as e:
        st.error(f"Error saving: {e}")
        return False

def get_google_sheets_client():
    try:
        if 'gcp_service_account' in os.environ:
            import json
            creds_dict = json.loads(os.environ['gcp_service_account'])
        elif hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets['gcp_service_account'])
        else:
            return None
        
        from google.oauth2.service_account import Credentials
        import gspread
        
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        return gspread.authorize(creds)
    except:
        return None

# Initialize session state
if 'sessions_by_date' not in st.session_state:
    st.session_state.sessions_by_date = {}  # Dict of {date: [sessions]}
if 'assignments' not in st.session_state:
    st.session_state.assignments = {}
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = date.today()
if 'coach_roster' not in st.session_state:
    st.session_state.coach_roster = ['Conner', 'Jake B', 'Kai', 'Brady', 'Jack', 'Laird']
if 'rental_roster' not in st.session_state:
    st.session_state.rental_roster = ['Ella', 'Sarah', 'Mike', 'Alex']
if 'last_sync' not in st.session_state:
    st.session_state.last_sync = None
if 'force_date_change' not in st.session_state:
    st.session_state.force_date_change = None
if 'rental_assignments' not in st.session_state:
    st.session_state.rental_assignments = {}  # {(datetime, 'Opening'|'Closing'|session_key): person}
if 'opening_closing_times' not in st.session_state:
    st.session_state.opening_closing_times = {}  # {date: {'opening': time, 'closing': time}}

rules = load_coaching_rules()
gc = get_google_sheets_client()

try:
    SCHEDULE_SHEET_ID = st.secrets.get('daily_schedule_sheet_id', '')
except:
    SCHEDULE_SHEET_ID = ''

# Header
st.markdown('<div class="main-header">🏄 Multi-Day Schedule Builder</div>', unsafe_allow_html=True)

# Top controls - ALWAYS VISIBLE
col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

with col1:
    # Date picker that persists across tabs - mainly for manual date selection
    st.date_input(
        "📅 Pick Any Date",
        value=st.session_state.selected_date,
        key='main_date_picker',
        help="Select any date (or use Previous/Next buttons below)"
    )
    # Sync the widget value to selected_date when user manually changes it
    if 'main_date_picker' in st.session_state:
        if st.session_state.main_date_picker != st.session_state.selected_date:
            st.session_state.selected_date = st.session_state.main_date_picker
            st.rerun()

with col2:
    if gc and SCHEDULE_SHEET_ID:
        if st.button("🔄 Load", use_container_width=True, help="Load schedules from Google Sheets"):
            with st.spinner("Loading..."):
                loaded_sessions, loaded_assignments, loaded_coach_roster, loaded_rental_roster, loaded_rental_assignments, loaded_oc_times = load_from_google_sheets(gc, SCHEDULE_SHEET_ID)
                st.session_state.sessions_by_date = loaded_sessions
                st.session_state.assignments = loaded_assignments
                st.session_state.coach_roster = loaded_coach_roster
                st.session_state.rental_roster = loaded_rental_roster
                st.session_state.rental_assignments = loaded_rental_assignments
                st.session_state.opening_closing_times = loaded_oc_times
                st.session_state.last_sync = datetime.now()
                st.success("✅ Loaded!")
                st.rerun()

with col3:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

with col4:
    if st.button("🗑️ Clear Day", use_container_width=True, help="Clear sessions for selected date"):
        if st.session_state.selected_date in st.session_state.sessions_by_date:
            del st.session_state.sessions_by_date[st.session_state.selected_date]
            # Clear assignments for this date
            keys_to_remove = [k for k in st.session_state.assignments.keys() if k[0].date() == st.session_state.selected_date]
            for key in keys_to_remove:
                del st.session_state.assignments[key]
            st.success("Cleared!")
            st.rerun()

# Show current date prominently
st.markdown(f'<div class="date-badge" style="text-align:center;">📅 {st.session_state.selected_date.strftime("%A, %B %d, %Y")}</div>', unsafe_allow_html=True)

# Quick stats for current date
current_sessions = st.session_state.sessions_by_date.get(st.session_state.selected_date, [])
if current_sessions:
    total_roles = sum(len(s.get('roles', [])) for s in current_sessions)
    assigned_roles = sum(1 for (dt, side, role) in st.session_state.assignments.keys() if dt.date() == st.session_state.selected_date)
    st.caption(f"📊 {len(current_sessions)} sessions | {assigned_roles}/{total_roles} roles assigned")

# Quick date selector - show all scheduled dates as clickable buttons
if st.session_state.sessions_by_date:
    with st.expander("🗓️ Jump to Scheduled Date", expanded=False):
        st.caption("Click a date to jump to it")
        all_dates = sorted(st.session_state.sessions_by_date.keys())
        
        # Show dates in rows of 7 (one week)
        for week_start_idx in range(0, len(all_dates), 7):
            week_dates = all_dates[week_start_idx:week_start_idx + 7]
            cols = st.columns(len(week_dates))
            
            for idx, target_date in enumerate(week_dates):
                with cols[idx]:
                    session_count = len(st.session_state.sessions_by_date[target_date])
                    is_selected = target_date == st.session_state.selected_date
                    
                    # Show date info
                    if is_selected:
                        st.markdown(f'''
                        <div style="background:#1f77b4;color:white;padding:0.5rem;border-radius:0.5rem;text-align:center;margin-bottom:0.25rem;">
                            <strong>{target_date.strftime("%a %m/%d")}</strong><br>
                            {session_count} sessions
                        </div>
                        ''', unsafe_allow_html=True)
                        st.button("📍 Current", key=f"date_{target_date.isoformat()}", use_container_width=True, disabled=True)
                    else:
                        st.markdown(f'''
                        <div style="background:#f0f2f6;color:#333;padding:0.5rem;border-radius:0.5rem;text-align:center;margin-bottom:0.25rem;">
                            <strong>{target_date.strftime("%a %m/%d")}</strong><br>
                            {session_count} sessions
                        </div>
                        ''', unsafe_allow_html=True)
                        if st.button("Jump", key=f"date_{target_date.isoformat()}", use_container_width=True):
                            st.session_state.selected_date = target_date
                            st.rerun()

st.markdown('---')

# Tabs
tab1, tab2, tab3 = st.tabs(['➕ Create Sessions', '👥 Assign Coaches', '📋 View Schedule'])

with tab1:
    st.header(f'Create Sessions for {st.session_state.selected_date.strftime("%A, %b %d")}')
    st.caption('Add sessions to this date')
    
    # Opening/Closing Rental Blocks
    with st.expander("🏪 Opening & Closing (Rental Counter)", expanded=True):
        st.markdown("**Set times for rental counter opening/closing**")
        col_open, col_close = st.columns(2)
        
        # Get stored times for this date or use defaults
        current_times = st.session_state.opening_closing_times.get(st.session_state.selected_date, {})
        
        with col_open:
            st.markdown("**🔓 Opening**")
            default_opening = current_times.get('opening', time(8, 0))
            
            # Convert default to 12-hour format
            default_hour = default_opening.hour
            default_ampm = 'AM'
            if default_hour >= 12:
                default_ampm = 'PM'
                if default_hour > 12:
                    default_hour -= 12
            elif default_hour == 0:
                default_hour = 12
            
            # Custom AM/PM time selector
            open_col1, open_col2, open_col3 = st.columns([2, 2, 1])
            with open_col1:
                open_hour = st.selectbox('Hour', options=list(range(1, 13)), 
                                        index=default_hour-1, 
                                        key=f'open_hour_{st.session_state.selected_date}')
            with open_col2:
                open_minute = st.selectbox('Min', options=['00', '30'], 
                                          index=0 if default_opening.minute == 0 else 1,
                                          key=f'open_min_{st.session_state.selected_date}')
            with open_col3:
                open_ampm = st.selectbox('', options=['AM', 'PM'], 
                                        index=0 if default_ampm == 'AM' else 1,
                                        key=f'open_ampm_{st.session_state.selected_date}')
            
            # Convert to 24-hour time object
            hour_24 = open_hour if open_ampm == 'AM' else (open_hour + 12 if open_hour != 12 else 12)
            if open_ampm == 'AM' and open_hour == 12:
                hour_24 = 0
            opening_time = time(hour_24, int(open_minute))
            
            # Store the time for this specific date
            if st.session_state.selected_date not in st.session_state.opening_closing_times:
                st.session_state.opening_closing_times[st.session_state.selected_date] = {}
            st.session_state.opening_closing_times[st.session_state.selected_date]['opening'] = opening_time
            
            opening_person_key = (st.session_state.selected_date, 'OPENING')
            opening_assigned = st.session_state.rental_assignments.get(opening_person_key, '')
            
            opening_options = ['-- Unassigned --'] + st.session_state.rental_roster
            opening_idx = opening_options.index(opening_assigned) if opening_assigned in st.session_state.rental_roster else 0
            
            new_opening = st.selectbox(
                'Opening Staff',
                opening_options,
                index=opening_idx,
                key=f'opening_staff_{st.session_state.selected_date}'
            )
            
            if new_opening != '-- Unassigned --':
                st.session_state.rental_assignments[opening_person_key] = new_opening
            elif opening_person_key in st.session_state.rental_assignments:
                del st.session_state.rental_assignments[opening_person_key]
        
        with col_close:
            st.markdown("**🔒 Closing**")
            default_closing = current_times.get('closing', time(18, 0))
            
            # Convert default to 12-hour format
            default_hour = default_closing.hour
            default_ampm = 'AM'
            if default_hour >= 12:
                default_ampm = 'PM'
                if default_hour > 12:
                    default_hour -= 12
            elif default_hour == 0:
                default_hour = 12
            
            # Custom AM/PM time selector
            close_col1, close_col2, close_col3 = st.columns([2, 2, 1])
            with close_col1:
                close_hour = st.selectbox('Hour', options=list(range(1, 13)), 
                                         index=default_hour-1, 
                                         key=f'close_hour_{st.session_state.selected_date}')
            with close_col2:
                close_minute = st.selectbox('Min', options=['00', '30'], 
                                           index=0 if default_closing.minute == 0 else 1,
                                           key=f'close_min_{st.session_state.selected_date}')
            with close_col3:
                close_ampm = st.selectbox('', options=['AM', 'PM'], 
                                         index=0 if default_ampm == 'AM' else 1,
                                         key=f'close_ampm_{st.session_state.selected_date}')
            
            # Convert to 24-hour time object
            hour_24 = close_hour if close_ampm == 'AM' else (close_hour + 12 if close_hour != 12 else 12)
            if close_ampm == 'AM' and close_hour == 12:
                hour_24 = 0
            closing_time = time(hour_24, int(close_minute))
            
            # Store the time for this specific date
            st.session_state.opening_closing_times[st.session_state.selected_date]['closing'] = closing_time
            
            closing_person_key = (st.session_state.selected_date, 'CLOSING')
            closing_assigned = st.session_state.rental_assignments.get(closing_person_key, '')
            
            closing_options = ['-- Unassigned --'] + st.session_state.rental_roster
            closing_idx = closing_options.index(closing_assigned) if closing_assigned in st.session_state.rental_roster else 0
            
            new_closing = st.selectbox(
                'Closing Staff',
                closing_options,
                index=closing_idx,
                key=f'closing_staff_{st.session_state.selected_date}'
            )
            
            if new_closing != '-- Unassigned --':
                st.session_state.rental_assignments[closing_person_key] = new_closing
            elif closing_person_key in st.session_state.rental_assignments:
                del st.session_state.rental_assignments[closing_person_key]
        
        # Manage rental staff roster
        with st.expander("👥 Manage Rental Staff Roster"):
            new_rental_staff = st.text_input('Add rental staff name', key='new_rental_staff')
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button('➕ Add Rental Staff') and new_rental_staff:
                    if new_rental_staff not in st.session_state.rental_roster:
                        st.session_state.rental_roster.append(new_rental_staff)
                        st.success(f'Added {new_rental_staff}')
                        st.rerun()
            with col2:
                st.info(f"Rental Staff: {', '.join(st.session_state.rental_roster)}")
    
    st.markdown('---')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader('Session Details')
        
        # Custom AM/PM time selector
        time_col1, time_col2, time_col3 = st.columns([2, 2, 1])
        with time_col1:
            hour = st.selectbox('Hour', options=list(range(1, 13)), index=8, key='session_hour')  # Default 9
        with time_col2:
            minute = st.selectbox('Minute', options=['00', '30'], index=0, key='session_minute')
        with time_col3:
            ampm = st.selectbox('AM/PM', options=['AM', 'PM'], index=0, key='session_ampm')
        
        # Convert to 24-hour time object
        hour_24 = hour if ampm == 'AM' else (hour + 12 if hour != 12 else 12)
        if ampm == 'AM' and hour == 12:
            hour_24 = 0
        session_time = time(hour_24, int(minute))
        
        session_type = st.selectbox('Session Type', list(rules['session_types'].keys()), key='session_type')
    
    with col2:
        st.subheader(' ')
        st.write('')
        add_both = st.checkbox('Add both LEFT and RIGHT', value=True, key='add_both')
    
    st.markdown('---')
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown('<div style="background:#8B4513;color:white;padding:0.5rem;border-radius:0.5rem;text-align:center;font-weight:bold;">LEFT SIDE</div>', unsafe_allow_html=True)
        left_guests = st.number_input('Guests (LEFT)', min_value=0, max_value=30, value=0, key='left_guests')
        left_private = st.number_input('Private Lessons (LEFT)', min_value=0, max_value=5, value=0, key='left_private')
        
        left_baseline = calculate_baseline_coaches(session_type, left_guests, rules)
        left_roles = get_required_roles(session_type, left_baseline, left_private)
        
        if left_roles:
            st.info(f"Roles: {', '.join(left_roles)}")
        else:
            st.info("No coaches needed")
    
    with col_right:
        st.markdown('<div style="background:#2F4F4F;color:white;padding:0.5rem;border-radius:0.5rem;text-align:center;font-weight:bold;">RIGHT SIDE</div>', unsafe_allow_html=True)
        right_guests = st.number_input('Guests (RIGHT)', min_value=0, max_value=30, value=0, key='right_guests')
        right_private = st.number_input('Private Lessons (RIGHT)', min_value=0, max_value=5, value=0, key='right_private')
        
        right_baseline = calculate_baseline_coaches(session_type, right_guests, rules)
        right_roles = get_required_roles(session_type, right_baseline, right_private)
        
        if right_roles:
            st.info(f"Roles: {', '.join(right_roles)}")
        else:
            st.info("No coaches needed")
    
    st.markdown('---')
    
    if st.button('➕ Add Session(s)', type='primary', use_container_width=True):
        session_datetime = datetime.combine(st.session_state.selected_date, session_time)
        
        if st.session_state.selected_date not in st.session_state.sessions_by_date:
            st.session_state.sessions_by_date[st.session_state.selected_date] = []
        
        st.session_state.sessions_by_date[st.session_state.selected_date].append({
            'time': session_datetime,
            'session_type': session_type,
            'side': 'LEFT',
            'guests': left_guests,
            'private_lessons': left_private,
            'baseline_coaches': left_baseline,
            'roles': left_roles
        })
        
        if add_both:
            st.session_state.sessions_by_date[st.session_state.selected_date].append({
                'time': session_datetime,
                'session_type': session_type,
                'side': 'RIGHT',
                'guests': right_guests,
                'private_lessons': right_private,
                'baseline_coaches': right_baseline,
                'roles': right_roles
            })
        
        st.success(f'Added to {st.session_state.selected_date.strftime("%b %d")}!')
        st.rerun()
    
    # Show sessions for selected date
    if current_sessions:
        st.markdown('---')
        st.subheader('Sessions for This Day')
        
        sessions_by_time = defaultdict(list)
        for i, session in enumerate(current_sessions):
            sessions_by_time[session['time']].append((i, session))
        
        for time_key in sorted(sessions_by_time.keys()):
            sessions = sessions_by_time[time_key]
            
            with st.expander(f"🕐 {time_key.strftime('%I:%M %p')} - {sessions[0][1]['session_type']}", expanded=True):
                cols = st.columns(len(sessions) + 1)
                
                for idx, (session_idx, session) in enumerate(sessions):
                    with cols[idx]:
                        st.markdown(f"**{session['side']}**")
                        st.write(f"👥 {session['guests']} guests")
                        st.write(f"🎓 {session['private_lessons']} private")
                        if session['roles']:
                            st.write(f"{', '.join(session['roles'])}")
                
                with cols[-1]:
                    if st.button('🗑️', key=f'del_{time_key}_{st.session_state.selected_date}'):
                        st.session_state.sessions_by_date[st.session_state.selected_date] = [
                            s for s in st.session_state.sessions_by_date[st.session_state.selected_date]
                            if s['time'] != time_key
                        ]
                        st.rerun()

with tab2:
    st.header(f'Assign Coaches for {st.session_state.selected_date.strftime("%A, %b %d")}')
    
    # Weekly Schedule Overview - Show who's working each day
    if st.session_state.sessions_by_date:
        with st.expander("📅 Weekly Schedule Overview", expanded=False):
            # Get all dates that have sessions
            all_dates = sorted(st.session_state.sessions_by_date.keys())
            
            # Build a coach workload summary
            coach_schedule = defaultdict(lambda: defaultdict(list))  # {coach: {date: [times]}}
            
            for date_key in all_dates:
                for session in st.session_state.sessions_by_date[date_key]:
                    # Check coach assignments for this session
                    for role in session.get('roles', []):
                        assignment_key = (session['time'], session['side'], role)
                        if assignment_key in st.session_state.assignments:
                            coach_name = st.session_state.assignments[assignment_key]
                            time_str = session['time'].strftime('%I:%M %p')
                            coach_schedule[coach_name][date_key].append(f"{time_str} {session['side'][:1]} {role[:3]}")
            
            # Display as table
            if coach_schedule:
                for coach in sorted(st.session_state.coach_roster):
                    if coach in coach_schedule:
                        st.markdown(f"**{coach}:**")
                        coach_dates = coach_schedule[coach]
                        date_cols = st.columns(min(len(all_dates), 7))
                        for idx, date_key in enumerate(all_dates[:7]):
                            with date_cols[idx]:
                                assignments = coach_dates.get(date_key, [])
                                if assignments:
                                    st.markdown(f"**{date_key.strftime('%a %m/%d')}**")
                                    for assignment in assignments:
                                        st.caption(assignment)
                                else:
                                    st.markdown(f"~~{date_key.strftime('%a %m/%d')}~~")
                        st.markdown('---')
    
    if not current_sessions:
        st.info(f'👈 No sessions for {st.session_state.selected_date.strftime("%b %d")}. Create some in the "Create Sessions" tab.')
    else:
        with st.expander('👥 Manage Coach Roster'):
            new_coach = st.text_input('Add coach name')
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button('➕ Add') and new_coach:
                    if new_coach not in st.session_state.coach_roster:
                        st.session_state.coach_roster.append(new_coach)
                        st.success(f'Added {new_coach}')
                        st.rerun()
            with col2:
                st.info(f"Roster: {', '.join(st.session_state.coach_roster)}")
        
        st.markdown('---')
        
        sessions_by_time = defaultdict(list)
        for session in current_sessions:
            sessions_by_time[session['time']].append(session)
        
        for time_key in sorted(sessions_by_time.keys()):
            sessions = sessions_by_time[time_key]
            main = sessions[0]
            
            st.markdown(f"### 🕐 {time_key.strftime('%I:%M %p')} - {main['session_type']}")
            
            # Rental assignment for this time slot
            rental_key = (time_key, 'SESSION')
            rental_assigned = st.session_state.rental_assignments.get(rental_key, '')
            rental_options = ['-- Unassigned --'] + st.session_state.rental_roster
            rental_idx = rental_options.index(rental_assigned) if rental_assigned in st.session_state.rental_roster else 0
            
            st.markdown("**🏪 Rentals During This Session:**")
            new_rental = st.selectbox(
                'Rental Counter Staff',
                rental_options,
                index=rental_idx,
                key=f'rental_{st.session_state.selected_date}_{time_key.strftime("%H%M")}',
                help="Who is managing rentals during this session?"
            )
            
            if new_rental != '-- Unassigned --':
                st.session_state.rental_assignments[rental_key] = new_rental
            elif rental_key in st.session_state.rental_assignments:
                del st.session_state.rental_assignments[rental_key]
            
            st.markdown('---')
            
            cols = st.columns(len(sessions))
            for idx, session in enumerate(sessions):
                with cols[idx]:
                    bg_color = '#8B4513' if session['side'] == 'LEFT' else '#2F4F4F'
                    st.markdown(f'''
                    <div style="background:{bg_color};color:white;padding:1rem;border-radius:0.5rem;margin-bottom:0.5rem;">
                        <strong>{session['side']}</strong><br>
                        {session['guests']} guests | {session['private_lessons']} private
                    </div>
                    ''', unsafe_allow_html=True)
                    
                    if session['roles']:
                        for role_idx, role in enumerate(session['roles']):
                            key = (session['time'], session['side'], role)
                            assigned = st.session_state.assignments.get(key, '')
                            
                            options = ['-- Unassigned --'] + st.session_state.coach_roster
                            idx_default = options.index(assigned) if assigned in st.session_state.coach_roster else 0
                            
                            new_assignment = st.selectbox(
                                role,
                                options,
                                index=idx_default,
                                key=f'assign_{st.session_state.selected_date}_{time_key.strftime("%H%M")}_{idx}_{role_idx}'
                            )
                            
                            if new_assignment != '-- Unassigned --':
                                st.session_state.assignments[key] = new_assignment
                            elif key in st.session_state.assignments:
                                del st.session_state.assignments[key]
                    else:
                        st.caption('*No coaches needed*')
            
            st.markdown('---')
        
        if gc and SCHEDULE_SHEET_ID:
            if st.button('💾 Save All to Google Sheets', type='primary'):
                if save_to_google_sheets(
                    gc, 
                    SCHEDULE_SHEET_ID, 
                    st.session_state.sessions_by_date, 
                    st.session_state.assignments, 
                    st.session_state.coach_roster,
                    st.session_state.rental_roster,
                    st.session_state.rental_assignments,
                    st.session_state.opening_closing_times
                ):
                    st.session_state.last_sync = datetime.now()
                    st.success('✅ Saved all dates!')
        else:
            st.warning('⚠️ Google Sheets not configured')

with tab3:
    st.header(f'Schedule for {st.session_state.selected_date.strftime("%A, %B %d, %Y")}')
    
    if not current_sessions:
        st.info('No sessions for this date')
    else:
        # Stats at top
        total_roles = sum(len(s.get('roles', [])) for s in current_sessions)
        assigned_roles = sum(1 for (dt, side, role) in st.session_state.assignments.keys() if dt.date() == st.session_state.selected_date)
        
        col1, col2, col3 = st.columns(3)
        col1.metric('Sessions', len(current_sessions))
        col2.metric('Roles Needed', total_roles)
        col3.metric('Assigned', f'{assigned_roles}/{total_roles}')
        
        st.markdown('---')
        
        # Show OPENING
        if st.session_state.selected_date in st.session_state.opening_closing_times:
            times = st.session_state.opening_closing_times[st.session_state.selected_date]
            opening_person = st.session_state.rental_assignments.get((st.session_state.selected_date, 'OPENING'), 'UNASSIGNED')
            
            if 'opening' in times:
                opening_time_str = times['opening'].strftime('%I:%M %p')
                st.markdown(f'''
                <div style="background:#2e7d32;color:white;padding:0.75rem;border-radius:0.5rem;margin-bottom:1rem;">
                    <strong>🔓 OPENING</strong> - {opening_time_str}<br>
                    Rentals: {opening_person}
                </div>
                ''', unsafe_allow_html=True)
        
        st.markdown('---')
        
        # Sessions
        sessions_by_time = defaultdict(list)
        for session in current_sessions:
            sessions_by_time[session['time']].append(session)
        
        for time_key in sorted(sessions_by_time.keys()):
            sessions = sessions_by_time[time_key]
            main = sessions[0]
            
            # Get rental assignment for this session
            rental_key = (time_key, 'SESSION')
            rental_person = st.session_state.rental_assignments.get(rental_key, 'UNASSIGNED')
            
            st.markdown(f"### {time_key.strftime('%I:%M %p')} - {main['session_type']} <span style='float:right;color:#666;font-size:0.9rem;'>🏪 Rentals: {rental_person}</span>", unsafe_allow_html=True)
            
            # Display LEFT and RIGHT side by side
            cols = st.columns(len(sessions))
            for idx, session in enumerate(sessions):
                with cols[idx]:
                    bg_color = '#8B4513' if session['side'] == 'LEFT' else '#2F4F4F'
                    
                    roles_html = ''
                    if session['roles']:
                        for role in session['roles']:
                            key = (session['time'], session['side'], role)
                            coach = st.session_state.assignments.get(key, 'UNASSIGNED')
                            roles_html += f'<div style="margin:0.25rem 0;"><strong>{role}:</strong> {coach}</div>'
                    else:
                        roles_html = '<em>No coaches needed</em>'
                    
                    st.markdown(f'''
                    <div style="background:{bg_color};color:white;padding:1rem;border-radius:0.5rem;margin:0.5rem 0;">
                        <strong>{session['side']}</strong> - {session['guests']} guests, {session['private_lessons']} private<br>
                        <div style="margin-top:0.5rem;">{roles_html}</div>
                    </div>
                    ''', unsafe_allow_html=True)
            
            st.markdown('---')
        
        # Show CLOSING at bottom
        if st.session_state.selected_date in st.session_state.opening_closing_times:
            times = st.session_state.opening_closing_times[st.session_state.selected_date]
            closing_person = st.session_state.rental_assignments.get((st.session_state.selected_date, 'CLOSING'), 'UNASSIGNED')
            
            if 'closing' in times:
                closing_time_str = times['closing'].strftime('%I:%M %p')
                st.markdown(f'''
                <div style="background:#c62828;color:white;padding:0.75rem;border-radius:0.5rem;margin-top:1rem;margin-bottom:1rem;">
                    <strong>🔒 CLOSING</strong> - {closing_time_str}<br>
                    Rentals: {closing_person}
                </div>
                ''', unsafe_allow_html=True)
        
        st.markdown('---')
        
        if st.button('📥 Export This Day to Excel'):
            export_data = []
            for session in sorted(current_sessions, key=lambda x: x['time']):
                if session['roles']:
                    for role in session['roles']:
                        key = (session['time'], session['side'], role)
                        coach = st.session_state.assignments.get(key, 'UNASSIGNED')
                        export_data.append({
                            'Time': session['time'].strftime('%I:%M %p'),
                            'Session Type': session['session_type'],
                            'Side': session['side'],
                            'Guests': session['guests'],
                            'Private Lessons': session['private_lessons'],
                            'Role': role,
                            'Assigned Coach': coach
                        })
                else:
                    export_data.append({
                        'Time': session['time'].strftime('%I:%M %p'),
                        'Session Type': session['session_type'],
                        'Side': session['side'],
                        'Guests': session['guests'],
                        'Private Lessons': session['private_lessons'],
                        'Role': 'N/A',
                        'Assigned Coach': 'No coaches needed'
                    })
            
            df = pd.DataFrame(export_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Schedule', index=False)
            output.seek(0)
            
            st.download_button(
                '📥 Download Excel',
                output,
                file_name=f'schedule_{st.session_state.selected_date.strftime("%Y%m%d")}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

st.markdown('---')
if st.session_state.last_sync:
    st.caption(f'🏄 Multi-Day Schedule Builder | Last saved: {st.session_state.last_sync.strftime("%I:%M %p")} | v3.1')
else:
    st.caption('🏄 Multi-Day Schedule Builder | v3.1')
