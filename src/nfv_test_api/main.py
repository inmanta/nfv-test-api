"""
       Copyright 2021 Inmanta

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import logging

import click  # type: ignore
from flask import Flask  # type: ignore
from flask_cors import CORS  # type: ignore

from nfv_test_api.config import get_config
from nfv_test_api.v2 import blueprint as controllers

app = Flask(__name__)
app.simulate = False
CORS(app)
app.config["RESTPLUS_MASK_SWAGGER"] = False
app.register_blueprint(controllers)

# Notes:
#   * Static content available on /static


LOGGER = logging.getLogger(__name__)


@click.command()
@click.option("--config", help="The configuration file to use")
def main(config):
    cfg = get_config(config)
    app.run(host=cfg.host, port=cfg.port)


if __name__ == "__main__":
    main()
