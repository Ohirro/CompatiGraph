# Use Debian 11 (Bullseye) as the base image
FROM debian:bookworm

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Update the package repository and install development tools
RUN apt-get update -qq && apt-get install -y \
    build-essential \
    git \
    vim \
    curl \
    wget \
    sudo \
    lsb-release \
    ca-certificates \
    python3-pip \
    python3-venv \
    python3-tqdm \
    python3-requests \
    black \
    apt-rdepends \
    python3-debian \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for development
ARG USERNAME=devuser
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user with sudo access
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Switch to the non-root user
USER $USERNAME

# Set the default working directory
WORKDIR /home/$USERNAME

# Switch back to dialog for any ad-hoc use of apt-get
ENV DEBIAN_FRONTEND=dialog

# Optional: If you use a specific port for development, expose it with the EXPOSE instruction
# EXPOSE 3000

CMD ["/bin/bash"]