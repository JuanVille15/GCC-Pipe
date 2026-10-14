'''Modulo general para los errores de validacion de cada ETL -- Pipeline'''

import pandas as pd

from pandera.errors import SchemaErrors
from dataclasses import dataclass

@dataclass(frozen=True)
class ResumenFallas():
    estructura:pd.DataFrame
    filas:pd.DataFrame

def resumir_fallas(
    error:SchemaErrors, 
    df:pd.DataFrame,
    contexto: list[str]
) -> ResumenFallas:
    
    # --- Validar si col contexto existen en df --- #
    
    faltantes = [
        c for c in contexto
        if c not in df.columns
    ]
    
    if faltantes:
        raise ValueError(f'Faltan col dentro del df validado: {", ".join(faltantes)}')
    
    # --- Tabla de fallas --- #
    fc = error.failure_cases
    
    # --- Se crean los dos grupos: estructura y filas --- #
    estructura = fc[fc['index'].isna()]
    filas = fc[fc['index'].notna()]
    
    # --- Se une el detalle a filas --- #
    detalle = filas.merge(df[contexto], left_on='index', right_index=True, how='left', validate='many_to_one')

    return ResumenFallas(estructura=estructura, filas=detalle)
    