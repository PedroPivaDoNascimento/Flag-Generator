from fpdf import FPDF
from pathlib import Path
from typing import Union, Optional, Dict, Any
import logging

from models.country import Country
from models.flag_service import FlagService, FlagServiceError
from views.pdf_generator import PDFGenerator, PDFGenerationError

logger = logging.getLogger(__name__)

class CopaFlagController:
    """
    Controller: Orquestra o fluxo entre Model e View.
    - Coordena carregamento, processamento e geração de saída
    - Centraliza tratamento de erros de alto nível
    """
    
    def __init__(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path] = ".",
        timeout: int = 10,
        config_path: Optional[str] = None
    ):
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.timeout = timeout
        self.config_path = config_path
        
        self._flag_service: Optional[FlagService] = None
        self._pdf_generator: Optional[PDFGenerator] = None
    
    def _initialize_components(self) -> None:
        """Inicializa dependências do Model e View."""
        self._flag_service = FlagService(
            file_path=self.input_file,
            timeout=self.timeout,
            config_path=self.config_path
        )
        self._pdf_generator = PDFGenerator(output_dir=self.output_dir)
    
    def _create_pdf_instance(self) -> FPDF:
        """Factory method para instância padronizada de PDF."""
        return FPDF(orientation='P', unit='mm', format='A4')
    
    def process_all(self) -> Dict[str, Any]:
        """
        Método principal: executa todo o fluxo de processamento.
        Retorna dicionário com estatísticas para logging/relatório.
        """
        stats = {
            'total': 0,
            'processed': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            # 1. Inicializar componentes
            self._initialize_components()
            
            # 2. Model: Carregar dados
            countries = self._flag_service.load_countries_from_excel()
            stats['total'] = len(countries)
            
            if not countries:
                logger.warning("Nenhum país válido encontrado para processamento")
                return stats
            
            # 3. View: Preparar documentos
            pdf_color = self._create_pdf_instance()
            pdf_outline = self._create_pdf_instance()
            
            logger.info(f"Iniciando processamento de {stats['total']} países...")
            
            # 4. Loop principal de processamento
            for index, country in enumerate(countries, start=1):
                try:
                    # Model: Buscar imagem
                    flag_image = self._flag_service.fetch_flag_image(country)
                    if flag_image is None:
                        stats['failed'] += 1
                        stats['errors'].append(f"Fetch falhou: {country.code}")
                        continue
                    
                    # View: Adicionar aos PDFs
                    self._pdf_generator.add_color_page(pdf_color, flag_image, index)
                    self._pdf_generator.add_outline_page(pdf_outline, flag_image, index)
                    
                    stats['processed'] += 1
                    logger.info(f"✓ ({stats['processed']}/{stats['total']}): {country.code.upper()}")
                    
                except Exception as e:
                    stats['failed'] += 1
                    error_msg = f"Erro no país {country.code} (#{index}): {e}"
                    stats['errors'].append(error_msg)
                    logger.error(error_msg, exc_info=True)
            
            # 5. View: Finalizar e exportar
            color_path = self._pdf_generator.save_pdf(pdf_color, "bandeiras_coloridas.pdf")
            outline_path = self._pdf_generator.save_pdf(pdf_outline, "bandeiras_para_colorir.pdf")
            
            # 6. Tentar download automático (Colab)
            self._pdf_generator.download_file_colab(color_path)
            self._pdf_generator.download_file_colab(outline_path)
            
            logger.info(f"✅ Sucesso! {stats['processed']} páginas geradas.")
            
        except FlagServiceError as e:
            error_msg = f"[MODEL] {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        except PDFGenerationError as e:
            error_msg = f"[VIEW] {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        except Exception as e:
            error_msg = f"[CONTROLLER] Erro crítico: {e}"
            logger.exception(error_msg)
            stats['errors'].append(error_msg)
        
        return stats