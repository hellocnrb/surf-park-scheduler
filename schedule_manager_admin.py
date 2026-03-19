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
    """Load all schedules from Google Sheets"""
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        data = sheet.get_all_values()
        
        if len(data) < 2:
            return {}, {}
        
        sessions_by_date = defaultdict(list)
        assignments = {}
        
        for row in data[1:]:  # Skip header
            if len(row) >= 7:
                try:
                    time_str = row[0]
                    session_datetime = datetime.strptime(f"{row[7]} {time_str}", "%Y-%m-%d %I:%M %p")
                    
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
                    
                    session_date = session_datetime.date()
                    sessions_by_date[session_date].append(session)
                    
                    # Load assignment
                    if row[5] != 'N/A' and row[6] != 'No coaches needed':
                        key = (session_datetime, row[2], row[5])
                        assignments[key] = row[6]
                
                except Exception as e:
                    continue
        
        return dict(sessions_by_date), assignments
    
    except Exception as e:
        st.error(f"Error loading: {e}")
        return {}, {}

def save_to_google_sheets(gc, sheet_id, all_sessions, assignments):
    """Save all schedules to Google Sheets"""
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        
        rows = [['Time', 'Session Type', 'Side', 'Guests', 'Private Lessons', 'Role', 'Assigned Coach', 'Date']]
        
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
                            session_date.strftime('%Y-%m-%d')
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
                        session_date.strftime('%Y-%m-%d')
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
if 'last_sync' not in st.session_state:
    st.session_state.last_sync = None

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
    # Date picker that persists across tabs
    new_date = st.date_input(
        "📅 Working On",
        value=st.session_state.selected_date,
        key='main_date_picker',
        help="Select the date you want to view/edit"
    )
    if new_date != st.session_state.selected_date:
        st.session_state.selected_date = new_date
        st.rerun()

with col2:
    if gc and SCHEDULE_SHEET_ID:
        if st.button("🔄 Load", use_container_width=True, help="Load schedules from Google Sheets"):
            with st.spinner("Loading..."):
                loaded_sessions, loaded_assignments = load_from_google_sheets(gc, SCHEDULE_SHEET_ID)
                st.session_state.sessions_by_date = loaded_sessions
                st.session_state.assignments = loaded_assignments
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
st.markdown(f'<div class="date-badge">📅 {st.session_state.selected_date.strftime("%A, %B %d, %Y")}</div>', unsafe_allow_html=True)

# Quick stats for current date
current_sessions = st.session_state.sessions_by_date.get(st.session_state.selected_date, [])
if current_sessions:
    total_roles = sum(len(s.get('roles', [])) for s in current_sessions)
    assigned_roles = sum(1 for (dt, side, role) in st.session_state.assignments.keys() if dt.date() == st.session_state.selected_date)
    st.caption(f"📊 {len(current_sessions)} sessions | {assigned_roles}/{total_roles} roles assigned")

# Week overview
if st.session_state.sessions_by_date:
    with st.expander("📅 Week Overview", expanded=False):
        week_dates = sorted(st.session_state.sessions_by_date.keys())
        cols = st.columns(min(len(week_dates), 7))
        for idx, d in enumerate(week_dates[:7]):
            with cols[idx]:
                session_count = len(st.session_state.sessions_by_date[d])
                is_selected = d == st.session_state.selected_date
                style = "background:#1f77b4;color:white;" if is_selected else "background:#f0f2f6;"
                st.markdown(f'''
                <div style="{style}padding:0.5rem;border-radius:0.5rem;text-align:center;">
                    <strong>{d.strftime("%a %m/%d")}</strong><br>
                    {session_count} sessions
                </div>
                ''', unsafe_allow_html=True)
                if st.button(f"View", key=f"goto_{d}", use_container_width=True):
                    st.session_state.selected_date = d
                    st.rerun()

st.markdown('---')

# Tabs
tab1, tab2, tab3 = st.tabs(['➕ Create Sessions', '👥 Assign Coaches', '📋 View Schedule'])

with tab1:
    st.header(f'Create Sessions for {st.session_state.selected_date.strftime("%A, %b %d")}')
    st.caption('Add sessions to this date')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader('Session Details')
        session_time = st.time_input('Time', value=time(9, 0), key='session_time')
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
                        for role in session['roles']:
                            key = (session['time'], session['side'], role)
                            assigned = st.session_state.assignments.get(key, '')
                            
                            options = ['-- Unassigned --'] + st.session_state.coach_roster
                            idx_default = options.index(assigned) if assigned in st.session_state.coach_roster else 0
                            
                            new_assignment = st.selectbox(
                                role,
                                options,
                                index=idx_default,
                                key=f'assign_{st.session_state.selected_date}_{time_key}_{session["side"]}_{role}'
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
                if save_to_google_sheets(gc, SCHEDULE_SHEET_ID, st.session_state.sessions_by_date, st.session_state.assignments):
                    st.session_state.last_sync = datetime.now()
                    st.success('✅ Saved all dates!')
        else:
            st.warning('⚠️ Google Sheets not configured')

with tab3:
    st.header(f'Schedule for {st.session_state.selected_date.strftime("%A, %B %d, %Y")}')
    
    if not current_sessions:
        st.info('No sessions for this date')
    else:
        total_roles = sum(len(s.get('roles', [])) for s in current_sessions)
        assigned_roles = sum(1 for (dt, side, role) in st.session_state.assignments.keys() if dt.date() == st.session_state.selected_date)
        
        col1, col2, col3 = st.columns(3)
        col1.metric('Sessions', len(current_sessions))
        col2.metric('Roles Needed', total_roles)
        col3.metric('Assigned', f'{assigned_roles}/{total_roles}')
        
        st.markdown('---')
        
        sessions_by_time = defaultdict(list)
        for session in current_sessions:
            sessions_by_time[session['time']].append(session)
        
        for time_key in sorted(sessions_by_time.keys()):
            sessions = sessions_by_time[time_key]
            main = sessions[0]
            
            st.markdown(f"### {time_key.strftime('%I:%M %p')} - {main['session_type']}")
            
            for session in sessions:
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
