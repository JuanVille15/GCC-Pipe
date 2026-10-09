'''Orquesta todas las piezas de ACR'''

from pathlib import Path

from gcc_pipe.core.pipeline import Pipeline
from gcc_pipe.extractors.excel import ExcelExtractor
from gcc_pipe.pipelines.acr_hist.schema import AcrRawSchema

PROCESO = 'acr_hist'

def build(cfg:dict, kind:str='month') -> Pipeline:
    
    return Pipeline(
        name=f'{PROCESO}_{kind}', 
        extractor=ExcelExtractor(
            Path(cfg['source']['path']),
            sub_paths=cfg["source"]["sub_paths"][kind], 
        ), 
        raw_schema=AcrRawSchema, 
    )