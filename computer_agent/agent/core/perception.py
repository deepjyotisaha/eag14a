"""
Perception Module - Analyzes current state and decides next action
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path
from config.log_config import setup_logging, logger_json_block, logger_prompt

logger = setup_logging(__name__)

class Perception:
    def __init__(self, model_manager):
        self.model = model_manager
        self.prompt_path = Path("agent/prompts/perception_prompt.txt")

    async def analyze(self, ctx, pipeline_result: Dict[str, Any], snapshot_type: str = "user_query") -> Dict[str, Any]:
        """
        Analyze current state and decide next action
        
        Args:
            ctx: Agent context
            pipeline_result: Result from pipeline analysis
            snapshot_type: Type of snapshot (user_query or step_result)
            
        Returns:
            Dict containing perception results
        """
        try:
            # Build perception input
            perception_input = {
                "snapshot_type": snapshot_type,
                "original_query": ctx.query,
                "raw_input": ctx.query if snapshot_type == "user_query" else str(pipeline_result),
                "pipeline_output": pipeline_result,
                "completed_steps": [step.to_dict() for step in ctx.steps.values() if step.status == "completed"],
                "failed_steps": [step.to_dict() for step in ctx.steps.values() if step.status == "failed"]
            }
            
            # Get prompt template
            prompt_template = self.prompt_path.read_text(encoding="utf-8")
            full_prompt = f"{prompt_template.strip()}\n\n```json\n{json.dumps(perception_input, indent=2)}\n```"
            
            # Log the prompt
            logger_prompt(logger, "📝 Perception prompt:", full_prompt)
            
            # Get LLM response
            response = await self.model.generate_text(prompt=full_prompt)
            
            # Parse response
            perception = json.loads(response)
            
            # Log perception results
            logger_json_block(logger, "Perception Results", perception)
            
            return perception
            
        except Exception as e:
            logger.error(f"Perception analysis failed: {str(e)}")
            raise
