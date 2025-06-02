# src/windowManager/mcp_server_windows_test.py
import asyncio
import aiohttp
import json
from typing import Dict, Any
import time
import signal
import sys

class MCPTestClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session = None
        self.sse_connection = None
        self._running = True

    async def connect(self):
        """Establish connection to the MCP server"""
        try:
            self.session = aiohttp.ClientSession()
            # Connect to SSE endpoint
            self.sse_connection = await self.session.get(f"{self.base_url}/sse")
            print("Connected to MCP server")
            return True
        except Exception as e:
            print(f"Failed to connect to MCP server: {e}")
            await self.close()  # Clean up on connection failure
            return False

    async def get_available_tools(self) -> Dict:
        """Get list of available tools"""
        if not self._running:
            return {}
        try:
            async with self.session.get(f"{self.base_url}/tools") as response:
                return await response.json()
        except Exception as e:
            print(f"Failed to get tools: {e}")
            return {}

    async def execute_command(self, command: str, params: Dict[str, Any]) -> Dict:
        """Execute a command on the MCP server"""
        if not self._running:
            return {"error": "Client is shutting down"}
        try:
            data = {
                "command": command,
                "params": params
            }
            async with self.session.post(f"{self.base_url}/command", json=data) as response:
                return await response.json()
        except asyncio.CancelledError:
            print("Command execution cancelled")
            return {"error": "Command cancelled"}
        except Exception as e:
            print(f"Failed to execute command {command}: {e}")
            return {"error": str(e)}

    async def get_command_history(self) -> list:
        """Get command execution history"""
        if not self._running:
            return []
        try:
            async with self.session.get(f"{self.base_url}/history") as response:
                return await response.json()
        except Exception as e:
            print(f"Failed to get command history: {e}")
            return []

    async def close(self):
        """Close the client connection"""
        self._running = False
        try:
            if self.sse_connection and not self.sse_connection.closed:
                await self.sse_connection.close()
        except Exception as e:
            print(f"Error closing SSE connection: {e}")
        
        try:
            if self.session and not self.session.closed:
                await self.session.close()
        except Exception as e:
            print(f"Error closing session: {e}")

async def run_tests():
    client = MCPTestClient()
    
    def signal_handler(sig, frame):
        print("\nShutting down gracefully...")
        asyncio.create_task(client.close())
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Connect to server
        if not await client.connect():
            print("Failed to connect to server. Exiting...")
            return

        # Get available tools
        print("\n=== Available Tools ===")
        tools = await client.get_available_tools()
        print(json.dumps(tools, indent=2))

        # Test window commands
        print("\n=== Testing Window Commands ===")
        
        # Get current windows
        windows = await client.execute_command("get_windows", {"show_minimized": True})
        print("\nCurrent Windows:", json.dumps(windows, indent=2))
        
        if windows and "windows" in windows and windows["windows"]:
            window_id = windows["windows"][0]["id"]
            
            # Test window operations
            commands = [
                ("maximize", {"window_id": window_id}),
                ("minimize", {"window_id": window_id}),
                ("maximize", {"window_id": window_id}),
                ("move", {"window_id": window_id, "x": 100, "y": 100}),
                ("resize", {"window_id": window_id, "width": 800, "height": 600})
            ]
            
            for cmd, params in commands:
                if not client._running:
                    break
                print(f"\nExecuting {cmd}...")
                result = await client.execute_command(cmd, params)
                print(f"Result: {json.dumps(result, indent=2)}")
                await asyncio.sleep(1)

        # Test mouse commands
        print("\n=== Testing Mouse Commands ===")
        mouse_commands = [
            ("click", {"button": "left", "x": 100, "y": 100}),
            ("doubleclick", {"button": "left", "x": 200, "y": 200}),
            ("scroll", {"direction": "up", "amount": 3, "x": 300, "y": 300})
        ]
        
        for cmd, params in mouse_commands:
            if not client._running:
                break
            print(f"\nExecuting {cmd}...")
            result = await client.execute_command(cmd, params)
            print(f"Result: {json.dumps(result, indent=2)}")
            await asyncio.sleep(1)

        # Test keyboard commands
        print("\n=== Testing Keyboard Commands ===")
        keyboard_commands = [
            ("type", {"text": "Hello from MCP Test Client!"}),
            ("send", {"keys": "ctrl+c"})
        ]
        
        for cmd, params in keyboard_commands:
            if not client._running:
                break
            print(f"\nExecuting {cmd}...")
            result = await client.execute_command(cmd, params)
            print(f"Result: {json.dumps(result, indent=2)}")
            await asyncio.sleep(1)

        # Test system commands
        print("\n=== Testing System Commands ===")
        system_commands = [
            ("computer", {}),
            ("user", {}),
            ("msgbox", {
                "title": "MCP Test",
                "message": "This is a test message box",
                "x": 400,
                "y": 300
            })
        ]
        
        for cmd, params in system_commands:
            if not client._running:
                break
            print(f"\nExecuting {cmd}...")
            result = await client.execute_command(cmd, params)
            print(f"Result: {json.dumps(result, indent=2)}")
            await asyncio.sleep(1)

        # Get command history
        print("\n=== Command History ===")
        history = await client.get_command_history()
        print(json.dumps(history, indent=2))

    except asyncio.CancelledError:
        print("\nTest execution cancelled")
    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    print("Starting MCP Test Client...")
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        print("\nTest client stopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}")