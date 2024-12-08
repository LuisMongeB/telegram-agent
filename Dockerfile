FROM mcr.microsoft.com/azure-functions/python:4-python3.11

# Set environment variables for Azure Functions
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Install ffmpeg for audio processing
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt /
RUN pip install -r /requirements.txt

# Create the necessary directory structure
RUN mkdir -p /home/site/wwwroot

# Copy application files in the correct order and to the right locations
# First, copy the shared code to maintain proper imports
COPY shared_code /home/site/wwwroot/shared

# Copy the functions directory with your webhook handler
COPY functions /home/site/wwwroot/functions

# Copy the Azure Functions configuration files
COPY host.json /home/site/wwwroot/
COPY local.settings.json /home/site/wwwroot/
COPY function_app.py /home/site/wwwroot/

# Set the Python path to ensure imports work correctly
ENV PYTHONPATH="/home/site/wwwroot"

# Run config.py to set up environment (if needed)
RUN python /home/site/wwwroot/shared_code/config.py || true