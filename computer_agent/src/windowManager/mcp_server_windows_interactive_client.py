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
        # Print available tools by fetching from the server
        # Print the window summary ONCE at startup
        await self.print_windows_summary()
        await self.print_server_commands()
        await self.interactive_loop()

    async def close(self):
        self._running = False
        if self.sse_task:
            self.sse_task.cancel()
        if self.session:
            await self.session.close()

    async def listen_sse(self):
        """Listen for SSE events from the server (prints only server commands and errors)"""
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
                                # Print server commands ONCE on connection
                                if data.get('status') == 'connected':
                                    tools = data.get('tools', {})
                                    print("\n=== MCP Server Connected ===")
                                    print("Available Commands:")
                                    for section, commands in tools.items():
                                        if not commands:
                                            continue
                                        section_title = {
                                            "window_commands": "📋 Window Commands",
                                            "mouse_commands": "🖱️  Mouse Commands",
                                            "keyboard_commands": "⌨️  Keyboard Commands",
                                            "system_commands": "💻 System Commands"
                                        }.get(section, section)
                                        print(f"\n{section_title}:")
                                        for cmd, info in commands.items():
                                            params = ', '.join(f"{k}: {v}" for k, v in info.get('params', {}).items())
                                            print(f"  • {cmd}: {info['description']}")
                                            if params:
                                                print(f"    Parameters: {params}")
                                    print("\n✅ Ready to accept commands!\n")
                                    continue
                                # Only print errors or important server events, not [Command] get_windows
                                if 'command' in data and data['command'] != 'get_windows':
                                    result = data.get('result', {})
                                    status = "✅" if result.get('success', False) else "❌"
                                    message = result.get('message', result.get('error', ''))
                                    print(f"[Command] {data['command']}: {status} {message}")
                        except Exception:
                            continue
        except Exception:
            pass

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

        # Group windows by monitor and application
        monitors = {}
        for window in windows:
            monitor_id = window.get('screen', 0)
            proc = window.get('proc', 'Unknown')
            
            if monitor_id not in monitors:
                monitors[monitor_id] = {
                    'windows': [],
                    'apps': {}
                }
            
            if proc not in monitors[monitor_id]['apps']:
                monitors[monitor_id]['apps'][proc] = {
                    'windows': [],
                    'count': 0,
                    'minimized': 0,
                    'visible': 0
                }
            
            app_data = monitors[monitor_id]['apps'][proc]
            app_data['windows'].append(window)
            app_data['count'] += 1
            if window.get('minimized', False):
                app_data['minimized'] += 1
            else:
                app_data['visible'] += 1
            
            monitors[monitor_id]['windows'].append(window)

        # Print summary
        print("=" * 80)
        print(f"WINDOW MANAGER - {len(windows)} windows across {len(monitors)} monitors")
        print("=" * 80)
        
        # Print each monitor's windows
        for monitor_id, monitor_data in sorted(monitors.items()):
            print(f"\n📺 MONITOR {monitor_id}")
            print(f"   Windows: {len(monitor_data['windows'])}")
            print("-" * 60)
            
            if not monitor_data['apps']:
                print("   No applications on this monitor")
                continue
            
            for app_name, app_data in monitor_data['apps'].items():
                print(f"\n   🖥️  {app_name}")
                print(f"      Total: {app_data['count']} | Visible: {app_data['visible']} | Minimized: {app_data['minimized']}")
                
                # Show visible windows
                visible_windows = [w for w in app_data['windows'] if not w.get('minimized', False)]
                for window in visible_windows:
                    title = window.get('title', 'Unknown')
                    title = title[:50] + "..." if len(title) > 50 else title
                    hwnd = window.get('hwnd', 'Unknown')
                    full_id = window.get('window_id', hwnd)
                    print(f"      ├─ 👁️  {title}")
                    print(f"      │   HWND: {hwnd}")
                    print(f"      │   Full ID: {full_id}")
                    print(f"      │   Position: ({window['rect'][0]}, {window['rect'][1]})")
                    print(f"      │   Size: {window['rect'][2]-window['rect'][0]}x{window['rect'][3]-window['rect'][1]}")
                
                # Show minimized windows
                minimized_windows = [w for w in app_data['windows'] if w.get('minimized', False)]
                if minimized_windows:
                    print(f"      │")
                    for window in minimized_windows:
                        title = window.get('title', 'Unknown')
                        title = title[:50] + "..." if len(title) > 50 else title
                        hwnd = window.get('hwnd', 'Unknown')
                        full_id = window.get('window_id', hwnd)
                        print(f"      ├─ 📦 {title} (minimized)")
                        print(f"      │   HWND: {hwnd}")
                        print(f"      │   Full ID: {full_id}")

        print("\n" + "=" * 80)
        print("\n💡 TIP: Use the full window ID for commands")
        print("   Example: maximize <full_id>, minimize <full_id>, close <full_id>")

    async def print_server_commands(self):
        """Fetch and print the available commands from the server."""
        tools = await self.get_available_tools()
        print("\n=== MCP Server Commands ===")
        for section, commands in tools.items():
            if not commands:
                continue
            section_title = {
                "window_commands": "📋 Window Commands",
                "mouse_commands": "🖱️  Mouse Commands",
                "keyboard_commands": "⌨️  Keyboard Commands",
                "system_commands": "💻 System Commands"
            }.get(section, section)
            print(f"\n{section_title}:")
            for cmd, info in commands.items():
                params = ', '.join(f"{k}: {v}" for k, v in info.get('params', {}).items())
                print(f"  • {cmd}: {info['description']}")
                if params:
                    print(f"    Parameters: {params}")
        
        # Add command chaining examples
        print("\n🔗 Command Chaining:")
        print("  Chain multiple commands using ' : ' (space-colon-space)")
        print("\n  Examples:")
        print("  • maximize 12345678 : move 12345678 100 100 : resize 12345678 800 600")
        print("  • cursor 200 200 : click : send ctrl+c : cursor 300 300 : click : send ctrl+v")
        print("  • launch notepad.exe 1 false : cursor 100 100 : click : type Hello World : send ctrl+s")
        print("\n  Note: Commands execute in sequence with small delays between them.")
        print("        If any command fails, the chain stops at that point.")
        
        print("\n✅ Ready to accept commands!\n")

    async def interactive_loop(self):
        """Run the interactive window controller"""
        print("🚀 Starting Interactive Window Manager...")
        
        # Initial display
        #await self.print_windows_summary()
        
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
            await self.print_server_commands()
            return
        
        # Command chaining
        if ' : ' in user_input:
            commands = [cmd.strip() for cmd in user_input.split(' : ')]
            for i, cmd in enumerate(commands):
                if not cmd:
                    continue
                result = await self._execute_single_command(cmd)
                status = "✅" if result.get('success', False) else "❌"
                message = result.get('message', result.get('error', 'Unknown error'))
                print(f"{status} {message}")
                if not result.get('success', False):
                    print(f"⚠️  Chain stopped at step {i+1}")
                    break
                await asyncio.sleep(0.1)
            return
        
        # Single command execution
        result = await self._execute_single_command(user_input)
        status = "✅" if result.get('success', False) else "❌"
        message = result.get('message', result.get('error', 'Unknown result'))

        # Special handling for get_windows
        if user_input.strip().startswith("get_windows") and result.get('success', False):
            windows = result.get('result', {}).get('windows', [])
            print(f"{status} Found {len(windows)} windows")
            for w in windows:
                print(f"  - Title: {w.get('title', 'Unknown')}, HWND: {w.get('hwnd', 'Unknown')}, Full ID: {w.get('window_id', w.get('hwnd', 'Unknown'))}, App: {w.get('proc', 'Unknown')}, Minimized: {w.get('minimized', False)}, Screen: {w.get('screen', 'Unknown')}")
        else:
            print(f"{status} {message}")

    async def _execute_single_command(self, command_str: str) -> Dict:
        """Execute a single command - internal method for chaining"""
        parts = command_str.strip().split()
        if not parts:
            return {"error": "Empty command"}
        
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
        
        # NEW: If this is a window command and the second argument is present, treat it as window_id
        if cmd in tools.get('window_commands', {}) and len(parts) >= 2:
            params['window_id'] = parts[1]
            # Add extra params for resize/move/screen/monitor if needed
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