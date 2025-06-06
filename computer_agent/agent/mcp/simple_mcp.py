"""
Simple MCP Client for Windows Automation
"""
import asyncio
import json
import logging
import aiohttp
from typing import Dict, Any, List, Optional
from pathlib import Path
from config.log_config import setup_logging

logger = setup_logging(__name__)

class SimpleMCP:
    def __init__(self, server_config: Dict[str, Any]):
        """
        Initialize SimpleMCP with Windows server config
        
        Args:
            server_config: Configuration for the Windows MCP server
        """
        self.server_config = server_config
        self.server_id = server_config["id"]
        self.base_url = "http://localhost:8080"  # SSE server URL
        self.session = None
        self.initialized = False
        self.tools = {}
        
    async def initialize(self) -> None:
        """Initialize the MCP client and connect to server"""
        if self.initialized:
            return
            
        try:
            # Create aiohttp session
            self.session = aiohttp.ClientSession()
            
            # Connect to SSE endpoint to get initial tools
            async with self.session.get(f"{self.base_url}/sse") as resp:
                async for line in resp.content:
                    if line:
                        try:
                            decoded = line.decode().strip()
                            if decoded.startswith("data: "):
                                data = json.loads(decoded[6:])
                                if data.get('status') == 'connected':
                                    self.tools = data.get('tools', {})
                                    self.initialized = True
                                    
                                    # Print available tools
                                    print("\n=== Available MCP Tools ===")
                                    for category, tools in self.tools.items():
                                        print(f"\n{category.upper()}:")
                                        for tool_name, tool_info in tools.items():
                                            print(f"  - {tool_name}: {tool_info['description']}")
                                            if tool_info.get('params'):
                                                print(f"    Params: {tool_info['params']}")
                                    print("\n========================\n")
                                    break
                        except Exception as e:
                            logger.error(f"Failed to parse SSE data: {e}")
                            continue
            
            logger.info(f"SimpleMCP initialized with {len(self.tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize SimpleMCP: {str(e)}")
            if self.session:
                await self.session.close()
            raise
            
    async def list_tools(self) -> Dict:
        """Get list of available tools from the server"""
        try:
            async with self.session.get(f"{self.base_url}/tools") as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to list tools: {str(e)}")
            return {}
            
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool with given arguments
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments for the tool
            
        Returns:
            Result of the tool execution
        """
        if not self.initialized:
            raise RuntimeError("SimpleMCP not initialized")
            
        try:
            data = {"command": tool_name, "params": arguments}
            async with self.session.post(f"{self.base_url}/command", json=data) as response:
                result = await response.json()
                logger.info(f"Tool {tool_name} executed with result: {result}")
                return result
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_name}: {str(e)}")
            raise
            
    async def shutdown(self) -> None:
        """Shutdown the MCP client"""
        if self.session:
            await self.session.close()
            self.initialized = False