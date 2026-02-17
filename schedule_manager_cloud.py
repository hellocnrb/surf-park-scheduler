"""
Surf Park Schedule Manager - Cloud Edition
Web-based with Google Sheets integration for multi-user access
Optimized for mobile and desktop
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from collections import defaultdict
import yaml
import io
import json
from google.oauth2.service_account import Credentials
import gspread

from coaching_rules_engine import CoachingRulesEngine

# Mobile-optimized page config
st.set_page_config(
    page_title="Surf Schedule",
    page_icon="🏄",
    layout="wide",
    initial_sidebar_state="collapsed",  # Better for mobile
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Surf Park Schedule Manager"
    }
)

# Mobile-friendly CSS
st.markdown("""
<style>
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.5rem !important;
        }
        .stButton>button {
            width: 100%;
            padding: 0.75rem;
            font-size: 1rem;
        }
        .stSelectbox {
            font-size: 1rem;
        }
    }
    
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .session-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    
    .left-side {
        background-color: #8B4513;
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    .right-side {
        background-color: #2F4F4F;
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    .stButton>button {
        border-radius: 0.5rem;
        font-weight: 600;
    }
    
    /* Larger touch targets for mobile */
    .stSelectbox [data-baseweb="select"] {
        min-height: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# Google Sheets Configuration
def get_google_sheets_client():
    """Initialize Google Sheets client"""
    try:
        # Try to get credentials from Streamlit secrets (for deployment)
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
    except:
        # Fall back to local file for development
        try:
            creds = Credentials.from_service_account_file(
                'google_credentials.json',
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
        except:
            st.error("⚠️ Google Sheets credentials not found. See setup instructions.")
            return None
    
    return gspread.authorize(creds)

def load_weekly_schedule_from_sheets(gc, sheet_id):
    """Load weekly schedule from Google Sheets"""
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        data = sheet.get_all_values()
        
        if len(data) < 2:
            return {}
        
        # Parse header row for dates
        dates = []
        for col in data[0][1:]:
            try:
                dates.append(datetime.strptime(col, '%Y-%m-%d').date())
            except:
                continue
        
        # Parse coach rows
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
    """Save weekly schedule to Google Sheets"""
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        
        # Build data
        dates = [week_start + timedelta(days=i) for i in range(7)]
        header = ['Coach'] + [d.strftime('%Y-%m-%d') for d in dates]
        
        rows = [header]
        for coach in sorted(schedule.keys()):
            row = [coach]
            for d in dates:
                row.append(schedule[coach].get(d, 'available'))
            rows.append(row)
        
        # Clear and update
        sheet.clear()
        sheet.update('A1', rows)
        return True
    except Exception as e:
        st.error(f"Error saving schedule: {e}")
        return False

def load_coach_assignments_from_sheets(gc, sheet_id):
    """Load coach assignments from Google Sheets"""
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        data = sheet.get_all_values()
        
        if len(data) < 2:
            return {}
        
        assignments = {}
        for row in data[1:]:  # Skip header
            if len(row) >= 4:
                try:
                    dt = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                    side = row[1]
                    role = row[2]
                    coach = row[3]
                    assignments[(dt, side, role)] = coach
                except:
                    continue
        
        return assignments
    except Exception as e:
        st.error(f"Error loading assignments: {e}")
        return {}

def save_coach_assignments_to_sheets(gc, sheet_id, assignments):
    """Save coach assignments to Google Sheets"""
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        
        rows = [['DateTime', 'Side', 'Role', 'Coach']]
        for (dt, side, role), coach in assignments.items():
            rows.append([
                dt.strftime('%Y-%m-%d %H:%M:%S'),
                side,
                role,
                coach
            ])
        
        sheet.clear()
        sheet.update('A1', rows)
        return True
    except Exception as e:
        st.error(f"Error saving assignments: {e}")
        return False

def load_coach_roster_from_sheets(gc, sheet_id):
    """Load coach roster from Google Sheets"""
    try:
        sheet = gc.open_by_key(sheet_id).sheet1
        data = sheet.get_all_values()
        return [row[0] for row in data[1:] if row and row[0]]  # Skip header
    except:
        return ['Conner', 'Jake B', 'Kai', 'Brady', 'Jack', 'Laird']

def save_coach_roster_to_sheets(gc, sheet_id, roster):
    """Save coach roster to Google Sheets"""
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
    """Load coaching rules engine"""
    with open('coaching_rules.yaml') as f:
        return CoachingRulesEngine(yaml.safe_load(f))

def process_csv(f):
    """Process uploaded sessions CSV"""
    df = pd.read_csv(f)
    return [{
        'datetime_start': pd.to_datetime(r['datetime_start']),
        'side': r['side'],
        'session_type': r['session_type'],
        'booked_guests': int(r['booked_guests']),
        'private_lessons_count': int(r.get('private_lessons_count', 0))
    } for _, r in df.iterrows()]

# Initialize Google Sheets client
gc = get_google_sheets_client()

# Initialize session state
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

# Try to get sheet IDs from secrets or use defaults
try:
    WEEKLY_SHEET_ID = st.secrets.get("weekly_schedule_sheet_id", "")
    ASSIGNMENTS_SHEET_ID = st.secrets.get("assignments_sheet_id", "")
    ROSTER_SHEET_ID = st.secrets.get("roster_sheet_id", "")
except:
    WEEKLY_SHEET_ID = ""
    ASSIGNMENTS_SHEET_ID = ""
    ROSTER_SHEET_ID = ""

# Header
st.markdown('<div class="main-header">🏄 Surf Park Scheduler</div>', unsafe_allow_html=True)

# Sync status
col1, col2 = st.columns([3, 1])
with col1:
    if st.session_state.last_sync:
        st.caption(f"📡 Last synced: {st.session_state.last_sync.strftime('%I:%M %p')}")
    else:
        st.caption("📡 Not synced yet")
with col2:
    if st.button("🔄 Sync", use_container_width=True):
        if gc and WEEKLY_SHEET_ID and ASSIGNMENTS_SHEET_ID and ROSTER_SHEET_ID:
            with st.spinner("Syncing..."):
                st.session_state.weekly_schedule = load_weekly_schedule_from_sheets(gc, WEEKLY_SHEET_ID)
                st.session_state.coach_assignments = load_coach_assignments_from_sheets(gc, ASSIGNMENTS_SHEET_ID)
                st.session_state.coach_roster = load_coach_roster_from_sheets(gc, ROSTER_SHEET_ID)
                st.session_state.last_sync = datetime.now()
            st.success("✅ Synced!")
            st.rerun()

# Sidebar
with st.sidebar:
    st.header('📁 Upload Sessions')
    
    up = st.file_uploader('Sessions CSV', type=['csv'])
    if up:
        eng = load_engine()
        proc, _ = eng.process_csv_data(process_csv(up))
        if proc:
            st.session_state.processed_sessions = proc
            st.success(f'✅ {len(proc)} sessions')
    
    if st.button('📊 Load Sample', use_container_width=True):
        try:
            eng = load_engine()
            proc, _ = eng.process_csv_data(process_csv(open('sample_sessions.csv', 'rb')))
            st.session_state.processed_sessions = proc
            st.success('✅ Sample loaded')
        except:
            st.error('Sample file not found')

# Main tabs
tab1, tab2, tab3 = st.tabs(['📅 Weekly', '📋 Daily', '📊 Stats'])

with tab1:
    st.header('📅 Weekly Schedule')
    
    # Coach management
    with st.expander("👥 Manage Coaches", expanded=False):
        new_coach = st.text_input('Add New Coach')
        if st.button('➕ Add Coach', use_container_width=True) and new_coach:
            if new_coach not in st.session_state.coach_roster:
                st.session_state.coach_roster.append(new_coach)
                if gc and ROSTER_SHEET_ID:
                    save_coach_roster_to_sheets(gc, ROSTER_SHEET_ID, st.session_state.coach_roster)
                st.success(f'Added {new_coach}')
                st.rerun()
        
        if st.session_state.coach_roster:
            st.info(f'📋 {", ".join(st.session_state.coach_roster)}')
    
    # Week selector
    ws = st.date_input('Week Starting', value=date.today())
    dates = [ws + timedelta(days=i) for i in range(7)]
    
    st.caption('💡 Enter time ranges (e.g., "9-5"), "off", or "available"')
    
    # Build schedule table
    data = []
    for coach in st.session_state.coach_roster:
        row = {'Coach': coach}
        for d in dates:
            row[d.strftime('%a %m/%d')] = st.session_state.weekly_schedule.get(coach, {}).get(d, 'available')
        data.append(row)
    
    df = pd.DataFrame(data)
    edited = st.data_editor(
        df,
        use_container_width=True,
        num_rows='fixed',
        hide_index=True
    )
    
    # Save buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button('💾 Save to Cloud', type='primary', use_container_width=True):
            # Update local state
            for _, row in edited.iterrows():
                coach = row['Coach']
                if coach not in st.session_state.weekly_schedule:
                    st.session_state.weekly_schedule[coach] = {}
                for d in dates:
                    st.session_state.weekly_schedule[coach][d] = row[d.strftime('%a %m/%d')]
            
            # Save to Google Sheets
            if gc and WEEKLY_SHEET_ID:
                if save_weekly_schedule_to_sheets(gc, WEEKLY_SHEET_ID, st.session_state.weekly_schedule, ws):
                    st.success('✅ Saved to cloud!')
                    st.session_state.last_sync = datetime.now()
            else:
                st.warning('⚠️ Google Sheets not configured')
    
    with col2:
        if st.button('📥 Export Excel', use_container_width=True):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                edited.to_excel(writer, sheet_name='Weekly', index=False)
            output.seek(0)
            st.download_button(
                'Download',
                output,
                file_name=f'weekly_{ws.strftime("%Y%m%d")}.xlsx',
                use_container_width=True
            )

with tab2:
    st.header('📋 Daily Assignments')
    
    if not st.session_state.processed_sessions:
        st.info('👈 Upload sessions CSV or load sample data')
    else:
        sess = st.session_state.processed_sessions
        dates_avail = sorted(set(s.datetime_start.date() for s in sess))
        
        # Date selector
        sel_date = st.selectbox(
            'Select Date',
            dates_avail,
            format_func=lambda d: d.strftime('%A, %B %d, %Y')
        )
        
        # Staff summary
        with st.expander("👥 Staff Working Today", expanded=True):
            staff = []
            for coach, schedule in st.session_state.weekly_schedule.items():
                if sel_date in schedule and schedule[sel_date] != 'off':
                    staff.append({'Staff': coach, 'Hours': schedule[sel_date]})
            
            if staff:
                st.table(pd.DataFrame(staff))
            else:
                st.info('Set availability in Weekly tab')
        
        # Sessions
        day_sess = [s for s in sess if s.datetime_start.date() == sel_date]
        by_hour = defaultdict(list)
        for s in day_sess:
            by_hour[s.datetime_start.hour].append(s)
        
        for hour in sorted(by_hour.keys()):
            main = by_hour[hour][0]
            time_str = main.datetime_start.strftime('%I:%M%p').lower()
            
            st.markdown(f"### {time_str} - {main.session_type}")
            
            # Mobile-friendly: stack on small screens
            for s in by_hour[hour]:
                with st.container():
                    st.markdown(f"""
                    <div class='{"left-side" if s.side == "LEFT" else "right-side"}'>
                        <strong>{s.side}</strong> - {s.booked_guests} guests
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Roles
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
                            
                            new = st.selectbox(
                                role,
                                opts,
                                index=idx,
                                key=f'{hour}_{s.side}_{role}'
                            )
                            
                            if new != '-- Unassigned --':
                                st.session_state.coach_assignments[key] = new
                            elif key in st.session_state.coach_assignments:
                                del st.session_state.coach_assignments[key]
                    else:
                        st.caption('*No coaches needed*')
            
            st.markdown('---')
        
        # Save assignments
        col1, col2 = st.columns(2)
        with col1:
            if st.button('💾 Save Assignments', type='primary', use_container_width=True):
                if gc and ASSIGNMENTS_SHEET_ID:
                    if save_coach_assignments_to_sheets(gc, ASSIGNMENTS_SHEET_ID, st.session_state.coach_assignments):
                        st.success('✅ Saved to cloud!')
                        st.session_state.last_sync = datetime.now()
                else:
                    st.warning('⚠️ Google Sheets not configured')
        
        with col2:
            if st.button('📥 Export Daily', use_container_width=True):
                export_data = []
                for hour in sorted(by_hour.keys()):
                    for s in by_hour[hour]:
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
                        
                        for role in roles:
                            key = (s.datetime_start, s.side, role)
                            export_data.append({
                                'Time': s.datetime_start.strftime('%I:%M %p'),
                                'Session': s.session_type,
                                'Side': s.side,
                                'Role': role,
                                'Coach': st.session_state.coach_assignments.get(key, 'UNASSIGNED')
                            })
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    pd.DataFrame(export_data).to_excel(writer, sheet_name='Daily', index=False)
                output.seek(0)
                st.download_button(
                    'Download Excel',
                    output,
                    file_name=f'daily_{sel_date.strftime("%Y%m%d")}.xlsx',
                    use_container_width=True
                )

with tab3:
    st.header('📊 Statistics')
    
    if st.session_state.processed_sessions:
        sess = st.session_state.processed_sessions
        
        col1, col2, col3 = st.columns(3)
        col1.metric('Sessions', len(sess))
        col2.metric('Coach-Hours', sum(s.total_coaches_required for s in sess))
        col3.metric('w/ Coaches', sum(1 for s in sess if not s.is_no_coach_required))
        
        # Simplified heatmap for mobile
        st.subheader('📈 Demand Overview')
        hdata = defaultdict(lambda: defaultdict(int))
        for s in sess:
            hdata[s.datetime_start.date()][s.datetime_start.hour] += s.total_coaches_required
        
        dates_h = sorted(hdata.keys())
        hours = list(range(6, 20))  # Focus on operating hours
        matrix = [[hdata[d].get(h, 0) for d in dates_h] for h in hours]
        df_heat = pd.DataFrame(
            matrix,
            index=[f'{h:02d}:00' for h in hours],
            columns=[d.strftime('%m/%d') for d in dates_h]
        )
        
        fig = px.imshow(
            df_heat,
            labels=dict(x='Date', y='Hour', color='Coaches'),
            color_continuous_scale='YlOrRd',
            aspect='auto'
        )
        fig.update_layout(height=400)  # Smaller for mobile
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('Upload sessions to see stats')

# Footer
st.markdown('---')
st.caption('🏄 Surf Park Schedule Manager | Cloud Edition')