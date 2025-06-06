import asyncio
import logging
from agent.computer_agent import ComputerAgent

# Set up logging
logging.basicConfig(level=logging.INFO)

async def main():
    # Create agent
    agent = ComputerAgent()
    
    # Test query
    query = "Open Notepad and type 'Hello World'"
    
    # Run agent
    result = await agent.run(query)
    
    # Print result
    print("\nAgent Result:")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Session ID: {result['session_id']}")
        print(f"Summary saved to: {result['summary_path']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())
