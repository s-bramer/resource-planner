# 1. Use an official Python image as the base
FROM python:3.11-slim

# 2. Set the working directory in the container
WORKDIR /app

# 3. Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy your app code into the container
COPY . .

# 5. Expose the port Streamlit runs on
EXPOSE 8501

# 6. Command to run when the container starts
CMD ["streamlit", "run", "resource_planner.py", "--server.address=0.0.0.0"]