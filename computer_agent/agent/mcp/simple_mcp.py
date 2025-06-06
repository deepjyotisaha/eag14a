"""
Simple MCP Client for Windows Automation
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SimpleMCP:
    def __init__(self, server_config: Dict[str, Any]):
        """
        Initialize SimpleMCP with Windows server config
        
        Args:
            server_config: Configuration for the Windows MCP server
        """
        self.server_config = server_config
        self.server_id = server_config["id"]
        self.script_path = server_config["script"]
        self.working_dir = server_config["cwd"]
        self.process = None
        self.tools = []
        self.initialized = False
        
    async def initialize(self) -> None:
        """Initialize the MCP server and load tools"""
        if self.initialized:
            return
            
        try:
            # Start the MCP server process
            self.process = await asyncio.create_subprocess_exec(
                "python",
                self.script_path,
                cwd=self.working_dir,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for server to start
            await asyncio.sleep(2)
            
            # Load available tools
            self.tools = await self.list_tools()
            self.initialized = True
            
            logger.info(f"SimpleMCP initialized with {len(self.tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize SimpleMCP: {str(e)}")
            raise
            
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from the server"""
        try:
            response = await self._send_command("list_tools", {})
            return response.get("tools", [])
        except Exception as e:
            logger.error(f"Failed to list tools: {str(e)}")
            return []
            
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
            response = await self._send_command("execute_tool", {
                "tool_name": tool_name,
                "arguments": arguments
            })
            return response.get("result")
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_name}: {str(e)}")
            raise
            
    async def _send_command(self, command: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a command to the MCP server
        
        Args:
            command: Command to send
            data: Command data
            
        Returns:
            Server response
        """
        if not self.process:
            raise RuntimeError("MCP server not running")
            
        try:
            # Prepare command
            cmd = {
                "command": command,
                "data": data
            }
            
            # Send command
            self.process.stdin.write(json.dumps(cmd).encode() + b"\n")
            await self.process.stdin.drain()
            
            # Read response
            response_line = await self.process.stdout.readline()
            response = json.loads(response_line.decode())
            
            if response.get("status") == "error":
                raise Exception(response.get("error", "Unknown error"))
                
            return response.get("data", {})
            
        except Exception as e:
            logger.error(f"Failed to send command {command}: {str(e)}")
            raise
            
    async def shutdown(self) -> None:
        """Shutdown the MCP server"""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception as e:
                logger.error(f"Error during shutdown: {str(e)}")
            finally:
                self.process = None
                self.initialized = False