ARG SERVER_VERSION=local+container

FROM centos:7 AS bcl-build

RUN test -n $SERVER_VERSION
RUN yum update -y \
    && yum install -y wget unzip git python-devel \
    && yum groupinstall -y "Development Tools"


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# get and install bcl2fastq
RUN cd /tmp \
    && wget https://www.dropbox.com/s/idi0xfu0thurk7q/bcl2fastq2-v2-20-0-linux-x86-64.zip \
    && unzip bcl2fastq2-v2-20-0-linux-x86-64.zip \
    && yum install -y bcl2fastq2-v2.20.0.422-Linux-x86_64.rpm
RUN rm /tmp/bcl2fastq2*

# Start with rocker/tidyverse base image
FROM rocker/verse:3.6.3
COPY --from=bcl-build /usr/local/bin/bcl2fastq /usr/local/bin/bcl2fastq

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
    libcairo2-dev \
    libfontconfig1-dev \
    ca-certificates \
    dos2unix \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

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

RUN pip3 install git+https://github.com/lab-grid/script-runner.git@e7fe853a4e553f3a3c889d2724de40b232b08081

COPY ./entrypoint.sh /entrypoint.sh
RUN dos2unix /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY ./ .

ENV PYTHONPATH="${RBASE}:${PYTHONPATH}"
ENV FLASK_APP=/app/main.py
ENV SERVER_VERSION=$SERVER_VERSION

ENTRYPOINT [ "/entrypoint.sh" ]
