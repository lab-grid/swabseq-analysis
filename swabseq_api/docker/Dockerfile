# Start with rocker/tidyverse base image
FROM rocker/verse:3.6.3
# FROM ubuntu:16.04


#===============================================================================
 #Fix umask so that everything run at rstudio/user level is group-writable
 RUN echo "umask 0002" >> /home/rstudio/.bashrc


#===============================================================================

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
    parallel


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# R Deps
RUN install2.r --error \
    glmnet \
    speedglm \
    sandwich \
    ggbeeswarm \
    BiocManager \
    stringdist \
    viridis \
    argparser


# Install SwabSeq
RUN git clone https://github.com/kkovary/swabseq_aws.git

# Build dependencies
#RUN apt-get update -qq \
#    && apt-get -y install \
#        --no-install-recommends \
#        apt-transport-https \
#        ca-certificates \
#    && echo "deb [trusted=yes] https://basespace.bintray.com/BaseSpaceCLI-DEB trusty main" | tee -a /etc/apt/sources.list.d/basespace-cli.list \
#    && apt-get update -qq \
#    && apt-get -y install \
#        --no-install-recommends \
#        basespace-cli \
#    && rm -rf /var/lib/apt/lists/*

# Install BaseSpace
 #RUN mkdir -p /bin/bs

 #RUN wget "https://api.bintray.com/content/basespace/BaseSpaceCLI-EarlyAccess-BIN/latest/\$latest/amd64-linux/bs?bt_package=latest" -P /bin/bs

 #RUN chmod u+x /bin/bs

# Install bioconductor packages
RUN R --slave -e "BiocManager::install(c('edgeR', 'qvalue', 'ShortRead', 'Rqc'))"

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# other utils

#
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# final touches

 RUN echo "alias ll='ls -Alrth'" >> ~/.bashrc
 RUN echo "alias ll='ls -Alrth'" >> /home/rstudio/.bashrc
 WORKDIR /home/rstudio
