# swabseq_api

Copy of kkovary/swabseq_aws that has been edited in the following ways:
- deleted the option to push results to github
- instead, it just writes results to local disk, in provided directory path (which will be used by Flask API wrapper to write to a random temp directory)
- added Flask app.py that calls the R scripts
- added a Dockerfile that logs into Basespace to be able to get files, and installs the necessary R and Python dependencies.

## Usage
 * `Rscript countAmpliconsAWS.R --basespaceID [ID for run] --threads [number of threads for running bcl2fastq]`
 * The basespaceID is used to identify the run on BaseSpace and then download the raw data which is then demultiplexed with bcl2fastq and then analyzed, where a PDF of run info and results is generated, along with a csv file with the unique DNA barcodes for each sample, the location of that sample on 96 and 384 well plates, the number of counts for the targeted amplicons, and the classification of the sample (COVID positive, COVID negative, or inconclusive/failed sample).

