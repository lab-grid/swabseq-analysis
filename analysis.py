import base64
import csv
import glob
import tempfile
import traceback
import os
import shutil
import subprocess
from celery import Celery


# Celery ----------------------------------------------------------------------

celery = Celery(
    'swabseq-analysis-celery',
    backend=os.environ.get('CELERY_RESULT_BACKEND', None),
    broker=os.environ.get('CELERY_BROKER_URL', None),
)

# celery.conf.update(app.config)


# Analysis --------------------------------------------------------------------

count_table_fields = {
    'plateIndex': 'Plate_384_Number',
    'plateCell': 'Sample_Well',
    'marker1': 'index',
    'marker2': 'index2',
    'classification': 'classification',
}

def result_is_valid(result):
    return result.get('plateIndex', 'NA') != 'NA' \
        and result.get('plateCell', 'NA') != 'NA' \
        and result.get('marker1', 'NA') != 'NA' \
        and result.get('marker2', 'NA') != 'NA'

def b64encode_file(filepath):
    with open(filepath, "rb") as input_file:
        return base64.b64encode(input_file.read()).decode('utf-8')

def read_csv_as_dict_list(filepath, filter_fn=None):
    with open(filepath, "r") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        if filter_fn is None:
            filter_fn = lambda x: True
        return [x for x in csv_reader if filter_fn(x)]

def rename_fields(original, fields):
    return {
        new_field: original[original_field]
        for new_field, original_field
        in fields.items()
        if original_field in original
    }

def do_analysis(rundir, basespace_id, threads=8, season=None, debug=False):
    os.makedirs(os.path.join(rundir, "out"))

    script_args = [
        "Rscript",
        "--vanilla",
        "code/countAmpliconsAWS.R",
        "--rundir",
        f"{rundir}/",
        "--basespaceID",
        basespace_id,
    ]
    
    if threads is not None:
        script_args.append("--threads")
        script_args.append(str(threads))

    if season is not None:
        script_args.append("--season")
        script_args.append(season)
        
    if debug:
        script_args.append("--debug")

    subprocess.check_call(script_args)

    count_table_raw = read_csv_as_dict_list(f"{rundir}/LIMS_results.csv")

    attachments = {
        'LIMS_results.csv': b64encode_file(f"{rundir}/LIMS_results.csv"),
    }
    for pdf_attachment in glob.glob(f"{rundir}/*.pdf"):
        attachments[os.path.basename(pdf_attachment)] = b64encode_file(pdf_attachment)
    
    results = []
    for row in count_table_raw:
        result = rename_fields(row, count_table_fields)
        if result_is_valid(result):
            results.append(result)

    return {
        'status': 'ready',
        'basespace_id': basespace_id,
        'results': results,
        'attachments': attachments,
    }

def log_disk_usage(path = None):
    if path is None:
        path = os.getcwd()
    stat = shutil.disk_usage(path)
    print(f"Disk usage statistics for '{path}':")
    print(stat)

@celery.task()
def run_analysis(basespace_id, rundir=None, season=None):
    try:
        threads = int(os.environ.get('RSCRIPT_THREADS', '8'))
        debug = os.environ.get('RSCRIPT_DEBUG', 'False') == 'True'
        rscript_rundir = os.environ.get('RSCRIPT_RUNDIR', os.getcwd())

        # Run R script and zip results to generate temp file
        if debug:
            # If we're in debug mode, don't delete the work directory
            rundir = tempfile.TemporaryDirectory(prefix=f"{basespace_id}-results-", dir=rscript_rundir).name
            log_disk_usage()
            try:
                return do_analysis(rundir, basespace_id, threads, season, debug)
            finally:
                log_disk_usage()
        else:
            with tempfile.TemporaryDirectory(prefix=f"{basespace_id}-results-", dir=rscript_rundir) as rundir:
                log_disk_usage()
                try:
                    return do_analysis(rundir, basespace_id, threads, season, debug)
                finally:
                    log_disk_usage()
    except Exception as ex:
        ex_str = traceback.format_exc()
        print(ex_str)
        return {
            'status': 'failed',
            'error': ex_str,
        }
