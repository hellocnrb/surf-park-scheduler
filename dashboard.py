"""
Surf Park Coaching Requirements Dashboard
Interactive Streamlit web application
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, time
from collections import defaultdict
import yaml
import io

from coaching_rules_engine import CoachingRulesEngine, Session

# Page config
st.set_page_config(
    page_title="Surf Park Coaching Dashboard",
    page_icon="🏄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .peak-hour {
        background-color: #ff7f0e;
        color: white;
        font-weight: bold;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'sessions' not in st.session_state:
    st.session_state.sessions = None
if 'processed_sessions' not in st.session_state:
    st.session_state.processed_sessions = None

def load_engine():
    """Load the rules engine with configuration"""
    try:
        with open('coaching_rules.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return CoachingRulesEngine(config)
    except FileNotFoundError:
        st.error("⚠️ coaching_rules.yaml not found. Please ensure it's in the same directory.")
        st.stop()

def process_uploaded_csv(uploaded_file):
    """Process uploaded CSV file"""
    try:
        # Read CSV
        df = pd.read_csv(uploaded_file)
        
        # Convert to required format
        sessions_data = []
        for _, row in df.iterrows():
            sessions_data.append({
                'datetime_start': pd.to_datetime(row['datetime_start']),
                'side': row['side'],
                'session_type': row['session_type'],
                'booked_guests': int(row['booked_guests']),
                'private_lessons_count': int(row.get('private_lessons_count', 0))
            })
        
        return sessions_data
    except Exception as e:
        st.error(f"❌ Error reading CSV: {e}")
        return None

def create_hourly_heatmap(processed_sessions):
    """Create interactive heatmap of coaching requirements"""
    # Aggregate by date and hour
    heatmap_data = defaultdict(lambda: defaultdict(int))
    
    for session in processed_sessions:
        date = session.datetime_start.date()
        hour = session.datetime_start.hour
        heatmap_data[date][hour] += session.total_coaches_required
    
    # Convert to DataFrame
    dates = sorted(heatmap_data.keys())
    hours = list(range(24))
    
    matrix = []
    for hour in hours:
        row = []
        for date in dates:
            row.append(heatmap_data[date].get(hour, 0))
        matrix.append(row)
    
    df_heatmap = pd.DataFrame(
        matrix,
        index=[f"{h:02d}:00" for h in hours],
        columns=[d.strftime('%Y-%m-%d') for d in dates]
    )
    
    # Create heatmap
    fig = px.imshow(
        df_heatmap,
        labels=dict(x="Date", y="Hour", color="Coaches Required"),
        color_continuous_scale="YlOrRd",
        aspect="auto"
    )
    
    fig.update_layout(
        title="Coaching Demand Heatmap",
        height=600,
        xaxis_title="Date",
        yaxis_title="Hour of Day"
    )
    
    return fig

def create_daily_breakdown(processed_sessions):
    """Create daily breakdown chart"""
    daily_totals = defaultdict(int)
    
    for session in processed_sessions:
        date = session.datetime_start.date()
        daily_totals[date] += session.total_coaches_required
    
    dates = sorted(daily_totals.keys())
    totals = [daily_totals[d] for d in dates]
    
    fig = go.Figure(data=[
        go.Bar(
            x=[d.strftime('%Y-%m-%d') for d in dates],
            y=totals,
            marker_color='#1f77b4',
            text=totals,
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title="Total Coach-Hours by Day",
        xaxis_title="Date",
        yaxis_title="Total Coach-Hours",
        height=400,
        showlegend=False
    )
    
    return fig

def create_session_type_breakdown(processed_sessions):
    """Create session type breakdown pie chart"""
    type_totals = defaultdict(int)
    
    for session in processed_sessions:
        type_totals[session.session_type] += session.total_coaches_required
    
    # Remove zero values
    type_totals = {k: v for k, v in type_totals.items() if v > 0}
    
    fig = go.Figure(data=[go.Pie(
        labels=list(type_totals.keys()),
        values=list(type_totals.values()),
        hole=0.3
    )])
    
    fig.update_layout(
        title="Coach-Hours by Session Type",
        height=400
    )
    
    return fig

def create_hourly_chart(processed_sessions, selected_date):
    """Create hourly breakdown for specific date"""
    # Filter by date
    date_sessions = [s for s in processed_sessions 
                     if s.datetime_start.date() == selected_date]
    
    # Aggregate by hour and side
    hourly_data = defaultdict(lambda: {'LEFT': 0, 'RIGHT': 0})
    
    for session in date_sessions:
        hour = session.datetime_start.hour
        hourly_data[hour][session.side] += session.total_coaches_required
    
    hours = sorted(hourly_data.keys())
    left_coaches = [hourly_data[h]['LEFT'] for h in hours]
    right_coaches = [hourly_data[h]['RIGHT'] for h in hours]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Left Side',
        x=[f"{h:02d}:00" for h in hours],
        y=left_coaches,
        marker_color='#1f77b4'
    ))
    
    fig.add_trace(go.Bar(
        name='Right Side',
        x=[f"{h:02d}:00" for h in hours],
        y=right_coaches,
        marker_color='#ff7f0e'
    ))
    
    fig.update_layout(
        title=f"Hourly Breakdown - {selected_date}",
        xaxis_title="Hour",
        yaxis_title="Coaches Required",
        barmode='stack',
        height=400
    )
    
    return fig

def generate_excel_report(processed_sessions):
    """Generate Excel report with multiple sheets"""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Daily requirements sheet
        daily_data = []
        hourly_data = defaultdict(lambda: {'left': None, 'right': None})
        
        for session in processed_sessions:
            hourly_data[session.datetime_start][session.side.lower()] = session
        
        for dt in sorted(hourly_data.keys()):
            sides = hourly_data[dt]
            left = sides['left']
            right = sides['right']
            
            daily_data.append({
                'Date': dt.date(),
                'Time': dt.strftime('%H:%M'),
                'Left Coaches': left.total_coaches_required if left else 0,
                'Left Baseline': left.baseline_coaches if left else 0,
                'Left Private': left.private_coaches if left else 0,
                'Right Coaches': right.total_coaches_required if right else 0,
                'Right Baseline': right.baseline_coaches if right else 0,
                'Right Private': right.private_coaches if right else 0,
                'Hourly Total': (left.total_coaches_required if left else 0) + 
                               (right.total_coaches_required if right else 0)
            })
        
        df_daily = pd.DataFrame(daily_data)
        df_daily.to_excel(writer, sheet_name='Daily Requirements', index=False)
        
        # Session details sheet
        session_data = []
        for session in processed_sessions:
            session_data.append({
                'Date': session.datetime_start.date(),
                'Time': session.datetime_start.strftime('%H:%M'),
                'Side': session.side,
                'Session Type': session.session_type,
                'Booked Guests': session.booked_guests,
                'Private Lessons': session.private_lessons_count,
                'Baseline Coaches': session.baseline_coaches,
                'Private Coaches': session.private_coaches,
                'Total Coaches': session.total_coaches_required,
                'Coach Start Time': session.coach_start_time.strftime('%H:%M'),
                'No Coach Required': session.is_no_coach_required
            })
        
        df_sessions = pd.DataFrame(session_data)
        df_sessions.to_excel(writer, sheet_name='Session Details', index=False)
        
        # Summary sheet
        summary_data = {
            'Metric': [
                'Total Sessions',
                'Sessions Needing Coaches',
                'Total Coach-Hours',
                'Date Range Start',
                'Date Range End',
                'Average Coaches per Hour'
            ],
            'Value': [
                len(processed_sessions),
                sum(1 for s in processed_sessions if not s.is_no_coach_required),
                sum(s.total_coaches_required for s in processed_sessions),
                min(s.datetime_start for s in processed_sessions).date(),
                max(s.datetime_start for s in processed_sessions).date(),
                round(sum(s.total_coaches_required for s in processed_sessions) / len(processed_sessions), 2)
            ]
        }
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
    
    output.seek(0)
    return output

# Main app
def main():
    st.markdown('<div class="main-header">🏄 Surf Park Coaching Dashboard</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Data Upload")
        
        uploaded_file = st.file_uploader(
            "Upload Sessions CSV",
            type=['csv'],
            help="Upload a CSV file with columns: datetime_start, side, session_type, booked_guests, private_lessons_count"
        )
        
        if uploaded_file is not None:
            with st.spinner("Processing sessions..."):
                sessions_data = process_uploaded_csv(uploaded_file)
                
                if sessions_data:
                    engine = load_engine()
                    processed, errors = engine.process_csv_data(sessions_data)
                    
                    if errors:
                        st.warning(f"⚠️ {len(errors)} validation errors")
                        with st.expander("View errors"):
                            for error in errors:
                                st.error(error)
                    
                    if processed:
                        st.session_state.processed_sessions = processed
                        st.success(f"✅ Processed {len(processed)} sessions")
                    else:
                        st.error("❌ No valid sessions to process")
        
        st.markdown("---")
        
        # Sample data option
        if st.button("📊 Load Sample Data"):
            with st.spinner("Loading sample data..."):
                try:
                    sessions_data = process_uploaded_csv(open('sample_sessions.csv', 'rb'))
                    if sessions_data:
                        engine = load_engine()
                        processed, _ = engine.process_csv_data(sessions_data)
                        st.session_state.processed_sessions = processed
                        st.success(f"✅ Loaded {len(processed)} sample sessions")
                except:
                    st.error("❌ sample_sessions.csv not found")
        
        st.markdown("---")
        st.markdown("### ⚙️ About")
        st.info("Upload your sessions CSV to visualize coaching requirements and download reports.")
    
    # Main content
    if st.session_state.processed_sessions:
        sessions = st.session_state.processed_sessions
        
        # Summary metrics
        st.header("📊 Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_sessions = len(sessions)
        total_coaches = sum(s.total_coaches_required for s in sessions)
        sessions_with_coaches = sum(1 for s in sessions if not s.is_no_coach_required)
        avg_coaches = total_coaches / len(sessions) if sessions else 0
        
        with col1:
            st.metric("Total Sessions", total_sessions)
        with col2:
            st.metric("Total Coach-Hours", total_coaches)
        with col3:
            st.metric("Sessions Needing Coaches", sessions_with_coaches)
        with col4:
            st.metric("Avg Coaches/Hour", f"{avg_coaches:.1f}")
        
        # Date range
        dates = [s.datetime_start.date() for s in sessions]
        date_range = f"{min(dates)} to {max(dates)}"
        st.info(f"📅 Date Range: {date_range}")
        
        # Peak hours
        hourly_totals = defaultdict(int)
        for s in sessions:
            hourly_totals[s.datetime_start] += s.total_coaches_required
        
        peak_hours = sorted(hourly_totals.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_hours = [(dt, total) for dt, total in peak_hours if total > 0]
        
        if peak_hours:
            st.subheader("🔥 Peak Hours")
            cols = st.columns(len(peak_hours))
            for i, (dt, total) in enumerate(peak_hours):
                with cols[i]:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 1.2rem; font-weight: bold;">{dt.strftime('%Y-%m-%d %H:%M')}</div>
                        <div style="font-size: 2rem; color: #ff7f0e;">{total} coaches</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Visualizations
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Heatmap", "📊 Charts", "📋 Data Table", "📥 Export"])
        
        with tab1:
            st.plotly_chart(create_hourly_heatmap(sessions), use_container_width=True)
        
        with tab2:
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(create_daily_breakdown(sessions), use_container_width=True)
            
            with col2:
                st.plotly_chart(create_session_type_breakdown(sessions), use_container_width=True)
            
            # Hourly breakdown for selected date
            st.subheader("Hourly Breakdown by Date")
            unique_dates = sorted(set(s.datetime_start.date() for s in sessions))
            selected_date = st.selectbox("Select Date", unique_dates)
            
            st.plotly_chart(create_hourly_chart(sessions, selected_date), use_container_width=True)
        
        with tab3:
            st.subheader("Session Details")
            
            # Create DataFrame
            session_data = []
            for s in sessions:
                session_data.append({
                    'Date': s.datetime_start.date(),
                    'Time': s.datetime_start.strftime('%H:%M'),
                    'Side': s.side,
                    'Type': s.session_type,
                    'Guests': s.booked_guests,
                    'Private': s.private_lessons_count,
                    'Baseline': s.baseline_coaches,
                    'Private Coaches': s.private_coaches,
                    'Total': s.total_coaches_required,
                    'No Coach Req': '✓' if s.is_no_coach_required else ''
                })
            
            df = pd.DataFrame(session_data)
            
            # Filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filter_date = st.multiselect("Filter by Date", df['Date'].unique())
            with col2:
                filter_side = st.multiselect("Filter by Side", df['Side'].unique())
            with col3:
                filter_type = st.multiselect("Filter by Type", df['Type'].unique())
            
            # Apply filters
            if filter_date:
                df = df[df['Date'].isin(filter_date)]
            if filter_side:
                df = df[df['Side'].isin(filter_side)]
            if filter_type:
                df = df[df['Type'].isin(filter_type)]
            
            # Display table
            st.dataframe(df, use_container_width=True, height=400)
            
            # Summary stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Filtered Sessions", len(df))
            with col2:
                st.metric("Total Coaches", df['Total'].sum())
            with col3:
                st.metric("Avg Coaches", f"{df['Total'].mean():.1f}")
        
        with tab4:
            st.subheader("📥 Download Reports")
            
            st.markdown("""
            Download your coaching requirements in Excel format with multiple sheets:
            - **Daily Requirements**: Hour-by-hour breakdown
            - **Session Details**: Complete session information
            - **Summary**: Key metrics and totals
            """)
            
            if st.button("Generate Excel Report", type="primary"):
                with st.spinner("Generating report..."):
                    excel_file = generate_excel_report(sessions)
                    
                    st.download_button(
                        label="📥 Download Excel Report",
                        data=excel_file,
                        file_name=f"coaching_requirements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.success("✅ Report generated! Click button above to download.")
    
    else:
        # Welcome screen
        st.info("👈 Upload a sessions CSV file in the sidebar to get started, or load sample data.")
        
        st.markdown("""
        ### 📋 CSV Format Required
        
        Your CSV should have these columns:
        - `datetime_start` - Session start time (YYYY-MM-DD HH:MM:SS)
        - `side` - Either "LEFT" or "RIGHT"
        - `session_type` - Beginner, Novice, Progressive, Intermediate, Advanced, Expert, Pro, or Pro_Barrel
        - `booked_guests` - Number of guests (integer)
        - `private_lessons_count` - Number of private lessons (integer)
        
        ### 📊 Features
        
        - **Interactive Heatmap**: See demand patterns across days and hours
        - **Charts & Visualizations**: Daily totals, session type breakdown, hourly details
        - **Filterable Tables**: Drill down into specific dates, sides, or session types
        - **Excel Export**: Download formatted reports with multiple sheets
        - **Peak Hour Detection**: Automatically identify high-demand periods
        
        ### 🚀 Quick Start
        
        1. Click "Load Sample Data" to see the dashboard in action
        2. Upload your own CSV to analyze your real data
        3. Download Excel reports for scheduling
        """)

if __name__ == "__main__":
    main()
