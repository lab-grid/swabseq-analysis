import base64
import csv
import tempfile
import os
import subprocess
from flask import abort, request, send_file
from flask_restx import Resource, fields, Namespace

from authorization import requires_auth
from server import app


api = Namespace('swabseq', description='Operations for Swabseq sequence data analysis.', path='/')


swabseq_input = api.model('SwabseqInput', {
    'basespace': fields.String()
})
swabseq_result = api.model('SwabseqResult', {})
swabseq_attachments = api.model('SwabseqAttachments', {
    'LIMS_results.csv': fields.String(),
    'run_info.csv': fields.String(),
    'countTable.csv': fields.String(),
    'SampleSheet.csv': fields.String(),
})
swabseq_output = api.model('SwabseqOutput', {
    'id': fields.String(),
    'results': fields.List(fields.Nested(swabseq_result)),
    'attachments': fields.Nested(swabseq_attachments),
})


basespace_id_param = {
    'description': 'String Basespace ID',
    'in': 'path',
    'type': 'string'
}


count_table_fields = {
    'plateIndex': 'Plate_384_Number',
    'plateCell': 'Sample_Well',
    'marker1': 'index',
    'marker2': 'index2',
    'classification': 'classification',
}


def b64encode_file(filepath):
    with open(filepath, "r") as input_file:
        return base64.b64encode(input_file.read()).encode()

def read_csv_as_dict_list(filepath):
    with open(filepath, "r") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        return [x for x in csv_reader]

def rename_fields(original, fields):
    return {
        new_field: original[original_field]
        for new_field, original_field
        in fields.items()
    }


@api.route('/swabseq/<string:basespace_id>')
class RunsResource(Resource):
    @api.doc(security='token', body=swabseq_input, params={'basespace_id': basespace_id_param})
    @requires_auth
    def get(self, basespace_id):
        if not basespace_id:
            abort(400, description='Error. Not a valid Basespace run name string')
            return

        # Run R script and zip results to generate temp file
        with tempfile.TemporaryDirectory(prefix=f"{basespace_id}-results-", dir=os.getcwd()) as rundir:
            # rundir = tempfile.TemporaryDirectory(prefix=f"{basespace_id}-results-", dir=os.getcwd()).name
            os.makedirs(os.path.join(rundir, "out"))

            subprocess.call([
                "Rscript",
                "--vanilla",
                "code/countAmpliconsAWS.R",
                "--rundir",
                f"{rundir}/",
                "--basespaceID",
                basespace_id,
                "--threads",
                f"{app.config['RSCRIPT_THREADS']}"
            ])

            count_table_raw = read_csv_as_dict_list(f"{rundir}/countTable.csv")

            return {
                'id': basespace_id,
                'results': [rename_fields(row, count_table_fields) for row in count_table_raw],
                'attachments': {
                    'LIMS_results.csv': b64encode_file(f"{rundir}/LIMS_results.csv"),
                    'run_info.csv': b64encode_file(f"{rundir}/run_info.csv"),
                    f"{basespace_id}.pdf": b64encode_file(f"{rundir}/{basespace_id}.pdf"),
                    'countTable.csv': b64encode_file(f"{rundir}/countTable.csv"),
                    'SampleSheet.csv': b64encode_file(f"{rundir}/SampleSheet.csv"),
                },
            }
