import tempfile
import subprocess
from flask import abort, request, send_file
from flask_restx import Resource, fields, Namespace

from authorization import requires_auth


api = Namespace('swabseq', description='Operations for Swabseq sequence data analysis.', path='/')


swabseq_input = api.model('SwabseqInput', {
    'basespace': fields.String()
})


@api.route('/swabseq')
class RunsResource(Resource):
    @api.doc(security='token', body=swabseq_input)
    @requires_auth
    def post(self):
        try:
            data_dict = request.json
        except Exception:
            abort(400, description='Error. Not a valid Basespace run name. Please provide json with field basespace:<Basespace ID>')
            return

        basespace_id = data_dict['basespace'] if 'basespace' in data_dict else None
        if not basespace_id:
            abort(400, description='Error. Not a valid Basespace run name string')
            return

        # Run R script and zip results to generate temp file
        with tempfile.TemporaryDirectory(prefix=f"{basespace_id}-results-") as rundir:
            subprocess.call([
                "Rscript",
                "--vanilla",
                "swabseq_api/code/countAmpliconsAWS.R",
                "--rundir",
                f"{rundir}/",
                "--basespaceID",
                basespace_id,
                "--threads",
                "8"
            ])

            with tempfile.TemporaryDirectory(prefix=f"{basespace_id}-results-zipped-") as zipdir:
                results_file = f"{zipdir}/results.zip"
                subprocess.call([
                    "zip",
                    "-r",
                    results_file,
                    f"{rundir}/LIMS_results.csv",
                    f"{rundir}/run_info.csv",
                    f"{rundir}/{basespace_id}.pdf",
                    f"{rundir}/countTable.csv",
                    f"{rundir}/SampleSheet.csv",
                ])
                return send_file(
                    results_file,
                    mimetype="application/zip",
                    attachment_filename="results.zip",
                    as_attachment=True,
                )
