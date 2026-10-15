'''Orquesta todas las piezas de ACR'''

from pathlib import Path

from sqlalchemy import Engine

from gcc_pipe.config import SQL_PATH
from gcc_pipe.core.pipeline import Pipeline
from gcc_pipe.extractors.excel import ExcelExtractor
from gcc_pipe.loaders.oracle import OracleLoader, crear_paso
from gcc_pipe.pipelines.acr_hist.schema import AcrRawSchema, AcrTargetSchema

PROCESO = 'acr_hist'

def build(cfg:dict, engine:Engine, kind:str='month') -> Pipeline:
    
    # --- Se crean los pasos asociados --- #
    
    pasos = [crear_paso(nombre=p['nombre'], ruta=SQL_PATH /p['sql'], modo=p['modo']) for p in cfg['target']['pasos']]
    
    return Pipeline(
        name=f'{PROCESO}_{kind}', 
        extractor=ExcelExtractor(
            Path(cfg['source']['path']),
            sub_paths=cfg["source"]["sub_paths"][kind], 
        ), 
        raw_schema=AcrRawSchema,
        target_schema=AcrTargetSchema,
        loader=OracleLoader(engine=engine, pasos=pasos)
    )