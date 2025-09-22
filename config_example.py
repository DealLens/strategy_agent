"""
Configuration example for DealLens Strategy Agent

Copy this file to config.py and update with your actual API keys.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Azure OpenAI Configuration
AOAI_API_KEY = os.getenv("AOAI_API_KEY", "your_azure_openai_api_key_here")
AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT", "https://your-resource-name.openai.azure.com/")
AOAI_DEPLOY_GPT4O = os.getenv("AOAI_DEPLOY_GPT4O", "gpt-4o")
AOAI_API_VERSION = os.getenv("AOAI_API_VERSION", "2024-10-21")

# OpenAI Configuration (Alternative)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

# Application Configuration
APP_NAME = "DealLens Strategy Agent"
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Streamlit Configuration
STREAMLIT_THEME = "light"
STREAMLIT_LAYOUT = "wide"
