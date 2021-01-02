"""Sets up a flask-restx server for running the swabseq analysis R-script."""

import server

from api.swabseq import api as swabseq
from api.health import api as server_health


app = server.app
api = server.api
api.add_namespace(swabseq)
api.add_namespace(server_health)


if __name__ == '__main__':
    app.run()
