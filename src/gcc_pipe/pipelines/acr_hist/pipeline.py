'''Orquesta todas las piezas de ACR'''
from pathlib import Path

from sqlalchemy import Engine

from gcc_pipe.config import SQL_PATH
from gcc_pipe.core.pipeline import Pipeline
from gcc_pipe.extractors.excel import ExcelExtractor
from gcc_pipe.loaders.oracle import OracleLoader, crear_paso
from gcc_pipe.pipelines.acr_hist.schema import AcrRawSchema, AcrTargetSchema

PROCESO = 'acr_hist'

def build(cfg:dict, engine:Engine, periodo: str | None, kind:str='month') -> Pipeline:
    
    # --- Se crean los pasos asociados --- #
    
    pasos = [crear_paso(nombre=p['nombre'], ruta=SQL_PATH /p['sql'], modo=p['modo']) for p in cfg['target']['pasos']]
    
    if kind == 'month':
        if periodo is None:
            raise ValueError('month requiere de un periodo')
        else: sub_paths = [f'{sp}/{periodo}' for sp in cfg["source"]["sub_paths"][kind]]
    else:
        sub_paths = cfg["source"]["sub_paths"][kind]
       
    return Pipeline(
        name=f'{PROCESO}_{kind}_{periodo}' if kind=='month' else f'{PROCESO}_{kind}', 
        extractor=ExcelExtractor(
            Path(cfg['source']['path']),
            sub_paths=sub_paths, 
        ), 
        raw_schema=AcrRawSchema,
        target_schema=AcrTargetSchema,
        loader=OracleLoader(engine=engine, pasos=pasos)
    )