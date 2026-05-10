import requests
import pandas as pd
from pathlib import Path
from typing import List, Optional, Union
from PIL import Image
import io
import logging

from .country import Country

logger = logging.getLogger(__name__)

class FlagServiceError(Exception):
    """Exceção personalizada para erros no serviço de bandeiras."""
    pass

class FlagService:
    """
    Model: Responsável pela lógica de negócio.
    - Leitura do arquivo Excel
    - Requisições à API FlagCDN
    """
    
    def __init__(self, file_path: Union[str, Path], timeout: int = 10, config_path: Optional[str] = None):
        self.file_path = Path(file_path)
        self.timeout = timeout
        self.config_path = config_path
        self.countries: List[Country] = []
    
    def load_countries_from_excel(self, column_name: str = 'País') -> List[Country]:
        """Carrega países do Excel e cria objetos Country."""
        if not self.file_path.exists():
            raise FlagServiceError(f"Arquivo não encontrado: {self.file_path}")
        
        try:
            df = pd.read_excel(self.file_path)
        except Exception as e:
            raise FlagServiceError(f"Erro ao ler arquivo Excel: {e}")
        
        if column_name not in df.columns:
            available = list(df.columns)
            raise FlagServiceError(f"Coluna '{column_name}' não encontrada. Disponíveis: {available}")
        
        countries = []
        for idx, row in df.iterrows():
            raw_name = str(row[column_name]).strip()
            if not raw_name or raw_name.lower() in ('nan', 'none', ''):
                continue
            
            try:
                code = Country.normalize_code(raw_name, self.config_path)
                country = Country(name=raw_name, code=code, original_name=raw_name)
                countries.append(country)
            except Exception as e:
                logger.warning(f"Erro ao processar linha {idx} ('{raw_name}'): {e}")
                continue
        
        self.countries = countries
        logger.info(f"{len(countries)} países carregados com sucesso")
        return countries
    
    def fetch_flag_image(self, country: Country) -> Optional[Image.Image]:
        """Busca imagem da bandeira via API FlagCDN."""
        try:
            response = requests.get(country.flag_url, timeout=self.timeout)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content)).convert("RGB")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout ao buscar bandeira: {country.code}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"HTTP {response.status_code} para {country.code}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de rede para {country.code}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao processar imagem de {country.code}: {e}")
            return None