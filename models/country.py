from dataclasses import dataclass, field
from typing import Optional, ClassVar, Dict
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class Country:
    """Representa um país com informações para busca da bandeira."""
    name: str
    code: str
    original_name: Optional[str] = None
    
    # Carregamento dinâmico do mapeamento (escalável)
    _mappings: ClassVar[Optional[Dict[str, str]]] = None
    
    @classmethod
    def load_mappings(cls, config_path: Optional[str] = None) -> Dict[str, str]:
        """Carrega mapeamento de arquivo JSON ou usa padrão."""
        if cls._mappings is not None:
            return cls._mappings
            
        default_mappings = {
            'inglaterra': 'gb-eng', 'england': 'gb-eng',
            'escócia': 'gb-sct', 'scotland': 'gb-sct',
            'país de gales': 'gb-wls', 'wales': 'gb-wls',
            'reino unido': 'gb', 'united kingdom': 'gb',
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    cls._mappings = config.get('special_codes', default_mappings)
                    logger.info(f"Mappings carregados de: {config_path}")
                    return cls._mappings
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Falha ao carregar config: {e}. Usando padrão.")
        
        cls._mappings = default_mappings
        return cls._mappings
    
    @classmethod
    def normalize_code(cls, country_name: str, config_path: Optional[str] = None) -> str:
        """Normaliza nome do país para código FlagCDN."""
        mappings = cls.load_mappings(config_path)
        normalized = country_name.strip().lower()
        return mappings.get(normalized, normalized)
    
    @property
    def flag_url(self) -> str:
        """Gera URL da FlagCDN para este país."""
        return f"https://flagcdn.com/w2560/{self.code}.png"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.code})"