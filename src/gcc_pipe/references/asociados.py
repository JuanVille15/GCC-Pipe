import pandas as pd

from sqlalchemy import Engine
from gcc_pipe.config import SQL_QUERY_PATH
from gcc_pipe.core.db import read_batch

def consulta_tipo_documento(
    df:pd.DataFrame, 
    engine:Engine,
    key:str,
) -> pd.DataFrame:
    
    # --- Documentos unicos --- #
    unicos = df[key].unique().tolist()
    
    # --- Resolver la ruta al query --- #
    query_path = SQL_QUERY_PATH / "tipo_documento.sql"
    if not query_path.is_file():
        raise FileNotFoundError(f'Error resolviendo ruta: {query_path} - No existe: {query_path.name}')
    
    query = query_path.read_text(encoding='utf-8')
    
    # --- Se consulta x lotes --- #
    with engine.connect() as con:
        tipos = read_batch(query=query, con=con, valores=unicos,)
    
    return tipos