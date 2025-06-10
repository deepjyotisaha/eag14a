import os
import json
from functools import wraps
import networkx as nx
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def load_configuration():
    """Load and validate configuration from config.json"""
    config_path = "utils/config.json"
    
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found!")
        return None
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None

def debug_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        config = load_configuration()
        if config and config.get("mode", "").lower() == "debug":
            return func(*args, **kwargs)
    return wrapper

@debug_only
def debug_print(*args, **kwargs):
    print(*args, **kwargs)

def render_graph(graph: nx.DiGraph, depth: int = 1, title: str = "Computer Agent", color: str = "blue"):
    """Render the execution graph with step status and details
    
    Args:
        graph: NetworkX directed graph
        depth: Depth of the graph to show
        title: Title for the graph
        color: Color theme for the graph
    """
    logger.info(f"\n{'='*80}\n{title} Execution Graph (Depth: {depth})\n{'='*80}")
    
    # Print nodes with their status
    for node_id in graph.nodes:
        node = graph.nodes[node_id]["data"]
        status_emoji = {
            "pending": "⏳",
            "completed": "✅",
            "failed": "❌",
            "skipped": "⏭️"
        }.get(node.status, "❓")
        
        logger.info(f"\n{status_emoji} Step: {node.index}")
        logger.info(f"   Description: {node.description}")
        logger.info(f"   Type: {node.type}")
        
        if node.result:
            logger.info(f"   Result: {json.dumps(node.result, indent=2)}")
        if node.error:
            logger.info(f"   Error: {node.error}")
        if node.perception:
            logger.info(f"   Perception: {json.dumps(node.perception, indent=2)}")
        if node.from_step:
            logger.info(f"   From Step: {node.from_step}")
            
    logger.info(f"\n{'='*80}")
