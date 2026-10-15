import os
import argparse
import pandas as pd
from datetime import datetime, date, timedelta

from dotenv import load_dotenv
from gcc_pipe.config import load_pipeline_config, get_db_settings
from gcc_pipe.core.checkpoints import write_checkpoint, checkpoint_path
from gcc_pipe.pipelines.acr_hist.pipeline import build
from gcc_pipe.pipelines.acr_hist.transform import transform
from gcc_pipe.core.exceptions import ExtractError, LoadError
from gcc_pipe.references.asociados import consulta_tipo_documento
from gcc_pipe.core.db import build_gcc_con
from gcc_pipe.core.validation import resumir_fallas

from pandera.errors import SchemaErrors

ETLS = ['acr_hist']
KIND = ['hist','month']
MESES = list(range(1,13))

def validar_periodo(texto:str) -> str:
    
    # --- constantes --- #
    largo = len(texto)
    es_digito = texto.isdigit()
     
    # --- Validaciones --- #
    
    if largo != 6 or not es_digito:
        raise argparse.ArgumentTypeError(f"{texto} no es un periodo valido (YYYYMM, mes 01-12)")
    
    mes = int(texto[4:])
    
    if mes not in MESES:
        raise argparse.ArgumentTypeError(f"{texto} no es un periodo valido (YYYYMM, mes 01-12)")

    return texto

def periodo_anterior(hoy:date) -> str:
    return (hoy.replace(day=1) - timedelta(days=1)).strftime('%Y%m')


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
    
    p_extract.add_argument(
        '--periodo',
        type=validar_periodo,
        default=None,
        help='Periodo YYYYMM a cargar (solo month). Por defecto el mes anterior',
    )
    
    args = parser.parse_args()
    
    # --- resolver periodo --- #
    
    kind = args.kind
    periodo = args.periodo
    
    if kind == 'hist':
        if periodo:
            raise ValueError('Argumento --Periodo solo aplica a --kind month')
    elif periodo is None:
        periodo = periodo_anterior(date.today())
        
    # --- Preparamos --- #
    load_dotenv()
    cfg = load_pipeline_config(process=args.proceso,env=os.environ)
    engine = build_gcc_con(get_db_settings(os.environ))
    pipeline = build(cfg=cfg, engine=engine, periodo=periodo, kind=args.kind)
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
    
    
    # ── Validar el contrato de entrada ── #
    try:
        pipeline.raw_schema.validate(df, lazy=True)
    except SchemaErrors as e:
        ruta_fallas = path.parent / "raw_failures.csv"
        fallas_raw = resumir_fallas(error=e, df=df, contexto=['_source_file','_sub_path'])
        estructura = fallas_raw.estructura
        filas = fallas_raw.filas
        if not estructura.empty:
            print('La estructura de origen cambio...'
                  f'\n{estructura.to_string()}')
        
        print('Se obtuvieron Fallos por regla...'
              f'\n{filas.groupby(['column','check'])['index'].nunique().to_string()}')
        
        print(f'Errores por archivo...'
              f'\n{filas.groupby("_source_file")['index'].nunique().to_string()}')
        
        # --- Se guardan los detalles en raw --- #
        filas.to_csv(ruta_fallas, sep=';', index=False)
        return 1
    
    # --- Si pasa se elimina, si llega a haber archivo de falla --- #
    ruta_fallas = path.parent / "raw_failures.csv"
    ruta_fallas.unlink(missing_ok=True)
    
    # ===============
    # TRANSFORMACION
    # ===============
    
    # --- Se consulta la referencia --- #
    lista_cedulas = pd.to_numeric(df['Cedula'], errors='raise').astype(int).drop_duplicates().to_list()
    ref = consulta_tipo_documento(lista_cedulas,engine=engine)
    
    # --- Se genera la transformacion de df --- #
    result = transform(df=df, ref=ref)
    
    validos = result.validos
    cuarentena = result.cuarentena
    
    # --- Se realiza el chekpoint de la cuarentena --- #
    print(f'Exportando {len(cuarentena)} casos a cuarentena...')
    path_cuarentena = write_checkpoint(cuarentena, pipeline.name, run_date, stage='quarantine')
    print(f'Cuarentena correctamente exportada en: {path_cuarentena}')
    
    # --- Se genera la validacion de los validos --- #
    try:
        pipeline.target_schema.validate(validos, lazy=True)
    except SchemaErrors as e:
        resumen = resumir_fallas(e, validos, contexto=['_source_file','_sub_path'])
        print(f'Contrato de Salida {pipeline.name} fallo -- No se carga nada')
        estructura_t = resumen.estructura
        filas_t = resumen.filas
        if not estructura_t.empty:
            print('Estructura de salida incorrecta...'
                  f'\n{estructura_t[['column','check','failure_case']].to_string()}')

        print('Se obtuvieron los siguientes fallos por regla'
              f'\n{filas_t.groupby(['check'])['index'].nunique().to_string()}')
        
        print('Errores por archivo'
              f'\n{filas_t.groupby('_source_file')['index'].nunique().to_string()}')
        
        # --- Se guardan los valores --- #
        ruta_fallas = checkpoint_path(pipeline.name, run_date, 'transformed').parent / "target_failures.csv" 
        ruta_fallas.parent.mkdir(parents=True, exist_ok=True)
        filas_t.to_csv(ruta_fallas, index=False, sep=';')
        print(f'Archivo de fallas exportado en: {ruta_fallas}')
        return 1
    
    # --- Validacion de periodo --- #
    periodos = validos['PERIODO'].unique().tolist()
    if kind == 'month':
        if set(periodos) != {int(periodo)}:
            print(f'Se requiere carga {periodo} y se obtuvo {periodos}'
                  f'\n{validos.groupby(['_source_file','PERIODO']).size().to_string()}')
            return 1

    # --- Sino falla se exporta el .parquet en transformed --- #
    path_t = write_checkpoint(validos, pipeline.name, run_date, 'transformed')
    size = len(validos)
    registros_origen = validos.groupby('PROCESO_ORIGEN').size()
    print(f'Archivo paso la validacion con {size} filas'
          f'\nPersistido correctamente en {path_t}'
          '\nDetalle por proceso origen'
          f'\n{registros_origen.to_string()}')
    
    # --- Se elimina el archivo de fallas si antes huo falla --- # 
    
    ruta_fallas = checkpoint_path(pipeline.name, run_date, 'transformed').parent / "target_failures.csv"
    ruta_fallas.unlink(missing_ok=True)
           
    # ===============
    # CARGA - GCC
    # ===============
    
    loaded_at = datetime.now()    
    try:
        resultado = pipeline.loader.load(validos, loaded_at)
    except LoadError as e:
        e.add_note(f'Pipeline {pipeline.name}');raise
        
    ultimo_paso = list(resultado.filas_por_paso)[-1]
    enviadas = len(validos)
    insertadas = resultado.filas_por_paso[ultimo_paso]
    diferencia = insertadas - enviadas
    print('-Filas por paso', resultado.filas_por_paso)
    print('-Fechas de insercion', resultado.fecha_insercion)
    
    if diferencia != 0:
        print(f'DESCUADRE EN LA CARGA - {pipeline.name} (corrida {run_date})'
              f'\nFilas enviadas:   {enviadas}'
              f'\nFilas cargadas:   {insertadas}'
              f'\nDiferencia:       {diferencia}')

        print('La transaccion ya hizo commit: estos datos ya estan en la tabla.'
              f'\nFirma de la carga: FECHA_INSERCION = {loaded_at.isoformat(sep=' ')}')
        return 1
        
    return 0
    
