"""
Computer Agent Context - Manages agent state and execution context
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import os
from pathlib import Path

class StepType:
    ROOT = "ROOT"
    PERCEPTION = "PERCEPTION"
    DECISION = "DECISION"
    TOOL_EXECUTION = "TOOL_EXECUTION"

class Step:
    def __init__(self, step_id: str, description: str, step_type: str, from_step: Optional[str] = None):
        self.id = step_id
        self.description = description
        self.type = step_type
        self.from_step = from_step
        self.status = "pending"  # pending, completed, failed
        self.result = None
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "type": self.type,
            "from_step": self.from_step,
            "status": self.status,
            "result": self.result,
            "timestamp": self.timestamp
        }

class ComputerAgentContext:
    def __init__(self, session_id: str, query: str):
        self.session_id = session_id
        self.query = query
        self.steps: Dict[str, Step] = {}
        self.current_step = None
        self.pipeline_output = None  # Stores the enhanced pipeline output
        self.screenshot_path = None
        self.start_time = datetime.now()
        
        # Create output directory for this session
        self.output_dir = Path(f"outputs/{datetime.now().strftime('%Y/%m/%d')}/{session_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize with root step
        self.add_step("ROOT", "Initial query", StepType.ROOT)

    def add_step(self, step_id: str, description: str, step_type: str, from_step: Optional[str] = None) -> Step:
        """Add a new step to the context"""
        step = Step(step_id, description, step_type, from_step)
        self.steps[step_id] = step
        self.current_step = step
        return step

    def mark_step_completed(self, step_id: str, result: Any = None) -> None:
        """Mark a step as completed with optional result"""
        if step_id in self.steps:
            self.steps[step_id].status = "completed"
            self.steps[step_id].result = result

    def mark_step_failed(self, step_id: str, error: str) -> None:
        """Mark a step as failed with error message"""
        if step_id in self.steps:
            self.steps[step_id].status = "failed"
            self.steps[step_id].result = {"error": error}

    def get_step(self, step_id: str) -> Optional[Step]:
        """Get a step by ID"""
        return self.steps.get(step_id)

    def save_summary(self) -> str:
        """Save the session summary to a JSON file"""
        summary = {
            "session_id": self.session_id,
            "query": self.query,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "steps": [step.to_dict() for step in self.steps.values()],
            "pipeline_output": self.pipeline_output,
            "screenshot_path": str(self.screenshot_path) if self.screenshot_path else None
        }
        
        output_file = self.output_dir / "session_summary.json"
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)
            
        return str(output_file)
