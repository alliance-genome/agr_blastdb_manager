from datetime import datetime
from enum import Enum
from typing import List

import orjson
from pydantic import BaseModel as PydanticBaseModel, EmailStr, AnyUrl


class BaseModel(PydanticBaseModel):
    """
    Extend the Pydantic BaseModel to add JSON (de)serialization via orjson.
    See https://pydantic-docs.helpmanual.io/usage/model_config/
    """

    class Config:
        json_loads = orjson.loads

        @staticmethod
        def json_dumps(v, *, default):
            # orjson.dumps returns bytes, to match standard json.dumps we need to decode
            return orjson.dumps(v, default=default,
                                option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS | orjson.OPT_APPEND_NEWLINE).decode()


class BlastDBType(str, Enum):
    """
    NCBI types for BLAST databases.
    Taken from the dbtype flag of the makeblastdb command line tool.
    """
    nucl = 'nucl'
    prot = 'prot'


class BlastDBMetaData(BaseModel):
    """
    Class for representing the individual BLAST database metadata.
    """
    URI: AnyUrl
    blast_title: str
    description: str
    genus: str
    species: str
    md5sum: str
    taxon_id: int
    version: str
    bioproject: str = None
    seqtype: BlastDBType = BlastDBType.nucl


class AGRBlastMetadata(BaseModel):
    """
    Class for representing the AGR BLAST database top level
    metadata section.
    """
    contact: EmailStr
    dataProvider: str
    release: str
    dateProduced: datetime = None


class AGRBlastDatabases(BaseModel):
    """
    Class for representing the entire AGR BLAST database metadata file.

    :param data - List of BlastDBMetaData  objects
    :param metaData - Global metadata section.
    """
    data: List[BlastDBMetaData]
    metaData: AGRBlastMetadata
