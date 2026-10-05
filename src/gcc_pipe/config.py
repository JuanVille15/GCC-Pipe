'''Carga configuracion'''
import yaml
import re

from typing import Any, Mapping
from pathlib import Path
from gcc_pipe.utils.exceptions import EmptyConfigError, LoadConfigError, MissingEnvVarError


ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "config"
ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

def _expand_env_vars(
    valor:Any, 
    env: Mapping[str,str]
) -> Any:
    if isinstance(valor, dict):
        new = {}
        for k,v in valor.items():
            new[k] = _expand_env_vars(v, env)
        return new
    elif isinstance(valor, list):
        new = []
        for e in valor:
            new.append(_expand_env_vars(e, env))
        return new
    elif isinstance(valor, str):
        nombres = ENV_VAR_PATTERN.findall(valor)
        faltantes= [
            n for n in nombres if
            n not in env
        ]
        
        if faltantes:
            raise MissingEnvVarError(f'Faltan Variables de entorno: {", ".join(v for v in faltantes)}'
                                     '\nDefinelas en .env')
        
        resultado = valor
        for name in nombres:
            texto_a_buscar = "${" + name + "}"
            resultado = resultado.replace(texto_a_buscar, env[name])
        return resultado
    else:
        return valor
        

def load_pipeline_config(
    process: str, 
    env: Mapping[str,str],
    config_dir: Path = CONFIG_PATH,
) -> dict:
    
    # --- Resolver la ruta del archivo --- #
    origin_path = config_dir/'pipelines'/f'{process}.yaml'
    
    if not origin_path.is_file():
        raise FileNotFoundError(f'No se pudo encontrar {origin_path.name} en: {origin_path.parent}')
    
    # --- Si existe la ruta: leer --- #
    with open(origin_path, encoding='utf-8') as f:
        try:
            cfg = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise LoadConfigError(f'Error Cargando configuracion: {origin_path.name} - {e}') from e
    
    if not isinstance(cfg, dict):
        raise EmptyConfigError(f'La configuracion del pipeline: {origin_path.name} esta vacia')
    
    # --- Si existe cfg:dict, se reemplazan las variables de ambiente --- #
    
    cfg = _expand_env_vars(
        cfg,
        env=env, 
    )
    
    return cfg

if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    env = os.environ
    cfg = load_pipeline_config(process='acr_hist', env=env,)