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
        output_dir = get_output_folder(session_id)
        logger.info(f"Output directory: {output_dir}")
        ctx = ComputerAgentContext(session_id, query)
        
        try:
            logger.info(f"Starting computer agent session {session_id}")
            step_count = 0
            
            while step_count < self.max_steps:
                # Step 1: Take screenshot and run pipeline for current state
                log_step("📸 Taking screenshot")
                screenshot_path = take_screenshot(output_dir=str(ctx.output_dir))
                ctx.screenshot_path = screenshot_path
                logger.info(f"Screenshot taken and saved to {screenshot_path}")
                
                # Run pipeline on screenshot
                log_step("🔍 Running image processing pipeline")
                pipeline_result = await run_pipeline(screenshot_path, mode="mcp_deploy", output_dir=str(ctx.output_dir))
                ctx.pipeline_output = pipeline_result
                log_json_block("Pipeline Result", pipeline_result)
                log_step("🔍 Image processing pipeline completed")
                
                
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

                log_step("🧠 Running perception analysis")
                perception = await self.perception.analyze(
                    ctx, 
                    pipeline_result,
                    snapshot_type=snapshot_type
                )
                ctx.mark_step_completed(perception_step.id, perception)
                log_json_block(f"📌 Perception output ({step_count + 1})", perception, char_limit=2000)
                
                # When perception suggests summarization
                if perception.get("route") == "summarize":
                    logger.info("Perception suggests summarization - task complete")
                    return await self.summary.summarize(query, ctx, perception)
                
                # Step 3: Decision
                decision_step = ctx.add_step(
                    f"DECISION_{step_count + 1}",
                    "Deciding next action",
                    StepType.DECISION,
                    from_step=f"PERCEPTION_{step_count + 1}"
                )
                
                log_step("🤔 Making decision")
                decision = await self.decision.decide(ctx, perception)
                ctx.mark_step_completed(decision_step.id, decision)
                log_json_block(f"📌 Decision output ({step_count + 1})", decision)
                
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
                
                # Log tool execution details
                log_step(f"🛠️ Executing tool: {decision['selected_tool']}", decision["tool_parameters"])
                #log_json_block("Tool Parameters", decision["tool_parameters"])
                
                # Execute tool with retries
                retry_count = 0
                while retry_count < self.max_retries:
                    try:
                        logger.info(f"Attempt {retry_count + 1}/{self.max_retries} to execute {decision['selected_tool']}")
                        
                        # Execute the tool
                        result = await self.multi_mcp.execute_tool(
                            decision["selected_tool"],
                            decision["tool_parameters"]
                        )

                        log_json_block(f"🛠️ Tool Execution Result ({step_count + 1})", result)
                        
                        # Check if the result indicates failure
                        if isinstance(result, dict) and result.get('success') is False:
                            error_msg = result.get('message', 'Unknown error')
                            log_step(f"❌ Tool execution failed: {error_msg}")
                            logger.error(f"❌ Tool execution failed: {error_msg}")
                            
                            # Take screenshot and run pipeline to understand the error state
                            #log_step("📸 Taking screenshot after error")
                            #screenshot_path = take_screenshot(output_dir=str(ctx.output_dir))
                            #ctx.screenshot_path = screenshot_path
                            
                            # Run pipeline on error screenshot
                            #log_step("🔍 Running image processing pipeline after error")
                            #pipeline_result = await run_pipeline(screenshot_path, mode="mcp_deploy", output_dir=str(ctx.output_dir))
                            #ctx.pipeline_output = pipeline_result
                            
                            # TODO: Remove this once we have a way to run the pipeline after error
                            ctx.pipeline_output = ""
                            
                            # Run perception to understand the error
                            error_perception_step = ctx.add_step(
                                f"ERROR_PERCEPTION_{step_count + 1}_{retry_count + 1}",
                                "Analyzing error state",
                                StepType.PERCEPTION,
                                from_step=f"TOOL_{step_count + 1}"
                            )
                            
                            log_step("🧠 Running perception analysis for error")
                            logger.info("🧠 Running perception analysis for error")
                            # Pass error message in the context instead of as a parameter
                            ctx.current_error = error_msg
                            error_perception = await self.perception.analyze(
                                ctx, 
                                pipeline_result,
                                snapshot_type="error_state"
                            )
                            ctx.mark_step_completed(error_perception_step.id, error_perception)
                            log_json_block(f"📌 Error Perception output ({step_count + 1}_{retry_count + 1})", error_perception)
                            
                            # Run decision to determine next action based on error
                            error_decision_step = ctx.add_step(
                                f"ERROR_DECISION_{step_count + 1}_{retry_count + 1}",
                                "Deciding next action after error",
                                StepType.DECISION,
                                from_step=f"ERROR_PERCEPTION_{step_count + 1}_{retry_count + 1}"
                            )
                            
                            log_step("🤔 Making decision after error")
                            logger.info("🤔 Making decision after error")
                            error_decision = await self.decision.decide(ctx, error_perception)
                            ctx.mark_step_completed(error_decision_step.id, error_decision)
                            log_json_block(f"📌 Error Decision output ({step_count + 1}_{retry_count + 1})", error_decision)
                            
                            # Update tool parameters based on error decision
                            if error_decision.get("selected_tool") == decision["selected_tool"]:
                                decision["tool_parameters"] = error_decision["tool_parameters"]
                                retry_count += 1
                                logger.warning(f"🔄 Retrying tool execution with updated parameters ({retry_count}/{self.max_retries})")
                                await asyncio.sleep(1)  # Wait before retry
                                continue
                            else:
                                # If decision suggests a different tool, break the retry loop
                                logger.info("Decision suggests using a different tool, breaking retry loop")
                                break
                        
                        # Log successful execution
                        log_step(f"✅ Tool {decision['selected_tool']} executed successfully")
                        log_json_block("Tool Execution Result", result)
                        
                        # Mark step as completed
                        ctx.mark_step_completed(tool_step.id, result)
                        break
                        
                    except Exception as e:
                        retry_count += 1
                        logger.error(f"❌ Tool execution failed: {str(e)}")
                        
                        if retry_count == self.max_retries:
                            logger.error(f"❌ All {self.max_retries} attempts failed for {decision['selected_tool']}")
                            ctx.mark_step_failed(tool_step.id, str(e))
                            raise
                            
                        logger.warning(f"🔄 Retrying tool execution ({retry_count}/{self.max_retries})")
                        await asyncio.sleep(1)  # Wait before retry
                
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
