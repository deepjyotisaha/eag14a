import asyncio
import os
from dotenv import load_dotenv
from agent.computer_agent import ComputerAgent


async def main():
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment variable
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    # Initialize agent
    agent = ComputerAgent(api_key=api_key)
    
    # Test query
    query = "Open Notepad and type 'Hello World'"
    
    # Run agent
    result = await agent.run(query)
    
    # Print result
    print("\nAgent Result:")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Session ID: {result['session_id']}")
        if 'summary_path' in result:
            print(f"Summary saved to: {result['summary_path']}")
        if 'summary' in result:
            print(f"Summary: {result['summary']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())
