from dotenv import load_dotenv
import os
import logging

load_dotenv()

# Chatbot Configuration
EMBEDDING_DIMENSION = 1536
AUTHORIZATION_TOKEN = os.environ['AUTHORIZATION_TOKEN']

# Secret Keys
COGNITIVE_SEARCH_CONFIG = {
    'api_key': os.environ['COGNITIVE_SEARCH_API_KEY'],
    'endpoint': os.environ['COGNITIVE_SEARCH_ENDPOINT'],
    'index_name': os.environ['COGNITIVE_SEARCH_INDEX_NAME']
}

ADA_CONFIG = {
    'api_key': os.environ['OPENAI_API_KEY'],
    'api_base': os.environ['OPENAI_API_BASE'],
    'api_version': os.environ['ADA_API_VERSION'],
    'model': os.environ['ADA_MODEL'],
    'deployment_name': os.environ['ADA_DEPLOYMENT_NAME']
}

GPT_CONFIG = {
    'api_key': os.environ['OPENAI_API_KEY'],
    'api_base': os.environ['OPENAI_API_BASE'],
    'api_version': os.environ['GPT_API_VERSION'],
    'model': os.environ['GPT_MODEL'],
    'deployment_name': os.environ['GPT_DEPLOYMENT_NAME']
}

BLOB_STORAGE_CONFIG = {
    'connection_string': os.environ['BLOB_STORAGE_CONNECTION_STRING'],
    'container_name': os.environ['BLOB_STORAGE_CONTAINER_NAME']
}

# API Settings
PORT = "8000"
HOST = "0.0.0.0"
CONCURRENCY_LIMIT = 50

# Logging Configuration
logger = logging.getLogger('PoC')
formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s', "%Y-%m-%d %H:%M:%S")

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)
app_logger = logger
