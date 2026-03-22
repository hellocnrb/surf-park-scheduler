"""
Surf Park Daily Schedule Builder V2
For Head Coaches - Multi-day scheduling with role assignment
FIXES: Combined tabs, inline editing, duplicate prevention, opening/closing persistence
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
from collections import defaultdict
import yaml
import io
import os
import uuid

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

def save_to_google_sheets(gc, sheet_id, all_sessions, assignments, staff_roster, rental_assignments, opening_closing_times):
    """Save everything to Google Sheets with proper structure"""
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        
        rows = [['Type', 'SessionID', 'Date', 'Time', 'SessionType', 'Side', 'Guests', 'Private', 'Role', 'StaffName', 'RentalPerson', 'StaffRoster']]
        
        # Row 2: Save staff roster (combined coaches and rental staff)
        if staff_roster:
            rows.append(['STAFF_ROSTER', '', '', '', '', '', '', '', '', '', '', ','.join(staff_roster)])
        
        # Save opening/closing times and assignments
        for date_key, times_dict in opening_closing_times.items():
            date_str = date_key.strftime('%Y-%m-%d')
            
            if 'opening' in times_dict:
                opening_time_str = times_dict['opening'].strftime('%I:%M %p')
                opening_person = rental_assignments.get((date_key, 'OPENING'), '')
                rows.append(['OPENING', '', date_str, opening_time_str, '', '', '', '', '', '', opening_person, ''])
            
            if 'closing' in times_dict:
                closing_time_str = times_dict['closing'].strftime('%I:%M %p')
                closing_person = rental_assignments.get((date_key, 'CLOSING'), '')
                rows.append(['CLOSING', '', date_str, closing_time_str, '', '', '', '', '', '', closing_person, ''])
        
        # Save sessions with their unique IDs
        for session_date, sessions in sorted(all_sessions.items()):
            for session in sessions:
                session_id = session.get('id', str(uuid.uuid4()))
                date_str = session_date.strftime('%Y-%m-%d')
                time_str = session['time'].strftime('%I:%M %p')
                
                # Save rental assignment for this session
                rental_key = (session['time'], 'SESSION')
                rental_person = rental_assignments.get(rental_key, '')
                
                roles = session.get('roles', [])
                if roles:
                    for role in roles:
                        assignment_key = (session['time'], session['side'], role)
                        staff_name = assignments.get(assignment_key, '')
                        rows.append([
                            'SESSION',
                            session_id,
                            date_str,
                            time_str,
                            session['session_type'],
                            session['side'],
                            session['guests'],
                            session['private_lessons'],
                            role,
                            staff_name,
                            rental_person,
                            ''
                        ])
                else:
                    rows.append([
                        'SESSION',
                        session_id,
                        date_str,
                        time_str,
                        session['session_type'],
                        session['side'],
                        session['guests'],
                        session['private_lessons'],
                        '',
                        '',
                        rental_person,
                        ''
                    ])
        
        sheet.clear()
        sheet.update('A1', rows)
        return True
    except Exception as e:
        st.error(f"Error saving: {e}")
        return False

def load_from_google_sheets(gc, sheet_id):
    """Load everything from Google Sheets"""
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        data = sheet.get_all_values()
        
        if len(data) < 2:
            return {}, {}, [], {}, {}
        
        sessions_by_date = defaultdict(list)
        assignments = {}
        staff_roster = []
        rental_assignments = {}
        opening_closing_times = {}
        seen_session_ids = set()
        
        for row in data[1:]:  # Skip header
            if not row or len(row) < 2:
                continue
            
            row_type = row[0]
            
            # Load staff roster (combined coaches and rental staff)
            if row_type == 'STAFF_ROSTER' and len(row) >= 12 and row[11]:
                staff_roster = [c.strip() for c in row[11].split(',') if c.strip()]
                continue
            
            # Load opening/closing
            if row_type in ['OPENING', 'CLOSING'] and len(row) >= 11:
                try:
                    date_obj = datetime.strptime(row[2], '%Y-%m-%d').date()
                    time_obj = datetime.strptime(row[3], '%I:%M %p').time()
                    
                    if date_obj not in opening_closing_times:
                        opening_closing_times[date_obj] = {}
                    
                    if row_type == 'OPENING':
                        opening_closing_times[date_obj]['opening'] = time_obj
                        if row[10]:
                            rental_assignments[(date_obj, 'OPENING')] = row[10]
                    else:  # CLOSING
                        opening_closing_times[date_obj]['closing'] = time_obj
                        if row[10]:
                            rental_assignments[(date_obj, 'CLOSING')] = row[10]
                except:
                    continue
            
            # Load sessions
            if row_type == 'SESSION' and len(row) >= 11:
                try:
                    session_id = row[1]
                    date_obj = datetime.strptime(row[2], '%Y-%m-%d').date()
                    time_obj = datetime.strptime(row[3], '%I:%M %p').time()
                    session_datetime = datetime.combine(date_obj, time_obj)
                    
                    # Only create session once per session_id
                    if session_id not in seen_session_ids:
                        session = {
                            'id': session_id,
                            'time': session_datetime,
                            'session_type': row[4],
                            'side': row[5],
                            'guests': int(row[6]) if row[6] else 0,
                            'private_lessons': int(row[7]) if row[7] else 0,
                            'baseline_coaches': 0,
                            'roles': []
                        }
                        
                        # Recalculate roles
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
                        
                        sessions_by_date[date_obj].append(session)
                        seen_session_ids.add(session_id)
                    
                    # Load coach assignment
                    if row[8] and row[9]:  # role and coach name
                        assignment_key = (session_datetime, row[5], row[8])
                        assignments[assignment_key] = row[9]
                    
                    # Load rental assignment
                    if row[10]:
                        rental_key = (session_datetime, 'SESSION')
                        rental_assignments[rental_key] = row[10]
                
                except Exception as e:
                    continue
        
        # Set defaults if not loaded
        if not staff_roster:
            staff_roster = ['Conner', 'Jake B', 'Kai', 'Brady', 'Jack', 'Laird', 'Ella', 'Sarah', 'Mike', 'Alex']
        
        return dict(sessions_by_date), assignments, staff_roster, rental_assignments, opening_closing_times
    
    except Exception as e:
        st.error(f"Error loading: {e}")
        return {}, {}, [], {}, {}

# Initialize session state
if 'sessions_by_date' not in st.session_state:
    st.session_state.sessions_by_date = {}
if 'assignments' not in st.session_state:
    st.session_state.assignments = {}
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = date.today()
if 'staff_roster' not in st.session_state:
    st.session_state.staff_roster = ['Conner', 'Jake B', 'Kai', 'Brady', 'Jack', 'Laird', 'Ella', 'Sarah', 'Mike', 'Alex']
if 'last_sync' not in st.session_state:
    st.session_state.last_sync = None
if 'rental_assignments' not in st.session_state:
    st.session_state.rental_assignments = {}
if 'opening_closing_times' not in st.session_state:
    st.session_state.opening_closing_times = {}

rules = load_coaching_rules()
gc = get_google_sheets_client()

try:
    SCHEDULE_SHEET_ID = st.secrets.get('daily_schedule_sheet_id', '')
except:
    SCHEDULE_SHEET_ID = ''

# Header
st.markdown('<div class="main-header">🏄 Schedule Manager</div>', unsafe_allow_html=True)

# Top controls
col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

with col1:
    st.date_input(
        "📅 Pick Any Date",
        value=st.session_state.selected_date,
        key='main_date_picker',
        help="Select date to view/edit"
    )
    if 'main_date_picker' in st.session_state:
        if st.session_state.main_date_picker != st.session_state.selected_date:
            st.session_state.selected_date = st.session_state.main_date_picker
            st.rerun()

with col2:
    if gc and SCHEDULE_SHEET_ID:
        if st.button("🔄 Load", use_container_width=True):
            with st.spinner("Loading..."):
                loaded_sessions, loaded_assignments, loaded_staff_roster, loaded_rental_assignments, loaded_oc_times = load_from_google_sheets(gc, SCHEDULE_SHEET_ID)
                st.session_state.sessions_by_date = loaded_sessions
                st.session_state.assignments = loaded_assignments
                st.session_state.staff_roster = loaded_staff_roster
                st.session_state.rental_assignments = loaded_rental_assignments
                st.session_state.opening_closing_times = loaded_oc_times
                st.session_state.last_sync = datetime.now()
                st.success("✅ Loaded!")
                st.rerun()

with col3:
    if gc and SCHEDULE_SHEET_ID:
        if st.button("💾 Save", use_container_width=True):
            with st.spinner("Saving..."):
                if save_to_google_sheets(
                    gc, SCHEDULE_SHEET_ID,
                    st.session_state.sessions_by_date,
                    st.session_state.assignments,
                    st.session_state.staff_roster,
                    st.session_state.rental_assignments,
                    st.session_state.opening_closing_times
                ):
                    st.session_state.last_sync = datetime.now()
                    st.success("✅ Saved!")

with col4:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

# Show current date
st.markdown(f'<div class="date-badge" style="text-align:center;">📅 {st.session_state.selected_date.strftime("%A, %B %d, %Y")}</div>', unsafe_allow_html=True)

# Quick stats for current date
current_sessions = st.session_state.sessions_by_date.get(st.session_state.selected_date, [])
if current_sessions:
    total_roles = sum(len(s.get('roles', [])) for s in current_sessions)
    assigned_roles = sum(1 for (dt, side, role) in st.session_state.assignments.keys() if dt.date() == st.session_state.selected_date)
    st.caption(f"📊 {len(current_sessions)} sessions | {assigned_roles}/{total_roles} roles assigned")

st.markdown('---')

# COMBINED TAB: Manage & Assign
tab1, tab2 = st.tabs(['📋 Manage & Assign', '👁️ View Schedule'])

with tab1:
    st.header(f'Manage Sessions - {st.session_state.selected_date.strftime("%A, %b %d")}')
    
    # Opening/Closing section
    with st.expander("🏪 Opening & Closing", expanded=True):
        current_times = st.session_state.opening_closing_times.get(st.session_state.selected_date, {})
        
        col_open, col_close = st.columns(2)
        
        with col_open:
            st.markdown("**🔓 Opening**")
            default_opening = current_times.get('opening', time(8, 0))
            default_hour_open = default_opening.hour
            default_ampm_open = 'AM' if default_hour_open < 12 else 'PM'
            if default_hour_open > 12:
                default_hour_open -= 12
            elif default_hour_open == 0:
                default_hour_open = 12
            
            oc1, oc2, oc3 = st.columns([2, 2, 1])
            with oc1:
                open_hour = st.selectbox('Hour', list(range(1, 13)), index=default_hour_open-1, key=f'oh_{st.session_state.selected_date}')
            with oc2:
                open_min = st.selectbox('Min', ['00', '30'], index=0 if default_opening.minute == 0 else 1, key=f'om_{st.session_state.selected_date}')
            with oc3:
                open_ap = st.selectbox('', ['AM', 'PM'], index=0 if default_ampm_open == 'AM' else 1, key=f'oa_{st.session_state.selected_date}')
            
            hour_24 = open_hour if open_ap == 'AM' else (open_hour + 12 if open_hour != 12 else 12)
            if open_ap == 'AM' and open_hour == 12:
                hour_24 = 0
            opening_time = time(hour_24, int(open_min))
            
            if st.session_state.selected_date not in st.session_state.opening_closing_times:
                st.session_state.opening_closing_times[st.session_state.selected_date] = {}
            st.session_state.opening_closing_times[st.session_state.selected_date]['opening'] = opening_time
            
            opening_person_key = (st.session_state.selected_date, 'OPENING')
            opening_assigned = st.session_state.rental_assignments.get(opening_person_key, '')
            opening_options = ['-- Unassigned --'] + st.session_state.staff_roster
            opening_idx = opening_options.index(opening_assigned) if opening_assigned in st.session_state.staff_roster else 0
            
            new_opening = st.selectbox('Opening Staff', opening_options, index=opening_idx, key=f'os_{st.session_state.selected_date}')
            
            if new_opening != '-- Unassigned --':
                st.session_state.rental_assignments[opening_person_key] = new_opening
            elif opening_person_key in st.session_state.rental_assignments:
                del st.session_state.rental_assignments[opening_person_key]
        
        with col_close:
            st.markdown("**🔒 Closing**")
            default_closing = current_times.get('closing', time(18, 0))
            default_hour_close = default_closing.hour
            default_ampm_close = 'AM' if default_hour_close < 12 else 'PM'
            if default_hour_close > 12:
                default_hour_close -= 12
            elif default_hour_close == 0:
                default_hour_close = 12
            
            cc1, cc2, cc3 = st.columns([2, 2, 1])
            with cc1:
                close_hour = st.selectbox('Hour', list(range(1, 13)), index=default_hour_close-1, key=f'ch_{st.session_state.selected_date}')
            with cc2:
                close_min = st.selectbox('Min', ['00', '30'], index=0 if default_closing.minute == 0 else 1, key=f'cm_{st.session_state.selected_date}')
            with cc3:
                close_ap = st.selectbox('', ['AM', 'PM'], index=0 if default_ampm_close == 'AM' else 1, key=f'ca_{st.session_state.selected_date}')
            
            hour_24 = close_hour if close_ap == 'AM' else (close_hour + 12 if close_hour != 12 else 12)
            if close_ap == 'AM' and close_hour == 12:
                hour_24 = 0
            closing_time = time(hour_24, int(close_min))
            
            if st.session_state.selected_date not in st.session_state.opening_closing_times:
                st.session_state.opening_closing_times[st.session_state.selected_date] = {}
            st.session_state.opening_closing_times[st.session_state.selected_date]['closing'] = closing_time
            
            closing_person_key = (st.session_state.selected_date, 'CLOSING')
            closing_assigned = st.session_state.rental_assignments.get(closing_person_key, '')
            closing_options = ['-- Unassigned --'] + st.session_state.staff_roster
            closing_idx = closing_options.index(closing_assigned) if closing_assigned in st.session_state.staff_roster else 0
            
            new_closing = st.selectbox('Closing Staff', closing_options, index=closing_idx, key=f'cs_{st.session_state.selected_date}')
            
            if new_closing != '-- Unassigned --':
                st.session_state.rental_assignments[closing_person_key] = new_closing
            elif closing_person_key in st.session_state.rental_assignments:
                del st.session_state.rental_assignments[closing_person_key]
        
        # Manage staff roster (combined - everyone can do both roles)
        with st.expander("👥 Manage Staff Roster"):
            st.caption("All staff are cross-trained for both coaching and rental counter")
            new_staff = st.text_input('Add staff member', key='new_staff')
            if st.button('➕ Add Staff') and new_staff:
                if new_staff not in st.session_state.staff_roster:
                    st.session_state.staff_roster.append(new_staff)
                    st.success(f'Added {new_staff}')
                    st.rerun()
            st.info(f"Staff Roster: {', '.join(st.session_state.staff_roster)}")
    
    st.markdown('---')
    
    # Add new session section
    with st.expander("➕ Add New Session", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader('Time & Type')
            tc1, tc2, tc3 = st.columns([2, 2, 1])
            with tc1:
                new_hour = st.selectbox('Hour', list(range(1, 13)), index=8, key='new_hour')
            with tc2:
                new_min = st.selectbox('Min', ['00', '30'], index=0, key='new_min')
            with tc3:
                new_ap = st.selectbox('AM/PM', ['AM', 'PM'], index=0, key='new_ap')
            
            hour_24 = new_hour if new_ap == 'AM' else (new_hour + 12 if new_hour != 12 else 12)
            if new_ap == 'AM' and new_hour == 12:
                hour_24 = 0
            new_time = time(hour_24, int(new_min))
            
            new_type = st.selectbox('Session Type', list(rules['session_types'].keys()), key='new_type')
        
        with col2:
            st.subheader(' ')
            add_both = st.checkbox('Add LEFT and RIGHT', value=True, key='add_both_new')
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown('**LEFT**')
            left_g = st.number_input('Guests', 0, 30, 0, key='left_g_new')
            left_p = st.number_input('Private', 0, 5, 0, key='left_p_new')
        
        with col_right:
            st.markdown('**RIGHT**')
            right_g = st.number_input('Guests', 0, 30, 0, key='right_g_new')
            right_p = st.number_input('Private', 0, 5, 0, key='right_p_new')
        
        if st.button('➕ Add Session(s)', type='primary'):
            session_datetime = datetime.combine(st.session_state.selected_date, new_time)
            
            # Check for duplicates
            if st.session_state.selected_date in st.session_state.sessions_by_date:
                existing_times_sides = [(s['time'], s['side']) for s in st.session_state.sessions_by_date[st.session_state.selected_date]]
                if (session_datetime, 'LEFT') in existing_times_sides and add_both:
                    st.error(f"⚠️ LEFT session already exists at {new_time.strftime('%I:%M %p')}")
                    st.stop()
                if (session_datetime, 'RIGHT') in existing_times_sides and add_both:
                    st.error(f"⚠️ RIGHT session already exists at {new_time.strftime('%I:%M %p')}")
                    st.stop()
            
            if st.session_state.selected_date not in st.session_state.sessions_by_date:
                st.session_state.sessions_by_date[st.session_state.selected_date] = []
            
            # Add LEFT
            left_baseline = calculate_baseline_coaches(new_type, left_g, rules)
            left_roles = get_required_roles(new_type, left_baseline, left_p)
            
            st.session_state.sessions_by_date[st.session_state.selected_date].append({
                'id': str(uuid.uuid4()),
                'time': session_datetime,
                'session_type': new_type,
                'side': 'LEFT',
                'guests': left_g,
                'private_lessons': left_p,
                'baseline_coaches': left_baseline,
                'roles': left_roles
            })
            
            # Add RIGHT if checked
            if add_both:
                right_baseline = calculate_baseline_coaches(new_type, right_g, rules)
                right_roles = get_required_roles(new_type, right_baseline, right_p)
                
                st.session_state.sessions_by_date[st.session_state.selected_date].append({
                    'id': str(uuid.uuid4()),
                    'time': session_datetime,
                    'session_type': new_type,
                    'side': 'RIGHT',
                    'guests': right_g,
                    'private_lessons': right_p,
                    'baseline_coaches': right_baseline,
                    'roles': right_roles
                })
            
            st.success(f'Added session at {new_time.strftime("%I:%M %p")}!')
            st.rerun()
    
    st.markdown('---')
    
    # Display and edit existing sessions
    if not current_sessions:
        st.info('No sessions for this date. Add one above!')
    else:
        st.subheader('Sessions & Assignments')
        
        sessions_by_time = defaultdict(list)
        for session in current_sessions:
            sessions_by_time[session['time']].append(session)
        
        for time_key in sorted(sessions_by_time.keys()):
            sessions = sessions_by_time[time_key]
            main = sessions[0]
            
            with st.container():
                # Header with time and current type
                main = sessions[0]
                st.markdown(f"### {time_key.strftime('%I:%M %p')} - {main['session_type']}")
                
                # Type editor - full width right under the title
                current_type_idx = list(rules['session_types'].keys()).index(main['session_type'])
                new_session_type = st.selectbox(
                    'Session Type',
                    list(rules['session_types'].keys()),
                    index=current_type_idx,
                    key=f'type_{time_key}_{st.session_state.selected_date}'
                )
                
                # Apply type change to all sessions at this time
                for session in sessions:
                    session['session_type'] = new_session_type
                
                st.markdown('---')
                
                # Rental assignment
                rental_key = (time_key, 'SESSION')
                rental_assigned = st.session_state.rental_assignments.get(rental_key, '')
                rental_options = ['-- Unassigned --'] + st.session_state.staff_roster
                rental_idx = rental_options.index(rental_assigned) if rental_assigned in st.session_state.staff_roster else 0
                
                st.markdown("**🏪 Rentals During This Session:**")
                new_rental_assign = st.selectbox(
                    'Rental Counter',
                    rental_options,
                    index=rental_idx,
                    key=f'rental_{time_key}_{st.session_state.selected_date}',
                    label_visibility='collapsed'
                )
                
                if new_rental_assign != '-- Unassigned --':
                    st.session_state.rental_assignments[rental_key] = new_rental_assign
                elif rental_key in st.session_state.rental_assignments:
                    del st.session_state.rental_assignments[rental_key]
                
                st.markdown('---')
                
                # Sessions side by side
                cols = st.columns(len(sessions))
                
                for idx, session in enumerate(sessions):
                    with cols[idx]:
                        bg_color = '#8B4513' if session['side'] == 'LEFT' else '#2F4F4F'
                        st.markdown(f'''
                        <div style="background:{bg_color};color:white;padding:1rem;border-radius:0.5rem;margin-bottom:0.5rem;">
                            <strong>{session['side']}</strong>
                        </div>
                        ''', unsafe_allow_html=True)
                        
                        # Inline edit fields
                        session['guests'] = st.number_input(
                            'Guests',
                            0, 30,
                            session['guests'],
                            key=f"g_{session['id']}"
                        )
                        
                        session['private_lessons'] = st.number_input(
                            'Private',
                            0, 5,
                            session['private_lessons'],
                            key=f"p_{session['id']}"
                        )
                        
                        # Recalculate roles based on updated type (set at session level)
                        baseline = calculate_baseline_coaches(session['session_type'], session['guests'], rules)
                        session['baseline_coaches'] = baseline
                        session['roles'] = get_required_roles(session['session_type'], baseline, session['private_lessons'])
                        
                        # Coach assignments
                        if session['roles']:
                            st.markdown("**Coach Assignments:**")
                            for role_idx, role in enumerate(session['roles']):
                                key = (session['time'], session['side'], role)
                                assigned = st.session_state.assignments.get(key, '')
                                
                                options = ['-- Unassigned --'] + st.session_state.staff_roster
                                idx_default = options.index(assigned) if assigned in st.session_state.staff_roster else 0
                                
                                new_assignment = st.selectbox(
                                    role,
                                    options,
                                    index=idx_default,
                                    key=f'assign_{session["id"]}_{role_idx}'
                                )
                                
                                if new_assignment != '-- Unassigned --':
                                    st.session_state.assignments[key] = new_assignment
                                elif key in st.session_state.assignments:
                                    del st.session_state.assignments[key]
                        else:
                            st.caption('*No coaches needed*')
                
                # Buttons below both sessions - side by side
                st.markdown('---')
                
                button_col1, button_col2 = st.columns(2)
                
                with button_col1:
                    # Duplicate button - creates both LEFT and RIGHT sessions
                    if st.button('📋 Duplicate Session', key=f'dup_{time_key}_{st.session_state.selected_date}', use_container_width=True):
                        # Duplicate all sessions at this time (both LEFT and RIGHT)
                        for session in sessions:
                            new_session = session.copy()
                            new_session['id'] = str(uuid.uuid4())
                            st.session_state.sessions_by_date[st.session_state.selected_date].append(new_session)
                        st.success(f'Duplicated {time_key.strftime("%I:%M %p")} session')
                        st.rerun()
                
                with button_col2:
                    # Delete button - removes entire session (both LEFT and RIGHT at this time)
                    if st.button('🗑️ Delete Session', key=f'del_{time_key}_{st.session_state.selected_date}', use_container_width=True, type='secondary'):
                        # Remove all sessions at this time
                        st.session_state.sessions_by_date[st.session_state.selected_date] = [
                            s for s in st.session_state.sessions_by_date[st.session_state.selected_date]
                            if s['time'] != time_key
                        ]
                        st.success(f'Deleted {time_key.strftime("%I:%M %p")} session')
                        st.rerun()
                
                st.markdown('---')

with tab2:
    st.header(f'View Schedule - {st.session_state.selected_date.strftime("%A, %B %d, %Y")}')
    
    # Always show opening/closing if they exist
    has_opening_closing = st.session_state.selected_date in st.session_state.opening_closing_times
    
    if not current_sessions and not has_opening_closing:
        st.info('No sessions or opening/closing times set for this date')
    else:
        # Stats (only if there are sessions)
        if current_sessions:
            total_roles = sum(len(s.get('roles', [])) for s in current_sessions)
            assigned_roles = sum(1 for (dt, side, role) in st.session_state.assignments.keys() if dt.date() == st.session_state.selected_date)
            
            col1, col2, col3 = st.columns(3)
            col1.metric('Sessions', len(current_sessions))
            col2.metric('Roles Needed', total_roles)
            col3.metric('Assigned', f'{assigned_roles}/{total_roles}')
            
            st.markdown('---')
        
        # Opening
        if st.session_state.selected_date in st.session_state.opening_closing_times:
            times = st.session_state.opening_closing_times[st.session_state.selected_date]
            if 'opening' in times:
                opening_person = st.session_state.rental_assignments.get((st.session_state.selected_date, 'OPENING'), 'UNASSIGNED')
                st.markdown(f'''
                <div style="background:#2e7d32;color:white;padding:0.75rem;border-radius:0.5rem;margin-bottom:1rem;">
                    <strong>🔓 OPENING</strong> - {times['opening'].strftime('%I:%M %p')}<br>
                    Rentals: {opening_person}
                </div>
                ''', unsafe_allow_html=True)
        
        # Sessions (only if they exist)
        if current_sessions:
            st.markdown('---')
            
            sessions_by_time = defaultdict(list)
            for session in current_sessions:
                sessions_by_time[session['time']].append(session)
        
        for time_key in sorted(sessions_by_time.keys()):
            sessions = sessions_by_time[time_key]
            main = sessions[0]
            
            rental_key = (time_key, 'SESSION')
            rental_person = st.session_state.rental_assignments.get(rental_key, 'UNASSIGNED')
            
            st.markdown(f"### {time_key.strftime('%I:%M %p')} - {main['session_type']} <span style='float:right;color:#666;font-size:0.9rem;'>🏪 Rentals: {rental_person}</span>", unsafe_allow_html=True)
            
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
        
        # Closing (show even if no sessions)
        if st.session_state.selected_date in st.session_state.opening_closing_times:
            times = st.session_state.opening_closing_times[st.session_state.selected_date]
            if 'closing' in times:
                closing_person = st.session_state.rental_assignments.get((st.session_state.selected_date, 'CLOSING'), 'UNASSIGNED')
                st.markdown(f'''
                <div style="background:#c62828;color:white;padding:0.75rem;border-radius:0.5rem;margin-top:1rem;margin-bottom:1rem;">
                    <strong>🔒 CLOSING</strong> - {times['closing'].strftime('%I:%M %p')}<br>
                    Rentals: {closing_person}
                </div>
                ''', unsafe_allow_html=True)
        
        st.markdown('---')
        
        # Export to PDF (only if there's something to export)
        if current_sessions or has_opening_closing:
            if st.button('📄 Export to PDF'):
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#1f77b4'),
                spaceAfter=12,
                alignment=1  # Center
            )
            title = Paragraph(f"Schedule for {st.session_state.selected_date.strftime('%A, %B %d, %Y')}", title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.2*inch))
            
            # Opening
            if st.session_state.selected_date in st.session_state.opening_closing_times:
                times = st.session_state.opening_closing_times[st.session_state.selected_date]
                if 'opening' in times:
                    opening_person = st.session_state.rental_assignments.get((st.session_state.selected_date, 'OPENING'), 'UNASSIGNED')
                    opening_text = f"🔓 OPENING - {times['opening'].strftime('%I:%M %p')} | Rentals: {opening_person}"
                    elements.append(Paragraph(opening_text, styles['Normal']))
                    elements.append(Spacer(1, 0.1*inch))
            
            # Sessions
            sessions_by_time = defaultdict(list)
            for session in current_sessions:
                sessions_by_time[session['time']].append(session)
            
            for time_key in sorted(sessions_by_time.keys()):
                sessions = sessions_by_time[time_key]
                main = sessions[0]
                
                # Session header
                rental_key = (time_key, 'SESSION')
                rental_person = st.session_state.rental_assignments.get(rental_key, 'UNASSIGNED')
                
                header_style = ParagraphStyle(
                    'SessionHeader',
                    parent=styles['Heading2'],
                    fontSize=12,
                    textColor=colors.HexColor('#1f77b4'),
                    spaceAfter=6
                )
                session_header = Paragraph(
                    f"{time_key.strftime('%I:%M %p')} - {main['session_type']} | Rentals: {rental_person}",
                    header_style
                )
                elements.append(session_header)
                
                # Build table data for this session
                table_data = []
                
                for session in sessions:
                    side_color = colors.HexColor('#8B4513') if session['side'] == 'LEFT' else colors.HexColor('#2F4F4F')
                    
                    # Side header row
                    table_data.append([
                        Paragraph(f"<b>{session['side']}</b>", styles['Normal']),
                        '',
                        ''
                    ])
                    
                    # Guest info
                    table_data.append([
                        'Details',
                        f"{session['guests']} guests, {session['private_lessons']} private",
                        ''
                    ])
                    
                    # Coach assignments
                    if session['roles']:
                        for role in session['roles']:
                            key = (session['time'], session['side'], role)
                            coach = st.session_state.assignments.get(key, 'UNASSIGNED')
                            table_data.append([
                                role,
                                coach,
                                ''
                            ])
                    else:
                        table_data.append(['No coaches needed', '', ''])
                    
                    # Separator
                    table_data.append(['', '', ''])
                
                # Create table
                table = Table(table_data, colWidths=[2*inch, 2.5*inch, 2*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                
                elements.append(table)
                elements.append(Spacer(1, 0.2*inch))
            
            # Closing
            if st.session_state.selected_date in st.session_state.opening_closing_times:
                times = st.session_state.opening_closing_times[st.session_state.selected_date]
                if 'closing' in times:
                    closing_person = st.session_state.rental_assignments.get((st.session_state.selected_date, 'CLOSING'), 'UNASSIGNED')
                    closing_text = f"🔒 CLOSING - {times['closing'].strftime('%I:%M %p')} | Rentals: {closing_person}"
                    elements.append(Paragraph(closing_text, styles['Normal']))
            
            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            
                st.download_button(
                    '📄 Download PDF',
                    buffer,
                    file_name=f'schedule_{st.session_state.selected_date.strftime("%Y%m%d")}.pdf',
                    mime='application/pdf'
                )

st.markdown('---')

# Bottom action buttons
if gc and SCHEDULE_SHEET_ID:
    bottom_col1, bottom_col2, bottom_col3 = st.columns([1, 1, 2])
    
    with bottom_col1:
        if st.button("🔄 Load All", use_container_width=True, key='bottom_load'):
            with st.spinner("Loading..."):
                loaded_sessions, loaded_assignments, loaded_staff_roster, loaded_rental_assignments, loaded_oc_times = load_from_google_sheets(gc, SCHEDULE_SHEET_ID)
                st.session_state.sessions_by_date = loaded_sessions
                st.session_state.assignments = loaded_assignments
                st.session_state.staff_roster = loaded_staff_roster
                st.session_state.rental_assignments = loaded_rental_assignments
                st.session_state.opening_closing_times = loaded_oc_times
                st.session_state.last_sync = datetime.now()
                st.success("✅ Loaded!")
                st.rerun()
    
    with bottom_col2:
        if st.button("💾 Save All", use_container_width=True, key='bottom_save'):
            with st.spinner("Saving..."):
                if save_to_google_sheets(
                    gc, SCHEDULE_SHEET_ID,
                    st.session_state.sessions_by_date,
                    st.session_state.assignments,
                    st.session_state.staff_roster,
                    st.session_state.rental_assignments,
                    st.session_state.opening_closing_times
                ):
                    st.session_state.last_sync = datetime.now()
                    st.success("✅ Saved!")

st.markdown('---')
if st.session_state.last_sync:
    st.caption(f'🏄 Schedule Manager v4.1.6 | Last saved: {st.session_state.last_sync.strftime("%I:%M %p")}')
else:
    st.caption('🏄 Schedule Manager v4.1.6')
