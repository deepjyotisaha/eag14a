"""
Computer Agent Loop - Main execution loop for the computer agent
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

from .context import ComputerAgentContext, StepType, Step
from pipeline.screenshot import take_screenshot
from pipeline.pipeline import run_pipeline
from utils.output_manager import get_output_folder
from config.log_config import setup_logging, log_step, logger_json_block, log_json_block
from agent.core.perception import Perception
from agent.core.decision import Decision
from agent.core.summary import Summary

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
        self.summary = Summary(model_manager)
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
        base_output_dir = get_output_folder(session_id)  # Store base output directory
        logger.info(f"Output directory: {base_output_dir}")
        ctx = ComputerAgentContext(session_id, query)
        
        try:
            logger.info(f"Starting computer agent session {session_id}")
            step_count = 0
            
            while step_count < self.max_steps:
                log_step(f"🔄 Starting new cycle with step count {step_count + 1}")
                logger.info(f"🔄 Starting new cycle with step count {step_count + 1}")

                # Create step directory at the same level
                step_output_dir = base_output_dir.joinpath(f"step_{step_count + 1}")
                step_output_dir.mkdir(parents=True, exist_ok=True)

                # Step 1: Take screenshot and run pipeline for current state
                log_step("📸 Taking screenshot")
                screenshot_path = take_screenshot(
                    output_dir=str(step_output_dir),
                    suffix=f"step_{step_count + 1}"
                )
                ctx.screenshot_path = screenshot_path
                logger.info(f"Screenshot taken and saved to {screenshot_path}")
                
                # Run pipeline on screenshot
                log_step("🔍 Running image processing pipeline")
                pipeline_result = await run_pipeline(screenshot_path, mode="mcp_deploy", output_dir=str(step_output_dir))
                ctx.pipeline_output = pipeline_result
                #log_json_block("Pipeline Result", pipeline_result)
                log_step("🔍 Image processing pipeline completed")
                
                #pipeline_result = {"pipeline_output": "No Screenshot"}
                
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

                log_step(f"🧠 Running perception analysis for step {step_count + 1}")
                logger.info(f"🧠 Running perception analysis for step {step_count + 1}")
                perception = await self.perception.analyze(
                    ctx, 
                    pipeline_result,
                    snapshot_type=snapshot_type
                )
                logger.info(f"🧠 Perception analysis completed for step {step_count + 1}")
                ctx.mark_step_completed(perception_step.id, perception)
                log_json_block(f"📌 Perception output for step {step_count + 1}", perception, char_limit=2000)
                
                # When perception suggests summarization
                if perception.get("route") == "summarize":
                    logger.info("Perception suggests summarization - task complete")
                    log_step(f"🔄 Summarization task complete for step {step_count + 1}")
                    #ctx.print_cycle_steps(step_count + 1)
                    return await self.summary.summarize(query, ctx, perception)
                
                # Step 3: Decision
                decision_step = ctx.add_step(
                    f"DECISION_{step_count + 1}",
                    "Deciding next action",
                    StepType.DECISION,
                    from_step=f"PERCEPTION_{step_count + 1}"
                )
                
                log_step(f"🤔 Making decision for step {step_count + 1}")
                logger.info(f"🤔 Making decision for step {step_count + 1}")
                decision = await self.decision.decide(ctx, perception)
                logger.info(f"🤔 Decision completed for step {step_count + 1}")
                ctx.mark_step_completed(decision_step.id, decision)
                log_json_block(f"📌 Decision output for step {step_count + 1}", decision)
                
                # Step 4: Tool Execution
                if not decision.get("selected_tool"):
                    logger.warning(f"🔄 No tool selected by decision module for step {step_count + 1}")
                    log_step(f"🔄 No tool selected by decision module for step {step_count + 1}")
                    break
                    
                tool_step = ctx.add_step(
                    f"TOOL_{step_count + 1}",
                    f"Executing {decision['selected_tool']}",
                    StepType.TOOL_EXECUTION,
                    from_step=f"DECISION_{step_count + 1}"
                )
                
                # Log tool execution details
                log_step(f"🛠️ Executing tool for step {step_count + 1}: {decision['selected_tool']}", decision["tool_parameters"])
                logger.info(f"🛠️ Executing tool for step {step_count + 1}: {decision['selected_tool']}")
                logger.info(f"🛠️ Tool Parameters for step {step_count + 1}: {decision['tool_parameters']}")
                #log_json_block(f"📌 Tool Parameters for step {step_count + 1}", decision["tool_parameters"])
                
                # Execute tool with retries
                #execution_result = await self._execute_with_retry(ctx, decision, tool_step)
                execution_result = await self._execute_tool(ctx, decision, tool_step)
                logger.info(f"🛠️ Tool execution completed for step {step_count + 1}")
                logger.info(f"🛠️ Execution result for step {step_count + 1}: {execution_result}")
                log_json_block(f"📌 Execution result for step {step_count + 1}", execution_result)
                
                # Record complete cycle
                ctx.record_cycle(perception, decision, execution_result)

                # Print all cycles up to current
                #ctx.print_cycle_steps(step_count + 1)
                
                step_count += 1
            
            # When max steps reached
            if step_count >= self.max_steps:
                logger.warning(f"Reached maximum steps ({self.max_steps}) without completion")
                return await self.summary.summarize(
                    query, 
                    ctx, 
                    {"route": "summarize", "solution_summary": f"Maximum steps ({self.max_steps}) reached without completion"}
                )
            
            # Normal completion
            return await self.summary.summarize(
                query,
                ctx,
                {"route": "summarize", "solution_summary": "Task completed successfully"}
            )
            
        except Exception as e:
            logger.error(f"Error in computer agent session {session_id}: {str(e)}")
            if ctx.current_step:
                ctx.mark_step_failed(ctx.current_step.id, str(e))
            
            # Error case
            return await self.summary.summarize(
                query,
                ctx,
                {"route": "summarize", "solution_summary": f"Task failed: {str(e)}"}
            )

    async def _execute_tool(self, ctx: ComputerAgentContext, decision: Dict[str, Any], tool_step: Step) -> Dict[str, Any]:
        """
        Execute a tool without retry logic
        
        Args:
            ctx: Agent context
            decision: Decision containing tool and parameters
            tool_step: Step object for tracking
            
        Returns:
            Dict containing execution result
        """
        try:
            # Execute the tool
            result = await self.multi_mcp.execute_tool(
                decision["selected_tool"],
                decision["tool_parameters"]
            )
            
            # Mark step as completed with result
            ctx.mark_step_completed(tool_step.id, result)
            return result
            
        except Exception as e:
            # Mark step as failed and raise the exception
            ctx.mark_step_failed(tool_step.id, str(e))
            raise

    async def _execute_with_retry(self, ctx: ComputerAgentContext, decision: Dict[str, Any], tool_step: Step) -> Dict[str, Any]:
        """Execute tool with retry logic"""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                result = await self.multi_mcp.execute_tool(
                    decision["selected_tool"],
                    decision["tool_parameters"]
                )
                
                if isinstance(result, dict) and result.get('success') is False:
                    # Handle failure
                    error_msg = result.get('message', 'Unknown error')
                    error_perception = await self._handle_error(ctx, error_msg, decision)
                    
                    if error_perception.get("should_retry"):
                        retry_count += 1
                        decision = await self._adjust_decision(ctx, error_perception)
                        continue
                    
                # Success or non-retryable error
                ctx.mark_step_completed(tool_step.id, result)
                return result
                
            except Exception as e:
                retry_count += 1
                if retry_count == self.max_retries:
                    ctx.mark_step_failed(tool_step.id, str(e))
                    raise
                await asyncio.sleep(1)

    async def _handle_error(self, ctx: ComputerAgentContext, error_msg: str, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Handle error state and determine if retry is needed"""
        # Create error perception step
        error_perception_step = ctx.add_step(
            f"ERROR_PERCEPTION_{ctx.current_step.id}",
            "Analyzing error state",
            StepType.PERCEPTION,
            from_step=ctx.current_step.id
        )
        
        # Run perception on error
        error_perception = await self.perception.analyze(
            ctx,
            ctx.pipeline_output,
            snapshot_type="error_state"
        )
        ctx.mark_step_completed(error_perception_step.id, error_perception)
        
        return error_perception

    async def _adjust_decision(self, ctx: ComputerAgentContext, error_perception: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust decision based on error perception"""
        # Create error decision step
        error_decision_step = ctx.add_step(
            f"ERROR_DECISION_{ctx.current_step.id}",
            "Deciding next action after error",
            StepType.DECISION,
            from_step=f"ERROR_PERCEPTION_{ctx.current_step.id}"
        )
        
        # Run decision on error perception
        error_decision = await self.decision.decide(ctx, error_perception)
        ctx.mark_step_completed(error_decision_step.id, error_decision)
        
        return error_decision
