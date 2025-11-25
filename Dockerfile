FROM python:3.11-slim

WORKDIR /app

# Install system deps needed for some Python packages (keep minimal)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage layer caching
COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . /app

# Expose port (Posit Connect or container runtime can map this)
EXPOSE 8000

# Run Shiny in production mode; allow PORT env override
CMD ["python", "-m", "shiny", "run", "--production", "app:app", "--port", "8000"]
