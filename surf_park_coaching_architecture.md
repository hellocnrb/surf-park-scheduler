# Surf Park Coaching Automation - Architecture & Implementation Plan

## Executive Summary

This document presents an optimal solution for automating staffing decision-making for Austin Park Surf's coaching schedule. The system is designed to be configuration-driven, deterministic, testable, and extensible from basic requirements forecasting to full coach assignment optimization.

**Recommended Stack**: Python-based solution with clear separation of concerns, configuration-driven rules, and multiple output formats. This approach balances implementation speed, maintainability, and extensibility.

---

## 1. OPTIMAL SOLUTION ARCHITECTURE

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  • CSV Ingestion (sessions, coach availability, assignments)     │
│  • Validation & Normalization                                    │
│  • Data Quality Checks                                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CONFIGURATION LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  • Session Type Definitions (capacity, baseline rules)           │
│  • Staffing Rules (thresholds, formulas)                         │
│  • Business Constraints (breaks, shift lengths)                  │
│  • Versioned Configuration (YAML/JSON)                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    COMPUTATION LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  • Rules Engine (deterministic calculations)                     │
│  • Requirement Calculator (per side, per hour)                   │
│  • Aggregation Engine (daily, weekly views)                      │
│  • [FUTURE] Assignment Optimizer                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER (Optional)                    │
├─────────────────────────────────────────────────────────────────┤
│  • SQLite for development/testing                                │
│  • PostgreSQL for production                                     │
│  • Audit trail for requirement changes                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                       OUTPUT LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  • CSV Exports (requirements, assignments)                       │
│  • JSON API (for dashboards)                                     │
│  • Excel Reports (formatted views)                               │
│  • Dashboard (web-based visualization)                           │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

1. **Configuration-Driven**: All business rules live in versioned config files, not code
2. **Testable**: Pure functions with clear inputs/outputs enable comprehensive testing
3. **Extensible**: Clear layer boundaries allow adding features without refactoring
4. **Maintainable**: Single source of truth eliminates spreadsheet logic drift
5. **Scalable**: Can start simple (CSV in/out) and grow to full optimization system

---

## 2. DATA MODEL

### Core Entities

```python
# Domain Objects (Python dataclasses)

@dataclass
class SessionType:
    """Session type definition"""
    name: str                    # e.g., "Beginner", "Novice", "Pro"
    capacity: int                # max guests per side
    baseline_rules: Dict[str, int]  # guest_count_range -> baseline_coaches
    # Example: {"1-14": 2, "15+": 3} for Beginner

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

@dataclass
class CoachRequirement:
    """Aggregated coaching need for reporting"""
    datetime_start: datetime
    hour: int
    left_side_coaches: int
    right_side_coaches: int
    hourly_total: int
    left_baseline: int
    left_private: int
    right_baseline: int
    right_private: int
    
@dataclass
class Coach:
    """Coach roster entry (Phase 3)"""
    coach_id: str
    name: str
    skill_level: int  # 1-5, where 5 can teach any session
    max_hours_per_day: int = 8
    min_break_minutes: int = 30
    
@dataclass
class Availability:
    """Coach availability window (Phase 3)"""
    coach_id: str
    date: date
    start_time: time
    end_time: time
    is_available: bool = True
    
@dataclass
class Assignment:
    """Coach assigned to session (Phase 3)"""
    assignment_id: str
    session_datetime: datetime
    session_side: str
    coach_id: str
    role: str  # e.g., "pusher", "tutor", "flowter", "private"
```

### Database Schema (Optional - for Phase 2+)

```sql
-- Session Types Configuration
CREATE TABLE session_types (
    session_type_id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    capacity INT NOT NULL,
    baseline_rules JSONB NOT NULL,  -- {"1-14": 2, "15+": 3}
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Sessions (imported from CSV)
CREATE TABLE sessions (
    session_id SERIAL PRIMARY KEY,
    datetime_start TIMESTAMP NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('LEFT', 'RIGHT')),
    session_type VARCHAR(50) REFERENCES session_types(name),
    booked_guests INT NOT NULL DEFAULT 0,
    private_lessons_count INT NOT NULL DEFAULT 0,
    
    -- Computed fields
    baseline_coaches INT NOT NULL DEFAULT 0,
    total_coaches_required INT NOT NULL DEFAULT 0,
    coach_start_time TIMESTAMP,
    is_no_coach_required BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    last_calculated TIMESTAMP,
    
    UNIQUE(datetime_start, side)
);

-- Coach Roster (Phase 3)
CREATE TABLE coaches (
    coach_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    skill_level INT CHECK (skill_level BETWEEN 1 AND 5),
    max_hours_per_day INT DEFAULT 8,
    min_break_minutes INT DEFAULT 30,
    active BOOLEAN DEFAULT TRUE
);

-- Availability (Phase 3)
CREATE TABLE availability (
    availability_id SERIAL PRIMARY KEY,
    coach_id INT REFERENCES coaches(coach_id),
    availability_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    
    UNIQUE(coach_id, availability_date, start_time)
);

-- Assignments (Phase 3)
CREATE TABLE assignments (
    assignment_id SERIAL PRIMARY KEY,
    session_id INT REFERENCES sessions(session_id),
    coach_id INT REFERENCES coaches(coach_id),
    role VARCHAR(50),  -- pusher, tutor, flowter, private
    assigned_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(session_id, coach_id)
);

-- Audit Log
CREATE TABLE calculation_audit (
    audit_id SERIAL PRIMARY KEY,
    calculation_date TIMESTAMP NOT NULL,
    sessions_processed INT,
    total_coaches_required INT,
    config_version VARCHAR(50),
    run_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### CSV Input/Output Schemas

#### Input: sessions.csv
```csv
datetime_start,side,session_type,booked_guests,private_lessons_count
2026-02-15 11:00:00,LEFT,Pro,6,0
2026-02-15 11:00:00,RIGHT,Pro,8,0
2026-02-15 12:00:00,LEFT,Novice,3,0
2026-02-15 12:00:00,RIGHT,Novice,7,1
2026-02-15 13:00:00,LEFT,Expert,10,0
```

#### Output: coach_requirements_daily.csv
```csv
datetime_start,hour,left_side_coaches,left_baseline,left_private,right_side_coaches,right_baseline,right_private,hourly_total,is_peak_hour
2026-02-15 11:00:00,11,0,0,0,0,0,0,0,False
2026-02-15 12:00:00,12,2,2,0,3,2,1,5,True
2026-02-15 13:00:00,13,0,0,0,0,0,0,0,False
```

#### Output: coach_requirements_weekly.csv
```csv
hour,monday_total,tuesday_total,wednesday_total,thursday_total,friday_total,saturday_total,sunday_total,weekly_total,avg_per_day
11,0,0,2,2,3,5,4,16,2.3
12,4,4,5,5,6,8,7,39,5.6
13,2,2,3,3,4,5,4,23,3.3
```

---

## 3. RULES ENGINE DESIGN

### Configuration File (coaching_rules.yaml)

```yaml
version: "1.0"
last_updated: "2026-02-14"

session_types:
  Beginner:
    capacity: 20
    baseline_rules:
      - guest_range: [0, 0]
        baseline_coaches: 0
      - guest_range: [1, 14]
        baseline_coaches: 2
      - guest_range: [15, 999]
        baseline_coaches: 3
    coach_roles: ["pusher", "tutor", "flowter"]
    
  Novice:
    capacity: 19
    baseline_rules:
      - guest_range: [0, 0]
        baseline_coaches: 0
      - guest_range: [1, 14]
        baseline_coaches: 2
      - guest_range: [15, 999]
        baseline_coaches: 3
    coach_roles: ["pusher", "tutor", "flowter"]
    
  Progressive:
    capacity: 18
    baseline_rules:
      - guest_range: [0, 0]
        baseline_coaches: 0
      - guest_range: [1, 9]
        baseline_coaches: 1
      - guest_range: [10, 999]
        baseline_coaches: 2
    coach_roles: ["coach", "flowter"]
    
  Intermediate:
    capacity: 13
    baseline_rules:
      - guest_range: [0, 999]
        baseline_coaches: 0
    coach_roles: []
    
  Advanced:
    capacity: 12
    baseline_rules:
      - guest_range: [0, 999]
        baseline_coaches: 0
    coach_roles: []
    
  Expert:
    capacity: 12
    baseline_rules:
      - guest_range: [0, 999]
        baseline_coaches: 0
    coach_roles: []
    
  Pro:
    capacity: 10
    baseline_rules:
      - guest_range: [0, 999]
        baseline_coaches: 0
    coach_roles: []
    
  Pro_Barrel:
    capacity: 10  # Configurable, TBD
    baseline_rules:
      - guest_range: [0, 999]
        baseline_coaches: 0
    coach_roles: []

private_lessons:
  coaches_per_lesson: 1
  can_group: false  # Future: allow grouping private lessons

operational_settings:
  coach_arrival_minutes_before_session: 30
  sides: ["LEFT", "RIGHT"]
```

### Core Rules Engine Functions

```python
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import yaml

class CoachingRulesEngine:
    """Deterministic rules engine for coaching requirements"""
    
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.session_types = self.config['session_types']
        self.private_config = self.config['private_lessons']
        self.ops_settings = self.config['operational_settings']
    
    def calculate_baseline_coaches(
        self, 
        session_type: str, 
        booked_guests: int
    ) -> int:
        """
        Calculate baseline coaching requirement based on session type and guest count.
        
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
        
        Conditions:
        1. No guests AND no private lessons, OR
        2. Session is Intermediate+ AND no private lessons
        
        Args:
            session_type: Name of session type
            booked_guests: Number of guests booked
            private_lessons_count: Number of private lessons
            
        Returns:
            True if no coaches needed
        """
        advanced_types = ['Intermediate', 'Advanced', 'Expert', 'Pro', 'Pro_Barrel']
        
        # Condition 1: Nobody booked
        if booked_guests == 0 and private_lessons_count == 0:
            return True
        
        # Condition 2: Advanced session with no private lessons
        if session_type in advanced_types and private_lessons_count == 0:
            return True
        
        return False
    
    def calculate_coach_start_time(
        self,
        session_start: datetime
    ) -> datetime:
        """
        Calculate when coaches should arrive (30 min before session).
        
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
        
        Args:
            datetime_start: Session start time
            side: "LEFT" or "RIGHT"
            session_type: Session type name
            booked_guests: Number of booked guests
            private_lessons_count: Number of private lessons (default 0)
            
        Returns:
            Session object with all computed fields
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
        
        Args:
            session_type: Session type name
            booked_guests: Number of booked guests
            
        Returns:
            List of validation error messages (empty if valid)
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
```

---

## 4. COMPREHENSIVE TEST CASES

### Test Suite (10+ Test Cases)

```python
import pytest
from datetime import datetime

class TestCoachingRulesEngine:
    
    @pytest.fixture
    def engine(self):
        return CoachingRulesEngine('coaching_rules.yaml')
    
    # BASELINE CALCULATION TESTS
    
    def test_beginner_1_guest(self, engine):
        """Test: Beginner with 1 guest requires 2 baseline coaches"""
        baseline = engine.calculate_baseline_coaches('Beginner', 1)
        assert baseline == 2
    
    def test_beginner_14_guests(self, engine):
        """Test: Beginner with 14 guests requires 2 baseline coaches (boundary)"""
        baseline = engine.calculate_baseline_coaches('Beginner', 14)
        assert baseline == 2
    
    def test_beginner_15_guests(self, engine):
        """Test: Beginner with 15 guests requires 3 baseline coaches (threshold)"""
        baseline = engine.calculate_baseline_coaches('Beginner', 15)
        assert baseline == 3
    
    def test_beginner_20_guests(self, engine):
        """Test: Beginner at capacity (20) requires 3 baseline coaches"""
        baseline = engine.calculate_baseline_coaches('Beginner', 20)
        assert baseline == 3
    
    def test_beginner_zero_guests(self, engine):
        """Test: Beginner with 0 guests requires 0 baseline coaches"""
        baseline = engine.calculate_baseline_coaches('Beginner', 0)
        assert baseline == 0
    
    def test_progressive_9_guests(self, engine):
        """Test: Progressive with 9 guests requires 1 baseline coach (boundary)"""
        baseline = engine.calculate_baseline_coaches('Progressive', 9)
        assert baseline == 1
    
    def test_progressive_10_guests(self, engine):
        """Test: Progressive with 10 guests requires 2 baseline coaches (threshold)"""
        baseline = engine.calculate_baseline_coaches('Progressive', 10)
        assert baseline == 2
    
    def test_intermediate_full_capacity(self, engine):
        """Test: Intermediate at capacity (13) requires 0 baseline coaches"""
        baseline = engine.calculate_baseline_coaches('Intermediate', 13)
        assert baseline == 0
    
    def test_pro_any_guests(self, engine):
        """Test: Pro session always requires 0 baseline coaches"""
        for guests in [0, 5, 10]:
            baseline = engine.calculate_baseline_coaches('Pro', guests)
            assert baseline == 0
    
    # PRIVATE LESSON TESTS
    
    def test_private_lessons_single(self, engine):
        """Test: 1 private lesson requires 1 additional coach"""
        private = engine.calculate_private_coaches(1)
        assert private == 1
    
    def test_private_lessons_multiple(self, engine):
        """Test: 3 private lessons require 3 additional coaches"""
        private = engine.calculate_private_coaches(3)
        assert private == 3
    
    def test_private_lessons_zero(self, engine):
        """Test: 0 private lessons require 0 additional coaches"""
        private = engine.calculate_private_coaches(0)
        assert private == 0
    
    # TOTAL CALCULATION TESTS
    
    def test_total_beginner_with_private(self, engine):
        """Test: Beginner (5 guests) + 2 private lessons = 4 total coaches"""
        baseline, private, total = engine.calculate_total_coaches(
            'Beginner', 5, 2
        )
        assert baseline == 2
        assert private == 2
        assert total == 4
    
    def test_total_intermediate_with_private(self, engine):
        """Test: Intermediate (10 guests) + 1 private = 1 total coach"""
        baseline, private, total = engine.calculate_total_coaches(
            'Intermediate', 10, 1
        )
        assert baseline == 0
        assert private == 1
        assert total == 1
    
    # NO-COACH-REQUIRED TESTS
    
    def test_no_coach_zero_guests_zero_private(self, engine):
        """Test: 0 guests + 0 private = no coach required"""
        result = engine.is_no_coach_required('Beginner', 0, 0)
        assert result == True
    
    def test_no_coach_intermediate_no_private(self, engine):
        """Test: Intermediate with guests but no private = no coach required"""
        result = engine.is_no_coach_required('Intermediate', 10, 0)
        assert result == True
    
    def test_no_coach_intermediate_with_private(self, engine):
        """Test: Intermediate with private lesson = coach required"""
        result = engine.is_no_coach_required('Intermediate', 10, 1)
        assert result == False
    
    def test_no_coach_beginner_with_guests(self, engine):
        """Test: Beginner with guests = coach required"""
        result = engine.is_no_coach_required('Beginner', 5, 0)
        assert result == False
    
    # EDGE CASES
    
    def test_unknown_session_type(self, engine):
        """Test: Unknown session type raises ValueError"""
        with pytest.raises(ValueError):
            engine.calculate_baseline_coaches('UnknownType', 5)
    
    def test_validation_over_capacity(self, engine):
        """Test: Booking over capacity returns validation error"""
        errors = engine.validate_session('Beginner', 25)
        assert len(errors) == 1
        assert 'exceeds capacity' in errors[0]
    
    def test_validation_negative_guests(self, engine):
        """Test: Negative guest count returns validation error"""
        errors = engine.validate_session('Beginner', -5)
        assert len(errors) == 1
        assert 'Negative guest count' in errors[0]
    
    def test_coach_start_time(self, engine):
        """Test: Coach start time is 30 minutes before session"""
        session_start = datetime(2026, 2, 15, 11, 0, 0)
        coach_start = engine.calculate_coach_start_time(session_start)
        expected = datetime(2026, 2, 15, 10, 30, 0)
        assert coach_start == expected
    
    # INTEGRATION TEST
    
    def test_full_session_processing(self, engine):
        """Test: Complete session processing pipeline"""
        session = engine.process_session(
            datetime_start=datetime(2026, 2, 15, 12, 0, 0),
            side='LEFT',
            session_type='Novice',
            booked_guests=7,
            private_lessons_count=1
        )
        
        assert session.baseline_coaches == 2
        assert session.private_coaches == 1
        assert session.total_coaches_required == 3
        assert session.is_no_coach_required == False
        assert session.coach_start_time == datetime(2026, 2, 15, 11, 30, 0)
```

---

## 5. PHASED IMPLEMENTATION ROADMAP

### Phase 1: Core Requirements Calculation (Weeks 1-2)

**Goal**: Compute coaching requirements from sessions CSV

**Deliverables**:
- Configuration file (YAML) with all rules
- Rules engine class with core calculation functions
- CSV ingestion pipeline with validation
- Unit test suite (10+ tests)
- Basic CLI tool for processing sessions
- Output: coach_requirements_daily.csv

**Tasks**:
1. Set up project structure (Python package)
2. Implement Session and SessionType data models
3. Build CoachingRulesEngine class
4. Create YAML configuration file
5. Write comprehensive test suite
6. Build CSV ingestion pipeline with pandas
7. Implement basic reporting (daily requirements CSV)
8. Add data validation and error handling
9. Create simple CLI interface

**Success Criteria**:
- All tests pass
- Can process sample CSV and generate requirements
- Rules match existing Excel logic
- Configuration can be updated without code changes

### Phase 2: Reporting & Dashboards (Weeks 3-4)

**Goal**: Human-readable views and analytics

**Deliverables**:
- Weekly aggregation reports
- Excel exports with formatting
- JSON API for dashboard consumption
- Basic web dashboard (Flask/Streamlit)
- Audit logging

**Tasks**:
1. Build aggregation functions (hourly, daily, weekly)
2. Implement peak hour detection
3. Create formatted Excel exports (with colors, totals)
4. Set up optional SQLite/PostgreSQL storage
5. Build simple REST API (Flask) or direct Streamlit app
6. Create dashboard views:
   - Daily ops view (hour-by-hour grid)
   - Weekly planning view (heatmap)
   - Coverage gaps visualization
7. Add calculation audit logging
8. Implement report scheduling (optional)

**Success Criteria**:
- Dashboard shows real-time requirements
- Reports match operational needs
- Ops team can make staffing decisions from views
- Historical tracking available

### Phase 3: Coach Assignment Optimization (Weeks 5-8) [OPTIONAL]

**Goal**: Automatically assign coaches to sessions

**Deliverables**:
- Coach roster and availability management
- Assignment optimization engine
- Constraint satisfaction
- Assignment outputs (CSV + visual)

**Tasks**:
1. Extend data model for Coach, Availability, Assignment
2. Build coach availability management
3. Design optimization objective function
4. Implement constraint solver (OR-Tools CP-SAT)
5. Create assignment algorithm
6. Build assignment validation
7. Generate assignment reports
8. Add manual override capability
9. Implement assignment audit trail

**Success Criteria**:
- Optimizer finds valid assignments for 90%+ of scenarios
- Respects all constraints (availability, breaks, skills)
- Better than manual assignment (less understaffing)
- Easy to override/adjust assignments

---

## 6. PHASE 3: OPTIMIZATION DESIGN (OPTIONAL)

### Objective Function

**Primary Goal**: Minimize understaffing while respecting constraints

```python
# Objective function components (in priority order):

1. CRITICAL: Meet all required coaching coverage
   - Hard constraint: total_assigned >= total_required per session
   - Penalty: 1000 points per missing coach (very high cost)

2. IMPORTANT: Minimize overstaffing
   - Soft constraint: prefer total_assigned == total_required
   - Penalty: 10 points per extra coach

3. DESIRABLE: Balance workload across coaches
   - Soft constraint: similar hours per coach per day
   - Penalty: 1 point per hour deviation from mean

4. DESIRABLE: Minimize coach idle time
   - Soft constraint: group shifts (fewer gaps)
   - Penalty: 5 points per gap hour

5. OPTIONAL: Match skill levels to sessions
   - Soft constraint: assign experienced coaches to advanced sessions
   - Penalty: 2 points for skill mismatch
```

### Constraints

```python
# Hard Constraints (must be satisfied):

1. Availability
   - Coach can only be assigned if available for that time slot
   - Include travel time between assignments

2. Maximum hours per day
   - Coach cannot exceed max_hours_per_day
   - Default: 8 hours

3. Minimum break between sessions
   - If assigned to consecutive blocks, must have break
   - Default: 30 minutes after every 2-3 hours

4. No double-booking
   - Coach cannot be assigned to both sides simultaneously
   - One coach, one place, one time

5. Required coaching coverage
   - total_assigned >= total_required for each session

# Soft Constraints (can be violated with penalty):

1. Preferred maximum consecutive hours
   - Prefer not to assign more than 4 hours without break
   - Can violate if necessary

2. Skill level appropriateness
   - Prefer skill level 5 coaches for Beginner/Novice
   - Can assign any skill level if needed

3. Workload fairness
   - Try to distribute hours evenly across available coaches
   - Can violate for operational needs
```

### Suggested Algorithm: CP-SAT (Constraint Programming)

**Why CP-SAT over ILP or Greedy?**

1. **Better for scheduling**: CP-SAT excels at assignment and scheduling problems
2. **Handles complex constraints**: Can express "no gaps > X hours" naturally
3. **Fast**: Google OR-Tools CP-SAT is highly optimized
4. **Flexible**: Easy to add/remove constraints without rewriting solver
5. **Proven**: Used in production scheduling systems worldwide

**Alternative Approaches**:

- **Greedy Algorithm** (Phase 3A - Quick Win):
  - Pro: Simple to implement, fast
  - Con: May miss optimal solutions
  - Use case: Initial prototype or when CP-SAT is overkill
  
- **Integer Linear Programming (ILP)** (If CP-SAT struggles):
  - Pro: Can handle very large problems
  - Con: Harder to express scheduling constraints
  - Use case: If problem size grows beyond CP-SAT capabilities

**Implementation Sketch (CP-SAT)**:

```python
from ortools.sat.python import cp_model

class CoachAssignmentOptimizer:
    
    def optimize(
        self,
        sessions: List[Session],
        coaches: List[Coach],
        availability: Dict[str, List[Availability]]
    ) -> List[Assignment]:
        """
        Find optimal coach assignments using CP-SAT.
        
        Returns:
            List of Assignment objects
        """
        model = cp_model.CpModel()
        
        # Decision variables: assign[session_id, coach_id] = 0 or 1
        assigns = {}
        for session in sessions:
            for coach in coaches:
                var_name = f'assign_{session.session_id}_{coach.coach_id}'
                assigns[(session.session_id, coach.coach_id)] = \
                    model.NewBoolVar(var_name)
        
        # CONSTRAINT 1: Meet coaching requirements
        for session in sessions:
            model.Add(
                sum(assigns[(session.session_id, c.coach_id)] 
                    for c in coaches) >= session.total_coaches_required
            )
        
        # CONSTRAINT 2: Respect availability
        for session in sessions:
            for coach in coaches:
                if not self._is_available(coach, session, availability):
                    model.Add(assigns[(session.session_id, coach.coach_id)] == 0)
        
        # CONSTRAINT 3: Max hours per day
        for coach in coaches:
            daily_sessions = [s for s in sessions 
                            if s.datetime_start.date() == target_date]
            model.Add(
                sum(assigns[(s.session_id, coach.coach_id)] 
                    for s in daily_sessions) <= coach.max_hours_per_day
            )
        
        # CONSTRAINT 4: No double-booking (same time, different sides)
        for hour_slot in unique_hour_slots:
            simultaneous = [s for s in sessions 
                          if s.datetime_start == hour_slot]
            for coach in coaches:
                model.Add(
                    sum(assigns[(s.session_id, coach.coach_id)] 
                        for s in simultaneous) <= 1
                )
        
        # OBJECTIVE: Minimize understaffing + overstaffing
        understaffing = []
        overstaffing = []
        
        for session in sessions:
            assigned = sum(assigns[(session.session_id, c.coach_id)] 
                          for c in coaches)
            required = session.total_coaches_required
            
            # Track shortage
            shortage = model.NewIntVar(0, 10, f'shortage_{session.session_id}')
            model.Add(shortage >= required - assigned)
            understaffing.append(shortage)
            
            # Track excess
            excess = model.NewIntVar(0, 10, f'excess_{session.session_id}')
            model.Add(excess >= assigned - required)
            overstaffing.append(excess)
        
        model.Minimize(
            1000 * sum(understaffing) +  # Critical: cover requirements
            10 * sum(overstaffing)       # Important: avoid overstaffing
        )
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 60.0
        status = solver.Solve(model)
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._extract_assignments(sessions, coaches, assigns, solver)
        else:
            raise ValueError("No feasible solution found")
    
    def _is_available(self, coach, session, availability):
        """Check if coach is available for session"""
        # Implementation details...
        pass
    
    def _extract_assignments(self, sessions, coaches, assigns, solver):
        """Convert solver variables to Assignment objects"""
        assignments = []
        for session in sessions:
            for coach in coaches:
                if solver.Value(assigns[(session.session_id, coach.coach_id)]) == 1:
                    assignments.append(Assignment(
                        assignment_id=f"{session.session_id}_{coach.coach_id}",
                        session_datetime=session.datetime_start,
                        session_side=session.side,
                        coach_id=coach.coach_id,
                        role="assigned"
                    ))
        return assignments
```

---

## 7. OPEN QUESTIONS & ASSUMPTIONS

### Open Questions

1. **Pro Barrel Capacity**: Currently TBD - what should it be? (Assumed 10 for now)

2. **Private Lesson Grouping**: Should multiple private lessons ever share a coach? (Assumed no for Phase 1)

3. **Coach Roles**: Do we need to enforce specific roles (pusher, tutor, flowter) or just count? (Assumed count only for Phase 1)

4. **Skill Level Requirements**: Which session types need which skill levels? (Deferred to Phase 3)

5. **Break Rules**: Exact break timing rules? After how many consecutive hours? (Assumed 30 min every 3 hours for Phase 3)

6. **Shift Preferences**: Do coaches have preferred times? Morning/afternoon preferences? (Deferred to Phase 3)

7. **Emergency Coverage**: How to handle last-minute coach unavailability? (Manual override capability in Phase 3)

8. **Historical Data**: Do we need to import existing assignments for analysis? (Optional Phase 2 enhancement)

### Assumptions Made

1. **CSV Format**: Assuming standard datetime format (YYYY-MM-DD HH:MM:SS)
2. **Side Values**: Assuming "LEFT"/"RIGHT" (can easily support "Left"/"Right")
3. **Session Duration**: Assuming all sessions are 1 hour
4. **Coach Arrival Time**: Fixed at 30 minutes before (configurable in YAML)
5. **One Coach per Private**: 1:1 ratio for Phase 1 (can add grouping later)
6. **No Meal Breaks**: Breaks are short (30 min), not meal breaks (deferred to Phase 3)
7. **Storage Optional**: Can run entirely on CSV files, database is optional
8. **Same-Day Scheduling**: Assuming we're scheduling within same day (no overnight shifts)

---

## 8. SAMPLE INPUT/OUTPUT

### Sample Input (sessions.csv)

```csv
datetime_start,side,session_type,booked_guests,private_lessons_count
2026-02-15 11:00:00,LEFT,Pro,6,0
2026-02-15 11:00:00,RIGHT,Pro,8,0
2026-02-15 12:00:00,LEFT,Novice,3,0
2026-02-15 12:00:00,RIGHT,Novice,7,1
2026-02-15 13:00:00,LEFT,Expert,10,0
2026-02-15 13:00:00,RIGHT,Expert,8,0
2026-02-15 14:00:00,LEFT,Intermediate,5,0
2026-02-15 14:00:00,RIGHT,Intermediate,13,2
2026-02-15 15:00:00,LEFT,Progressive,8,0
2026-02-15 15:00:00,RIGHT,Progressive,12,1
2026-02-15 16:00:00,LEFT,Beginner,16,1
2026-02-15 16:00:00,RIGHT,Beginner,14,0
```

### Sample Output (coach_requirements_daily.csv)

```csv
datetime_start,hour,left_side_coaches,left_baseline,left_private,right_side_coaches,right_baseline,right_private,hourly_total,left_no_coach_required,right_no_coach_required,is_peak_hour
2026-02-15 11:00:00,11,0,0,0,0,0,0,0,True,True,False
2026-02-15 12:00:00,12,2,2,0,3,2,1,5,False,False,True
2026-02-15 13:00:00,13,0,0,0,0,0,0,0,True,True,False
2026-02-15 14:00:00,14,0,0,0,2,0,2,2,True,False,False
2026-02-15 15:00:00,15,1,1,0,3,2,1,4,False,False,False
2026-02-15 16:00:00,16,4,3,1,2,2,0,6,False,False,True
```

### Sample Output (formatted_daily_report.xlsx)

```
Austin Park Surf - Daily Coach Requirements
Date: February 15, 2026

Hour | Left Side | Left (B/P) | Right Side | Right (B/P) | Hourly Total | Peak
-----|-----------|------------|------------|-------------|--------------|------
11:00|     0     |    0/0     |     0      |    0/0      |      0       |  
12:00|     2     |    2/0     |     3      |    2/1      |    ⭐ 5     | ⭐
13:00|     0     |    0/0     |     0      |    0/0      |      0       |
14:00|     0     |    0/0     |     2      |    0/2      |      2       |
15:00|     1     |    1/0     |     3      |    2/1      |      4       |
16:00|     4     |    3/1     |     2      |    2/0      |    ⭐ 6     | ⭐

Daily Total: 22 coach-hours required
Peak Hours: 12:00 (5), 16:00 (6)
Average per hour: 3.7 coaches

B = Baseline coaches | P = Private lesson coaches
⭐ = Peak hour (highest demand)
```

---

## 9. RECOMMENDED TECH STACK

### Core Application
- **Language**: Python 3.10+
- **Data Processing**: pandas, numpy
- **Configuration**: PyYAML or pydantic-settings
- **Testing**: pytest, hypothesis (property-based testing)
- **Optimization** (Phase 3): OR-Tools (Google)

### Storage (Optional)
- **Development**: SQLite (built-in)
- **Production**: PostgreSQL 14+
- **ORM**: SQLAlchemy (optional)

### API/Dashboard (Phase 2)
- **Option A - Rapid**: Streamlit (fastest to deploy)
- **Option B - Flexible**: Flask + React
- **Option C - Full-Stack**: FastAPI + Vue.js

### Deployment
- **Containerization**: Docker
- **Orchestration**: docker-compose (simple) or Kubernetes (complex)
- **Scheduling**: cron or Airflow (for automated runs)

### Development Tools
- **Version Control**: Git
- **Code Quality**: black (formatter), flake8 (linter), mypy (type checking)
- **Documentation**: Sphinx or MkDocs

---

## 10. SUCCESS METRICS

### Phase 1 Metrics
- ✓ All 10+ unit tests pass
- ✓ Processes 1000+ sessions in < 5 seconds
- ✓ 100% match with existing Excel logic
- ✓ Zero validation errors on clean data

### Phase 2 Metrics
- ✓ Dashboard loads in < 2 seconds
- ✓ Reports generated in < 10 seconds
- ✓ 90%+ user satisfaction (ops team survey)
- ✓ Reduce planning time by 50%+

### Phase 3 Metrics (if implemented)
- ✓ Finds valid assignment for 95%+ scenarios
- ✓ Optimization runs in < 60 seconds
- ✓ Reduces understaffing by 30%+
- ✓ Reduces overstaffing by 20%+
- ✓ Coach satisfaction score improves

---

## 11. NEXT STEPS

### Immediate Actions (Week 1)

1. **Review & Approve Architecture**
   - Stakeholder review of this document
   - Confirm rules and assumptions
   - Prioritize Phase 3 (yes/no decision)

2. **Set Up Development Environment**
   - Create Git repository
   - Set up Python virtual environment
   - Install dependencies
   - Create project structure

3. **Finalize Configuration**
   - Review coaching_rules.yaml
   - Confirm Pro Barrel capacity
   - Validate all session type rules
   - Get sign-off on edge cases

4. **Begin Phase 1 Development**
   - Implement data models
   - Build rules engine
   - Write test suite
   - Start with MVP CLI tool

### Decision Points

**DECISION 1**: Database or CSV-only?
- **Recommendation**: Start with CSV-only (Phase 1), add database in Phase 2 if needed
- **Reasoning**: Simpler, faster, less infrastructure

**DECISION 2**: Build Phase 3 (optimization)?
- **Recommendation**: Yes, but after Phase 2 proves value
- **Reasoning**: High ROI if manual assignment is time-consuming

**DECISION 3**: Dashboard technology?
- **Recommendation**: Streamlit for Phase 2 (fastest)
- **Reasoning**: Can replace with custom dashboard later if needed

**DECISION 4**: Hosting/deployment?
- **Recommendation**: Start with local execution, containerize in Phase 2
- **Reasoning**: Avoids premature infrastructure investment

---

## 12. CONCLUSION

This architecture provides a **scalable, maintainable, and testable** solution for automating surf park coaching decisions. The phased approach allows you to:

1. **Validate quickly** (Phase 1: 2 weeks to working system)
2. **Add value incrementally** (Phase 2: reporting and visibility)
3. **Optimize if needed** (Phase 3: full automation)

The configuration-driven design ensures rules can be updated without code changes, eliminating spreadsheet logic drift. The comprehensive test suite provides confidence in calculations. And the clear architecture allows the system to grow from simple CSV processing to full-scale optimization without major rewrites.

**Estimated Timeline**:
- Phase 1: 2 weeks (core functionality)
- Phase 2: 2 weeks (dashboards and reporting)
- Phase 3: 4 weeks (optimization, if approved)
- **Total**: 8 weeks to full system

**Next Step**: Review this architecture, confirm decisions, and we can begin implementation immediately.
