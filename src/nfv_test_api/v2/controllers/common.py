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
from typing import Type

from flask_restx import Namespace, SchemaModel  # type: ignore
from pydantic import BaseModel
from pydantic.schema import model_schema


def add_model_schema(namespace: Namespace, model: Type[BaseModel]) -> SchemaModel:
    base_schema = model_schema(
        model, by_alias=False, ref_prefix=f"#/definitions/{model.__name__}/definitions/"
    )
    schema_model = namespace.schema_model(name=base_schema["title"], schema=base_schema)

    return schema_model
