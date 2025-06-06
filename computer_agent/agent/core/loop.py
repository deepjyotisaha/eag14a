"""
Computer Agent Loop - Main execution loop for the computer agent
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

from .context import ComputerAgentContext, StepType
from pipeline.screenshot import take_screenshot
from pipeline.pipeline import run_pipeline
from utils.output_manager import get_output_folder
from config.log_config import setup_logging

# Set up logging
logger = setup_logging(__name__)


class ComputerAgentLoop:
    def __init__(self, multi_mcp):
        """
        Initialize the computer agent loop
        
        Args:
            multi_mcp: MultiMCP instance for tool execution
        """
        self.multi_mcp = multi_mcp
        self.max_steps = 10  # Maximum number of steps per session
        self.max_retries = 3  # Maximum retries per step
        
    async def run(self, query: str) -> Dict[str, Any]:
        """
        Run the computer agent loop
        
        Args:
            query: User's query
            
        Returns:
            Dict containing the result of the operation
        """
        # Create session ID and context
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir = get_output_folder(session_id)
        ctx = ComputerAgentContext(session_id, query)
        
        try:
            logger.info(f"Starting computer agent session {session_id}")
            
            # Step 1: Take screenshot and run pipeline
            screenshot_path = take_screenshot(output_dir=str(ctx.output_dir))
            ctx.screenshot_path = screenshot_path
            
            # Run pipeline on screenshot
            pipeline_result = await run_pipeline(screenshot_path, mode="deploy_mcp", output_dir=str(ctx.output_dir))
            ctx.pipeline_output = pipeline_result
            
            # Add perception step
            perception_step = ctx.add_step(
                "PERCEPTION_1",
                "Initial perception of screen state",
                StepType.PERCEPTION,
                from_step="ROOT"
            )
            
            # TODO: Add perception logic here using pipeline_result
            # For now, we'll just mark it as completed
            ctx.mark_step_completed("PERCEPTION_1", pipeline_result)
            
            # Step 2: Decision making
            decision_step = ctx.add_step(
                "DECISION_1",
                "Decide next action based on perception",
                StepType.DECISION,
                from_step="PERCEPTION_1"
            )
            
            # TODO: Add decision logic here
            # For now, we'll just mark it as completed
            ctx.mark_step_completed("DECISION_1", {"action": "example_action"})
            
            # Step 3: Tool execution
            tool_step = ctx.add_step(
                "TOOL_1",
                "Execute decided action",
                StepType.TOOL_EXECUTION,
                from_step="DECISION_1"
            )
            
            # TODO: Add tool execution logic here
            # For now, we'll just mark it as completed
            ctx.mark_step_completed("TOOL_1", {"result": "example_result"})
            
            # Save session summary
            summary_path = ctx.save_summary()
            logger.info(f"Session summary saved to {summary_path}")
            
            return {
                "status": "success",
                "session_id": session_id,
                "summary_path": summary_path,
                "steps": [step.to_dict() for step in ctx.steps.values()]
            }
            
        except Exception as e:
            logger.error(f"Error in computer agent session {session_id}: {str(e)}")
            if ctx.current_step:
                ctx.mark_step_failed(ctx.current_step.id, str(e))
            
            # Save session summary even if there was an error
            summary_path = ctx.save_summary()
            
            return {
                "status": "failed",
                "session_id": session_id,
                "error": str(e),
                "summary_path": summary_path,
                "steps": [step.to_dict() for step in ctx.steps.values()]
            }
