# swabseq-analysis

Turns kkovary/swabseq_aws into a containerized Flask API with authentication.

Original code has been edited in the following ways:
- deleted the option to push results to github
- instead, it just writes results to local disk, in provided directory path (which will be used by Flask API wrapper to
  write to a random temp directory)
- added Flask app.py that calls the R scripts
- added a Dockerfile that logs into Basespace to be able to get files, and installs the necessary R and Python
  dependencies.

## Development

To run the server locally:
```
docker-compose up --build
```

To test, run 2 scripts. One to generate results for the demo sequencing data, and the other to retrieve those results (use .ps only if using Microsoft Powershell):
```
./test_unauthenticated.sh
<record the id returned>
<wait several minutes until server stops printing processing messages>
./test_unauthenticated-results.sh <id> > demo_output.json
```

Before running first time, create a .env file:
```
cp example.env .env
```

Before running first time, if you will pull sequencing data from Basespace, generate a default.cfg file:

```
docker-compose run --rm server bs auth \
    --scopes "BROWSE GLOBAL,READ GLOBAL,CREATE GLOBAL,MOVETOTRASH GLOBAL,START APPLICATIONS,MANAGE APPLICATIONS" \
    --force
```

This will create a `default.cfg` file in the `./.basespace` directory. Future calls to `docker-compose up` will use
the credentials saved in the `./.basespace` directory.

## Original Script Usage instructions for demo script:

* `Rscript countAmpliconsAWS.R --basespaceID [ID for run] --threads [number of threads for running bcl2fastq]`
* The `--basespaceID` is used to identify the run on BaseSpace and then download the raw data which is then
  demultiplexed with `bcl2fastq` and then analyzed, where a PDF of run info and results is generated, along with a csv
  file with the unique DNA barcodes for each sample, the location of that sample on 96 and 384 well plates, the number
  of counts for the targeted amplicons, and the classification of the sample (COVID positive, COVID negative, or
  inconclusive/failed sample).
