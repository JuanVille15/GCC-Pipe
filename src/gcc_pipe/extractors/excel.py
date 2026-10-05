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