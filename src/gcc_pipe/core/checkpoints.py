'''Logica general para todos los ELTs: Resuevle rutas, persiste y carga'''
import pandas as pd

from datetime import date
from pathlib import Path

from gcc_pipe.config import DATA_PATH
from gcc_pipe.utils.exceptions import PersistFileError

# --- Constantes de modulo --- #

CHECKPOINTS_DIR = DATA_PATH / "checkpoints" 

# --- Etapas validas --- #

STAGES = (
    'raw', 
    'transformed', 
)

def checkpoint_path(
    pipeline: str, 
    run_date:date, 
    stage: str, 
    base_dir: Path = CHECKPOINTS_DIR) -> Path:
    
    if stage not in STAGES:
        raise ValueError(f'Etapa invalida: {stage}. Validas: {", ".join(STAGES)}')

    return base_dir.joinpath(pipeline, run_date.isoformat(), f"{stage}.parquet")

def write_checkpoint(
    df:pd.DataFrame, 
    pipeline:str, 
    run_date:date, 
    stage:str,
    base_dir: Path = CHECKPOINTS_DIR, 
) -> Path:
    
    # --- Resolver la ruta y crear las carpetas --- # 
    path = checkpoint_path(pipeline, run_date, stage, base_dir)
    path.parent.mkdir(
        parents=True, 
        exist_ok=True, 
    )
    
    # --- Se crea el nombre del archivo temporal --- #
    
    file_name = path.name
    tmp = path.with_name(f'{file_name}.tmp')
    
    try:
        # --- Escribimos el archivo con la terminacion temporal --- #
        df.to_parquet(
            tmp, 
            engine='pyarrow',
            index=False, 
        )
        
        # --- Convertimos el archivo tmp al final --- #
        
        tmp.replace(path)
    
    except Exception as e:
        raise PersistFileError(f'No se pudo guardar el checkpoint {stage} de {pipeline} ({run_date})') from e
    finally:
        tmp.unlink(missing_ok=True)

    return path

def read_checkpoint(
    pipeline:str, 
    run_date:date, 
    stage:str, 
    base_dir: Path = CHECKPOINTS_DIR,
) -> pd.DataFrame:
    
    # --- Resolver la ruta --- #
    
    path = checkpoint_path(pipeline, run_date, stage, base_dir)
    
    if not path.is_file():
        raise FileNotFoundError(f'No existe el checkpoint {stage} del pipeline {pipeline} para la fecha {run_date}')
    
    return pd.read_parquet(path, engine='pyarrow')