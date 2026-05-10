from fpdf import FPDF
from PIL import Image, ImageOps, ImageFilter
from pathlib import Path
from typing import Union, Optional
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

class PDFGenerationError(Exception):
    """Exceção personalizada para erros na geração de PDF."""
    pass

class PDFGenerator:
    """
    View: Responsável exclusivamente pela apresentação.
    - Formatação do PDF
    - Processamento de imagem (bordas, filtros)
    - Interface de saída (salvar/download)
    """
    
    # Constantes de layout
    PAGE_FORMAT = 'A4'
    MARGIN_MM = 10
    IMAGE_WIDTH_MM = 190
    IMAGE_Y_POS_MM = 30
    COLOR_BORDER_PX = 2
    OUTLINE_BORDER_PX = 5
    EDGE_THRESHOLD = 200
    
    def __init__(self, output_dir: Union[str, Path] = "."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _process_color_image(self, image: Image.Image) -> Image.Image:
        """Adiciona borda preta à imagem colorida."""
        return ImageOps.expand(image, border=self.COLOR_BORDER_PX, fill='black')
    
    def _process_outline_image(self, image: Image.Image) -> Image.Image:
        """Converte imagem para versão 'para colorir' (contorno)."""
        gray = image.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        # Inverte e aplica threshold para contorno limpo
        outline = ImageOps.invert(edges).point(
            lambda x: 0 if x < self.EDGE_THRESHOLD else 255
        )
        return ImageOps.expand(outline, border=self.OUTLINE_BORDER_PX, fill='black')
    
    def _save_temp_image(self, image: Image.Image, prefix: str, index: int) -> Path:
        """Salva imagem em arquivo temporário."""
        temp_path = self.output_dir / f"temp_{prefix}_{index}.png"
        image.save(temp_path, format='PNG')
        return temp_path
    
    def _cleanup_temp_file(self, path: Path) -> None:
        """Remove arquivo temporário com tratamento seguro."""
        try:
            if path.exists():
                path.unlink()
        except OSError as e:
            logger.warning(f"Falha ao remover arquivo temporário {path}: {e}")
    
    def add_color_page(self, pdf: FPDF, image: Image.Image, index: int) -> None:
        """Adiciona página com bandeira colorida ao PDF."""
        try:
            processed = self._process_color_image(image)
            temp_path = self._save_temp_image(processed, "c", index)
            
            pdf.add_page()
            pdf.image(
                str(temp_path),
                x=self.MARGIN_MM,
                y=self.IMAGE_Y_POS_MM,
                w=self.IMAGE_WIDTH_MM
            )
            self._cleanup_temp_file(temp_path)
        except Exception as e:
            raise PDFGenerationError(f"Erro ao adicionar página colorida #{index}: {e}")
    
    def add_outline_page(self, pdf: FPDF, image: Image.Image, index: int) -> None:
        """Adiciona página com bandeira para colorir ao PDF."""
        try:
            processed = self._process_outline_image(image)
            temp_path = self._save_temp_image(processed, "o", index)
            
            pdf.add_page()
            pdf.image(
                str(temp_path),
                x=self.MARGIN_MM,
                y=self.IMAGE_Y_POS_MM,
                w=self.IMAGE_WIDTH_MM
            )
            self._cleanup_temp_file(temp_path)
        except Exception as e:
            raise PDFGenerationError(f"Erro ao adicionar página contorno #{index}: {e}")
    
    def save_pdf(self, pdf: FPDF, filename: str) -> Path:
        """Salva PDF no disco e retorna o caminho."""
        output_path = self.output_dir / filename
        try:
            pdf.output(str(output_path))
            logger.info(f"PDF salvo: {output_path}")
            return output_path
        except Exception as e:
            raise PDFGenerationError(f"Erro ao salvar PDF '{filename}': {e}")
    
    def download_file_colab(self, filepath: Union[str, Path]) -> bool:
        """Tenta fazer download no ambiente Google Colab."""
        try:
            from google.colab import files
            files.download(str(filepath))
            logger.info(f"Download iniciado: {filepath}")
            return True
        except ImportError:
            logger.debug("Ambiente Colab não detectado - download ignorado")
            return False
        except Exception as e:
            logger.error(f"Erro no download Colab: {e}")
            return False