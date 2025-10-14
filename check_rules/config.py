import os
import logging
from google import genai
from google.genai import types

# This file centralizes database path configurations to avoid circular imports.

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get the project root directory (which is the parent of the 'check_rules' directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define the main directory for databases
DATABASES_DIR = os.path.join(PROJECT_ROOT, 'databases')

# Path for the main claims database
DB_PATH = os.getenv(
    'DB_PATH', 
    os.path.join(DATABASES_DIR, 'claims_database.db')
)

# Path for the rules database
RULES_DB_PATH = os.getenv(
    'RULES_DB_PATH', 
    os.path.join(DATABASES_DIR, 'rules.db')
)

# Path for processed output directory
PROCESSED_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'processed_output', 'results')

# Ensure the databases directory exists
if not os.path.exists(DATABASES_DIR):
    os.makedirs(DATABASES_DIR)
    logging.info(f"Created directory: {DATABASES_DIR}")


# --- Gemini Model Configuration ---
from dotenv import load_dotenv

# Load environment variables from .env file located in the project root
ENV_PATH = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(ENV_PATH):
    load_dotenv(dotenv_path=ENV_PATH)
    logging.info(f"Loaded environment variables from {ENV_PATH}")
else:
    logging.warning(f".env file not found at {ENV_PATH}. Environment variables should be set manually.")

# Get Gemini API Key from environment variable
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Get Gemini Model Name from environment variable, with a fallback
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

def get_gemini_model(response_mime_type: str = "text/plain", enable_thinking: bool = False):
    """
    Initializes and returns a Gemini client for the configured model.

    Reads the GOOGLE_API_KEY and model name from environment variables.

    Args:
        response_mime_type (str): The desired MIME type for the response
                                  (e.g., "text/plain", "application/json").
        enable_thinking (bool): Whether to enable the thinking capability for
                               Gemini 2.5 models (default: False).

    Returns:
        A tuple containing (client, model_name, config) for generating content.
    """
    if not GOOGLE_API_KEY:
        logging.error("GOOGLE_API_KEY environment variable not found or set.")
        return None

    try:
        # Initialize the client
        client = genai.Client(api_key=GOOGLE_API_KEY)
        
        # Configure thinking budget based on enable_thinking parameter
        # -1 = unlimited thinking (default for Gemini 2.5 models)
        #  0 = disable thinking completely
        thinking_budget = -1 if enable_thinking else 0
        
        # Create configuration with thinking settings
        config = types.GenerateContentConfig(
            response_mime_type=response_mime_type
        )
        
        # Only add thinking_config if using Gemini 2.5 models
        if "2.5" in GEMINI_MODEL_NAME:
            config.thinking_config = types.ThinkingConfig(thinking_budget=thinking_budget)
        
        return client, GEMINI_MODEL_NAME, config
    except Exception as e:
        logging.error(f"Failed to initialize Gemini client: {e}")
        return None

