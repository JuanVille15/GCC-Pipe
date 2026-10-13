from sqlalchemy import Engine,create_engine
from sqlalchemy.engine import URL
from gcc_pipe.config import get_db_settings

from dotenv import load_dotenv
import os
def build_gcc_con(config:dict[str,str]) -> Engine:
    
    c_url = URL.create(
            "oracle+oracledb",
            username=config['USER'],
            password=config['PASSWORD'],
            host=config['SERVER'],
            port=int(config['PORT']),
            query={"service_name": config['SERVICE']},
        )

    con_gcc = create_engine(url=c_url)
    
    return con_gcc

if __name__ == '__main__':
    
    load_dotenv()
    env = os.environ
    
    gcc_engine = build_gcc_con(get_db_settings(env))
    with gcc_engine.connect() as conn:
        print(f'Conexion DWH GCC establecida✅')