import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from agent.models.mode_manager import ModelManager
from config.log_config import setup_logging, logger_json_block

logger = setup_logging(__name__)

class Summary:
    def __init__(self, model_manager: ModelManager, prompt_path: str = "agent/prompts/summary_prompt.txt"):
        """
        Initialize the summary module
        
        Args:
            model_manager: ModelManager instance for LLM integration
            prompt_path: Path to the summary prompt template
        """
        self.model = model_manager
        self.prompt_path = prompt_path
        
        # Verify prompt file exists
        if not Path(self.prompt_path).exists():
            raise FileNotFoundError(f"Summary prompt file not found: {self.prompt_path}")

    async def summarize(self, query: str, ctx, latest_perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarize computer operations and create final plan
        
        Args:
            query: Original query
            ctx: Computer context
            latest_perception: Latest perception output
            
        Returns:
            dict: Final plan with summary
        """
        try:
            # Read prompt template
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
                
            if not prompt_template:
                raise ValueError(f"Summary prompt file is empty: {self.prompt_path}")

            # Build summary input
            summary_input = {
                "original_query": query,
                "completed_steps": [step.to_dict() for step in ctx.steps.values() if step.status == "completed"],
                "failed_steps": [step.to_dict() for step in ctx.steps.values() if step.status == "failed"],
                "perception": latest_perception
            }

            # Format full prompt
            full_prompt = (
                f"Current Time: {datetime.utcnow().isoformat()}\n\n"
                f"{prompt_template.strip()}\n\n"
                f"{json.dumps(summary_input, indent=2)}"
            )

            # Generate summary
            summary = await self.model.generate_text(prompt=full_prompt)
            
            # Create final plan
            final_plan = {
                "status": "success",
                "session_id": ctx.session_id,
                "summary": summary,
                "summary_path": ctx.save_summary(),
                "steps": [step.to_dict() for step in ctx.steps.values()]
            }

            logger_json_block(logger, "Final plan", final_plan)
            return final_plan

        except Exception as e:
            logger.error(f"Error in summary generation: {str(e)}")
            return {
                "status": "failed",
                "session_id": ctx.session_id,
                "error": f"Summary generation failed: {str(e)}",
                "steps": [step.to_dict() for step in ctx.steps.values()]
            }
