import os
import pandas as pd

from gcc_pipe.core.exceptions import QueryError
from sqlalchemy import Engine, create_engine, Connection, text, bindparam
from sqlalchemy.engine import URL
from gcc_pipe.config import get_db_settings
from dotenv import load_dotenv

def build_gcc_con(config:dict[str,str]) -> Engine:
    
    c_url = URL.create(
            "oracle+oracledb",
            username=config['USER_GCC'],
            password=config['PASSWORD_GCC'],
            host=config['SERVER_GCC'],
            port=int(config['PORT_GCC']),
            query={"service_name": config['SERVICE_GCC']},
        )

    con_gcc = create_engine(url=c_url)
    
    return con_gcc

def read_batch(
    query:str,
    con:Connection,
    valores:list[int], 
    tamanio_lote:int=1_000,
    param: str ='ids'
) -> pd.DataFrame:
    
    if not valores:
        raise QueryError('La lista de valores se encuentra vacia')
        
    # --- Se crean lotes de consulta --- #
    lotes = [
        valores[i:i + tamanio_lote] 
        for i in range(0,len(valores), tamanio_lote)
    ]
    # --- Se itera por cada lote para consultar --- #
    results = []
    stmt = text(query).bindparams(bindparam(param, expanding=True))
    for i,lote in enumerate(lotes, start=1):
        try:
            df_temp  = (
                pd.read_sql(
                    stmt, 
                    con,
                    params={param:tuple(lote)}
                )
            )
            results.append(df_temp)
        except Exception as e:
            raise QueryError(f'Error consultando lote {i} - {e}') from e

    return pd.concat(results, axis=0, ignore_index=True)

if __name__ == '__main__':
    
    load_dotenv()
    env = os.environ
    
    gcc_engine = build_gcc_con(get_db_settings(env))
    with gcc_engine.connect() as conn:
        print(f'Conexion DWH GCC establecida✅')