#Before running first time, generate a default.cfg file:
#bs auth --scopes "BROWSE GLOBAL,READ GLOBAL,CREATE GLOBAL,MOVETOTRASH GLOBAL,START APPLICATIONS,MANAGE APPLICATIONS" --force

FROM centos:7 AS bcl-build

RUN yum update -y \
    && yum install -y wget unzip git python-devel \
    && yum groupinstall -y "Development Tools"


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
##### get and install bcl2fastq
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
    pigz \
    vim \
    git \
    less \
    curl \
    wget \
    parallel \
    python3-pip \
    bzip2 \
    ca-certificates \
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
    argparser

# Install bioconductor packages
RUN R --slave -e "BiocManager::install(c('savR', 'edgeR', 'qvalue', 'ShortRead', 'Rqc'))"

#config file for basespace
RUN mkdir /root/.basespace/
COPY default.cfg /root/.basespace/default.cfg

COPY . /app
EXPOSE 5000
WORKDIR /app

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python Env
RUN pip3 install Flask
RUN pip3 install flask-restplus
RUN pip3 install Werkzeug==0.16.1
RUN pip3 install boto3
RUN pip3 install pybase64
RUN pip3 install pandas
RUN pip3 freeze > /tmp/requirements.txt
#RUN pip3 install -r requirements.txt

ENV PYTHONPATH "${RBASE}:${PYTHONPATH}"
ENTRYPOINT ["python3"]
CMD ["app.py"]


