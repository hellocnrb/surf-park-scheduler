#!/usr/bin/env python3
"""
Surf Park Coaching Requirements Calculator - CLI Tool
Process sessions CSV and generate coaching requirement reports
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple

from coaching_rules_engine import CoachingRulesEngine, Session
import yaml


def load_sessions_from_csv(csv_path: str) -> List[Dict]:
    """Load sessions from CSV file"""
    sessions = []
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sessions.append({
                'datetime_start': datetime.strptime(row['datetime_start'], '%Y-%m-%d %H:%M:%S'),
                'side': row['side'],
                'session_type': row['session_type'],
                'booked_guests': int(row['booked_guests']),
                'private_lessons_count': int(row.get('private_lessons_count', 0))
            })
    
    return sessions


def write_daily_requirements_csv(sessions: List[Session], output_path: str):
    """Write daily requirements to CSV"""
    
    # Group by datetime_start (hour)
    hourly_data = defaultdict(lambda: {'left': None, 'right': None})
    
    for session in sessions:
        hourly_data[session.datetime_start][session.side.lower()] = session
    
    # Write CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'datetime_start', 'hour', 
            'left_side_coaches', 'left_baseline', 'left_private',
            'right_side_coaches', 'right_baseline', 'right_private',
            'hourly_total',
            'left_no_coach_required', 'right_no_coach_required',
            'is_peak_hour'
        ])
        
        # Calculate hourly totals to identify peaks
        hourly_totals = {}
        for dt, sides in hourly_data.items():
            left = sides['left']
            right = sides['right']
            total = 0
            if left:
                total += left.total_coaches_required
            if right:
                total += right.total_coaches_required
            hourly_totals[dt] = total
        
        max_total = max(hourly_totals.values()) if hourly_totals else 0
        
        # Data rows
        for dt in sorted(hourly_data.keys()):
            sides = hourly_data[dt]
            left = sides['left']
            right = sides['right']
            
            left_coaches = left.total_coaches_required if left else 0
            left_baseline = left.baseline_coaches if left else 0
            left_private = left.private_coaches if left else 0
            left_no_coach = left.is_no_coach_required if left else True
            
            right_coaches = right.total_coaches_required if right else 0
            right_baseline = right.baseline_coaches if right else 0
            right_private = right.private_coaches if right else 0
            right_no_coach = right.is_no_coach_required if right else True
            
            total = left_coaches + right_coaches
            is_peak = (total == max_total and total > 0)
            
            writer.writerow([
                dt.strftime('%Y-%m-%d %H:%M:%S'),
                dt.hour,
                left_coaches, left_baseline, left_private,
                right_coaches, right_baseline, right_private,
                total,
                left_no_coach, right_no_coach,
                is_peak
            ])
    
    print(f"✅ Daily requirements written to: {output_path}")


def write_weekly_summary_csv(sessions: List[Session], output_path: str):
    """Write weekly summary aggregated by hour of day"""
    
    # Group by date and hour
    daily_hourly = defaultdict(lambda: defaultdict(int))
    
    for session in sessions:
        date = session.datetime_start.date()
        hour = session.datetime_start.hour
        daily_hourly[date][hour] += session.total_coaches_required
    
    # Get all unique hours
    all_hours = set()
    for hourly_data in daily_hourly.values():
        all_hours.update(hourly_data.keys())
    
    # Get all unique dates
    all_dates = sorted(daily_hourly.keys())
    
    # Write CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        date_headers = [d.strftime('%Y-%m-%d') for d in all_dates]
        writer.writerow(['hour'] + date_headers + ['weekly_total', 'avg_per_day'])
        
        # Data rows
        for hour in sorted(all_hours):
            row = [f"{hour:02d}:00"]
            
            weekly_total = 0
            for date in all_dates:
                coaches = daily_hourly[date][hour]
                row.append(coaches)
                weekly_total += coaches
            
            avg_per_day = weekly_total / len(all_dates) if all_dates else 0
            row.append(weekly_total)
            row.append(f"{avg_per_day:.1f}")
            
            writer.writerow(row)
    
    print(f"✅ Weekly summary written to: {output_path}")


def print_summary_report(sessions: List[Session]):
    """Print human-readable summary to console"""
    
    # Calculate totals
    total_sessions = len(sessions)
    total_coach_hours = sum(s.total_coaches_required for s in sessions)
    sessions_needing_coaches = sum(1 for s in sessions if not s.is_no_coach_required)
    
    # Group by date
    by_date = defaultdict(list)
    for session in sessions:
        by_date[session.datetime_start.date()].append(session)
    
    # Group by hour for peaks
    by_hour = defaultdict(list)
    for session in sessions:
        by_hour[session.datetime_start].append(session)
    
    hourly_totals = {}
    for dt, sessions_list in by_hour.items():
        total = sum(s.total_coaches_required for s in sessions_list)
        hourly_totals[dt] = total
    
    # Find peak hours
    peak_hours = sorted(hourly_totals.items(), key=lambda x: x[1], reverse=True)[:3]
    
    print("\n" + "=" * 80)
    print("📊 COACHING REQUIREMENTS SUMMARY")
    print("=" * 80)
    print(f"\n📅 Date Range: {min(by_date.keys())} to {max(by_date.keys())}")
    print(f"📈 Total Sessions: {total_sessions}")
    print(f"👥 Sessions Needing Coaches: {sessions_needing_coaches}")
    print(f"⏰ Total Coach-Hours Required: {total_coach_hours}")
    
    print(f"\n🔥 Peak Hours:")
    for dt, total in peak_hours:
        if total > 0:
            print(f"   {dt.strftime('%Y-%m-%d %H:%M')} - {total} coaches")
    
    print(f"\n📆 Daily Breakdown:")
    for date in sorted(by_date.keys()):
        day_sessions = by_date[date]
        day_total = sum(s.total_coaches_required for s in day_sessions)
        print(f"   {date}: {day_total} coach-hours across {len(day_sessions)} sessions")
    
    # Session type breakdown
    by_type = defaultdict(lambda: {'count': 0, 'coaches': 0})
    for session in sessions:
        by_type[session.session_type]['count'] += 1
        by_type[session.session_type]['coaches'] += session.total_coaches_required
    
    print(f"\n📋 By Session Type:")
    for session_type in sorted(by_type.keys()):
        data = by_type[session_type]
        avg = data['coaches'] / data['count'] if data['count'] > 0 else 0
        print(f"   {session_type:12} - {data['count']:2} sessions, "
              f"{data['coaches']:3} coaches (avg {avg:.1f} per session)")
    
    print("\n" + "=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Calculate coaching requirements from sessions CSV'
    )
    parser.add_argument(
        'input_csv',
        help='Input CSV file with session data'
    )
    parser.add_argument(
        '--config',
        default='coaching_rules.yaml',
        help='Configuration YAML file (default: coaching_rules.yaml)'
    )
    parser.add_argument(
        '--output-daily',
        default='coach_requirements_daily.csv',
        help='Output file for daily requirements (default: coach_requirements_daily.csv)'
    )
    parser.add_argument(
        '--output-weekly',
        default='coach_requirements_weekly.csv',
        help='Output file for weekly summary (default: coach_requirements_weekly.csv)'
    )
    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='Skip printing summary to console'
    )
    
    args = parser.parse_args()
    
    # Check input file exists
    if not Path(args.input_csv).exists():
        print(f"❌ Error: Input file not found: {args.input_csv}")
        sys.exit(1)
    
    # Check config file exists
    if not Path(args.config).exists():
        print(f"❌ Error: Config file not found: {args.config}")
        sys.exit(1)
    
    print(f"\n🏄 Austin Park Surf - Coaching Requirements Calculator")
    print(f"=" * 80)
    print(f"📂 Input: {args.input_csv}")
    print(f"⚙️  Config: {args.config}")
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize rules engine
    engine = CoachingRulesEngine(config)
    print(f"✅ Loaded configuration version {config['version']}")
    
    # Load sessions from CSV
    print(f"\n📥 Loading sessions from CSV...")
    try:
        sessions_data = load_sessions_from_csv(args.input_csv)
        print(f"✅ Loaded {len(sessions_data)} sessions")
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        sys.exit(1)
    
    # Process sessions
    print(f"\n⚡ Processing sessions...")
    sessions, errors = engine.process_csv_data(sessions_data)
    
    if errors:
        print(f"\n⚠️  Validation Errors:")
        for error in errors:
            print(f"   {error}")
        print(f"\n✅ Processed {len(sessions)} valid sessions "
              f"({len(errors)} errors)")
    else:
        print(f"✅ Successfully processed all {len(sessions)} sessions")
    
    if not sessions:
        print("❌ No valid sessions to process. Exiting.")
        sys.exit(1)
    
    # Write outputs
    print(f"\n📤 Generating outputs...")
    write_daily_requirements_csv(sessions, args.output_daily)
    write_weekly_summary_csv(sessions, args.output_weekly)
    
    # Print summary
    if not args.no_summary:
        print_summary_report(sessions)
    
    print("✨ Done!")


if __name__ == "__main__":
    main()
