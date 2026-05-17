from fpdf import FPDF
from pathlib import Path
from typing import Union, Optional, Dict, Any, List, Tuple
from PIL import Image
import logging

from models.country import Country
from models.flag_service import FlagService, FlagServiceError
from views.pdf_generator import PDFGenerator, PDFGenerationError
from views.a4_sheet_generator import A4SheetGenerator, A4SheetGenerationError

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
        self._a4_generator: Optional[A4SheetGenerator] = None
    
    def _initialize_components(self) -> None:
        """Inicializa dependências do Model e View."""
        self._flag_service = FlagService(
            file_path=self.input_file,
            timeout=self.timeout,
            config_path=self.config_path
        )
        self._pdf_generator = PDFGenerator(output_dir=self.output_dir)
        self._a4_generator = A4SheetGenerator(output_dir=self.output_dir)
    
    def _create_pdf_instance(self) -> FPDF:
        """Factory method para instância padronizada de PDF."""
        return FPDF(orientation='P', unit='mm', format='A4')
    
    def process_all(self) -> Dict[str, Any]:
        """
        Método principal: executa todo o fluxo de processamento.
        Gera:
        1. PDF de bandeiras coloridas individuais (uma por página)
        2. PDF de bandeiras para colorir (uma por página)
        3. Folhas A4 com grid de 12 bandeiras coloridas cada
        
        Retorna dicionário com estatísticas para logging/relatório.
        """
        stats = {
            'total': 0,
            'processed': 0,
            'failed': 0,
            'errors': [],
            'sheets_created': 0
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
            
            # Coleta de dados para folhas A4
            a4_flags_data: List[Tuple[Image.Image, str]] = []
            
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
                    
                    # View: Adicionar aos PDFs individuais
                    self._pdf_generator.add_color_page(pdf_color, flag_image, index)
                    self._pdf_generator.add_outline_page(pdf_outline, flag_image, index)
                    
                    # Coletar dados para folhas A4
                    a4_flags_data.append((flag_image, country.name))
                    
                    stats['processed'] += 1
                    logger.info(f"✓ ({stats['processed']}/{stats['total']}): {country.code.upper()}")
                    
                except Exception as e:
                    stats['failed'] += 1
                    error_msg = f"Erro no país {country.code} (#{index}): {e}"
                    stats['errors'].append(error_msg)
                    logger.error(error_msg, exc_info=True)
            
            # 5. View: Finalizar e exportar PDFs individuais
            color_path = self._pdf_generator.save_pdf(pdf_color, "bandeiras_coloridas.pdf")
            outline_path = self._pdf_generator.save_pdf(pdf_outline, "bandeiras_para_colorir.pdf")
            
            # 6. Gerar folhas A4 com grid de bandeiras
            if a4_flags_data:
                sheets = self._a4_generator.create_sheets_from_flags(a4_flags_data)
                
                # Salvar cada folha
                for idx, sheet in enumerate(sheets, start=1):
                    sheet_filename = f"folha_a4_bandeiras_{idx}.pdf"
                    sheet_path = self._a4_generator.save_pdf(sheet, sheet_filename)
                    stats['sheets_created'] += 1
                    logger.info(f"Folha A4 #{idx} salva: {sheet_path}")
                
                # Download da primeira folha no Colab
                if sheets:
                    first_sheet_path = self.output_dir / "folha_a4_bandeiras_1.pdf"
                    self._a4_generator.download_file_colab(first_sheet_path)
            
            # 7. Tentar download automático (Colab)
            self._pdf_generator.download_file_colab(color_path)
            self._pdf_generator.download_file_colab(outline_path)
            
            logger.info(f"✅ Sucesso! {stats['processed']} páginas geradas.")
            logger.info(f"📄 {stats['sheets_created']} folhas A4 criadas.")
            
        except FlagServiceError as e:
            error_msg = f"[MODEL] {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        except (PDFGenerationError, A4SheetGenerationError) as e:
            error_msg = f"[VIEW] {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        except Exception as e:
            error_msg = f"[CONTROLLER] Erro crítico: {e}"
            logger.exception(error_msg)
            stats['errors'].append(error_msg)
        
        return stats