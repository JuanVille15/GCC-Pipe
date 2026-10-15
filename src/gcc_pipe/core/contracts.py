from datetime import datetime
from typing import Protocol

from dataclasses import dataclass

import pandas as pd

@dataclass(frozen=True)
class ResultadoCarga:
    filas_por_paso: dict[str,int]
    fecha_insercion: datetime


class Extractor(Protocol):
    def extract(self, extracted_at: datetime) -> pd.DataFrame: ...
    
class Loader(Protocol):
    def load(self, df:pd.DataFrame, loaded_at: datetime) -> ResultadoCarga: ...