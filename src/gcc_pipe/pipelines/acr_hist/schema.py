'''Contratos del pipeline - Entrada y salida'''
import pandas as pd
import pandera.pandas as pa

from pandera.typing import Series
from gcc_pipe.core.schemas import LineageSchema

# --- Valores fijos --- #

CATALOGO_ID = ['CC','CE','NIT','RC','PA','TI','NUI']
VALIDACION_NUMEROS = r"^-?\d+(\.\d+)?$"
VALIDACION_FECHA = r"^\d{4}-\d{2}-\d{2} 00:00:00$"
PROCESOS_ORIGEN = ['Activos','Inactivos','Retencion','Creditos']

# --- Esquema de entrada --- #

class AcrRawSchema(LineageSchema):
    '''Contrato de Entrada: El excel tal como llega: Todo TEXTO'''
            
    tipo_documento: Series[str] = pa.Field(
        alias='Tipo_Documento',
        nullable=False,
        isin=CATALOGO_ID,
    )
    
    cedula: Series[str] = pa.Field(
        alias='Cedula',
        nullable=False,
        str_length={"max_value": 17}
    )
    
    fecha_aplicacion: Series[str] = pa.Field(
        alias='Fecha_Aplicacion', 
        nullable=False,
        str_matches=VALIDACION_FECHA
    )
    
    monto_aportes: Series[str] = pa.Field(
        alias='Monto_Aportes',
        nullable=True,
        str_length={"max_value": 15}, 
        str_matches=VALIDACION_NUMEROS
    )
    
    monto_calamidad: Series[str] = pa.Field(
        alias='Monto_Calamidad',
        nullable=True,
        str_length={"max_value": 15}, 
        str_matches=VALIDACION_NUMEROS
    )
    
    monto_recreacion: Series[str] = pa.Field(
        alias='Monto_Recreacion',
        nullable=True,
        str_length={"max_value": 15}, 
        str_matches=VALIDACION_NUMEROS
    )
    
    Total_Pagado_Coomeva: Series[str] = pa.Field(
        alias='Total_Pagado_Coomeva',
        nullable=True,
        str_length={"max_value": 15}, 
        str_matches=VALIDACION_NUMEROS,
    )
    
    tipo_alternativa: Series[str] = pa.Field(
        alias='Tipo_Alternativa', 
        nullable=False, 
        str_length={"max_value": 50}
    )
    
    class Config:
        strict = True
        unique = [['Fecha_Aplicacion' , 'Tipo_Documento', 
                  'Cedula', 'Tipo_Alternativa']]
        
# --- Esquema de salida --- #

class AcrTargetSchema(LineageSchema):
    '''Contrato de salida -- carga'''
    
    periodo: Series[int] = pa.Field(
        alias='PERIODO', 
        nullable=False,
        le=999999,
        ge=0
    )

    tipo_alfabetico: Series[str] = pa.Field(
        alias='GCC_TIPO_ALFABETICO',
        nullable=False,
        isin=CATALOGO_ID
    )
    
    identificacion: Series[int] = pa.Field(
        alias='ASO_IDENTIFICACION',
        nullable=False,
        le=99999999999999999,
        gt=0
    )
    
    fecha_aplicacion: Series[pd.Timestamp] = pa.Field(
        alias='FECHA_APLICACION',
        nullable=False,
        ge=pd.Timestamp('2015-01-01'),
        le=pd.Timestamp('2030-12-31')
    )
    
    aplicado_aportes: Series[int] = pa.Field(
        alias='APLICADO_APORTES',
        nullable=True,
        ge=0,
        le=999999999999999
    )
    
    aplicado_calamidad: Series[int] = pa.Field(
        alias='APLICADO_CALAMIDAD',
        nullable=True,
        ge=0,
        le=999999999999999
    )
    
    aplicado_recreacion: Series[int] = pa.Field(
        alias='APLICADO_RECREACION',
        nullable=True,
        ge=0,
        le=999999999999999
    )
    
    total_pagado_coomeva: Series[int] = pa.Field(
        alias='TOTAL_PAGADO_COOMEVA',
        nullable=True,
        ge=0,
        le=999999999999999
    )
    
    proceso_origen: Series[str] = pa.Field(
        alias='PROCESO_ORIGEN',
        nullable=False,
        str_length={"max_value": 20},
        isin=PROCESOS_ORIGEN
    )
    
    alternativa: Series[str] = pa.Field(
        alias='ALTERNATIVA',
        nullable=False,
        str_length={'max_value':50}
    )
    
    indicador_cruce: Series[int] = pa.Field(
        alias='INDICADOR_CRUZE_INAC_ACT',
        nullable=False,
        isin=[0, 1]
    )
    
    tipo_documento_raw: Series[str] = pa.Field(
        alias='_tipo_documento_raw'
    )
    
    
    @pa.check('PERIODO', name='validacion_anio')
    def validacion_anio(cls, s):
        y = s // 100
        return ((y > 2000) & (y < 3000))
    
    @pa.check('PERIODO', name='validacion_mes')
    def validacion_mes(cls, s):
        m = s % 100
        return ((m >= 1) & (m <= 12))
    
    @pa.check('FECHA_APLICACION', name='sin_hora')
    def sin_hora(cls, s):
        return s.dt.normalize() == s
    
    
    @pa.dataframe_check(name='periodo_coincide_con_fecha')
    def periodo_coincide_con_fecha(cls, df):
        periodo_fecha = df['FECHA_APLICACION'].dt.strftime('%Y%m').astype(int)
        return periodo_fecha == df['PERIODO']

    class Config:
        strict=True
        unique=[[
            'PERIODO', 'GCC_TIPO_ALFABETICO', 
            'ASO_IDENTIFICACION', 'FECHA_APLICACION',
            'ALTERNATIVA'
        ]]