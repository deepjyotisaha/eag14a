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
from config.log_config import setup_logging, logger_json_block
from agent.core.perception import Perception
from agent.core.decision import Decision

# Set up logging
logger = setup_logging(__name__)


class ComputerAgentLoop:
    def __init__(self, multi_mcp, model_manager):
        """
        Initialize the computer agent loop
        
        Args:
            multi_mcp: MultiMCP instance for tool execution
            model_manager: ModelManager instance for LLM integration
        """
        self.multi_mcp = multi_mcp
        self.model_manager = model_manager
        self.perception = Perception(model_manager)
        self.decision = Decision(model_manager, multi_mcp)
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
        logger.info(f"Output directory: {output_dir}")
        ctx = ComputerAgentContext(session_id, query)
        
        try:
            logger.info(f"Starting computer agent session {session_id}")
            step_count = 0
            
            while step_count < self.max_steps:
                # Step 1: Take screenshot and run pipeline for current state
                screenshot_path = take_screenshot(output_dir=str(ctx.output_dir))
                ctx.screenshot_path = screenshot_path
                logger.info(f"Screenshot taken and saved to {screenshot_path}")
                
                # Run pipeline on screenshot
                pipeline_result = await run_pipeline(screenshot_path, mode="debug", output_dir=str(ctx.output_dir))
                ctx.pipeline_output = pipeline_result
                
                # Step 2: Perception
                perception_step = ctx.add_step(
                    f"PERCEPTION_{step_count + 1}",
                    "Analyzing current screen state",
                    StepType.PERCEPTION,
                    from_step="ROOT" if step_count == 0 else f"TOOL_{step_count}"
                )
                
                if step_count == 0:
                    snapshot_type = "user_query"
                else:
                    snapshot_type = "step_result"

                perception = await self.perception.analyze(
                    ctx, 
                    pipeline_result,
                    snapshot_type=snapshot_type
                )
                ctx.mark_step_completed(perception_step.id, perception)
                
                # Check if we should exit
                if perception.get("route") == "summarize":
                    logger.info("Perception suggests summarization - task complete")
                    return {
                        "status": "success",
                        "session_id": session_id,
                        "summary": perception.get("solution_summary", "Task completed"),
                        "steps": [step.to_dict() for step in ctx.steps.values()]
                    }
                
                # Step 3: Decision
                decision_step = ctx.add_step(
                    f"DECISION_{step_count + 1}",
                    "Deciding next action",
                    StepType.DECISION,
                    from_step=f"PERCEPTION_{step_count + 1}"
                )
                
                decision = await self.decision.decide(ctx, perception)
                ctx.mark_step_completed(decision_step.id, decision)
                
                # Step 4: Tool Execution
                if not decision.get("selected_tool"):
                    logger.warning("No tool selected by decision module")
                    break
                    
                tool_step = ctx.add_step(
                    f"TOOL_{step_count + 1}",
                    f"Executing {decision['selected_tool']}",
                    StepType.TOOL_EXECUTION,
                    from_step=f"DECISION_{step_count + 1}"
                )
                
                # Execute tool with retries
                retry_count = 0
                while retry_count < self.max_retries:
                    try:
                        result = await self.multi_mcp.execute_tool(
                            decision["selected_tool"],
                            decision["tool_parameters"]
                        )
                        ctx.mark_step_completed(tool_step.id, result)
                        break
                    except Exception as e:
                        retry_count += 1
                        if retry_count == self.max_retries:
                            ctx.mark_step_failed(tool_step.id, str(e))
                            raise
                        logger.warning(f"Tool execution failed, retrying ({retry_count}/{self.max_retries})")
                        await asyncio.sleep(1)  # Wait before retry
                
                step_count += 1
            
            # If we've reached max steps without completion
            if step_count >= self.max_steps:
                logger.warning(f"Reached maximum steps ({self.max_steps}) without completion")
                return {
                    "status": "max_steps_reached",
                    "session_id": session_id,
                    "error": f"Maximum steps ({self.max_steps}) reached without completion",
                    "steps": [step.to_dict() for step in ctx.steps.values()]
                }
            
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
