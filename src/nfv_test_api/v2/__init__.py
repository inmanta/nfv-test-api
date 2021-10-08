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
from typing import Dict, List, Optional, TypeVar

import requests  # type: ignore
from flask import Blueprint  # type: ignore
from flask_restplus import Api  # type: ignore

from nfv_test_api.v2.controllers.actions import namespace as actions_ns
from nfv_test_api.v2.controllers.interface import namespace as interface_ns
from nfv_test_api.v2.controllers.namespace import namespace as namespace_ns
from nfv_test_api.v2.controllers.route import namespace as route_ns

blueprint = Blueprint("api v2", __name__, url_prefix="/api/v2")

api_extension = Api(
    blueprint,
    title="NFV Test API",
    version="1.0",
    description="Test api for client side network operations",
    doc="/docs",
)

api_extension.add_namespace(namespace_ns)
api_extension.add_namespace(interface_ns)
api_extension.add_namespace(route_ns)
api_extension.add_namespace(actions_ns)


# Ugly patches to force openapi 3.0
from flask_restplus.swagger import Swagger  # type: ignore # noqa: E402

as_dict = Swagger.as_dict

T = TypeVar("T", List, Dict, object)


def replace_ref(schema: T, schema_prefix: str) -> T:
    """
    Return the same schema as given in input, with all the reference transformed to have the
    provided prefix.  What comes after the prefix is the last part of the prefix reference.
    The schema contains a reference if it is a dict, with a key "$ref".

    :param schema: A schema to recursively search references in
    :param schema_prefix: The new prefix to set
    """
    if isinstance(schema, List):
        return [replace_ref(item, schema_prefix) for item in schema]

    if isinstance(schema, Dict):
        if "$ref" in schema:
            schema["$ref"] = schema_prefix + schema["$ref"].split("/")[-1]
            return schema

        return {key: replace_ref(value, schema_prefix) for key, value in schema.items()}

    return schema


def as_dict_overwrite(self):
    d = as_dict(self)

    # Extract all the entity definitions that we have, even the nested ones
    definitions = dict()

    def extract_definitions(definition: dict, title: Optional[str] = None) -> None:
        if title and title not in definitions:
            definitions[title] = {key: value for key, value in definition.items() if key != "definitions"}

        for t, d in definition.get("definitions", dict()).items():
            extract_definitions(d, t)

    extract_definitions(d)

    # Place all the definitions in the definitions dict
    for title, definition in definitions.items():
        d["definitions"][title] = definition

    # Replacing all wrong references
    new_dict = replace_ref(d, "#/definitions/")

    # Converting the model to openapi 3 using swagger converter
    response = requests.post(
        "https://converter.swagger.io/api/convert", json=new_dict, headers={"content-type": "application/json"}
    )
    response.raise_for_status()

    new_dict = response.json()

    # In the conversion, we loose all of the "anyOf" in our schemas, so we set our old schemas back
    # The place where they should go has changed with the new format
    for title, definition in definitions.items():
        new_dict["components"]["schemas"][title] = definition

    # We replace the references again, with the new path where the definitions are located
    new_dict = replace_ref(new_dict, "#/components/schemas/")

    return new_dict


Swagger.as_dict = as_dict_overwrite
