FROM mcr.microsoft.com/azure-functions/python:4-python3.11

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Install ffmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt /
RUN pip install -r /requirements.txt

# Copy shared directory with config.py first
COPY ./shared_code /home/site/wwwroot/shared

# Copy the rest of the application
COPY . /home/site/wwwroot

# Set Python path
ENV PYTHON_PATH="/home/site/wwwroot"

# Run config.py before starting the Azure Functions host
RUN python /home/site/wwwroot/shared/config.py