"""
Decision Module - Decides next action based on perception
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path
from config.log_config import setup_logging, logger_json_block, logger_prompt
from agent.utils.json_parser import parse_llm_json

logger = setup_logging(__name__)

class Decision:
    def __init__(self, model_manager, multi_mcp):
        self.model = model_manager
        self.multi_mcp = multi_mcp
        self.prompt_path = Path("agent/prompts/decision_prompt.txt")

    async def decide(self, ctx, perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide next action based on perception
        
        Args:
            ctx: Agent context
            perception: Results from perception step
            
        Returns:
            Dict containing decision results
        """
        try:
            # Get available tools
            available_tools = await self.multi_mcp.list_tools()
            
            # Build decision input
            decision_input = {
                "original_query": ctx.query,
                "perception": perception,
                "available_tools": available_tools,
                "completed_steps": [step.to_dict() for step in ctx.steps.values() if step.status == "completed"],
                "failed_steps": [step.to_dict() for step in ctx.steps.values() if step.status == "failed"]
            }
            
            # Get prompt template
            prompt_template = self.prompt_path.read_text(encoding="utf-8")
            
            # Format tool list
            tool_list = "\n".join(
                f"- {tool_name}: {tool_info['description']}\n  Params: {tool_info.get('params', {})}"
                for category in available_tools.values()
                for tool_name, tool_info in category.items()
            )
            
            # Replace tool list in prompt
            full_prompt = prompt_template.replace("{TOOL_LIST}", tool_list)
            full_prompt = f"{full_prompt.strip()}\n\n```json\n{json.dumps(decision_input, indent=2)}\n```"
            
            # Log the prompt
            #logger_prompt(logger, "📝 Decision prompt:", full_prompt)
            
            # Get LLM response
            response = await self.model.generate_text(prompt=full_prompt)
            
            # Parse response using robust parser
            decision = parse_llm_json(response, required_keys=[
                "selected_tool",
                "tool_parameters",
                "reasoning",
                "confidence"
            ])
            
            # Log decision results
            logger_json_block(logger, "Decision Results", decision)
            
            return decision
            
        except Exception as e:
            logger.error(f"Decision making failed: {str(e)}")
            raise
