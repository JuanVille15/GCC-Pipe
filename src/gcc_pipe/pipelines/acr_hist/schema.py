'''Contratos del pipeline - Entrada y salida'''

import pandera.pandas as pa
from pandera.typing import Series
from gcc_pipe.core.schemas import LineageSchema

# --- Valores fijos --- #

CATALOGO_ID = ['CC','CE','NIT','RC','PA','TI','NUI']
VALIDACION_NUMEROS = r"^-?\d+(\.\d+)?$"
VALIDACION_FECHA = r"^\d{4}-\d{2}-\d{2} 00:00:00$"

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