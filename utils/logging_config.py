import logging
import sys
from pathlib import Path

def setup_logging(
    level: str = "INFO",
    log_file: str = "flag_processor.log",
    console: bool = True
) -> None:
    """
    Configura logging com saída para console e arquivo.
    
    Args:
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Nome do arquivo de log
        console: Se True, habilita saída no stdout
    """
    # Garantir que handlers não sejam duplicados em re-execuções
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Formatação
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    handlers = []
    
    # Handler para arquivo
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)
    handlers.append(file_handler)
    
    # Handler para console (opcional)
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(levelname)-8s | %(message)s'))
        handlers.append(console_handler)
    
    # Configurar root logger
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        force=True  # Substitui configurações anteriores
    )
    
    # Silenciar logs excessivos de bibliotecas externas
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)