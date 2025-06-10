"""
Computer Agent Context - Manages agent state and execution context
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import os
from pathlib import Path
from config.log_config import log_step, log_json_block, setup_logging, logger_json_block

logger = setup_logging(__name__)

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
        
        # Add state management (similar to browser agent)
        self.current_state: Dict[str, Any] = {}
        self.state_history: List[Dict[str, Any]] = []
        self.failed_steps: List[str] = []
        
        # Add memory management (similar to browser agent)
        self.memory: List[Dict[str, Any]] = []
        self.globals: Dict[str, Any] = {}
        self.global_history: Dict[str, List[Any]] = {}
        
        # Add cycle tracking directly in context (like browser agent)
        self.perception_history: List[Dict[str, Any]] = []
        self.decision_history: List[Dict[str, Any]] = []
        self.execution_history: List[Dict[str, Any]] = []
        
        # Add new fields as strings
        self.open_windows = ""  # Will store JSON string of open windows
        self.computer_state = ""  # Will store JSON string of computer state
        
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

    def update_open_windows(self, windows_json: str) -> None:
        """Update the open windows information as a JSON string"""
        self.open_windows = windows_json

    def update_computer_state(self, state_json: str) -> None:
        """Update the computer state information as a JSON string"""
        self.computer_state = state_json

    def save_summary(self) -> str:
        """Save the session summary to a JSON file"""
        summary = {
            "session_id": self.session_id,
            "query": self.query,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "steps": [step.to_dict() for step in self.steps.values()],
            "pipeline_output": self.pipeline_output,
            "screenshot_path": str(self.screenshot_path) if self.screenshot_path else None,
            "open_windows": self.open_windows,  # Already a string
            "computer_state": self.computer_state  # Already a string
        }
        
        output_file = self.output_dir / "session_summary.json"
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)
            
        return str(output_file)

    def print_cycle_steps(self, cycle_number: int) -> None:
        """
        Log all steps from all cycles up to the current cycle number
        
        Args:
            cycle_number: The current cycle number
        """
        
        if cycle_number <= 0:
            return
        
        # Log session header
        log_step(f"📋 Session Steps Summary (Up to Cycle {cycle_number})")
        
        # Iterate through all cycles up to current
        for current_cycle in range(1, cycle_number + 1):
            # Get steps for this cycle
            cycle_steps = []
            for step_id, step in self.steps.items():
                if step_id.startswith(f"PERCEPTION_{current_cycle}") or \
                   step_id.startswith(f"DECISION_{current_cycle}") or \
                   step_id.startswith(f"TOOL_{current_cycle}"):
                    cycle_steps.append(step)
            
            # Sort steps by their sequence
            cycle_steps.sort(key=lambda x: x.id)
            
            # Log cycle header
            log_step(f"🔄 Cycle {current_cycle}")
            
            # Log each step in sequence
            for step in cycle_steps:
                # Create step header with status indicator
                status_emoji = "✅" if step.status == "completed" else "❌" if step.status == "failed" else "⏳"
                log_step(f"{status_emoji} {step.id} - {step.type}")
                
                # Log step details in a compact format
                step_info = {
                    "Description": step.description,
                    "From Step": step.from_step,
                    "Timestamp": step.timestamp,
                    "Status": step.status
                }
                log_json_block("Step Info", step_info)
                
                # Log step result if exists
                if step.result:
                    if step.type == "TOOL_EXECUTION":
                        # For tool execution, show success and message
                        result_info = {
                            "Success": step.result.get("success", False),
                            "Message": step.result.get("message", "No message")
                        }
                    else:
                        # For perception and decision, show key information
                        result_info = {
                            "Key Points": {
                                k: v for k, v in step.result.items() 
                                if k in ["selected_tool", "tool_parameters", "confidence", "route", "local_goal_achieved"]
                            }
                        }
                    log_json_block("Result", result_info)
            
            # Log cycle summary
            log_step(f"📊 Cycle {current_cycle} Summary")
            logger.info(f"• Steps: {', '.join(step.id for step in cycle_steps)}")
            logger.info(f"• Status: {'✅ Completed' if all(step.status == 'completed' for step in cycle_steps) else '❌ Failed'}")
            logger.info(f"• Goal Achieved: {'✅ Yes' if self.perception_history[current_cycle-1].get('local_goal_achieved', False) else '❌ No'}")
            
            # Add separator between cycles
            if current_cycle < cycle_number:
                log_step("=" * 80)

    def record_cycle(self, perception: Dict[str, Any], decision: Dict[str, Any], execution: Dict[str, Any]) -> None:
        """Record a complete perception-decision-execution cycle"""
        # Record the cycle data
        self.perception_history.append(perception)
        self.decision_history.append(decision)
        self.execution_history.append(execution)
        
        # Update state with cycle information
        self.update_state({
            "last_cycle": {
                "perception": perception,
                "decision": decision,
                "execution": execution,
                "timestamp": datetime.now().isoformat()
            }
        })
        
        # Log cycle summary with proper formatting
        #cycle_number = len(self.perception_history)
        
        # Log perception
        #log_step("🧠 Running perception analysis")
        #log_json_block(f"📌 📌 Perception output ({cycle_number})", perception)
        
        # Log decision
        #log_step("🤔 Making decision")
        #log_json_block(f"📌 📌 Decision output ({cycle_number})", decision)
        
        # Log execution
        #log_step(f"🛠️ Executing tool: {decision.get('selected_tool', 'unknown')}")
        #log_json_block(f"📌 📌 Execution output ({cycle_number})", execution)
        
        # Log cycle status
        #log_step("📊 Cycle Status")
        #logger.info(f"• Goal Achieved: {perception.get('local_goal_achieved', False)}")
        #logger.info(f"• Confidence: {perception.get('confidence', 'N/A')}")
        #logger.info(f"• Route: {perception.get('route', 'N/A')}")
        #logger.info(f"• Computer State: {perception.get('computer_state', 'N/A')}")

    def update_state(self, new_state: Dict[str, Any]) -> None:
        """Update the current state with new values"""
        self.current_state.update(new_state)
        self.state_history.append({
            "timestamp": datetime.now().isoformat(),
            "state": self.current_state.copy()
        })

    def update_globals(self, new_vars: Dict[str, Any]) -> None:
        """Update global variables with versioning"""
        for k, v in new_vars.items():
            if k in self.globals:
                versioned_key = f"{k}__{len(self.global_history.get(k, []))}"
                self.globals[versioned_key] = v
                if k not in self.global_history:
                    self.global_history[k] = []
                self.global_history[k].append(v)
            else:
                self.globals[k] = v
                self.global_history[k] = [v]
