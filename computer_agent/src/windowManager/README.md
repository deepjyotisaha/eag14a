# MCP SSE Server

## Overview

The MCP SSE Server provides a RESTful and real-time (SSE) API for controlling windows, mouse, keyboard, and system functions on a Windows machine. It is designed for automation, remote control, and integration with other systems.

- **API Protocol:** HTTP (JSON)
- **Real-time Updates:** Server-Sent Events (SSE)
- **Short Window ID Support:** Use either the full window ID (format: `HWND_PID_HASH`) or the last 8 characters for window commands.

---

## Usage

### 1. Start the MCP SSE Server

If you use [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
uv venv  # Create a virtual environment (if not already)
uv pip install -r ../../../../requirements.txt  # Install dependencies (adjust path as needed)
uv pip install aiohttp psutil pywin32  # (if not in requirements.txt)
uv pip install -e .  # (if you have a setup.py/pyproject.toml)
```

Then start the server:

```bash
uv pip run python mcp_server_windows.py
# or, if uv pip run is not available:
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python mcp_server_windows.py
```

The server will start and listen on `http://localhost:8080`.

---

### 2. Use the Interactive Test Client

The interactive client lets you connect to the server, see available commands, and issue commands interactively.

```bash
uv pip run python mcp_server_windows_interactive_client.py
# or, if uv pip run is not available:
python mcp_server_windows_interactive_client.py
```

**Features:**
- Shows available server commands and parameters on connect.
- Prints a summary of all windows (with full and short IDs) at startup.
- Lets you enter commands like:
  ```
  maximize <window_id>
  minimize <window_id>
  close <window_id>
  move <window_id> 100 100
  click left 200 300
  send ctrl+c
  launch notepad.exe 1 false
  ```
- Supports command chaining with `:` (e.g., `minimize <id>:maximize <id>`).
- Prints results and errors in a user-friendly way.

---

### 3. Example Interactive Session

```
$ python mcp_server_windows_interactive_client.py

=== MCP Server Connected ===
Available Commands:
...

================================================================================
WINDOW MANAGER - 24 windows across 1 monitors
================================================================================

📺 MONITOR 1
   Windows: 24
------------------------------------------------------------

   🖥️  explorer.exe
      Total: 6 | Visible: 6 | Minimized: 0
      ├─ 👁️  windowManager - File Explorer
      │   HWND: 1117512
      │   Full ID: 1117512_12345_abcd1234
      │   Position: (100, 100)
      │   Size: 800x600

💻 Enter command (or 'q' to quit): maximize 1117512_12345_abcd1234
[Result] ✅ Window maximized

💻 Enter command (or 'q' to quit): send ctrl+s
[Result] ✅ Sent key combination

💻 Enter command (or 'q' to quit): q
Goodbye!
```

---

### 4. Tips

- Use the full window ID or the last 8 characters (short ID) for window commands.
- Use `refresh_windows` or `get_windows` to update the window list if you get "Window is no longer valid".
- All commands and parameters are shown at startup and can be listed again by typing `help` or `legend` (if implemented).

---

## Endpoints

| Method | Path         | Description                                 |
|--------|--------------|---------------------------------------------|
| GET    | `/sse`       | Connect for real-time event streaming (SSE) |
| POST   | `/command`   | Execute a command (window, mouse, etc.)     |
| GET    | `/tools`     | List all available tools and parameters     |
| GET    | `/history`   | Get command execution history               |

---

## Tool Categories and Commands

### 1. **Window Commands**

| Command      | Description                | Parameters                                                                 |
|--------------|----------------------------|----------------------------------------------------------------------------|
| maximize     | Maximize window            | `window_id` (string, full or last 8 chars)                                 |
| minimize     | Minimize window            | `window_id` (string)                                                       |
| close        | Close window               | `window_id` (string)                                                       |
| resize       | Resize window              | `window_id` (string), `width` (number), `height` (number)                  |
| move         | Move window                | `window_id` (string), `x` (number), `y` (number)                           |
| screen       | Move to screen position    | `window_id` (string), `screen` (number), `x` (number), `y` (number)        |
| monitor      | Move to monitor            | `window_id` (string), `monitor` (number)                                   |
| introspect   | Deep window introspection  | `window_id` (string)                                                       |
| tree         | Show UI hierarchy tree     | `window_id` (string)                                                       |
| get_windows  | Get all windows            | `show_minimized` (boolean)                                                 |

#### **Sample Usage**

```bash
curl -X POST http://localhost:8080/command \
  -H "Content-Type: application/json" \
  -d '{"command": "maximize", "params": {"window_id": "abcdefgh"}}'
```

```bash
curl -X POST http://localhost:8080/command \
  -H "Content-Type: application/json" \
  -d '{"command": "resize", "params": {"window_id": "abcdefgh", "width": 800, "height": 600}}'
```

---

### 2. **Mouse Commands**

| Command      | Description                | Parameters                                                                 |
|--------------|----------------------------|----------------------------------------------------------------------------|
| click        | Mouse click                | `button` (string: left/right/middle), `x` (number), `y` (number)           |
| doubleclick  | Double click               | `button` (string), `x` (number), `y` (number)                              |
| longclick    | Long click                 | `button` (string), `duration` (number), `x` (number), `y` (number)         |
| scroll       | Scroll                     | `direction` (string: up/down/left/right), `amount` (number), `x`, `y`      |
| drag         | Drag                       | `start_x`, `start_y`, `end_x`, `end_y` (numbers), `button`, `duration`     |

#### **Sample Usage**

```bash
curl -X POST http://localhost:8080/command \
  -H "Content-Type: application/json" \
  -d '{"command": "click", "params": {"button": "left", "x": 100, "y": 200}}'
```

```bash
curl -X POST http://localhost:8080/command \
  -H "Content-Type: application/json" \
  -d '{"command": "drag", "params": {"start_x": 100, "start_y": 200, "end_x": 300, "end_y": 400, "button": "left", "duration": 0.5}}'
```

---

### 3. **Keyboard Commands**

| Command      | Description                | Parameters                                                                 |
|--------------|----------------------------|----------------------------------------------------------------------------|
| send         | Send key combination       | `keys` (string, e.g., "ctrl+c")                                           |
| type         | Type text                  | `text` (string)                                                           |

#### **Sample Usage**

```bash
curl -X POST http://localhost:8080/command \
  -H "Content-Type: application/json" \
  -d '{"command": "send", "params": {"keys": "ctrl+s"}}'
```

```bash
curl -X POST http://localhost:8080/command \
  -H "Content-Type: application/json" \
  -d '{"command": "type", "params": {"text": "Hello, world!"}}'
```

---

### 4. **System Commands**

| Command      | Description                | Parameters                                                                 |
|--------------|----------------------------|----------------------------------------------------------------------------|
| launch       | Launch application         | `app_name` (string), `screen_id` (number), `fullscreen` (boolean)          |
| msgbox       | Show message box           | `title` (string), `message` (string), `x` (number), `y` (number)           |
| computer     | Get computer name          | (none)                                                                     |
| user         | Get user name              | (none)                                                                     |
| keys         | Show virtual key codes     | (none)                                                                     |

#### **Sample Usage**

```bash
curl -X POST http://localhost:8080/command \
  -H "Content-Type: application/json" \
  -d '{"command": "launch", "params": {"app_name": "C:\\Windows\\System32\\mspaint.exe", "screen_id": 1, "fullscreen": false}}'
```

```bash
curl -X POST http://localhost:8080/command \
  -H "Content-Type: application/json" \
  -d '{"command": "msgbox", "params": {"title": "Hello", "message": "This is a test", "x": 400, "y": 300}}'
```

---

## Real-Time Event Streaming (SSE)

- **Connect to `/sse`** using an SSE-capable client (e.g., EventSource in JavaScript).
- You will receive events such as:
  - `init` (on connect, with available tools)
  - `command_result` (when any client executes a command)

#### **Sample JavaScript Client**

```js
const evtSource = new EventSource("http://localhost:8080/sse");
evtSource.onmessage = (event) => {
  console.log("SSE event:", event.data);
};
```

---

## Tool Discovery

- **GET `/tools`** returns a JSON object describing all available commands and their parameters.

#### **Sample Usage**

```bash
curl http://localhost:8080/tools
```

---

## Command History

- **GET `/history`** returns a list of recent commands and their results.

#### **Sample Usage**

```bash
curl http://localhost:8080/history
```

---

## Notes

- For all window commands, you may use either the full window ID or the last 8 characters (short ID).
- All requests and responses use JSON.
- The server must be running on a Windows machine with the required dependencies.

---

## Example Workflow

1. **List all windows:**
   ```bash
   curl -X POST http://localhost:8080/command \
     -H "Content-Type: application/json" \
     -d '{"command": "get_windows", "params": {"show_minimized": true}}'
   ```
2. **Pick a window's ID (or last 8 chars), then maximize it:**
   ```bash
   curl -X POST http://localhost:8080/command \
     -H "Content-Type: application/json" \
     -d '{"command": "maximize", "params": {"window_id": "abcdefgh"}}'
   ```

---

## Troubleshooting

- If you receive an error about a window ID, ensure you are using a valid full or short ID from the latest `get_windows` call.
- For mouse/keyboard coordinates, ensure the target window is visible and not minimized.

---

## License

MIT (or as specified in your project) 