FROM debian:12
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /research
RUN apt update && apt install -yqq python3-dev python3-pip python3-yaml python3-debian graphviz python3-pygraphviz git vim mc && apt clean
COPY . .
CMD ["bash"]

