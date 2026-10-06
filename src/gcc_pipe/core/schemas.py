'''Contratos comunes para todos los pipelines'''

import pandas as pd

import pandera.pandas as pa
from pandera.typing import Series

class LineageSchema(pa.DataFrameModel):
    
    source_file: Series[str] = pa.Field(
        alias='_source_file',
        nullable=False, 
    )
    
    sub_path: Series[str] = pa.Field(
        alias='_sub_path',
        nullable=False, 
    )
    
    extracted_at: Series[pd.Timestamp] = pa.Field(
        alias='_extracted_at', 
        nullable=False, 
    )