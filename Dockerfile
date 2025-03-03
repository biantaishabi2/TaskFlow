FROM python:3.9-slim

WORKDIR /app

# 接收构建参数
ARG CLAUDE_CONFIG_PATH

# Install system dependencies and Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gnupg \
    sudo \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m claude-user && \
    echo "claude-user ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/claude-user && \
    chmod 0440 /etc/sudoers.d/claude-user

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Copy project files (excluding .dockerignore files)
COPY . /app/

# Set up Claude configuration directory for non-root user
RUN mkdir -p /home/claude-user/.claude

# Copy Claude configuration file
COPY ${CLAUDE_CONFIG_PATH} /home/claude-user/.claude/claude.json

# Fix ownership
RUN chown -R claude-user:claude-user /app /home/claude-user

# Install Python dependencies
RUN pip install --no-cache-dir \
    flask \
    requests \
    plotly \
    pandas \
    numpy \
    pexpect \
    rich \
    psutil \
    anthropic

# Create necessary directories
RUN mkdir -p /app/logs && chown -R claude-user:claude-user /app/logs

# Expose ports for visualization server
EXPOSE 9000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/claude-user/.npm-global/bin:${PATH}"
ENV HOME="/home/claude-user"
ENV CLAUDE_CONFIG_DIR="/home/claude-user/.claude"

# Switch to non-root user
USER claude-user

# Command to run when container starts
# Uncomment the appropriate entry point based on your needs:
CMD ["python", "task_decomposition_system.py"]
# CMD ["python", "parallel_task_decomposition_system.py"] 
# CMD ["python", "task_visualization_server.py"]
# CMD ["python", "claude_llm_bridge_rich.py"]
# CMD ["claude"]