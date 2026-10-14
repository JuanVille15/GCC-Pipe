'''Realiza las transformaciones necesarias para insertar'''
import pandas as pd
import numpy as np

from dataclasses import dataclass
from unidecode import unidecode
from datetime import date
from gcc_pipe.core.exceptions import TransformError


COL_NAMES = {
    'Tipo_Documento':'GCC_TIPO_ALFABETICO', 
    'Cedula': 'ASO_IDENTIFICACION', 
    'Fecha_Aplicacion': 'FECHA_APLICACION',
    'Monto_Aportes': 'APLICADO_APORTES',
    'Monto_Calamidad': 'APLICADO_CALAMIDAD', 
    'Monto_Recreacion': 'APLICADO_RECREACION', 
    'Total_Pagado_Coomeva': 'TOTAL_PAGADO_COOMEVA',
    'Tipo_Alternativa': 'ALTERNATIVA', 
}

COL_TYPES = {
    'Tipo_Documento':str, 
    'Cedula': int, 
    'Fecha_Aplicacion': date, 
    'Monto_Aportes':'Int64',
    'Monto_Calamidad':'Int64',
    'Monto_Recreacion': 'Int64',
    'Total_Pagado_Coomeva': 'Int64', 
    'Tipo_Alternativa':str
}

ORIGENES = {'Activos': 'Activos', 
            'Inactivos': 'Inactivos',
            'Retencion':'Retencion',
            'Creditos': 'Creditos',
        }

ORIGENES_NO_COMUNES = ['Activos', 'Inactivos']

COLUMNAS_FINALES = [
    'PERIODO', 'GCC_TIPO_ALFABETICO', 'ASO_IDENTIFICACION',
    'FECHA_APLICACION', 'APLICADO_APORTES', 'APLICADO_CALAMIDAD', 
    'APLICADO_RECREACION', 'TOTAL_PAGADO_COOMEVA', 'PROCESO_ORIGEN',
    'ALTERNATIVA', 'INDICADOR_CRUZE_INAC_ACT',
]


@dataclass(frozen=True)
class ResultadoTransform:
    validos: pd.DataFrame
    cuarentena: pd.DataFrame

def _asegurar_tipos(
    df:pd.DataFrame,
) -> pd.DataFrame:
    
    df = df.copy()

    # --- Se intenta cambiar los tipos --- #
    
    errors = []
    convertidas = {}
    
    for column,tipo in COL_TYPES.items():
        if tipo in [int,'Int64']:
            try:
                convertidas[column] = (
                    pd.to_numeric(df[column], errors='raise')
                ).astype(tipo)
            except ValueError as e:
                errors.append((column,e))
        elif tipo == date:
            try:
                convertidas[column] = (
                    pd.to_datetime(df[column], errors='raise', format="%Y-%m-%d %H:%M:%S")
                )
            except ValueError as e:
                errors.append((column,e))
        else:
            try:
                convertidas[column] = df[column].astype(tipo)
            except ValueError as e:
                errors.append((column,e))
    
    if errors:
        detalle = ", ".join(f"{col}: {e}" for col, e in errors)
        raise TransformError(f'Fallaron {len(errors)} conversiones -> {detalle}')

    return df.assign(**convertidas)
    
    
def _rename_columns(
    df:pd.DataFrame
) -> pd.DataFrame:
    
    faltantes = [
        c for c in COL_NAMES.keys() 
        if c not in df.columns
    ]
    
    if faltantes:
        raise TransformError(f'Error renombrando columnas -- Faltan: {", ".join(faltantes)}')
    
    return df.rename(
        columns=COL_NAMES
    )

def _asegurar_tipo_documento(
    df:pd.DataFrame, 
    ref: pd.DataFrame, 
) -> pd.DataFrame:
    
    # --- Se realiza el merge --- #
    
    cruzado = (
        pd.merge(
            left=df, 
            right=ref
            .assign(
                ASO_IDENTIFICACION = lambda d:
                    d['ASO_IDENTIFICACION'].astype(int)
            )
            .rename(
                columns={
                    'GCC_TIPO_ALFABETICO': 'TIPO_DOCUMENTO',
                }
            ),
            how='left', 
            on='ASO_IDENTIFICACION', 
            indicator=True,
            validate='many_to_one'
        )
    )
    
    # --- Se genera el motivo: cuarentena --- #
    
    cruzado = (
        cruzado
        .assign(
            _motivo_cuarentena = np.where(
                cruzado['_merge'] == 'left_only', 
                'id_not_in_gcc',
                pd.NA, #type: ignore
            )
        )
        .drop(
            columns='_merge',
        )
    )
    
    # --- Asegurar el tipo de documento --- #
    
    cruzado = (
        cruzado
        .assign(
            TIPO_DOCUMENTO = lambda d:
                d['TIPO_DOCUMENTO'].fillna(d['GCC_TIPO_ALFABETICO'])
        )
        .rename(
            columns={
                'GCC_TIPO_ALFABETICO': '_tipo_documento_raw',
                'TIPO_DOCUMENTO': 'GCC_TIPO_ALFABETICO',
            }
        )
    )

    return cruzado
    
def _columnas_calculadas(
    df:pd.DataFrame, 
) -> pd.DataFrame:
    
    df = df.copy()
    
    # --- La columna periodo --- #
    df = (
        df.assign(
            PERIODO = df['FECHA_APLICACION'].dt.strftime('%Y%m').astype(int)
        )
    )
    
    # --- Columna PROCESO_ORIGEN --- #
    df = (
        df.assign(
            PROCESO_ORIGEN = df['_sub_path'].str.split('/').str[0].map(ORIGENES)
        )
    )
    
    ## --- Validar si quedaron na's en PROCESO_ORIGEN: Enviar a cuarentena --- ##
    df = (
        df.assign(
            _motivo_cuarentena = (
                np.where(
                    ((df['_motivo_cuarentena'].isna()) & (df['PROCESO_ORIGEN'].isna())),
                    'no_valid_origen',
                    df['_motivo_cuarentena']
                )
            )
        )
    )
    
    # --- Eliminar acentos de la columna  ALTERNATIVA --- #
    
    df = (
        df.assign(
            ALTERNATIVA = df['ALTERNATIVA'].apply(unidecode)
        )
    )
    
    # --- INDICADOR CRUCE INACTIVOS ACTIVOS --- #
    
    claves = [df['ASO_IDENTIFICACION'], df['PERIODO']]
    
    tiene_activo = df['PROCESO_ORIGEN'].eq(ORIGENES_NO_COMUNES[0]).groupby(claves).transform('any')
    tiene_inactivo = df['PROCESO_ORIGEN'].eq(ORIGENES_NO_COMUNES[1]).groupby(claves).transform('any')
    
    df = (
        df.assign(
            INDICADOR_CRUZE_INAC_ACT = (tiene_activo & 
                                        tiene_inactivo & 
                                        df['PROCESO_ORIGEN'].isin(ORIGENES_NO_COMUNES)).astype(int)
        )
    )

    return df

def _separar(
    df:pd.DataFrame,
)-> ResultadoTransform:
    
    # --- orden columnas --- #
    otras = [c for c in df.columns if c not in COLUMNAS_FINALES]
    col_order = COLUMNAS_FINALES + otras
    df = df[col_order]
    
    # --- Se separan los dataframes --- #
    es_valido = df['_motivo_cuarentena'].isna()
    
    otras.remove('_motivo_cuarentena')
    validos = df.loc[es_valido, COLUMNAS_FINALES + otras]
    cuarentena = df[~es_valido][col_order]
    
    return ResultadoTransform(validos=validos, cuarentena=cuarentena)


def transform(
    df:pd.DataFrame,
    ref: pd.DataFrame, 
)-> ResultadoTransform:
    
    transformado = (
        df
        .pipe(_asegurar_tipos)
        .pipe(_rename_columns)
        .pipe(_asegurar_tipo_documento, ref=ref)
        .pipe(_columnas_calculadas)
    )

    return _separar(transformado)