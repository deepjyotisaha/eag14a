import asyncio
import aiohttp
import json
import os
import sys
import signal
from typing import Dict, Any

LEGEND_PATH = os.path.join(os.path.dirname(__file__), 'legend.txt')
SERVER_URL = "http://localhost:8080"

class MCPInteractiveClient:
    def __init__(self, base_url: str = SERVER_URL):
        self.base_url = base_url
        self.session = None
        self.sse_task = None
        self._running = True
        self.window_lookup = {}  # short_id -> full_id

    async def start(self):
        self.session = aiohttp.ClientSession()
        # Start SSE listener
        self.sse_task = asyncio.create_task(self.listen_sse())
        # Print initial summary and legend
        await self.print_windows_summary()
        self.print_legend()
        await self.interactive_loop()

    async def close(self):
        self._running = False
        if self.sse_task:
            self.sse_task.cancel()
        if self.session:
            await self.session.close()

    async def listen_sse(self):
        """Listen for SSE events from the server"""
        try:
            async with self.session.get(f"{self.base_url}/sse") as resp:
                async for line in resp.content:
                    if not self._running:
                        break
                    if line:
                        try:
                            decoded = line.decode().strip()
                            if decoded.startswith("data: "):
                                data = json.loads(decoded[6:])
                                
                                # Handle initial connection message
                                if data.get('status') == 'connected':
                                    # Store tools first
                                    tools = data.get('tools', {})
                                    self.available_tools = tools
                                    
                                    # Then format and print the output
                                    print("\n=== MCP Server Connected ===")
                                    print("Available Commands:")
                                    
                                    # Window Commands
                                    if 'window_commands' in tools:
                                        print("\n📋 Window Commands:")
                                        window_cmds = list(tools['window_commands'].items())
                                        for cmd, info in window_cmds:
                                            params = ', '.join(f"{k}: {v}" for k, v in info['params'].items())
                                            print(f"  • {cmd}: {info['description']}")
                                            if params:
                                                print(f"    Parameters: {params}")
                                    
                                    # Mouse Commands
                                    if 'mouse_commands' in tools:
                                        print("\n🖱️  Mouse Commands:")
                                        mouse_cmds = list(tools['mouse_commands'].items())
                                        for cmd, info in mouse_cmds:
                                            params = ', '.join(f"{k}: {v}" for k, v in info['params'].items())
                                            print(f"  • {cmd}: {info['description']}")
                                            if params:
                                                print(f"    Parameters: {params}")
                                    
                                    # Keyboard Commands
                                    if 'keyboard_commands' in tools:
                                        print("\n⌨️  Keyboard Commands:")
                                        keyboard_cmds = list(tools['keyboard_commands'].items())
                                        for cmd, info in keyboard_cmds:
                                            params = ', '.join(f"{k}: {v}" for k, v in info['params'].items())
                                            print(f"  • {cmd}: {info['description']}")
                                            if params:
                                                print(f"    Parameters: {params}")
                                    
                                    # System Commands
                                    if 'system_commands' in tools:
                                        print("\n💻 System Commands:")
                                        system_cmds = list(tools['system_commands'].items())
                                        for cmd, info in system_cmds:
                                            params = ', '.join(f"{k}: {v}" for k, v in info['params'].items())
                                            print(f"  • {cmd}: {info['description']}")
                                            if params:
                                                print(f"    Parameters: {params}")
                                    
                                    print("\n✅ Ready to accept commands!")
                                    continue
                                
                                # Handle other SSE messages
                                if 'command' in data:
                                    print(f"\n[Command] {data['command']}: {data.get('result', {}).get('message', '')}")
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            if self._running:
                                print(f"[SSE] Error processing message: {e}")
        except Exception as e:
            if self._running:
                print(f"[SSE] Connection error: {e}")

    async def get_available_tools(self) -> Dict:
        try:
            async with self.session.get(f"{self.base_url}/tools") as response:
                return await response.json()
        except Exception as e:
            print(f"Failed to get tools: {e}")
            return {}

    async def execute_command(self, command: str, params: Dict[str, Any]) -> Dict:
        try:
            data = {"command": command, "params": params}
            async with self.session.post(f"{self.base_url}/command", json=data) as response:
                return await response.json()
        except Exception as e:
            print(f"Failed to execute command {command}: {e}")
            return {"error": str(e)}

    async def get_windows(self, show_minimized=True):
        resp = await self.execute_command("get_windows", {"show_minimized": show_minimized})
        return resp

    async def print_windows_summary(self):
        """Print a clean summary of all windows organized by screen"""
        # Get all windows first
        result = await self.execute_command("get_windows", {"show_minimized": True})
        if not result.get('success', False):
            print(f"❌ Error: {result.get('error', 'Failed to get windows')}")
            return

        # Get windows from the nested 'result' field
        windows = result.get('result', {}).get('windows', [])
        if not windows:
            print("No windows found")
            return

        # Group windows by monitor
        monitors = {}
        for window in windows:
            monitor_id = window.get('screen', 0)
            if monitor_id not in monitors:
                monitors[monitor_id] = []
            monitors[monitor_id].append(window)

        # Print summary
        print("\n=== Window Summary ===")
        print(f"Total Windows: {len(windows)}")
        print(f"Total Monitors: {len(monitors)}")
        
        # Print each monitor's windows
        for monitor_id, monitor_windows in sorted(monitors.items()):
            print(f"\nMonitor {monitor_id}:")
            for window in monitor_windows:
                title = window.get('title', 'Unknown')
                proc = window.get('proc', 'Unknown')
                state = "MINIMIZED" if window.get('minimized', False) else "VISIBLE"
                print(f"  • {title} ({proc}) - {state}")

        # Add the window ID legend
        print("\n💡 TIP: Use the last 8 characters of any Window ID for commands")
        print("   Example: If ID is 'window_12345678_abcdefgh', use 'abcdefgh' for commands")

    def print_legend(self):
        print("\n=== Command Legend ===")
        try:
            with open(LEGEND_PATH, 'r', encoding='utf-8') as f:
                print(f.read())
        except Exception:
            print("Legend file not found.")

    async def interactive_loop(self):
        """Run the interactive window controller"""
        print("🚀 Starting Interactive Window Manager...")
        
        # Initial display
        await self.print_windows_summary()
        self.print_legend()
        
        while self._running:
            try:
                user_input = input("\n💻 Enter command (or 'q' to quit): ").strip()
                await self.handle_user_command(user_input)
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted by user. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    async def handle_user_command(self, user_input: str):
        """Handle user command with support for chaining"""
        user_input = user_input.strip()
        
        if not user_input:
            return
        
        if user_input.lower() == 'q':
            print("Goodbye!")
            self._running = False
            return
        
        if user_input.lower() == 'r':
            await self.print_windows_summary()
            return
        
        if user_input.lower() in ['legend', 'help']:
            self.print_legend()
            return
        
        # Check if this is a command chain
        if ' : ' in user_input:
            commands = [cmd.strip() for cmd in user_input.split(' : ')]
            print(f"🔗 Executing command chain ({len(commands)} steps)...")
            
            overall_success = True
            
            for i, cmd in enumerate(commands):
                if not cmd:
                    continue
                
                print(f"   Step {i+1}: {cmd}")
                result = await self._execute_single_command(cmd)
                
                if result.get('success', False):
                    print(f"   ✅ {result.get('message', 'Success')}")
                else:
                    print(f"   ❌ {result.get('error', 'Unknown error')}")
                    overall_success = False
                    print(f"   ⚠️  Chain stopped at step {i+1}")
                    break
                
                # Adaptive delay based on command type
                if 'click' in cmd.lower() or 'focus' in cmd.lower() or cmd.lower().endswith('f'):
                    await asyncio.sleep(0.3)  # Longer delay after focus/click operations
                elif 'send' in cmd.lower() or 'type' in cmd.lower():
                    await asyncio.sleep(0.2)  # Medium delay for keyboard operations
                else:
                    await asyncio.sleep(0.1)  # Short delay for other operations
            
            if overall_success:
                print(f"✅ Command chain completed successfully ({len(commands)} steps)")
            else:
                print(f"⚠️  Command chain stopped at step {i+1}")
            return
        
        # Single command execution
        result = await self._execute_single_command(user_input)
        status = "✅" if result.get('success', False) else "❌"
        message = result.get('message', result.get('error', 'Unknown result'))
        print(f"{status} {message}")

    async def _execute_single_command(self, command_str: str) -> Dict:
        """Execute a single command - internal method for chaining"""
        parts = command_str.strip().split()
        if not parts:
            return {"error": "Empty command"}
        
        # Get available tools
        tools = await self.get_available_tools()
        
        # Handle window commands with short ID
        if parts[0] in self.window_lookup and len(parts) >= 2:
            window_id = self.window_lookup[parts[0]]
            cmd = parts[1]
            params = {"window_id": window_id}
            
            # Add extra params if needed
            if cmd == 'resize' and len(parts) == 4:
                params["width"] = int(parts[2])
                params["height"] = int(parts[3])
            elif cmd == 'move' and len(parts) == 4:
                params["x"] = int(parts[2])
                params["y"] = int(parts[3])
            elif cmd == 'screen' and len(parts) == 5:
                params["screen"] = int(parts[2])
                params["x"] = int(parts[3])
                params["y"] = int(parts[4])
            elif cmd == 'monitor' and len(parts) == 3:
                params["monitor"] = int(parts[2])
            
            return await self.execute_command(cmd, params)
        
        # Handle other commands
        cmd = parts[0]
        params = {}
        
        # Parse parameters based on command type
        if cmd in tools.get('mouse_commands', {}):
            if cmd in ['click', 'doubleclick', 'longclick']:
                if len(parts) >= 2:
                    params["button"] = parts[1]
                if len(parts) >= 4:
                    params["x"] = int(parts[2])
                    params["y"] = int(parts[3])
                if cmd == 'longclick' and len(parts) >= 3:
                    params["duration"] = float(parts[2])
            elif cmd == 'scroll' and len(parts) >= 3:
                params["direction"] = parts[1]
                params["amount"] = int(parts[2])
                if len(parts) >= 5:
                    params["x"] = int(parts[3])
                    params["y"] = int(parts[4])
            elif cmd == 'drag' and len(parts) >= 7:
                params["start_x"] = int(parts[1])
                params["start_y"] = int(parts[2])
                params["end_x"] = int(parts[3])
                params["end_y"] = int(parts[4])
                params["button"] = parts[5]
                params["duration"] = float(parts[6])
        elif cmd in tools.get('keyboard_commands', {}):
            if cmd == 'send' and len(parts) >= 2:
                params["keys"] = ' '.join(parts[1:])
            elif cmd == 'type' and len(parts) >= 2:
                params["text"] = ' '.join(parts[1:])
        elif cmd in tools.get('system_commands', {}):
            if cmd == 'launch' and len(parts) >= 4:
                params["app_name"] = parts[1]
                params["screen_id"] = int(parts[2])
                params["fullscreen"] = parts[3].lower() != 'normal' if len(parts) > 3 else True
            elif cmd == 'msgbox' and len(parts) >= 4:
                params["title"] = parts[1]
                params["message"] = parts[2]
                if len(parts) >= 6:
                    params["x"] = int(parts[4])
                    params["y"] = int(parts[5])
        
        return await self.execute_command(cmd, params)

    async def connect(self):
        """Connect to the MCP server"""
        try:
            self.session = aiohttp.ClientSession()
            self.sse_url = f"http://{self.base_url}/sse"
            self.command_url = f"http://{self.base_url}/command"
            
            # Connect to SSE endpoint
            async with self.session.get(self.sse_url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to connect to SSE endpoint: {response.status}")
                
                # Read the initial SSE message
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            if data.get('status') == 'connected':
                                # Store tools but don't print raw JSON
                                self.available_tools = data.get('tools', {})
                                
                                # Print a nicely formatted welcome message
                                print("\n=== MCP Server Connected ===")
                                print("Available Commands:")
                                
                                # Window Commands
                                print("\n📋 Window Commands:")
                                for cmd, info in self.available_tools.get('window_commands', {}).items():
                                    params = ', '.join(f"{k}: {v}" for k, v in info['params'].items())
                                    print(f"  • {cmd}: {info['description']}")
                                    if params:
                                        print(f"    Parameters: {params}")
                                
                                # Mouse Commands
                                print("\n🖱️  Mouse Commands:")
                                for cmd, info in self.available_tools.get('mouse_commands', {}).items():
                                    params = ', '.join(f"{k}: {v}" for k, v in info['params'].items())
                                    print(f"  • {cmd}: {info['description']}")
                                    if params:
                                        print(f"    Parameters: {params}")
                                
                                # Keyboard Commands
                                print("\n⌨️  Keyboard Commands:")
                                for cmd, info in self.available_tools.get('keyboard_commands', {}).items():
                                    params = ', '.join(f"{k}: {v}" for k, v in info['params'].items())
                                    print(f"  • {cmd}: {info['description']}")
                                    if params:
                                        print(f"    Parameters: {params}")
                                
                                # System Commands
                                print("\n💻 System Commands:")
                                for cmd, info in self.available_tools.get('system_commands', {}).items():
                                    params = ', '.join(f"{k}: {v}" for k, v in info['params'].items())
                                    print(f"  • {cmd}: {info['description']}")
                                    if params:
                                        print(f"    Parameters: {params}")
                                
                                print("\n✅ Ready to accept commands!")
                                return True
                        except json.JSONDecodeError:
                            continue
                return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

if __name__ == "__main__":
    client = MCPInteractiveClient()
    loop = asyncio.get_event_loop()
    def signal_handler(sig, frame):
        print("\nShutting down gracefully...")
        loop.create_task(client.close())
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        loop.run_until_complete(client.start())
    except KeyboardInterrupt:
        print("\nClient stopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}") 