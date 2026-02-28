# System Architecture Visualization

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         YOUR BOOKING SYSTEM                          │
│                    (Exports sessions.csv daily)                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
                   ┌──────────────────┐
                   │  sessions.csv    │
                   │  ───────────────  │
                   │  datetime_start   │
                   │  side             │
                   │  session_type     │
                   │  booked_guests    │
                   │  private_lessons  │
                   └────────┬──────────┘
                            │
                            ▼
         ┌──────────────────────────────────────────┐
         │    process_sessions.py (CLI Tool)        │
         │    ─────────────────────────────         │
         │    1. Load & Validate CSV                │
         │    2. Apply Business Rules               │
         │    3. Calculate Requirements             │
         │    4. Generate Reports                   │
         └────────┬────────────────────┬────────────┘
                  │                    │
       ┌──────────▼─────────┐   ┌─────▼──────────┐
       │ coaching_rules.yaml │   │ Rules Engine   │
       │ ───────────────────  │   │ ──────────────  │
       │ • Session types     │   │ Core Logic:    │
       │ • Baseline rules    │   │ • Baseline calc│
       │ • Private lessons   │   │ • Private calc │
       │ • Capacities        │   │ • Total calc   │
       │ • Thresholds        │   │ • Validation   │
       └─────────────────────┘   └────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────┐
    │        OUTPUTS                  │
    ├─────────────────────────────────┤
    │                                 │
    │  1. Daily Requirements CSV      │
    │     • Hour by hour breakdown    │
    │     • Left/Right side details   │
    │     • Baseline vs Private       │
    │     • Peak hour indicators      │
    │                                 │
    │  2. Weekly Summary CSV          │
    │     • Aggregated by hour        │
    │     • Daily totals              │
    │     • Weekly averages           │
    │                                 │
    │  3. Console Summary             │
    │     • Total coach-hours         │
    │     • Peak hours                │
    │     • Session type breakdown    │
    │                                 │
    └─────────────────────────────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  Ops Team Uses  │
         │  for Scheduling │
         └─────────────────┘
```

## Rules Engine Logic Flow

```
SESSION INPUT
    |
    ├─> Session Type? ──┐
    |                   |
    └─> Booked Guests? ─┤
    |                   |
    └─> Private Lessons?│
                        |
                        ▼
              ┌──────────────────┐
              │   Validation     │
              │   ────────────   │
              │  • Type exists?  │
              │  • Within cap?   │
              │  • Valid count?  │
              └────────┬─────────┘
                       │
              ┌────────▼──────────┐
              │    YES            │  NO → Error Report
              └────────┬──────────┘
                       │
              ┌────────▼──────────────────┐
              │  Calculate Baseline       │
              │  ────────────────────      │
              │  IF Beginner/Novice:      │
              │    0 guests    → 0        │
              │    1-14 guests → 2        │
              │    15+ guests  → 3        │
              │  IF Progressive:          │
              │    0 guests    → 0        │
              │    1-9 guests  → 1        │
              │    10+ guests  → 2        │
              │  IF Advanced/Pro/etc:     │
              │    Always      → 0        │
              └────────┬──────────────────┘
                       │
              ┌────────▼──────────────────┐
              │  Calculate Private        │
              │  ────────────────────      │
              │  private_count × 1        │
              │  (1:1 ratio)              │
              └────────┬──────────────────┘
                       │
              ┌────────▼──────────────────┐
              │  Calculate Total          │
              │  ────────────────────      │
              │  total = baseline +       │
              │          private          │
              └────────┬──────────────────┘
                       │
              ┌────────▼──────────────────┐
              │  Mark No-Coach-Required?  │
              │  ────────────────────      │
              │  IF (guests==0 AND        │
              │      private==0) OR       │
              │     (advanced_type AND    │
              │      private==0)          │
              │  THEN mark=True           │
              └────────┬──────────────────┘
                       │
              ┌────────▼──────────────────┐
              │  Calculate Coach Start    │
              │  ────────────────────      │
              │  session_start - 30 min   │
              └────────┬──────────────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  OUTPUT SESSION  │
              │  with all fields │
              │  calculated      │
              └──────────────────┘
```

## Example Calculation

```
INPUT SESSION:
──────────────
datetime_start:     2026-02-15 12:00:00
side:               LEFT
session_type:       Novice
booked_guests:      7
private_lessons:    1

CALCULATION STEPS:
──────────────────
1. Validate:
   ✓ "Novice" exists in config
   ✓ 7 guests <= 19 capacity
   ✓ All values valid

2. Calculate Baseline:
   Novice with 7 guests
   → 1-14 range
   → baseline = 2

3. Calculate Private:
   1 private lesson
   → private = 1 × 1
   → private = 1

4. Calculate Total:
   total = 2 + 1
   → total = 3

5. Check No-Coach-Required:
   guests = 7 (not 0)
   type = Novice (not advanced)
   → no_coach_required = False

6. Calculate Coach Start:
   12:00:00 - 30 minutes
   → coach_start = 11:30:00

OUTPUT:
───────
datetime_start:           2026-02-15 12:00:00
side:                     LEFT
session_type:             Novice
booked_guests:            7
private_lessons_count:    1
baseline_coaches:         2  ← Calculated
private_coaches:          1  ← Calculated
total_coaches_required:   3  ← Calculated
coach_start_time:         2026-02-15 11:30:00  ← Calculated
is_no_coach_required:     False  ← Calculated
```

## Aggregation for Reporting

```
HOURLY AGGREGATION:
───────────────────
For each hour (e.g., 12:00):

Left Side:
  Session: Novice, 7 guests, 1 private
  → 3 coaches total (2 baseline + 1 private)

Right Side:
  Session: Novice, 15 guests, 0 private
  → 3 coaches total (3 baseline + 0 private)

Hourly Total: 3 + 3 = 6 coaches

OUTPUT ROW:
datetime_start: 2026-02-15 12:00:00
hour: 12
left_side_coaches: 3
left_baseline: 2
left_private: 1
right_side_coaches: 3
right_baseline: 3
right_private: 0
hourly_total: 6
is_peak_hour: True  (if 6 is max for the day)
```

## Configuration Structure

```
coaching_rules.yaml
│
├── version: "1.0"
│
├── session_types:
│   ├── Beginner:
│   │   ├── capacity: 20
│   │   └── baseline_rules:
│   │       ├── [0,0]    → 0 coaches
│   │       ├── [1,14]   → 2 coaches
│   │       └── [15,999] → 3 coaches
│   │
│   ├── Progressive:
│   │   ├── capacity: 18
│   │   └── baseline_rules:
│   │       ├── [0,0]    → 0 coaches
│   │       ├── [1,9]    → 1 coach
│   │       └── [10,999] → 2 coaches
│   │
│   └── Intermediate/Advanced/Expert/Pro/Pro_Barrel:
│       ├── capacity: varies
│       └── baseline_rules:
│           └── [0,999]  → 0 coaches
│
├── private_lessons:
│   ├── coaches_per_lesson: 1
│   └── can_group: false
│
└── operational_settings:
    ├── coach_arrival_minutes_before_session: 30
    └── sides: ["LEFT", "RIGHT"]
```

## Phased Roadmap Visual

```
PHASE 1: Core Requirements (CURRENT - 2 weeks)
╔════════════════════════════════════════╗
║  ✅ Rules engine                       ║
║  ✅ CSV processing                     ║
║  ✅ Validation                         ║
║  ✅ Daily/weekly reports               ║
║  ✅ 40+ tests passing                  ║
╚════════════════════════════════════════╝
                    │
                    ▼
PHASE 2: Dashboards & Analytics (2 weeks)
╔════════════════════════════════════════╗
║  📅 Web dashboard (Streamlit)          ║
║  📅 Excel exports with formatting      ║
║  📅 Historical tracking                ║
║  📅 Audit logging                      ║
║  📅 Automated scheduling               ║
╚════════════════════════════════════════╝
                    │
                    ▼
PHASE 3: Assignment Optimization (4 weeks)
╔════════════════════════════════════════╗
║  📅 Coach roster management            ║
║  📅 Availability tracking              ║
║  📅 Auto-assignment (CP-SAT)           ║
║  📅 Constraint satisfaction            ║
║  📅 Manual overrides                   ║
╚════════════════════════════════════════╝
                    │
                    ▼
           FULLY AUTOMATED SYSTEM
```

## Test Coverage Map

```
test_coaching_rules.py (40+ tests)
│
├── TestBaselineCalculation (14 tests)
│   ├── Zero guests
│   ├── Boundary values (1, 14, 15, 20)
│   ├── Threshold crossings
│   ├── All session types
│   └── At capacity
│
├── TestPrivateLessons (3 tests)
│   ├── Zero lessons
│   ├── Single lesson
│   └── Multiple lessons
│
├── TestTotalCalculation (4 tests)
│   ├── Baseline + Private
│   ├── Zero baseline with private
│   ├── Threshold boundaries
│   └── Multiple scenarios
│
├── TestNoCoachRequired (5 tests)
│   ├── Empty sessions
│   ├── Advanced types
│   ├── With/without private
│   └── Edge cases
│
├── TestValidation (4 tests)
│   ├── Unknown types
│   ├── Over capacity
│   ├── Negative values
│   └── Valid sessions
│
├── TestCoachStartTime (2 tests)
│   ├── 30 min calculation
│   └── Various hours
│
├── TestSessionProcessing (3 tests)
│   ├── Full pipeline - Beginner
│   ├── Full pipeline - Intermediate
│   └── Empty session
│
├── TestBatchProcessing (2 tests)
│   ├── Multiple sessions
│   └── With validation errors
│
└── TestEdgeCases (3 tests)
    ├── All boundaries
    ├── Max capacity
    └── Private with zero baseline
```

---

**Visual Summary:**
1. CSV goes in → Rules engine processes → Reports come out
2. All rules in YAML (no code changes needed)
3. 40+ tests ensure accuracy
4. Clear path from Phase 1 → Phase 2 → Phase 3
