'''Contenedor --- Define que debe llevar cada pipeline'''

import pandera.pandas as pa

from dataclasses import dataclass
from gcc_pipe.core.contracts import Extractor, Loader

@dataclass(frozen=True)
class Pipeline:
    name:str
    extractor:Extractor
    raw_schema: type[pa.DataFrameModel]
    target_schema: type[pa.DataFrameModel]
    loader: Loader