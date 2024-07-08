from typing_extensions import Annotated
import os
from os.path import expandvars
import re
from itertools import chain
# from pkg_resources import EntryPoint, iter_entry_points
# from importlib import import_module
# from first import first
# from typing import Any

# from pydantic.main import Model
from pydantic.types import SecretType

from pydantic import (
    ConfigDict,
    BaseModel,
    SecretStr,
    FilePath,
    AnyHttpUrl,
    ValidationError,
    RootModel,
    model_validator,
)

# from pydantic_core import ValidationError
from pydantic.functional_validators import (
    AfterValidator,
    GetCoreSchemaHandler,
    core_schema,
)

_var_re = re.compile(
    r"\${(?P<bname>[a-z0-9_]+)}" r"|" r"\$(?P<name>[^{][a-z_0-9]+)", flags=re.IGNORECASE
)


class NoExtraBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def exapnd_envvar(v):
    if found_vars := list(filter(len, chain.from_iterable(_var_re.findall(v)))):
        for var in found_vars:
            if (var_val := os.getenv(var)) is None:
                raise ValueError(f'Environment variable "{var}" missing.')

            if not len(var_val):
                raise ValueError(f'Environment variable "{var}" empty.')

        return expandvars(v)

    return v


MyEnvVar = Annotated[str, AfterValidator(exapnd_envvar)]


class _EnvExpand:
    """
    When a string value contains a reference to an environment variable, use
    this type to expand the contents of the variable using os.path.expandvars.

    For example like:
        password = "$MY_PASSWORD"
        foo_password = "${MY_PASSWORD}_foo"

    will be expanded, given MY_PASSWORD is set to 'boo!' in the environment:
        password -> "boo!"
        foo_password -> "boo!_foo"
    """

    @staticmethod
    def _validate(value: str):
        if value[0] != "$":
            raise ValueError(f"Value '{value}' does not start with '$'")
        return value

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda _v: exapnd_envvar(_v),
                info_arg=False,
                return_schema=core_schema.str_schema(),
            ),
        )


class EnvExpand(RootModel[_EnvExpand]):
    def __repr__(self):
        return self.model_dump()

    __str__ = __repr__


class EnvSecretStr(SecretStr):
    """
    The EnvSecretStr is used to define configuraiton options that store as
    Secret and validate as AnyHttpUrl
    """

    def get_secret_value(self) -> SecretType:
        return exapnd_envvar(super().get_secret_value())


def validate_url(url):
    try:
        return AnyHttpUrl(url=str(url))
    except ValidationError as exc:
        errmsg = exc.errors()[0]["msg"]
        raise ValueError(f"{errmsg}: {url}")


class EnvUrl(EnvExpand):
    """
    The EnvSecretUrl is used to define configuraiton options that store as
    Secret and validate as AnyHttpUrl
    """

    model_validator(mode="after")(staticmethod(validate_url))


class EnvSecretUrl(EnvSecretStr):
    """
    The EnvSecretUrl is used to define configuraiton options that store as
    Secret and validate as AnyHttpUrl
    """

    model_validator(mode="after")(staticmethod(validate_url))


class EnvCredential(NoExtraBaseModel):
    username: EnvExpand
    password: EnvSecretStr


class EnvFilePath(EnvExpand):
    """A FilePath field whose value can interpolate from env vars"""

    @model_validator(mode="after")
    @staticmethod
    def validate_path(value):
        return FilePath(str(value))


# class ImportPath(BaseModel):
#     @classmethod
#     def validate(cls, v):
#         try:
#             return import_module(name=v)
#         except ImportError as exc:
#             raise ValueError(f"Unable to import {v}: {str(exc)}")
#
#
# class EntryPointImportPath(BaseModel):
#     @classmethod
#     def validate(cls, v):
#         try:
#             return EntryPoint.parse(f"ep = {v}").resolve()
#         except ImportError:
#             raise ValueError(f"Unable to import {v}")
#
#
# class PackagedEntryPoint(BaseModel):
#     @classmethod
#     def validate(cls, v):
#         try:
#             group, _, name = v.partition(":")
#             ep = first(iter_entry_points(group=group, name=name))
#             return ep.resolve()
#
#         except AttributeError:
#             raise ValueError(f"Unable to find package-import: {v}")
#
#         except ImportError as exc:
#             raise ValueError(f"Unable to import {v}: {str(exc)}")
#
