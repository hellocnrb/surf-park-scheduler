"""
Surf Park Coaching Rules Engine
Implementation of deterministic coaching requirement calculations
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Literal
import yaml


@dataclass
class Session:
    """One side of lagoon for one hour"""
    datetime_start: datetime
    side: Literal["LEFT", "RIGHT"]
    session_type: str
    booked_guests: int
    private_lessons_count: int
    
    # Computed fields (calculated by rules engine)
    baseline_coaches: int = 0
    private_coaches: int = 0
    total_coaches_required: int = 0
    coach_start_time: datetime = None
    is_no_coach_required: bool = False


class CoachingRulesEngine:
    """Deterministic rules engine for coaching requirements"""
    
    def __init__(self, config: Dict):
        """
        Initialize rules engine with configuration dictionary.
        
        Args:
            config: Dictionary containing session_types, private_lessons, 
                   and operational_settings
        """
        self.config = config
        self.session_types = self.config['session_types']
        self.private_config = self.config['private_lessons']
        self.ops_settings = self.config['operational_settings']
    
    @classmethod
    def from_yaml(cls, config_path: str):
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return cls(config)
    
    def calculate_baseline_coaches(
        self, 
        session_type: str, 
        booked_guests: int
    ) -> int:
        """
        Calculate baseline coaching requirement based on session type and guest count.
        
        Business Rules:
        - Beginner/Novice: 0 for 0 guests, 2 for 1-14 guests, 3 for 15+ guests
        - Progressive: 0 for 0 guests, 1 for 1-9 guests, 2 for 10+ guests
        - Intermediate/Advanced/Expert/Pro/Pro_Barrel: 0 regardless of guests
        
        Args:
            session_type: Name of session type (e.g., "Beginner", "Pro")
            booked_guests: Number of guests booked
            
        Returns:
            Number of baseline coaches required (0-3)
            
        Raises:
            ValueError: If session_type is not recognized
        """
        if session_type not in self.session_types:
            raise ValueError(f"Unknown session type: {session_type}")
        
        rules = self.session_types[session_type]['baseline_rules']
        
        for rule in rules:
            min_guests, max_guests = rule['guest_range']
            if min_guests <= booked_guests <= max_guests:
                return rule['baseline_coaches']
        
        # Should never reach here if config is complete
        return 0
    
    def calculate_private_coaches(
        self, 
        private_lessons_count: int
    ) -> int:
        """
        Calculate additional coaches needed for private lessons.
        
        Business Rule: Each private lesson requires 1 additional coach (1:1 ratio)
        
        Args:
            private_lessons_count: Number of private lessons booked
            
        Returns:
            Number of additional coaches needed
        """
        coaches_per_lesson = self.private_config['coaches_per_lesson']
        return private_lessons_count * coaches_per_lesson
    
    def calculate_total_coaches(
        self,
        session_type: str,
        booked_guests: int,
        private_lessons_count: int
    ) -> Tuple[int, int, int]:
        """
        Calculate total coaching requirement for a session.
        
        Formula: total_coaches = baseline_coaches + private_coaches
        
        Args:
            session_type: Name of session type
            booked_guests: Number of guests booked
            private_lessons_count: Number of private lessons
            
        Returns:
            Tuple of (baseline_coaches, private_coaches, total_coaches)
        """
        baseline = self.calculate_baseline_coaches(session_type, booked_guests)
        private = self.calculate_private_coaches(private_lessons_count)
        total = baseline + private
        
        return baseline, private, total
    
    def is_no_coach_required(
        self,
        session_type: str,
        booked_guests: int,
        private_lessons_count: int
    ) -> bool:
        """
        Determine if session should be marked as "no coach required".
        
        Marking Conditions:
        1. No guests AND no private lessons, OR
        2. Session is Intermediate+ AND no private lessons
        
        Args:
            session_type: Name of session type
            booked_guests: Number of guests booked
            private_lessons_count: Number of private lessons
            
        Returns:
            True if no coaches needed (for formatting/display purposes)
        """
        advanced_types = ['Intermediate', 'Advanced', 'Expert', 'Pro', 'Pro_Barrel']
        
        # Condition 1: Nobody booked at all
        if booked_guests == 0 and private_lessons_count == 0:
            return True
        
        # Condition 2: Advanced session with no private lessons
        # (these sessions have 0 baseline coaches by design)
        if session_type in advanced_types and private_lessons_count == 0:
            return True
        
        return False
    
    def calculate_coach_start_time(
        self,
        session_start: datetime
    ) -> datetime:
        """
        Calculate when coaches should arrive (30 min before session by default).
        
        Args:
            session_start: Session start datetime
            
        Returns:
            Coach arrival datetime
        """
        minutes_before = self.ops_settings['coach_arrival_minutes_before_session']
        return session_start - timedelta(minutes=minutes_before)
    
    def process_session(
        self,
        datetime_start: datetime,
        side: str,
        session_type: str,
        booked_guests: int,
        private_lessons_count: int = 0
    ) -> Session:
        """
        Process a single session and return calculated Session object.
        
        This is the main entry point for processing a session row.
        
        Args:
            datetime_start: Session start time
            side: "LEFT" or "RIGHT"
            session_type: Session type name
            booked_guests: Number of booked guests
            private_lessons_count: Number of private lessons (default 0)
            
        Returns:
            Session object with all computed fields populated
        """
        baseline, private, total = self.calculate_total_coaches(
            session_type, booked_guests, private_lessons_count
        )
        
        no_coach_req = self.is_no_coach_required(
            session_type, booked_guests, private_lessons_count
        )
        
        coach_start = self.calculate_coach_start_time(datetime_start)
        
        return Session(
            datetime_start=datetime_start,
            side=side,
            session_type=session_type,
            booked_guests=booked_guests,
            private_lessons_count=private_lessons_count,
            baseline_coaches=baseline,
            private_coaches=private,
            total_coaches_required=total,
            coach_start_time=coach_start,
            is_no_coach_required=no_coach_req
        )
    
    def validate_session(
        self,
        session_type: str,
        booked_guests: int
    ) -> List[str]:
        """
        Validate session data against business rules.
        
        Checks:
        - Session type exists in configuration
        - Booked guests <= capacity
        - Booked guests >= 0
        
        Args:
            session_type: Session type name
            booked_guests: Number of booked guests
            
        Returns:
            List of validation error messages (empty list if valid)
        """
        errors = []
        
        if session_type not in self.session_types:
            errors.append(f"Unknown session type: {session_type}")
            return errors
        
        capacity = self.session_types[session_type]['capacity']
        if booked_guests > capacity:
            errors.append(
                f"Guests ({booked_guests}) exceeds capacity ({capacity}) "
                f"for {session_type}"
            )
        
        if booked_guests < 0:
            errors.append(f"Negative guest count: {booked_guests}")
        
        return errors
    
    def process_csv_data(
        self, 
        sessions_data: List[Dict]
    ) -> Tuple[List[Session], List[str]]:
        """
        Process multiple sessions from CSV-like data.
        
        Args:
            sessions_data: List of dictionaries with keys:
                          datetime_start, side, session_type, 
                          booked_guests, private_lessons_count
                          
        Returns:
            Tuple of (processed_sessions, validation_errors)
        """
        processed_sessions = []
        all_errors = []
        
        for idx, row in enumerate(sessions_data):
            # Validate first
            errors = self.validate_session(
                row['session_type'], 
                row['booked_guests']
            )
            
            if errors:
                for error in errors:
                    all_errors.append(f"Row {idx + 1}: {error}")
                continue  # Skip processing invalid row
            
            # Process valid session
            session = self.process_session(
                datetime_start=row['datetime_start'],
                side=row['side'],
                session_type=row['session_type'],
                booked_guests=row['booked_guests'],
                private_lessons_count=row.get('private_lessons_count', 0)
            )
            processed_sessions.append(session)
        
        return processed_sessions, all_errors


# Sample configuration that matches your requirements
SAMPLE_CONFIG = {
    "version": "1.0",
    "session_types": {
        "Beginner": {
            "capacity": 20,
            "baseline_rules": [
                {"guest_range": [0, 0], "baseline_coaches": 0},
                {"guest_range": [1, 14], "baseline_coaches": 2},
                {"guest_range": [15, 999], "baseline_coaches": 3}
            ]
        },
        "Novice": {
            "capacity": 19,
            "baseline_rules": [
                {"guest_range": [0, 0], "baseline_coaches": 0},
                {"guest_range": [1, 14], "baseline_coaches": 2},
                {"guest_range": [15, 999], "baseline_coaches": 3}
            ]
        },
        "Progressive": {
            "capacity": 18,
            "baseline_rules": [
                {"guest_range": [0, 0], "baseline_coaches": 0},
                {"guest_range": [1, 9], "baseline_coaches": 1},
                {"guest_range": [10, 999], "baseline_coaches": 2}
            ]
        },
        "Intermediate": {
            "capacity": 13,
            "baseline_rules": [
                {"guest_range": [0, 999], "baseline_coaches": 0}
            ]
        },
        "Advanced": {
            "capacity": 12,
            "baseline_rules": [
                {"guest_range": [0, 999], "baseline_coaches": 0}
            ]
        },
        "Expert": {
            "capacity": 12,
            "baseline_rules": [
                {"guest_range": [0, 999], "baseline_coaches": 0}
            ]
        },
        "Pro": {
            "capacity": 10,
            "baseline_rules": [
                {"guest_range": [0, 999], "baseline_coaches": 0}
            ]
        },
        "Pro_Barrel": {
            "capacity": 10,
            "baseline_rules": [
                {"guest_range": [0, 999], "baseline_coaches": 0}
            ]
        }
    },
    "private_lessons": {
        "coaches_per_lesson": 1,
        "can_group": False
    },
    "operational_settings": {
        "coach_arrival_minutes_before_session": 30,
        "sides": ["LEFT", "RIGHT"]
    }
}


def main():
    """Example usage of the rules engine"""
    
    # Initialize engine with sample config
    engine = CoachingRulesEngine(SAMPLE_CONFIG)
    
    # Example 1: Single session processing
    print("=" * 80)
    print("EXAMPLE 1: Processing Individual Sessions")
    print("=" * 80)
    
    test_cases = [
        ("Beginner", 5, 0, "Beginner with 5 guests, no private"),
        ("Beginner", 15, 1, "Beginner with 15 guests, 1 private"),
        ("Progressive", 9, 0, "Progressive with 9 guests (boundary)"),
        ("Progressive", 10, 1, "Progressive with 10 guests, 1 private"),
        ("Intermediate", 13, 0, "Intermediate at capacity, no private"),
        ("Intermediate", 10, 2, "Intermediate with 10 guests, 2 private"),
        ("Pro", 8, 0, "Pro with 8 guests, no private"),
    ]
    
    for session_type, guests, private, description in test_cases:
        baseline, private_coaches, total = engine.calculate_total_coaches(
            session_type, guests, private
        )
        no_coach = engine.is_no_coach_required(session_type, guests, private)
        
        print(f"\n{description}:")
        print(f"  Baseline: {baseline}, Private: {private_coaches}, Total: {total}")
        print(f"  No coach required: {no_coach}")
    
    # Example 2: CSV-like batch processing
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Processing CSV Data (Batch)")
    print("=" * 80)
    
    sample_data = [
        {
            'datetime_start': datetime(2026, 2, 15, 11, 0, 0),
            'side': 'LEFT',
            'session_type': 'Pro',
            'booked_guests': 6,
            'private_lessons_count': 0
        },
        {
            'datetime_start': datetime(2026, 2, 15, 11, 0, 0),
            'side': 'RIGHT',
            'session_type': 'Pro',
            'booked_guests': 8,
            'private_lessons_count': 0
        },
        {
            'datetime_start': datetime(2026, 2, 15, 12, 0, 0),
            'side': 'LEFT',
            'session_type': 'Novice',
            'booked_guests': 3,
            'private_lessons_count': 0
        },
        {
            'datetime_start': datetime(2026, 2, 15, 12, 0, 0),
            'side': 'RIGHT',
            'session_type': 'Novice',
            'booked_guests': 7,
            'private_lessons_count': 1
        },
    ]
    
    sessions, errors = engine.process_csv_data(sample_data)
    
    if errors:
        print("\nValidation Errors:")
        for error in errors:
            print(f"  ❌ {error}")
    
    print(f"\nProcessed {len(sessions)} sessions successfully:")
    print("\nTime | Side  | Type    | Guests | Private | Base | Priv | Total")
    print("-" * 75)
    for s in sessions:
        time_str = s.datetime_start.strftime("%H:%M")
        print(f"{time_str} | {s.side:5} | {s.session_type:8} | "
              f"{s.booked_guests:6} | {s.private_lessons_count:7} | "
              f"{s.baseline_coaches:4} | {s.private_coaches:4} | {s.total_coaches_required:5}")
    
    # Example 3: Hourly aggregation
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Hourly Requirements Summary")
    print("=" * 80)
    
    # Group by hour
    from collections import defaultdict
    hourly_reqs = defaultdict(lambda: {'left': 0, 'right': 0})
    
    for s in sessions:
        hour = s.datetime_start.hour
        if s.side == 'LEFT':
            hourly_reqs[hour]['left'] = s.total_coaches_required
        else:
            hourly_reqs[hour]['right'] = s.total_coaches_required
    
    print("\nHour | Left | Right | Total")
    print("-" * 35)
    for hour in sorted(hourly_reqs.keys()):
        left = hourly_reqs[hour]['left']
        right = hourly_reqs[hour]['right']
        total = left + right
        marker = "⭐" if total >= 4 else "  "
        print(f"{hour:02d}:00 | {left:4} | {right:5} | {total:5} {marker}")
    
    total_coaches = sum(h['left'] + h['right'] for h in hourly_reqs.values())
    print(f"\nTotal coach-hours needed: {total_coaches}")


if __name__ == "__main__":
    main()
