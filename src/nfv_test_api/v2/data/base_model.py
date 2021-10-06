import json
from typing import Any, Callable, Optional, Union

from pydantic import BaseModel


def dense_name(string: str) -> str:
    """
    Convert a name to its contracted form, without any "_" in it
    """
    return "".join(string.split("_"))


class IpBaseModel(BaseModel):
    class Config:
        underscore_attrs_are_private = True
        alias_generator = dense_name
        allow_population_by_field_name = True

    class CreateForm(BaseModel):
        pass

    class UpdateForm(BaseModel):
        pass

    def json_dict(
        self,
        *,
        include: Union["AbstractSetIntStr", "MappingIntStrAny"] = None,
        exclude: Union["AbstractSetIntStr", "MappingIntStrAny"] = None,
        by_alias: bool = False,
        skip_defaults: bool = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        encoder: Optional[Callable[[Any], Any]] = None,
        **dumps_kwargs: Any,
    ) -> dict:
        return json.loads(
            self.json(
                include=include,
                exclude=exclude,
                by_alias=by_alias,
                skip_defaults=skip_defaults,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
                encoder=encoder,
                **dumps_kwargs,
            )
        )
