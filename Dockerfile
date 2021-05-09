ARG SERVER_VERSION=local+container

# Start with rocker/tidyverse base image
FROM rocker/verse:3.6.3

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Install extra *nix utils
# x11, mesa, glu1 are so we can install paletteer
RUN apt-get update \
    && apt-get install -y \
    build-essential \
    libpq-dev \
    pigz \
    vim \
    git \
    less \
    curl \
    wget \
    parallel \
    python3-pip \
    bzip2 \
    bsdtar \
    libcairo2-dev \
    libfontconfig1-dev \
    ca-certificates \
    dos2unix \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# get and install bcl2fastq
RUN wget -qO- https://www.dropbox.com/s/idi0xfu0thurk7q/bcl2fastq2-v2-20-0-linux-x86-64.zip \
    | bsdtar -xOf - bcl2fastq2-v2.20.0.422-Linux-x86_64.rpm \
    | bsdtar -xf - -C / usr/local/bin/bcl2fastq

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Basespace
RUN wget "https://api.bintray.com/content/basespace/BaseSpaceCLI-EarlyAccess-BIN/latest/\$latest/amd64-linux/bs?bt_package=latest" -O /usr/local/bin/bs
RUN chmod +x /usr/local/bin/bs

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# R Deps
RUN install2.r --error \
    BiocManager \
    seqinr \
    viridis \
    GGally \
    reader \
    plater \
    XML \
    DT \
    glmnet \
    speedglm \
    sandwich \
    ggbeeswarm \
    stringdist \
    argparser \
    kableExtra

# Install bioconductor packages
RUN R --slave -e "BiocManager::install(c('savR', 'edgeR', 'qvalue', 'ShortRead', 'Rqc'))"

# Config file for basespace
RUN mkdir /root/.basespace/

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python Env
WORKDIR /app

RUN pip3 install \
    pandas \
    git+https://github.com/lab-grid/script-runner.git@3cdb80fa788ce5fdb139e90c4025b11e7f70c2f0

COPY ./entrypoint.sh /entrypoint.sh
RUN dos2unix /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY ./ .

ENV PYTHONPATH="${RBASE}:${PYTHONPATH}"
ENV FLASK_APP=script_runner.main:app
ENV SERVER_VERSION=$SERVER_VERSION

ENTRYPOINT [ "/entrypoint.sh" ]
