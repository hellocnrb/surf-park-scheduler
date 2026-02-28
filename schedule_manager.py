import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from collections import defaultdict
import yaml, io, pickle
from coaching_rules_engine import CoachingRulesEngine

st.set_page_config(page_title="Schedule Manager", page_icon="🏄", layout="wide")

def load_engine():
    with open('coaching_rules.yaml') as f:
        return CoachingRulesEngine(yaml.safe_load(f))

def process_csv(f):
    df = pd.read_csv(f)
    return [{'datetime_start': pd.to_datetime(r['datetime_start']), 'side': r['side'], 
             'session_type': r['session_type'], 'booked_guests': int(r['booked_guests']),
             'private_lessons_count': int(r.get('private_lessons_count', 0))} for _, r in df.iterrows()]

def save_assigns(a):
    try:
        with open('assigns.pkl','wb') as f:
            pickle.dump(a,f)
        return True
    except:
        return False

def load_assigns():
    try:
        with open('assigns.pkl','rb') as f:
            return pickle.load(f)
    except:
        return {}

# Init
if 'processed_sessions' not in st.session_state:
    st.session_state.processed_sessions = None
if 'weekly_schedule' not in st.session_state:
    st.session_state.weekly_schedule = {}
if 'coach_assignments' not in st.session_state:
    st.session_state.coach_assignments = load_assigns()
if 'coach_roster' not in st.session_state:
    st.session_state.coach_roster = ['Conner', 'Jake B', 'Kai', 'Brady', 'Jack', 'Laird']

# Auto-populate schedule
if not st.session_state.weekly_schedule:
    today = date.today()
    for i in range(-7, 30):
        d = today + timedelta(days=i)
        for coach in st.session_state.coach_roster:
            if coach not in st.session_state.weekly_schedule:
                st.session_state.weekly_schedule[coach] = {}
            st.session_state.weekly_schedule[coach][d] = 'available'

# Sidebar
with st.sidebar:
    st.header('📁 Data')
    
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
            proc, _ = eng.process_csv_data(process_csv(open('sample_sessions.csv','rb')))
            st.session_state.processed_sessions = proc
            st.success('✅ Loaded')
        except:
            st.error('Sample not found')
    
    st.markdown('---')
    st.subheader('💾 Assignments')
    col1, col2 = st.columns(2)
    with col1:
        if st.button('💾 Save'):
            if save_assigns(st.session_state.coach_assignments):
                st.success('Saved!')
    with col2:
        if st.button('📂 Load'):
            st.session_state.coach_assignments = load_assigns()
            st.success('Loaded!')
            st.rerun()

# Main
st.markdown('<h1 style="text-align:center;color:#1f77b4">🏄 Surf Park Schedule Manager</h1>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(['📅 Weekly Schedule', '📋 Daily Assignments', '📊 Analysis'])

with tab1:
    st.header('📅 Weekly Schedule')
    
    col1, col2 = st.columns([3, 1])
    with col1:
        new_coach = st.text_input('Add Coach')
    with col2:
        if st.button('➕ Add') and new_coach:
            if new_coach not in st.session_state.coach_roster:
                st.session_state.coach_roster.append(new_coach)
                for i in range(-7, 30):
                    d = date.today() + timedelta(days=i)
                    if new_coach not in st.session_state.weekly_schedule:
                        st.session_state.weekly_schedule[new_coach] = {}
                    st.session_state.weekly_schedule[new_coach][d] = 'available'
                st.success(f'Added {new_coach}')
                st.rerun()
    
    if st.session_state.coach_roster:
        st.info(f'📋 Roster: {", ".join(st.session_state.coach_roster)}')
    
    ws = st.date_input('Week Starting', value=date.today())
    dates = [ws + timedelta(days=i) for i in range(7)]
    
    st.subheader('⏰ Schedule')
    st.caption('Enter time ranges (e.g., "7-3", "9-5"), "off" for days off, or "available"')
    
    data = []
    for coach in st.session_state.coach_roster:
        row = {'Coach': coach}
        for d in dates:
            row[d.strftime('%a %m/%d')] = st.session_state.weekly_schedule.get(coach, {}).get(d, 'available')
        data.append(row)
    
    df = pd.DataFrame(data)
    edited = st.data_editor(df, use_container_width=True, num_rows='fixed')
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button('💾 Save Schedule', type='primary'):
            for _, row in edited.iterrows():
                coach = row['Coach']
                for d in dates:
                    st.session_state.weekly_schedule[coach][d] = row[d.strftime('%a %m/%d')]
            st.success('✅ Saved!')
    
    with col2:
        if st.button('📥 Export Weekly'):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                edited.to_excel(writer, sheet_name='Weekly', index=False)
            output.seek(0)
            st.download_button('Download', output, file_name=f'weekly_{ws.strftime("%Y%m%d")}.xlsx')

with tab2:
    st.header('📋 Daily Schedule & Coach Assignments')
    
    if not st.session_state.processed_sessions:
        st.info('👈 Click "Load Sample" in sidebar to get started')
    else:
        sess = st.session_state.processed_sessions
        dates_avail = sorted(set(s.datetime_start.date() for s in sess))
        
        sel_date = st.selectbox('Select Date', dates_avail, format_func=lambda d: d.strftime('%A, %B %d, %Y'))
        
        # Staff summary
        st.subheader('👥 Staff Working Today')
        staff = []
        for coach, schedule in st.session_state.weekly_schedule.items():
            if sel_date in schedule and schedule[sel_date] != 'off':
                staff.append({'Staff': coach, 'Hours': schedule[sel_date]})
        
        if staff:
            st.table(pd.DataFrame(staff))
        else:
            st.info('Set coach availability in Weekly Schedule tab')
        
        st.markdown('---')
        st.subheader('🏄 Sessions')
        
        day_sess = [s for s in sess if s.datetime_start.date() == sel_date]
        by_hour = defaultdict(list)
        for s in day_sess:
            by_hour[s.datetime_start.hour].append(s)
        
        for hour in sorted(by_hour.keys()):
            main = by_hour[hour][0]
            time_str = main.datetime_start.strftime('%I:%M%p').lower()
            end_str = (main.datetime_start + timedelta(hours=1)).strftime('%I:%M%p').lower()
            
            st.markdown(f"### {time_str}-{end_str} {main.session_type}")
            
            total_guests = sum(s.booked_guests for s in by_hour[hour])
            st.write(f"*Total Guests: {total_guests}*")
            
            c_left, c_right = st.columns(2)
            for s in by_hour[hour]:
                col = c_left if s.side == 'LEFT' else c_right
                with col:
                    st.markdown(f"""
                    <div style='background-color: {"#8B4513" if s.side == "LEFT" else "#2F4F4F"}; 
                                color: white; padding: 0.8rem; border-radius: 0.5rem; margin-bottom: 0.5rem;'>
                        <strong>{s.side} ({s.booked_guests} guests)</strong>
                    </div>
                    """, unsafe_allow_html=True)
                    
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
                            opts = ['-- No Coach Assigned --'] + st.session_state.coach_roster
                            idx = opts.index(assigned) if assigned in st.session_state.coach_roster else 0
                            
                            new = st.selectbox(role, opts, index=idx, key=f'{hour}_{s.side}_{role}')
                            if new != '-- No Coach Assigned --':
                                st.session_state.coach_assignments[key] = new
                            elif key in st.session_state.coach_assignments:
                                del st.session_state.coach_assignments[key]
                    else:
                        st.write('*No coaches required*')
            
            st.markdown('---')
        
        # Export
        if st.button('📥 Export Daily Schedule', type='primary'):
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
                    
                    if not roles:
                        export_data.append({
                            'Time': s.datetime_start.strftime('%I:%M %p'),
                            'Session': s.session_type,
                            'Side': s.side,
                            'Guests': s.booked_guests,
                            'Role': 'N/A',
                            'Coach': 'No coaches required'
                        })
                    else:
                        for role in roles:
                            key = (s.datetime_start, s.side, role)
                            export_data.append({
                                'Time': s.datetime_start.strftime('%I:%M %p'),
                                'Session': s.session_type,
                                'Side': s.side,
                                'Guests': s.booked_guests,
                                'Role': role,
                                'Coach': st.session_state.coach_assignments.get(key, 'UNASSIGNED')
                            })
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                pd.DataFrame(export_data).to_excel(writer, sheet_name='Daily Schedule', index=False)
            output.seek(0)
            st.download_button('📥 Download', output, file_name=f'daily_{sel_date.strftime("%Y%m%d")}.xlsx')

with tab3:
    st.header('📊 Requirements Analysis')
    
    if st.session_state.processed_sessions:
        sess = st.session_state.processed_sessions
        
        col1, col2, col3 = st.columns(3)
        col1.metric('Total Sessions', len(sess))
        col2.metric('Total Coach-Hours', sum(s.total_coaches_required for s in sess))
        col3.metric('Sessions Needing Coaches', sum(1 for s in sess if not s.is_no_coach_required))
        
        st.subheader('📈 Demand Heatmap')
        hdata = defaultdict(lambda: defaultdict(int))
        for s in sess:
            hdata[s.datetime_start.date()][s.datetime_start.hour] += s.total_coaches_required
        
        dates_h = sorted(hdata.keys())
        hours = list(range(24))
        matrix = [[hdata[d].get(h, 0) for d in dates_h] for h in hours]
        df_heat = pd.DataFrame(matrix, index=[f'{h:02d}:00' for h in hours], columns=[d.strftime('%m-%d') for d in dates_h])
        
        fig = px.imshow(df_heat, labels=dict(x='Date', y='Hour', color='Coaches'), color_continuous_scale='YlOrRd', aspect='auto')
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('Upload sessions to see analysis')
