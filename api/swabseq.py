from celery.result import AsyncResult

from flask import abort, request, send_file
from flask_restx import Resource, fields, Namespace

from analysis import run_analysis
from authorization import requires_auth
from server import app
from analysis import celery


api = Namespace('swabseq', description='Operations for Swabseq sequence data analysis.', path='/')


swabseq_result = api.model('SwabseqResult', {})
swabseq_attachments = api.model('SwabseqAttachments', {
    'LIMS_results.csv': fields.String(),
    'run_info.csv': fields.String(),
    'countTable.csv': fields.String(),
    'SampleSheet.csv': fields.String(),
})
swabseq_output = api.model('SwabseqOutput', {
    'id': fields.String(),
    'basespace_id': fields.String(),
    'status': fields.String(),
    'results': fields.List(fields.Nested(swabseq_result)),
    'attachments': fields.Nested(swabseq_attachments),
})


basespace_id_param = {
    'description': 'String Basespace ID',
    'in': 'path',
    'type': 'string'
}
task_id_param = {
    'description': 'String Task ID',
    'in': 'path',
    'type': 'string'
}
season_param = {
    'description': 'Season identifier',
    'in': 'query',
    'type': 'string'
}


@api.route('/swabseq/<string:basespace_id>')
class AnalysisTasksResource(Resource):
    @api.doc(security='token', model=swabseq_output, params={'basespace_id': basespace_id_param, 'season': season_param})
    @requires_auth
    def post(self, basespace_id):
        if not basespace_id:
            abort(400, description='Error. Not a valid Basespace run name string')
            return
        
        season = request.args.get('season')

        task = run_analysis.delay(basespace_id, season)

        return {
            "id": task.task_id,
            "status": "ready" if task.ready() else "not-ready",
        }


@api.route('/swabseq/<string:basespace_id>/<string:task_id>')
class AnalysisTaskResource(Resource):
    @api.doc(security='token', model=swabseq_output, params={'basespace_id': basespace_id_param, 'task_id': task_id_param})
    @requires_auth
    def get(self, basespace_id, task_id):
        if not basespace_id:
            abort(400, description='Error. Not a valid Basespace run name string')
            return

        result = AsyncResult(task_id)

        if result.ready():
            response = result.get()
            response['id'] = result.task_id
            return response
        else:
            return {
                'id': result.task_id,
                'status': 'not-ready',
            }
