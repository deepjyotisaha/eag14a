import asyncio
import os
from dotenv import load_dotenv
from agent.computer_agent import ComputerAgent
from config.log_config import setup_logging

# Set up logging
logger = setup_logging(__name__)

BANNER = """
──────────────────────────────────────────────────────
🔸  Computer Agent Assistant  🔸
Type your command and press Enter.
Type 'exit' or 'quit' to leave.
──────────────────────────────────────────────────────
"""

async def interactive():
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment variable
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    # Initialize agent
    logger.info("Initializing Computer Agent...")
    agent = ComputerAgent(api_key=api_key)
    
    # Print banner
    print(BANNER)
    
    conversation_history = []  # stores (query, response) tuples
    
    try:
        while True:
            print("\n")
            query = input("📝  You: ").strip()
            
            if query.lower() in {"exit", "quit"}:
                print("\n👋 Goodbye!")
                break
            
            logger.debug(f"📝 Query: {query}")
            
            # Construct context string from past rounds
            #context_prefix = ""
            #for idx, (q, r) in enumerate(conversation_history, start=1):
            #    context_prefix += f"Query {idx}: {q}\nResponse {idx}: {r}\n"
            
            #logger.debug(f"📝 Context Prefix: {context_prefix}")
            
            #full_query = context_prefix + f"Query {len(conversation_history)+1}: {query}"
            full_query = query

            try:
                # Run agent
                result = await agent.run(full_query)
                
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
                
                # Store in history
                #conversation_history.append((query, str(result)))
                
            except Exception as e:
                logger.error(f"Agent failed: {str(e)}")
                print(f"\n❌ Error: {str(e)}")
            
            # Ask to continue
            follow = input("\nContinue? (press Enter) or type 'exit': ").strip()
            if follow.lower() in {"exit", "quit"}:
                print("\n👋 Goodbye!")
                break
                
    finally:
        # Ensure agent is properly shut down
        await agent.mcp.shutdown()

if __name__ == "__main__":
    asyncio.run(interactive())
