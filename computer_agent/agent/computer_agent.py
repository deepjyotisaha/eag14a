"""
Computer Agent - Main agent class for computer UI automation
"""
import logging
from pathlib import Path
import yaml
from typing import Optional
import os

from .core.loop import ComputerAgentLoop
from .mcp.simple_mcp import SimpleMCP
from .models.mode_manager import ModelManager
from config.log_config import setup_logging

# Set up logging
logger = setup_logging(__name__)

class ComputerAgent:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the computer agent
        
        Args:
            api_key: Google API key (optional, can use environment variable)
        """
        logger.info("Initializing ComputerAgent...")
        
        # Load MCP server config
        config_path = Path("config/mcp_server_config.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            mcp_servers = config.get("mcp_servers", [])
            # Filter for windows server only
            windows_config = next(
                (server for server in mcp_servers if server["id"] == "windows"),
                None
            )
            if not windows_config:
                raise ValueError("Windows MCP server config not found")
        
        # Initialize SimpleMCP with windows config
        logger.info("Initializing SimpleMCP with windows tools...")
        self.mcp = SimpleMCP(windows_config)
        logger.info("SimpleMCP initialized with windows tools")
        
        # Initialize model manager
        logger.info("Initializing ModelManager...")
        self.model_manager = ModelManager(api_key=api_key)
        logger.info("ModelManager initialized")
        
        # Initialize agent loop
        self.loop = ComputerAgentLoop(self.mcp, self.model_manager)
        
    async def run(self, query: str) -> dict:
        """
        Run the computer agent with a user query
        
        Args:
            query: User's query
            
        Returns:
            dict: Result of the operation
        """
        try:
            logger.info("Starting computer agent operation...")
            
            # Initialize MCP
            await self.mcp.initialize()
            
            # Run the agent loop
            result = await self.loop.run(query)
            
            logger.info("Computer agent operation completed")
            return result
            
        except Exception as e:
            logger.error(f"Computer agent operation failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
        finally:
            # Ensure MCP is shut down
            await self.mcp.shutdown()
