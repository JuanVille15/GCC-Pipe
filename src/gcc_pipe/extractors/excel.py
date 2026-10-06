from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from gcc_pipe.utils.exceptions import ExtractError

import pandas as pd

# --- informacion de los archivos --- #

@dataclass(frozen=True)
class SourceFile:
    path: Path
    sub_path: str
    size_bytes: int
    modified_at: datetime
    
def discover_files(
    base_path: Path, 
    sub_paths: list[str], 
    pattern: str ='*.xlsx',
) -> list[SourceFile]:
    
    # --- Se valida la carpeta base --- #
    if not base_path.is_dir():
        raise ExtractError(f'No existe la carpeta base: {base_path}')
    
    # --- Se crean sub_paths --- #
    rutas = [
        base_path / sp for sp in sub_paths
    ]
    
    faltantes = [
        f for f in rutas
        if not f.is_dir()
    ]
    
    if faltantes:
        raise ExtractError(f'No existen las sub-carpetas: {", ".join(f.name for f in faltantes)}')
    
    # --- Buscar archivos por pattern --- #
    
    files = []
    for sub in sub_paths:
        sub_dir = base_path / sub
        
        for f in sub_dir.glob(pattern, case_sensitive=False):
            if f.name.startswith('~$') or not f.is_file():
                continue
            
            stat = f.stat()
            size_bytes = stat.st_size
            modified_at = datetime.fromtimestamp(stat.st_mtime)
            source_file = SourceFile(path=f, sub_path=sub, size_bytes=size_bytes, modified_at=modified_at)
            files.append(source_file)

    if not files:
        raise ExtractError(f'No se encontraron archivos: {pattern} en {base_path}')
    
    return sorted(files, key=lambda x: x.path)

def read_excel_file(
    path: Path, 
    sheet: str | int = 0, 
    header: int = 0, 
) -> pd.DataFrame:
    
    # --- Se intenta leer el archivo --- #
    
    try:
        df = (
            pd.read_excel(
                path, 
                sheet_name=sheet, 
                header=header, 
                dtype='str', 
                engine='openpyxl'
            )
        )
    except Exception as e:
        raise ExtractError(f'No se pudo leer: {path.name} Hoja: {sheet}') from e
    
    # --- Se eliminan filas completamente vacias --- #
    
    df = (
        df.dropna(
            axis=0, 
            how='all',
            ignore_index=True, 
        )
    )
    
    return df

def add_lineage(
    df:pd.DataFrame, 
    source: SourceFile, 
    extracted_at: datetime 
) -> pd.DataFrame:
    
    # --- Se agregan columnas METADATA en df --- #     
    df = (
        df
        .assign(
            _source_file = source.path.name, 
            _sub_path = source.sub_path, 
            _extracted_at = extracted_at
        )
    )
    
    return df

# =====================
# CLASE EXTRACTORA
# =====================

class ExcelExtractor:
    def __init__(self, base_path:Path, sub_paths:list[str], pattern:str='*.xlsx', sheet:str|int=0, header:int=0):
        
        self.base_path = base_path
        self.sub_paths = sub_paths
        self.pattern = pattern
        self.sheet = sheet
        self.header = header
        
    def extract(self, extracted_at:datetime) -> pd.DataFrame:
        source_files = discover_files(self.base_path, self.sub_paths, pattern=self.pattern)
        frames = []
        
        for s in source_files:
            df = read_excel_file(s.path, self.sheet, self.header)
            df = add_lineage(df, s, extracted_at=extracted_at)
            frames.append(df)

        return pd.concat(frames, axis=0, ignore_index=True)

