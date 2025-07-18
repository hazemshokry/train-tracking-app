# app/services/scoring_service.py

class ScoringService:
    WEIGHTS = {
        'time_valid': 0.25,
        'location_valid': 0.20,
        'consistency_valid': 0.20,
        'pattern_valid': 0.15,
        'route_valid': 0.15,
        'rate_limit_valid': 0.10, # Note: total weights > 1.0, adjusted for impact
        'duplicate_valid': 0.10,
    }

    def __init__(self, validation_results, user):
        self.validation_results = validation_results
        self.user = user

    def calculate_score(self):
        base_score = 0.0
        for key, weight in self.WEIGHTS.items():
            if self.validation_results.get(key):
                base_score += weight
        
        # Factor in user reliability
        # Final score is a blend of validation score and user's historic reliability
        final_score = (base_score * 0.7) + (self.user.reliability_score * 0.3)
        
        return min(max(final_score, 0.0), 1.0) # Clamp between 0.0 and 1.0