import pandas as pd

from datetime import datetime
from dataclasses import dataclass
from sqlalchemy import Engine, text
from pathlib import Path
from typing import Literal

from gcc_pipe.core.db import leer_sql, extraer_binds
from gcc_pipe.core.exceptions import LoadError, MissingParamError
from gcc_pipe.core.contracts import ResultadoCarga

MODOS = ('por_grupo','por_fila')

@dataclass(frozen=True)
class PasoSQL:
    nombre: str
    sql: str
    binds: tuple[str,...]
    modo:str
    
    def __post_init__(self):
        if self.modo not in MODOS:
            raise ValueError(f'modo {self.modo} invalido en {self.nombre} -- posibles: {", ".join(MODOS)}')
        
def crear_paso(nombre:str, ruta:Path, 
               modo:Literal['por_grupo','por_fila']) -> PasoSQL:
    
    sql = leer_sql(ruta)
    binds = tuple(extraer_binds(sql))
    return PasoSQL(nombre=nombre, sql=sql, binds=binds, modo=modo)

def construir_params(
    df:pd.DataFrame,
    paso: PasoSQL
) -> list[dict]:
    
    parametros_faltantes = [
        p for p in paso.binds
        if p not in df.columns
    ]
    
    if parametros_faltantes:
        raise MissingParamError(f'Paso {paso.nombre} con parametros faltantes {", ".join(parametros_faltantes)}')
    
    # --- Se seleccionan solo las columnas necesarias --- #
    c_params = df[list(paso.binds)]
    
    # --- si el modo es por grupo: Eliminar las filas repetidas --- #
    if paso.modo == 'por_grupo':
        c_params = c_params.drop_duplicates(ignore_index=True)
        
    return c_params.to_dict('records')

# ========
# LOADER
# ========

class OracleLoader:
    def __init__(self, engine:Engine, pasos:list[PasoSQL]):
        self.engine = engine
        self.pasos = tuple(pasos)
        if not pasos:
            raise LoadError('No hay pasos para realizar...')
        
    def load(self, df:pd.DataFrame, loaded_at: datetime) -> ResultadoCarga:
        
        # --- Validar si el df que pasan esta vacio --- #
        if df.empty:
            raise LoadError('No se encuentran datos para cargar...')
        
        # --- Se genera la columna: FECHA_INSERCION --- #
        
        df = df.assign(FECHA_INSERCION=loaded_at)
        
        # --- Se arman los parametros de todos los pasos --- #
        
        params = [construir_params(df,paso) for paso in self.pasos]
        
        # --- Se itera por paso y parametros: Se genera la transaccion como 1 --- #
        filas ={}
        with self.engine.begin() as con:
            for paso, parametros in zip(self.pasos,params):
                try:
                    resultado = con.execute(text(paso.sql), parametros)
                except Exception as e:
                    raise LoadError(f'Fallo el paso {paso.nombre}...') from e
                
                filas[paso.nombre] = resultado.rowcount
                
        return ResultadoCarga(filas_por_paso=filas,fecha_insercion=loaded_at)