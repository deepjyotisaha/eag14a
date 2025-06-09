"""
Execution Tracker - Manages execution attempts and retries
"""
from collections import defaultdict
from typing import Dict

class ExecutionTracker:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.attempts: Dict[str, int] = defaultdict(int)
        
    def should_retry(self, step_id: str) -> bool:
        """Check if step should be retried"""
        return self.attempts[step_id] < self.max_retries
        
    def record_attempt(self, step_id: str) -> None:
        """Record an execution attempt"""
        self.attempts[step_id] += 1
