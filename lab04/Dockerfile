FROM jenkins/ssh-agent

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       php-cli php-mbstring php-xml composer git unzip \
    && rm -rf /var/lib/apt/lists/*
