from typing import Pattern, Type

from flask_restplus import Namespace, SchemaModel
from pydantic import BaseModel
from pydantic.schema import model_schema


def add_model_schema(namespace: Namespace, model: Type[BaseModel]) -> SchemaModel:
    base_schema = model_schema(model, by_alias=False, ref_prefix=f"#/definitions/{model.__name__}/definitions/")
    schema_model = namespace.schema_model(name=base_schema["title"], schema=base_schema)

    return schema_model
