"""
Integration tests for Per-Field Confidence Router with existing system components.

Tests integration with existing event parsing pipeline and data models.
"""

import pytest
from datetime import datetime, timedelta
from services.per_field_confidence_router import PerFieldConfidenceRouter, ProcessingMethod
from models.event_models import FieldResult, ParsedEvent


class TestPerFieldConfidenceRouterIntegration:
    """Integration test suite for PerFieldConfidenceRouter."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.router = PerFieldConfidenceRouter()
    
    def test_integration_with_parsed_event(self):
        """Test router integration with ParsedEvent model."""
        # Create a ParsedEvent with field results
        now = datetime.now()
        parsed_event = ParsedEvent(
            title="Team Meeting",
            start_datetime=now,
            end_datetime=now + timedelta(hours=1),
            location="Conference Room A",
            confidence_score=0.8
        )
        
        # Add field results
        parsed_event.set_field_result('title', FieldResult(
            value="Team Meeting",
            source="regex",
            confidence=0.9,
            span=(0, 12)
        ))
        
        parsed_event.set_field_result('start_datetime', FieldResult(
            value=now,
            source="regex",
            confidence=0.95,
            span=(13, 25)
        ))
        
        parsed_event.set_field_result('location', FieldResult(
            value="Conference Room A",
            source="regex",
            confidence=0.8,
            span=(26, 43)
        ))
        
        # Validate field consistency using router
        validation = self.router.validate_field_consistency(parsed_event.field_results)
        
        assert validation.is_valid
        assert len(validation.missing_fields) == 0
        assert len(validation.warnings) == 0
    
    def test_routing_recommendations_for_real_text(self):
        """Test routing recommendations for realistic text scenarios."""
        test_cases = [
            {
                'text': "Meeting tomorrow at 2pm",
                'expected_high_confidence': ['start_datetime'],
                'expected_low_confidence': ['title', 'location']
            },
            {
                'text': "Annual Sales Conference on October 15, 2025 from 9am to 5pm at Convention Center",
                'expected_high_confidence': ['start_datetime', 'end_datetime', 'title', 'location'],
                'expected_low_confidence': []
            },
            {
                'text': "Team lunch with john.doe@company.com next Friday",
                'expected_high_confidence': ['start_datetime', 'participants'],
                'expected_low_confidence': ['location']
            }
        ]
        
        for case in test_cases:
            analyses = self.router.analyze_field_extractability(case['text'])
            
            # Check high confidence fields
            for field in case['expected_high_confidence']:
                if field in analyses:
                    assert analyses[field].confidence_potential >= 0.6, \
                        f"Field {field} should have high confidence for text: {case['text']}"
                    assert analyses[field].recommended_method in [ProcessingMethod.REGEX, ProcessingMethod.DETERMINISTIC], \
                        f"Field {field} should use regex/deterministic method"
            
            # Check low confidence fields
            for field in case['expected_low_confidence']:
                if field in analyses:
                    assert analyses[field].confidence_potential < 0.8, \
                        f"Field {field} should have lower confidence for text: {case['text']}"
    
    def test_processing_order_optimization_realistic(self):
        """Test processing order optimization with realistic field combinations."""
        # Scenario: User wants to parse all fields
        all_fields = ['title', 'start_datetime', 'end_datetime', 'location', 'participants', 'description']
        
        optimized_order = self.router.optimize_processing_order(all_fields)
        
        # Verify critical dependencies
        start_idx = optimized_order.index('start_datetime')
        end_idx = optimized_order.index('end_datetime')
        desc_idx = optimized_order.index('description')
        
        # start_datetime should be processed first
        assert start_idx == 0, "start_datetime should be processed first"
        
        # end_datetime should be after start_datetime
        assert end_idx > start_idx, "end_datetime should be processed after start_datetime"
        
        # description should be last (can be enhanced based on other fields)
        assert desc_idx == len(optimized_order) - 1, "description should be processed last"
    
    def test_field_consistency_validation_edge_cases(self):
        """Test field consistency validation with edge cases."""
        now = datetime.now()
        
        # Test case: Very short event duration
        results = {
            'title': FieldResult(value="Quick sync", source="regex", confidence=0.9, span=(0, 10)),
            'start_datetime': FieldResult(value=now, source="regex", confidence=0.9, span=(11, 20)),
            'end_datetime': FieldResult(value=now + timedelta(minutes=5), source="regex", confidence=0.9, span=(21, 30))
        }
        
        validation = self.router.validate_field_consistency(results)
        # Should have warning about very short duration
        assert 'end_datetime' in validation.field_warnings
        
        # Test case: Very long event duration
        results['end_datetime'] = FieldResult(
            value=now + timedelta(hours=30), 
            source="regex", 
            confidence=0.9, 
            span=(21, 30)
        )
        
        validation = self.router.validate_field_consistency(results)
        # Should have warning about very long duration
        assert 'end_datetime' in validation.field_warnings
    
    def test_confidence_threshold_adjustments_in_practice(self):
        """Test how confidence threshold adjustments work in practice."""
        # Test with location field (has -0.1 adjustment)
        location_confidence = 0.65  # Just above medium threshold
        method = self.router.route_processing_method('location', location_confidence)
        # With -0.1 adjustment: 0.65 - 0.1 = 0.55, which should route to LLM
        assert method == ProcessingMethod.LLM
        
        # Test with essential field (no adjustment)
        title_confidence = 0.65
        method = self.router.route_processing_method('title', title_confidence)
        # No adjustment: 0.65 >= 0.6, should route to deterministic
        assert method == ProcessingMethod.DETERMINISTIC
        
        # Test with description field (has -0.2 adjustment)
        desc_confidence = 0.55
        method = self.router.route_processing_method('description', desc_confidence)
        # With -0.2 adjustment: 0.55 - 0.2 = 0.35, which should skip
        assert method == ProcessingMethod.SKIP
    
    def test_routing_summary_for_audit_mode(self):
        """Test routing summary generation for audit mode API responses."""
        text = """
        Subject: Weekly Team Standup
        
        Our weekly standup meeting is scheduled for this Friday at 10:00 AM 
        in the main conference room. Please bring your status updates.
        
        Meeting will last for 1 hour.
        """
        
        analyses = self.router.analyze_field_extractability(text)
        summary = self.router.get_field_routing_summary(analyses)
        
        # Verify summary structure for audit mode
        required_keys = [
            'total_fields', 'routing_decisions', 'confidence_breakdown',
            'processing_order', 'high_confidence_fields', 'low_confidence_fields',
            'complexity_analysis', 'average_confidence', 'min_confidence', 'max_confidence'
        ]
        
        for key in required_keys:
            assert key in summary, f"Summary missing required key: {key}"
        
        # Verify routing decisions are valid
        for field, method in summary['routing_decisions'].items():
            assert method in ['regex', 'deterministic', 'llm', 'skip']
        
        # Verify confidence scores are in valid range
        for field, confidence in summary['confidence_breakdown'].items():
            assert 0.0 <= confidence <= 1.0
        
        # Verify processing order contains all analyzed fields
        assert len(summary['processing_order']) == len(analyses)
        assert set(summary['processing_order']) == set(analyses.keys())
    
    def test_real_world_email_parsing_scenario(self):
        """Test router with real-world email parsing scenario."""
        email_text = """
        From: manager@company.com
        To: team@company.com
        Subject: Q1 All-Hands Meeting
        
        Hi everyone,
        
        I'm scheduling our quarterly all-hands meeting for next Tuesday, 
        January 15th from 2:00 PM to 4:00 PM in the large auditorium.
        
        We'll be discussing Q4 results and Q1 goals. Please come prepared
        with your team updates.
        
        The meeting will be recorded for remote team members.
        
        Best regards,
        Sarah
        """
        
        # Analyze the email
        analyses = self.router.analyze_field_extractability(email_text)
        
        # Should detect multiple fields
        assert len(analyses) >= 4
        
        # Should have high confidence for several fields
        high_confidence_fields = [
            field for field, analysis in analyses.items() 
            if analysis.confidence_potential >= 0.8
        ]
        assert len(high_confidence_fields) >= 2
        
        # Generate processing recommendations
        summary = self.router.get_field_routing_summary(analyses)
        
        # Should recommend regex/deterministic for high-confidence fields
        regex_fields = [
            field for field, method in summary['routing_decisions'].items()
            if method == 'regex'
        ]
        assert len(regex_fields) >= 1
        
        # Verify processing order makes sense
        processing_order = summary['processing_order']
        if 'start_datetime' in processing_order:
            assert processing_order[0] == 'start_datetime'
        
        if 'description' in processing_order:
            assert processing_order[-1] == 'description'


if __name__ == '__main__':
    pytest.main([__file__])