# src/windowManager/paint_test.py
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
import time

class PaintTestClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.sse_connection: Optional[aiohttp.ClientResponse] = None
        self._running = True

    async def connect(self) -> bool:
        """Establish connection to the MCP server"""
        try:
            if self.session is not None:
                print("Session already exists, closing...")
                await self.close()
            
            self.session = aiohttp.ClientSession()
            print("Created new session")
            
            # Connect to SSE endpoint
            self.sse_connection = await self.session.get(f"{self.base_url}/sse")
            print("Connected to MCP server")
            return True
        except Exception as e:
            print(f"Failed to connect to MCP server: {e}")
            await self.close()
            return False

    async def execute_command(self, command: str, params: Dict[str, Any]) -> Dict:
        """Execute a command on the MCP server"""
        if self.session is None:
            return {"error": "Not connected to server"}
            
        try:
            data = {
                "command": command,
                "params": params
            }
            async with self.session.post(f"{self.base_url}/command", json=data) as response:
                if response.status != 200:
                    return {"error": f"Server returned status {response.status}"}
                return await response.json()
        except aiohttp.ClientError as e:
            print(f"Network error executing command {command}: {e}")
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            print(f"Failed to execute command {command}: {e}")
            return {"error": str(e)}

    async def close(self):
        """Close the client connection"""
        self._running = False
        
        # Close SSE connection
        if self.sse_connection is not None:
            try:
                if not self.sse_connection.closed:
                    await self.sse_connection.close()
            except Exception as e:
                print(f"Error closing SSE connection: {e}")
            finally:
                self.sse_connection = None
        
        # Close session
        if self.session is not None:
            try:
                if not self.session.closed:
                    await self.session.close()
            except Exception as e:
                print(f"Error closing session: {e}")
            finally:
                self.session = None

    async def wait_for_paint_window(self, max_retries: int = 5, retry_delay: int = 5) -> Optional[Dict]:
        """Wait for Paint window to appear"""
        for attempt in range(max_retries):
            print(f"\nAttempt {attempt + 1}/{max_retries} to find Paint window...")
            windows = await self.execute_command("get_windows", {"show_minimized": True})
            
            if "error" in windows:
                print(f"Failed to get windows: {windows['error']}")
                await asyncio.sleep(retry_delay)
                continue
                
            for window in windows.get("windows", []):
                if "Paint" in window.get("title", ""):
                    print(f"Found Paint window: {json.dumps(window, indent=2)}")
                    return window
            
            print(f"Paint window not found, waiting {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
        
        return None

async def run_paint_test():
    client = PaintTestClient()
    try:
        # Connect to server
        if not await client.connect():
            print("Failed to connect to server. Exiting...")
            return

        print("\n=== Starting Paint Test ===")
        
        # Launch Paint
        print("\nLaunching Paint...")
        result = await client.execute_command("launch", {
            "app_name": "C:\\Windows\\System32\\mspaint.exe",
            "screen_id": 1,
            "fullscreen": False
        })
        print(f"Launch result: {json.dumps(result, indent=2)}")
        
        if "error" in result:
            print(f"Failed to launch Paint: {result['error']}")
            return
        
        if not result.get("success", False):
            print(f"Launch failed: {result.get('message', 'Unknown error')}")
            return

        # Wait for Paint window to appear
        print("\nWaiting for Paint window to appear...")
        paint_window = await client.wait_for_paint_window()
        
        if not paint_window:
            print("Failed to find Paint window after multiple attempts")
            return
        
        window_id = paint_window["id"]
        print(f"Successfully found Paint window with ID: {window_id}")
        
        # Resize and position the window
        print("\nResizing and positioning Paint window...")
        resize_result = await client.execute_command("resize", {
            "window_id": window_id,
            "width": 800,
            "height": 600
        })
        if "error" in resize_result:
            print(f"Failed to resize window: {resize_result['error']}")
            return
        await asyncio.sleep(1)
        
        move_result = await client.execute_command("move", {
            "window_id": window_id,
            "x": 100,
            "y": 100
        })
        if "error" in move_result:
            print(f"Failed to move window: {move_result['error']}")
            return
        await asyncio.sleep(1)
        
        # Draw a simple shape
        print("\nDrawing a simple shape...")
        
        # Click to start drawing
        click_result = await client.execute_command("click", {
            "button": "left",
            "x": 200,
            "y": 200
        })
        if "error" in click_result:
            print(f"Failed to click: {click_result['error']}")
            return
        await asyncio.sleep(0.5)
        
        # Draw a line
        drag_result = await client.execute_command("drag", {
            "start_x": 200,
            "start_y": 200,
            "end_x": 400,
            "end_y": 400,
            "button": "left",
            "duration": 0.5
        })
        if "error" in drag_result:
            print(f"Failed to drag: {drag_result['error']}")
            return
        await asyncio.sleep(1)
        
        # Draw a circle
        click_result = await client.execute_command("click", {
            "button": "left",
            "x": 300,
            "y": 300
        })
        if "error" in click_result:
            print(f"Failed to click: {click_result['error']}")
            return
        await asyncio.sleep(0.5)
        
        drag_result = await client.execute_command("drag", {
            "start_x": 300,
            "start_y": 300,
            "end_x": 500,
            "end_y": 500,
            "button": "left",
            "duration": 0.5
        })
        if "error" in drag_result:
            print(f"Failed to drag: {drag_result['error']}")
            return
        await asyncio.sleep(1)
        
        # Type some text
        print("\nAdding some text...")
        click_result = await client.execute_command("click", {
            "button": "left",
            "x": 100,
            "y": 100
        })
        if "error" in click_result:
            print(f"Failed to click: {click_result['error']}")
            return
        await asyncio.sleep(0.5)
        
        type_result = await client.execute_command("type", {
            "text": "Hello from MCP Test!"
        })
        if "error" in type_result:
            print(f"Failed to type: {type_result['error']}")
            return
        await asyncio.sleep(1)
        
        # Save the file
        print("\nSaving the file...")
        save_result = await client.execute_command("send", {
            "keys": "ctrl+s"
        })
        if "error" in save_result:
            print(f"Failed to send save command: {save_result['error']}")
            return
        await asyncio.sleep(1)
        
        # Type filename
        type_result = await client.execute_command("type", {
            "text": "mcp_test_drawing"
        })
        if "error" in type_result:
            print(f"Failed to type filename: {type_result['error']}")
            return
        await asyncio.sleep(1)
        
        # Press Enter to save
        enter_result = await client.execute_command("send", {
            "keys": "enter"
        })
        if "error" in enter_result:
            print(f"Failed to save: {enter_result['error']}")
            return
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    print("Starting Paint Test Client...")
    try:
        asyncio.run(run_paint_test())
    except KeyboardInterrupt:
        print("\nTest stopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}")