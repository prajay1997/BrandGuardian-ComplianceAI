import os           # Access environment variables (like API keys)
import logging      # Python's built-in logging system
from azure.monitor.opentelemetry import configure_azure_monitor  
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
# ↑ Azure's OpenTelemetry integration - tracks app performance, errors, requests

# ========== CREATE A DEDICATED LOGGER ==========
# Creates a named logger specifically for telemetry-related messages
# This separates telemetry logs from your main application logs
logger = logging.getLogger("brand-guardian-telemetry")
# Example log output: "brand-guardian-telemetry - INFO - Azure Monitor enabled"


def setup_telemetry():
    """
    Initializes Azure Monitor OpenTelemetry.
    
    What is OpenTelemetry?
    - Industry-standard observability framework
    - Tracks: HTTP requests, database queries, errors, performance metrics
    - Sends this data to Azure Monitor (like a "flight data recorder" for your app)
    
    What does "hooks into FastAPI automatically" mean?
    - Once configured, it auto-captures every API request/response
    - No need to manually log each endpoint
    - Tracks response times, error rates, dependencies (like Azure Search calls)
    """
    
    # ========== STEP 1: RETRIEVE CONNECTION STRING ==========
    # Reads the Azure Monitor connection string from environment variables
    # Example: "InstrumentationKey=abc123;IngestionEndpoint=https://..."
    # This is like a "phone number" to send telemetry data to your Azure workspace
    connection_string = os.getenv("APPLICATION_INSIGHTS_CONNECTION_STRING")
    
    # ========== STEP 2: CHECK IF CONFIGURED ==========
    if not connection_string:
        # If the environment variable is missing/empty, telemetry won't work
        # 
        logger.warning("No Instrumentation Key found. Telemetry is DISABLED.")
        return  # Exit function early - don't try to configure Azure Monitor

    # ========== STEP 3: CONFIGURE AZURE MONITOR ==========
    try:
        # configure_azure_monitor() does the heavy lifting:
        # 1. Registers automatic instrumentation for:
        #    - HTTP requests (FastAPI endpoints)
        #    - Database calls (Azure Search queries)
        #    - Logging events
        # 2. Starts background thread to send data to Azure
        configure_azure_monitor(
            connection_string=connection_string,  # Where to send data
            logger_name="brand-guardian-tracer"   # Optional: custom tracer name
        )

        # Instrument outgoing HTTP calls
        HTTPXClientInstrumentor().instrument()
        RequestsInstrumentor().instrument()

        logger.info(" Azure Monitor Tracking Enabled & Connected!")
        logger.info("✅ HTTPX Instrumentation Enabled")
        logger.info("✅ Requests Instrumentation Enabled")
        
    except Exception as e:
        # ========== ERROR HANDLING ==========
        # If configuration fails (bad connection string, network issue, etc.)
        # 
        logger.error(f"Failed to initialize Azure Monitor: {e}")
        # Note: Function doesn't raise the error - telemetry failure shouldn't crash the app


'''
why do we use telemetry ?

without :
API is slow -> No idea which part
How many users today ? No Visibility

with :
/audit endpoint averages 4.5 s ( Indexer takes 3.8 s)
Error logs show : 12% of audits fail due to youtube download errors
Metrics Show : 450 API calls today, 89% success rate

'''