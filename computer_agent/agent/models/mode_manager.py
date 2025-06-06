"""
Model Manager - Handles LLM interactions
"""
import os
from typing import Optional
import google.generativeai as genai
from config.log_config import setup_logging

logger = setup_logging(__name__)

class ModelManager:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        """
        Initialize the model manager
        
        Args:
            api_key: Google API key (optional, can use environment variable)
            model: Model name to use
        """
        self.model_name = model
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Google API key not provided and GEMINI_API_KEY environment variable not set")
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        
    async def generate_text(self, prompt: str) -> str:
        """
        Generate text using the LLM
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated text
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Failed to generate text: {str(e)}")
            raise
