"""
Surf Park Daily Schedule Builder
For Head Coaches - Manual session creation and role assignment
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
from collections import defaultdict
import yaml
import io
import os

st.set_page_config(page_title="Daily Schedule", page_icon="🏄", layout="wide")

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
        st.caption("Enter password to access daily schedule builder")
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
.session-card { background: #f0f2f6; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0; border-left: 4px solid #1f77b4; }
.left-side { background-color: #8B4513; color: white; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0; }
.right-side { background-color: #2F4F4F; color: white; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0; }
.role-badge { display: inline-block; background: #e8f4f8; padding: 0.25rem 0.5rem; border-radius: 0.25rem; margin: 0.25rem; }
</style>
''', unsafe_allow_html=True)

# Load coaching rules
def load_coaching_rules():
    try:
        with open('coaching_rules.yaml') as f:
            return yaml.safe_load(f)
    except:
        # Default rules if file not found
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
    
    # Add private lesson coaches
    for i in range(private_lessons):
        roles.append(f'Private {i+1}')
    
    return roles

def save_to_google_sheets(gc, sheet_id, sessions, assignments):
    """Save schedule and assignments to Google Sheets"""
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        
        # Build data rows
        rows = [['Time', 'Session Type', 'Side', 'Guests', 'Private Lessons', 'Role', 'Assigned Coach']]
        
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
                        coach
                    ])
            else:
                rows.append([
                    session['time'].strftime('%I:%M %p'),
                    session['session_type'],
                    session['side'],
                    session['guests'],
                    session['private_lessons'],
                    'N/A',
                    'No coaches needed'
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
if 'sessions' not in st.session_state:
    st.session_state.sessions = []
if 'assignments' not in st.session_state:
    st.session_state.assignments = {}
if 'schedule_date' not in st.session_state:
    st.session_state.schedule_date = date.today()
if 'coach_roster' not in st.session_state:
    st.session_state.coach_roster = ['Conner', 'Jake B', 'Kai', 'Brady', 'Jack', 'Laird']

# Load rules
rules = load_coaching_rules()
gc = get_google_sheets_client()

# Get sheet ID
try:
    SCHEDULE_SHEET_ID = st.secrets.get('daily_schedule_sheet_id', '')
except:
    SCHEDULE_SHEET_ID = ''

# Header
st.markdown('<div class="main-header">🏄 Daily Schedule Builder</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.session_state.schedule_date = st.date_input(
        "📅 Schedule Date",
        value=st.session_state.schedule_date,
        key='date_picker'
    )
with col2:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()
with col3:
    if st.button("🗑️ Clear All", use_container_width=True):
        st.session_state.sessions = []
        st.session_state.assignments = {}
        st.success("Cleared!")
        st.rerun()

st.markdown('---')

# Tabs
tab1, tab2, tab3 = st.tabs(['➕ Create Sessions', '👥 Assign Coaches', '📋 View Schedule'])

with tab1:
    st.header('Create Sessions')
    st.caption('Build your daily schedule by adding sessions')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader('Session Details')
        
        session_time = st.time_input('Time', value=time(9, 0), key='session_time')
        session_type = st.selectbox(
            'Session Type',
            list(rules['session_types'].keys()),
            key='session_type'
        )
    
    with col2:
        st.subheader(' ')
        st.write('')  # Spacing
        add_both = st.checkbox('Add both LEFT and RIGHT', value=True, key='add_both')
    
    st.markdown('---')
    
    # LEFT and RIGHT columns
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown('<div style="background:#8B4513;color:white;padding:0.5rem;border-radius:0.5rem;text-align:center;font-weight:bold;">LEFT SIDE</div>', unsafe_allow_html=True)
        left_guests = st.number_input('Guests (LEFT)', min_value=0, max_value=30, value=0, key='left_guests')
        left_private = st.number_input('Private Lessons (LEFT)', min_value=0, max_value=5, value=0, key='left_private')
        
        left_baseline = calculate_baseline_coaches(session_type, left_guests, rules)
        left_roles = get_required_roles(session_type, left_baseline, left_private)
        
        if left_roles:
            st.info(f"Roles needed: {', '.join(left_roles)}")
        else:
            st.info("No coaches needed")
    
    with col_right:
        st.markdown('<div style="background:#2F4F4F;color:white;padding:0.5rem;border-radius:0.5rem;text-align:center;font-weight:bold;">RIGHT SIDE</div>', unsafe_allow_html=True)
        right_guests = st.number_input('Guests (RIGHT)', min_value=0, max_value=30, value=0, key='right_guests')
        right_private = st.number_input('Private Lessons (RIGHT)', min_value=0, max_value=5, value=0, key='right_private')
        
        right_baseline = calculate_baseline_coaches(session_type, right_guests, rules)
        right_roles = get_required_roles(session_type, right_baseline, right_private)
        
        if right_roles:
            st.info(f"Roles needed: {', '.join(right_roles)}")
        else:
            st.info("No coaches needed")
    
    st.markdown('---')
    
    if st.button('➕ Add Session(s)', type='primary', use_container_width=True):
        session_datetime = datetime.combine(st.session_state.schedule_date, session_time)
        
        # Add LEFT session
        st.session_state.sessions.append({
            'time': session_datetime,
            'session_type': session_type,
            'side': 'LEFT',
            'guests': left_guests,
            'private_lessons': left_private,
            'baseline_coaches': left_baseline,
            'roles': left_roles
        })
        
        # Add RIGHT session if checked
        if add_both:
            st.session_state.sessions.append({
                'time': session_datetime,
                'session_type': session_type,
                'side': 'RIGHT',
                'guests': right_guests,
                'private_lessons': right_private,
                'baseline_coaches': right_baseline,
                'roles': right_roles
            })
        
        st.success(f'Added session(s) at {session_time.strftime("%I:%M %p")}!')
        st.rerun()
    
    # Show created sessions
    if st.session_state.sessions:
        st.markdown('---')
        st.subheader('Created Sessions')
        
        # Group by time
        sessions_by_time = defaultdict(list)
        for i, session in enumerate(st.session_state.sessions):
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
                            st.write(f"Roles: {', '.join(session['roles'])}")
                
                with cols[-1]:
                    if st.button('🗑️ Delete', key=f'del_{time_key}'):
                        # Remove sessions at this time
                        st.session_state.sessions = [s for s in st.session_state.sessions if s['time'] != time_key]
                        st.rerun()

with tab2:
    st.header('Assign Coaches')
    
    if not st.session_state.sessions:
        st.info('👈 Create sessions first in the "Create Sessions" tab')
    else:
        # Coach roster management
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
                st.info(f"Current roster: {', '.join(st.session_state.coach_roster)}")
        
        st.markdown('---')
        
        # Group sessions by time
        sessions_by_time = defaultdict(list)
        for session in st.session_state.sessions:
            sessions_by_time[session['time']].append(session)
        
        # Display sessions for assignment
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
                                key=f'assign_{time_key}_{session["side"]}_{role}'
                            )
                            
                            if new_assignment != '-- Unassigned --':
                                st.session_state.assignments[key] = new_assignment
                            elif key in st.session_state.assignments:
                                del st.session_state.assignments[key]
                    else:
                        st.caption('*No coaches needed*')
            
            st.markdown('---')
        
        # Save button
        if gc and SCHEDULE_SHEET_ID:
            if st.button('💾 Save to Google Sheets', type='primary'):
                if save_to_google_sheets(gc, SCHEDULE_SHEET_ID, st.session_state.sessions, st.session_state.assignments):
                    st.success('✅ Saved to Google Sheets!')
        else:
            st.warning('⚠️ Google Sheets not configured. Add daily_schedule_sheet_id to secrets.')

with tab3:
    st.header('Schedule Overview')
    
    if not st.session_state.sessions:
        st.info('No sessions created yet')
    else:
        st.subheader(f"📅 {st.session_state.schedule_date.strftime('%A, %B %d, %Y')}")
        
        # Summary stats
        total_sessions = len(st.session_state.sessions)
        total_roles = sum(len(s.get('roles', [])) for s in st.session_state.sessions)
        assigned_roles = len(st.session_state.assignments)
        
        col1, col2, col3 = st.columns(3)
        col1.metric('Total Sessions', total_sessions)
        col2.metric('Roles Needed', total_roles)
        col3.metric('Roles Assigned', f'{assigned_roles}/{total_roles}')
        
        st.markdown('---')
        
        # Build schedule view
        sessions_by_time = defaultdict(list)
        for session in st.session_state.sessions:
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
                    <strong>{session['side']}</strong> - {session['guests']} guests, {session['private_lessons']} private lessons<br>
                    <div style="margin-top:0.5rem;">{roles_html}</div>
                </div>
                ''', unsafe_allow_html=True)
            
            st.markdown('---')
        
        # Export button
        if st.button('📥 Export to Excel'):
            export_data = []
            for session in sorted(st.session_state.sessions, key=lambda x: x['time']):
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
                file_name=f'schedule_{st.session_state.schedule_date.strftime("%Y%m%d")}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

st.markdown('---')
st.caption('🏄 Daily Schedule Builder | Head Coach Edition | v3.0')
