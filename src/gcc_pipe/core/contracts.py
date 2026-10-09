from datetime import datetime
from typing import Protocol

import pandas as pd

class Extractor(Protocol):
    def extract(self, extracted_at: datetime) -> pd.DataFrame: ...