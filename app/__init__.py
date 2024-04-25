#!/usr/bin/python3

"""
Main listener for DHCP-webhooks.
"""

import sys
import logging
from flask import Flask, request
from flask_restx import Api, Resource
from .utils.webhook_functions import parse_dhcp_log
from .utils.connection_functions import main

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout,
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )

app = Flask(__name__)
api = Api(app)

@api.route('/webhook')
class WebhookHandler(Resource):
    """
    Handler for incoming webhooks.
    """
    def post(self) -> None:
        """
        -X POST
        """

        data = parse_dhcp_log(str(request.get_data()))

        if data is None:
            return None, 200

        return main(data)

# @api.route('/initial')
# class WebhookHandler(Resource):
#     """
#     Handler for incoming webhooks.
#     """
#     def post(self) -> None:
#         """
#         -X POST
#         """

#         data = parse_init_log(str(request.get_data()))

#         if data is None:
#             return None, 200

#         return api_main(data)

if __name__ == '__main__':

    app.run(host="0.0.0.0", port=5001)
