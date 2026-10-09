import os
import argparse
import pandas as pd
from datetime import datetime, date


from dotenv import load_dotenv
from gcc_pipe.config import load_pipeline_config
from gcc_pipe.core.checkpoints import write_checkpoint
from gcc_pipe.pipelines.acr_hist.pipeline import build
from gcc_pipe.utils.exceptions import ExtractError

from pandera.errors import SchemaErrors

ETLS = ['acr_hist']
KIND = ['hist','month']


def main() -> int:
    
    parser = argparse.ArgumentParser(
        prog='gcc_pipe', 
        description='Proyecto que corre ETLs para el DWH GCC'
    )
    sub = parser.add_subparsers(dest='comando',required=True)
    
    # --- Extract --- #
    p_extract = sub.add_parser(
        'run', 
        help='Comando para correr una ETL entera // Argumento proceso'
    )
    
    p_extract.add_argument(
        '--proceso', 
        choices=ETLS, 
        required=True, 
        help='Proceso ETL que se quiere correr'
    )

    p_extract.add_argument(
        '--kind', 
        choices=KIND, 
        default='month', 
        help='Modo de ejecucion del programa --- Diario o Historico'
    )    
    
    args = parser.parse_args()    
    
    # --- Preparamos --- #
    load_dotenv()
    cfg = load_pipeline_config(process=args.proceso,env=os.environ)
    pipeline = build(cfg=cfg, kind=args.kind)
    run_date = date.today()
    extracted_at = datetime.now()
    
    # --- Extract --- #
    try:
        df = pipeline.extractor.extract(extracted_at=extracted_at)
    except ExtractError as e:
        e.add_note(f'Pipeline: {pipeline.name}'); raise
        
    duracion = datetime.now() - extracted_at   
    # --- CheckPoint: Guardar lo que llego antes de validar --- #
    path = write_checkpoint(df, pipeline.name, run_date,'raw')
    SIZE = len(df)
    DETALLE_POR_SUB = df.groupby(['_sub_path','_source_file']).size()
    print(f'Extraccion {args.proceso} . Corrida {run_date}'
          f'\nDuracion: {duracion}'
          f'\nFilas extraidas: {SIZE}'
          '\nFilas por subcarpeta y archivo'
          f'\n{DETALLE_POR_SUB.to_string()}'
          f'\nCheckpoint: {path}')
    
    
    # ── Validar el contrato de entrada ──
    try:
        pipeline.raw_schema.validate(df, lazy=True)
    except SchemaErrors as e:
        ruta_fallas = path.parent / "raw_failures.csv"
        fc = e.failure_cases
        estructura = fc[fc['index'].isna()]
        filas = fc[fc["index"].notna()]
        detalle = filas.merge(df[["_source_file", "_sub_path"]], left_on="index", right_index=True)
        if not estructura.empty:
            print(f'La estructura de origen cambio: {estructura.to_string()}')
        
        print('Se obtuvieron Fallos por regla...'
              f'\n{filas.groupby(['column','check']).size().to_string()}')
        
        print(f'Errores por archivo...'
              f'\n{detalle.groupby("_source_file").size().to_string()}')
        
        # --- Se guardan los detalles en raw --- #
        detalle.to_csv(ruta_fallas, sep=';', index=False)
        return 1

    return 0
    
