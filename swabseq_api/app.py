import csv, os, io
from flask import Flask, stream_with_context, send_file
from flask_restplus import Resource, Api, apidoc
from flask import jsonify, abort, Response, make_response
from werkzeug.middleware.proxy_fix import ProxyFix
import boto3, base64
import subprocess
import shutil

#Authentication
from flask import request

def add_headers(response, origin):
    """
    Published flask-cors libraries did not work with flask_restful, but adding these headers allows CORS with auth
    """
    response.headers.add('Access-Control-Allow-Origin', origin)
    response.headers.add('Access-Control-Allow-Methods', 'OPTIONS, POST')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization')
    return response

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'explorable1456secret'
app.config['JWT_TOKEN_LOCATION'] = ['cookies', 'headers']
app.config['UPLOAD_FOLDER'] = "."
app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
api = Api(app, version='1.0', title='Swabseq API', description='API for sequence analysis.')
api.namespaces = []
app.wsgi_app = ProxyFix(app.wsgi_app) # Let the swagger docs show up when we're on https

@app.before_request
def authorize_token():
    try:
        if (request.method != 'OPTIONS') and (request.method != 'GET'):
            #print(request, flush=True)
            if "Authorization" in request.headers:
                auth_header = request.headers["Authorization"]
                if "Bearer" in auth_header:
                    token_parts = auth_header.split(' ')
                    if len(token_parts) > 1:
                        token = auth_header.split(' ')[1]
                        #payload = jwt.decode(token, app.config['JWT_SECRET_KEY']) # not sure why verification is failing
                        #print(payload)
                        if token != 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c':
                            return "401 Unauthorized API Access\n{}\n\n", 401
                    else:
                        #print("No token passed!")
                        if False:
                            return "401 Unauthorized API Access\n{}\n\n", 401
                else:
                    return "401 Unauthorized API Access\n{}\n\n", 401
            else:
                return "401 Unauthorized API Access\n{}\n\n", 401
    except Exception as e:
        return "401 Unauthorized API Access\n{}\n\n".format(e), 401


ns = api.namespace('swabseq', description="Operations for Swabseq sequence data analysis.")


@ns.route('/analyze/', methods = ['POST', 'OPTIONS'])
@api.doc(delete=False)
class DescribeSmiles(Resource):

    @api.hide # hide options route from documentation
    def options(self):
        """Preflight request"""
        #print("handling request")
        #print(request)
        origin = request.headers['Origin']
        data = {"Allow": "POST"}
        response = make_response(jsonify(data), 200)
        response = add_headers(response, origin)
        return response

    def post(self):
        """
        Returns results files for a valid Basespace ID string, passed as json {basespace:string} with a POST request
        """

        def generate(data_dict):
            """
            Generate IO stream for file
            """
            data = io.StringIO()
            w = csv.writer(data)
            for key, value in data_dict.items():
                w.writerow([key, value])
                yield data.getvalue()
                data.seek(0)
                data.truncate(0)

        #print("handling post")
        origin = request.headers['Origin']
        #print(origin, flush=True)
        #print(request, flush=True)
        if "application/json" in request.headers['Content-Type']:
            data_dict = request.get_json()
            if "basespace" in data_dict:
                basespace_id = data_dict["basespace"]
            else:
                basespace_id = None
            if not basespace_id:
                response = make_response(jsonify("Error. Not a valid Basespace ID string"), 404)
                response = add_headers(response, origin)
                return response
            else:
                #Run R script and zip results to generate temp file
                rundir = "/app/" + basespace_id + "/"
                results_file = "results.zip"
                subprocess.call(["Rscript", "--vanilla", "code/countAmpliconsAWS.R", "--rundir", rundir, "--basespaceID", basespace_id, "--threads", "8"])
                shutil.make_archive(results_file, 'zip', rundir)
                return send_file(results_file, mimetype="application/zip",
                     attachment_filename="results.zip", as_attachment=True)

        else:
            response = make_response(jsonify("Error. Not a valid Basespace ID. Please provide json with field basespace:<Basespace ID>"), 404)
            response = add_headers(response, origin)
            return response




if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0")
