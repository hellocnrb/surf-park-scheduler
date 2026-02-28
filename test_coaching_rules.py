"""
Comprehensive Test Suite for Surf Park Coaching Rules Engine
Tests all business rules, edge cases, and integration scenarios
"""

import pytest
from datetime import datetime, timedelta
from coaching_rules_engine import CoachingRulesEngine, Session, SAMPLE_CONFIG


@pytest.fixture
def engine():
    """Fixture providing initialized rules engine"""
    return CoachingRulesEngine(SAMPLE_CONFIG)


class TestBaselineCalculation:
    """Tests for baseline coaching requirements calculation"""
    
    def test_beginner_zero_guests(self, engine):
        """
        TEST 1: Beginner with 0 guests requires 0 baseline coaches
        Business Rule: Empty session = no baseline coaches
        """
        baseline = engine.calculate_baseline_coaches('Beginner', 0)
        assert baseline == 0, "Empty Beginner session should require 0 coaches"
    
    def test_beginner_one_guest(self, engine):
        """
        TEST 2: Beginner with 1 guest requires 2 baseline coaches
        Business Rule: 1-14 guests = 2 coaches (pusher + tutor)
        """
        baseline = engine.calculate_baseline_coaches('Beginner', 1)
        assert baseline == 2, "Beginner with 1 guest should require 2 coaches"
    
    def test_beginner_boundary_14_guests(self, engine):
        """
        TEST 3: Beginner with 14 guests requires 2 baseline coaches (boundary test)
        Business Rule: 1-14 guests = 2 coaches, this is upper boundary
        """
        baseline = engine.calculate_baseline_coaches('Beginner', 14)
        assert baseline == 2, "Beginner with 14 guests should still require 2 coaches"
    
    def test_beginner_threshold_15_guests(self, engine):
        """
        TEST 4: Beginner with 15 guests requires 3 baseline coaches (threshold crossed)
        Business Rule: 15+ guests = 3 coaches (add flowter)
        """
        baseline = engine.calculate_baseline_coaches('Beginner', 15)
        assert baseline == 3, "Beginner with 15+ guests should require 3 coaches"
    
    def test_beginner_at_capacity(self, engine):
        """
        TEST 5: Beginner at capacity (20) requires 3 baseline coaches
        Business Rule: 15+ guests = 3 coaches, even at max capacity
        """
        baseline = engine.calculate_baseline_coaches('Beginner', 20)
        assert baseline == 3, "Beginner at capacity should require 3 coaches"
    
    def test_novice_same_as_beginner(self, engine):
        """
        TEST 6: Novice follows same rules as Beginner
        Business Rule: Novice has identical baseline rules to Beginner
        """
        # Test multiple points
        assert engine.calculate_baseline_coaches('Novice', 0) == 0
        assert engine.calculate_baseline_coaches('Novice', 5) == 2
        assert engine.calculate_baseline_coaches('Novice', 15) == 3
    
    def test_progressive_boundary_9_guests(self, engine):
        """
        TEST 7: Progressive with 9 guests requires 1 baseline coach (boundary)
        Business Rule: 1-9 guests = 1 coach
        """
        baseline = engine.calculate_baseline_coaches('Progressive', 9)
        assert baseline == 1, "Progressive with 9 guests should require 1 coach"
    
    def test_progressive_threshold_10_guests(self, engine):
        """
        TEST 8: Progressive with 10 guests requires 2 baseline coaches (threshold)
        Business Rule: 10+ guests = 2 coaches
        """
        baseline = engine.calculate_baseline_coaches('Progressive', 10)
        assert baseline == 2, "Progressive with 10+ guests should require 2 coaches"
    
    def test_progressive_at_capacity(self, engine):
        """
        TEST 9: Progressive at capacity (18) requires 2 baseline coaches
        Business Rule: 10+ guests = 2 coaches, even at capacity
        """
        baseline = engine.calculate_baseline_coaches('Progressive', 18)
        assert baseline == 2, "Progressive at capacity should require 2 coaches"
    
    def test_intermediate_always_zero(self, engine):
        """
        TEST 10: Intermediate always requires 0 baseline coaches
        Business Rule: Advanced sessions have no baseline requirement
        """
        for guests in [0, 5, 10, 13]:
            baseline = engine.calculate_baseline_coaches('Intermediate', guests)
            assert baseline == 0, f"Intermediate with {guests} guests should require 0 baseline"
    
    def test_advanced_always_zero(self, engine):
        """
        TEST 11: Advanced always requires 0 baseline coaches
        Business Rule: Advanced sessions have no baseline requirement
        """
        baseline = engine.calculate_baseline_coaches('Advanced', 12)
        assert baseline == 0, "Advanced session should require 0 baseline coaches"
    
    def test_expert_always_zero(self, engine):
        """
        TEST 12: Expert always requires 0 baseline coaches
        Business Rule: Expert sessions have no baseline requirement
        """
        baseline = engine.calculate_baseline_coaches('Expert', 12)
        assert baseline == 0, "Expert session should require 0 baseline coaches"
    
    def test_pro_always_zero(self, engine):
        """
        TEST 13: Pro always requires 0 baseline coaches
        Business Rule: Pro sessions have no baseline requirement
        """
        baseline = engine.calculate_baseline_coaches('Pro', 10)
        assert baseline == 0, "Pro session should require 0 baseline coaches"
    
    def test_pro_barrel_always_zero(self, engine):
        """
        TEST 14: Pro Barrel always requires 0 baseline coaches
        Business Rule: Pro Barrel sessions have no baseline requirement
        """
        baseline = engine.calculate_baseline_coaches('Pro_Barrel', 10)
        assert baseline == 0, "Pro Barrel session should require 0 baseline coaches"


class TestPrivateLessons:
    """Tests for private lesson coach calculations"""
    
    def test_private_zero_lessons(self, engine):
        """
        TEST 15: Zero private lessons require 0 additional coaches
        Business Rule: No private lessons = no private coaches
        """
        private = engine.calculate_private_coaches(0)
        assert private == 0, "0 private lessons should require 0 coaches"
    
    def test_private_one_lesson(self, engine):
        """
        TEST 16: One private lesson requires 1 additional coach
        Business Rule: 1:1 ratio for private lessons
        """
        private = engine.calculate_private_coaches(1)
        assert private == 1, "1 private lesson should require 1 coach"
    
    def test_private_multiple_lessons(self, engine):
        """
        TEST 17: Multiple private lessons each require 1 coach
        Business Rule: Each private lesson adds 1 coach (no grouping)
        """
        assert engine.calculate_private_coaches(2) == 2
        assert engine.calculate_private_coaches(3) == 3
        assert engine.calculate_private_coaches(5) == 5


class TestTotalCalculation:
    """Tests for total coaching requirement (baseline + private)"""
    
    def test_total_beginner_with_private(self, engine):
        """
        TEST 18: Total = baseline + private
        Example: Beginner (5 guests) + 2 private = 2 + 2 = 4 total
        """
        baseline, private, total = engine.calculate_total_coaches('Beginner', 5, 2)
        assert baseline == 2, "Baseline should be 2"
        assert private == 2, "Private should be 2"
        assert total == 4, "Total should be 4"
    
    def test_total_intermediate_no_baseline_with_private(self, engine):
        """
        TEST 19: Intermediate has 0 baseline but adds private coaches
        Example: Intermediate (10 guests) + 1 private = 0 + 1 = 1 total
        """
        baseline, private, total = engine.calculate_total_coaches('Intermediate', 10, 1)
        assert baseline == 0, "Intermediate baseline should be 0"
        assert private == 1, "Private should be 1"
        assert total == 1, "Total should be 1"
    
    def test_total_progressive_threshold_with_private(self, engine):
        """
        TEST 20: Progressive at threshold + private
        Example: Progressive (10 guests) + 1 private = 2 + 1 = 3 total
        """
        baseline, private, total = engine.calculate_total_coaches('Progressive', 10, 1)
        assert baseline == 2, "Progressive 10+ baseline should be 2"
        assert private == 1, "Private should be 1"
        assert total == 3, "Total should be 3"
    
    def test_total_beginner_threshold_with_private(self, engine):
        """
        TEST 21: Beginner at threshold + multiple private
        Example: Beginner (15 guests) + 2 private = 3 + 2 = 5 total
        """
        baseline, private, total = engine.calculate_total_coaches('Beginner', 15, 2)
        assert baseline == 3, "Beginner 15+ baseline should be 3"
        assert private == 2, "Private should be 2"
        assert total == 5, "Total should be 5"


class TestNoCoachRequired:
    """Tests for 'no coach required' marking logic"""
    
    def test_no_coach_zero_guests_zero_private(self, engine):
        """
        TEST 22: Empty session = no coach required
        Business Rule: 0 guests AND 0 private = mark as no-coach-required
        """
        result = engine.is_no_coach_required('Beginner', 0, 0)
        assert result == True, "Empty session should be marked no-coach-required"
    
    def test_no_coach_intermediate_no_private(self, engine):
        """
        TEST 23: Intermediate with guests but no private = no coach required
        Business Rule: Intermediate+ with 0 private = no coach required
        """
        result = engine.is_no_coach_required('Intermediate', 10, 0)
        assert result == True, "Intermediate without private should be marked no-coach-required"
    
    def test_no_coach_intermediate_with_private(self, engine):
        """
        TEST 24: Intermediate with private lesson = coach required
        Business Rule: Private lesson overrides no-coach marking
        """
        result = engine.is_no_coach_required('Intermediate', 10, 1)
        assert result == False, "Intermediate with private should NOT be marked no-coach-required"
    
    def test_no_coach_beginner_with_guests(self, engine):
        """
        TEST 25: Beginner with guests = coach required
        Business Rule: Beginner sessions with guests need coaches
        """
        result = engine.is_no_coach_required('Beginner', 5, 0)
        assert result == False, "Beginner with guests should NOT be marked no-coach-required"
    
    def test_no_coach_advanced_types(self, engine):
        """
        TEST 26: All advanced types without private = no coach required
        Business Rule: Advanced/Expert/Pro/Pro_Barrel without private = no coach
        """
        for session_type in ['Advanced', 'Expert', 'Pro', 'Pro_Barrel']:
            result = engine.is_no_coach_required(session_type, 10, 0)
            assert result == True, f"{session_type} without private should be marked no-coach-required"


class TestValidation:
    """Tests for input validation"""
    
    def test_validation_unknown_session_type(self, engine):
        """
        TEST 27: Unknown session type raises ValueError
        Business Rule: Only defined session types are valid
        """
        with pytest.raises(ValueError) as exc_info:
            engine.calculate_baseline_coaches('UnknownType', 5)
        assert 'Unknown session type' in str(exc_info.value)
    
    def test_validation_over_capacity(self, engine):
        """
        TEST 28: Booking over capacity returns validation error
        Business Rule: Cannot book more than capacity allows
        """
        errors = engine.validate_session('Beginner', 25)
        assert len(errors) == 1, "Should have 1 validation error"
        assert 'exceeds capacity' in errors[0], "Error should mention capacity"
    
    def test_validation_negative_guests(self, engine):
        """
        TEST 29: Negative guest count returns validation error
        Business Rule: Guest count cannot be negative
        """
        errors = engine.validate_session('Beginner', -5)
        assert len(errors) == 1, "Should have 1 validation error"
        assert 'Negative guest count' in errors[0], "Error should mention negative count"
    
    def test_validation_valid_session(self, engine):
        """
        TEST 30: Valid session returns no errors
        """
        errors = engine.validate_session('Beginner', 15)
        assert len(errors) == 0, "Valid session should have no errors"


class TestCoachStartTime:
    """Tests for coach arrival time calculation"""
    
    def test_coach_start_time_30_minutes_before(self, engine):
        """
        TEST 31: Coach start time is 30 minutes before session
        Business Rule: Coaches arrive 30 minutes early for setup
        """
        session_start = datetime(2026, 2, 15, 11, 0, 0)
        coach_start = engine.calculate_coach_start_time(session_start)
        expected = datetime(2026, 2, 15, 10, 30, 0)
        assert coach_start == expected, "Coach start should be 30 minutes before session"
    
    def test_coach_start_time_various_hours(self, engine):
        """
        TEST 32: Coach start time works for various hours
        """
        test_times = [
            (datetime(2026, 2, 15, 9, 0, 0), datetime(2026, 2, 15, 8, 30, 0)),
            (datetime(2026, 2, 15, 14, 0, 0), datetime(2026, 2, 15, 13, 30, 0)),
            (datetime(2026, 2, 15, 16, 30, 0), datetime(2026, 2, 15, 16, 0, 0)),
        ]
        for session_start, expected_coach_start in test_times:
            coach_start = engine.calculate_coach_start_time(session_start)
            assert coach_start == expected_coach_start


class TestSessionProcessing:
    """Integration tests for complete session processing"""
    
    def test_full_session_processing_beginner(self, engine):
        """
        TEST 33: Complete session processing pipeline - Beginner
        Integration test: Process entire session from inputs to outputs
        """
        session = engine.process_session(
            datetime_start=datetime(2026, 2, 15, 12, 0, 0),
            side='LEFT',
            session_type='Beginner',
            booked_guests=16,
            private_lessons_count=1
        )
        
        # Verify all computed fields
        assert session.baseline_coaches == 3, "Baseline should be 3 (15+ guests)"
        assert session.private_coaches == 1, "Private should be 1"
        assert session.total_coaches_required == 4, "Total should be 4"
        assert session.is_no_coach_required == False, "Should require coaches"
        assert session.coach_start_time == datetime(2026, 2, 15, 11, 30, 0)
        
        # Verify original fields preserved
        assert session.datetime_start == datetime(2026, 2, 15, 12, 0, 0)
        assert session.side == 'LEFT'
        assert session.session_type == 'Beginner'
        assert session.booked_guests == 16
        assert session.private_lessons_count == 1
    
    def test_full_session_processing_intermediate(self, engine):
        """
        TEST 34: Complete session processing pipeline - Intermediate
        Integration test: Advanced session with private lessons
        """
        session = engine.process_session(
            datetime_start=datetime(2026, 2, 15, 14, 0, 0),
            side='RIGHT',
            session_type='Intermediate',
            booked_guests=13,
            private_lessons_count=2
        )
        
        assert session.baseline_coaches == 0, "Intermediate baseline is 0"
        assert session.private_coaches == 2, "Private should be 2"
        assert session.total_coaches_required == 2, "Total should be 2"
        assert session.is_no_coach_required == False, "Has private so requires coaches"
    
    def test_full_session_processing_empty(self, engine):
        """
        TEST 35: Complete session processing - Empty session
        Integration test: No guests, no private lessons
        """
        session = engine.process_session(
            datetime_start=datetime(2026, 2, 15, 16, 0, 0),
            side='LEFT',
            session_type='Pro',
            booked_guests=0,
            private_lessons_count=0
        )
        
        assert session.baseline_coaches == 0
        assert session.private_coaches == 0
        assert session.total_coaches_required == 0
        assert session.is_no_coach_required == True, "Empty session marked as no-coach-required"


class TestBatchProcessing:
    """Tests for CSV-like batch processing"""
    
    def test_batch_processing_multiple_sessions(self, engine):
        """
        TEST 36: Process multiple sessions from CSV-like data
        Integration test: Batch processing workflow
        """
        sample_data = [
            {
                'datetime_start': datetime(2026, 2, 15, 11, 0, 0),
                'side': 'LEFT',
                'session_type': 'Pro',
                'booked_guests': 6,
                'private_lessons_count': 0
            },
            {
                'datetime_start': datetime(2026, 2, 15, 12, 0, 0),
                'side': 'LEFT',
                'session_type': 'Novice',
                'booked_guests': 7,
                'private_lessons_count': 1
            },
            {
                'datetime_start': datetime(2026, 2, 15, 12, 0, 0),
                'side': 'RIGHT',
                'session_type': 'Novice',
                'booked_guests': 15,
                'private_lessons_count': 0
            },
        ]
        
        sessions, errors = engine.process_csv_data(sample_data)
        
        assert len(errors) == 0, "Should have no validation errors"
        assert len(sessions) == 3, "Should process all 3 sessions"
        
        # Verify individual sessions
        assert sessions[0].total_coaches_required == 0  # Pro with no private
        assert sessions[1].total_coaches_required == 3  # Novice 7 guests + 1 private
        assert sessions[2].total_coaches_required == 3  # Novice 15 guests
    
    def test_batch_processing_with_validation_errors(self, engine):
        """
        TEST 37: Batch processing with invalid data
        Integration test: Validation error handling in batch
        """
        sample_data = [
            {
                'datetime_start': datetime(2026, 2, 15, 11, 0, 0),
                'side': 'LEFT',
                'session_type': 'Beginner',
                'booked_guests': 25,  # Over capacity!
                'private_lessons_count': 0
            },
            {
                'datetime_start': datetime(2026, 2, 15, 12, 0, 0),
                'side': 'LEFT',
                'session_type': 'Novice',
                'booked_guests': 10,  # Valid
                'private_lessons_count': 1
            },
        ]
        
        sessions, errors = engine.process_csv_data(sample_data)
        
        assert len(errors) == 1, "Should have 1 validation error"
        assert 'exceeds capacity' in errors[0], "Error should mention capacity"
        assert len(sessions) == 1, "Should only process the valid session"
        assert sessions[0].session_type == 'Novice', "Valid session should be processed"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""
    
    def test_edge_case_all_boundaries(self, engine):
        """
        TEST 38: Test all boundary values
        Edge case: Test every threshold boundary
        """
        test_cases = [
            ('Beginner', 0, 0),    # Lower boundary
            ('Beginner', 1, 2),    # Just over lower boundary
            ('Beginner', 14, 2),   # Upper boundary of tier 1
            ('Beginner', 15, 3),   # Lower boundary of tier 2
            ('Progressive', 0, 0), # Lower boundary
            ('Progressive', 1, 1), # Just over lower boundary
            ('Progressive', 9, 1), # Upper boundary of tier 1
            ('Progressive', 10, 2), # Lower boundary of tier 2
        ]
        
        for session_type, guests, expected_baseline in test_cases:
            baseline = engine.calculate_baseline_coaches(session_type, guests)
            assert baseline == expected_baseline, \
                f"{session_type} with {guests} should have {expected_baseline} baseline"
    
    def test_edge_case_max_capacity_all_types(self, engine):
        """
        TEST 39: Test at maximum capacity for all session types
        Edge case: Verify behavior at capacity limits
        """
        capacity_tests = [
            ('Beginner', 20, 3),
            ('Novice', 19, 3),
            ('Progressive', 18, 2),
            ('Intermediate', 13, 0),
            ('Advanced', 12, 0),
            ('Expert', 12, 0),
            ('Pro', 10, 0),
            ('Pro_Barrel', 10, 0),
        ]
        
        for session_type, capacity, expected_baseline in capacity_tests:
            baseline = engine.calculate_baseline_coaches(session_type, capacity)
            assert baseline == expected_baseline, \
                f"{session_type} at capacity should have {expected_baseline} baseline"
    
    def test_edge_case_private_lessons_with_zero_baseline(self, engine):
        """
        TEST 40: Private lessons work even when baseline is 0
        Edge case: Private lessons still require coaches for advanced sessions
        """
        # Intermediate with 10 guests (0 baseline) + 3 private lessons
        baseline, private, total = engine.calculate_total_coaches('Intermediate', 10, 3)
        assert baseline == 0, "Intermediate should have 0 baseline"
        assert private == 3, "Should have 3 private coaches"
        assert total == 3, "Total should equal private when baseline is 0"


def run_all_tests():
    """Run all tests and print summary"""
    import sys
    
    # Run pytest
    exit_code = pytest.main([__file__, '-v', '--tb=short'])
    
    if exit_code == 0:
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print(f"\n40+ comprehensive test cases validated successfully:")
        print("  ✓ Baseline calculation (14 tests)")
        print("  ✓ Private lesson calculation (3 tests)")
        print("  ✓ Total calculation (4 tests)")
        print("  ✓ No-coach-required logic (5 tests)")
        print("  ✓ Input validation (4 tests)")
        print("  ✓ Coach start time (2 tests)")
        print("  ✓ Session processing (3 tests)")
        print("  ✓ Batch processing (2 tests)")
        print("  ✓ Edge cases (3 tests)")
        print("\nRules engine is production-ready! ✨")
    else:
        print("\n" + "=" * 80)
        print("❌ SOME TESTS FAILED")
        print("=" * 80)
        print("Review the output above to see which tests failed.")
    
    return exit_code


if __name__ == "__main__":
    run_all_tests()
