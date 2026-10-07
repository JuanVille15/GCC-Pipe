from datetime import date, datetime

import pandas as pd
import pytest

from gcc_pipe.core.checkpoints import read_checkpoint, write_checkpoint

@pytest.fixture
def df_ejemplo():
    return pd.DataFrame({
        "Cedula": ["1", None, "3"],
        "_extracted_at": [datetime(2026, 10, 7, 8, 0)] * 3,
    })


def test_write_y_read_devuelven_mismo_dataframe(tmp_path, df_ejemplo):
    
    # --- Se crea el dataframe de prueba --- #
    
    df = df_ejemplo
    run_date = date(2026, 10, 7)
    
    # --- Ejecutar el test --- #
    
    write_checkpoint(df, 'acr_hist',run_date,'raw',tmp_path)
    leido = read_checkpoint('acr_hist',run_date,'raw',tmp_path)
    
    # --- Probar --- #
    pd.testing.assert_frame_equal(leido, df)
    
def test_write_no_deja_archivos_tmp(tmp_path,df_ejemplo):
    
    # --- Creamos dataframe de prueba --- #
    df = df_ejemplo
    run_date = date(2026, 10, 7)
    esperado = 'raw.parquet'
    
    # --- Lo escribimos y obtenemos el path --- #
    path = write_checkpoint(df, 'acr_hist',run_date,'raw',tmp_path)
    
    obtenido = [
        p.name for p in 
        path.parent.iterdir()
    ]
    
    # --- Realizamos la prueba --- #
    
    assert obtenido == [esperado]
    assert path.is_file()