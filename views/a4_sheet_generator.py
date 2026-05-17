"""
A4 Sheet Generator - Creates printable A4 sheets with flag grids.

This module provides functionality to generate A4-sized PDFs containing
a grid of 12 flags (4 columns x 3 rows) with country names, suitable
for printing.
"""

from fpdf import FPDF
from PIL import Image, ImageOps
from pathlib import Path
from typing import List, Tuple, Union, Optional, Dict
import logging
import tempfile
import os

logger = logging.getLogger(__name__)


class A4SheetGenerationError(Exception):
    """Custom exception for A4 sheet generation errors."""
    pass


class A4SheetGenerator:
    """
    View: Responsible for generating printable A4 sheets with flag grids.
    
    This class creates PDF sheets containing exactly 12 flags arranged
    in a 4x3 grid (4 columns, 3 rows), with each flag accompanied by
    its country name. Designed for high-quality printing.
    
    Attributes:
        output_dir: Directory path for output files
        dpi: Resolution for image rendering (default: 300 for print quality)
    """
    
    # A4 dimensions in mm
    A4_WIDTH_MM = 210
    A4_HEIGHT_MM = 297
    
    # Grid configuration
    GRID_COLUMNS = 4
    GRID_ROWS = 3
    FLAGS_PER_SHEET = 12
    
    # Margins and spacing (in mm)
    PAGE_MARGIN_MM = 10
    CELL_HORIZONTAL_MARGIN_MM = 5
    CELL_VERTICAL_MARGIN_MM = 8
    NAME_HEIGHT_MM = 12
    
    def __init__(self, output_dir: Union[str, Path] = ".", dpi: int = 300):
        """
        Initialize the A4SheetGenerator.
        
        Args:
            output_dir: Directory path for saving generated PDFs
            dpi: Dots per inch for image rendering (higher = better print quality)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi
    
    def _calculate_cell_dimensions(self) -> Dict[str, float]:
        """
        Calculate dimensions for each grid cell.
        
        Returns:
            Dictionary containing cell width, height, and spacing values
        """
        # Available width after margins
        available_width = (
            self.A4_WIDTH_MM - 
            (2 * self.PAGE_MARGIN_MM) - 
            ((self.GRID_COLUMNS + 1) * self.CELL_HORIZONTAL_MARGIN_MM)
        )
        cell_width = available_width / self.GRID_COLUMNS
        
        # Available height after margins and name areas
        total_name_height = self.NAME_HEIGHT_MM * self.GRID_ROWS
        available_height = (
            self.A4_HEIGHT_MM - 
            (2 * self.PAGE_MARGIN_MM) - 
            ((self.GRID_ROWS + 1) * self.CELL_VERTICAL_MARGIN_MM) -
            total_name_height
        )
        cell_height = available_height / self.GRID_ROWS
        
        return {
            'cell_width': cell_width,
            'cell_height': cell_height,
            'start_x': self.PAGE_MARGIN_MM + self.CELL_HORIZONTAL_MARGIN_MM,
            'start_y': self.PAGE_MARGIN_MM + self.CELL_VERTICAL_MARGIN_MM
        }
    
    def _process_flag_image(
        self, 
        image: Image.Image, 
        target_size: Tuple[int, int]
    ) -> Image.Image:
        """
        Process flag image for grid placement.
        
        Args:
            image: Original PIL Image of the flag
            target_size: Target (width, height) in pixels
            
        Returns:
            Processed and resized image with border
        """
        # Resize maintaining aspect ratio
        image_copy = image.copy()
        image_copy.thumbnail(target_size, Image.Resampling.LANCZOS)
        
        # Add subtle border for definition
        bordered = ImageOps.expand(image_copy, border=2, fill='black')
        
        return bordered
    
    def _save_temp_image(
        self, 
        image: Image.Image, 
        prefix: str, 
        index: int
    ) -> Path:
        """
        Save processed image to temporary file.
        
        Args:
            image: PIL Image to save
            prefix: Filename prefix
            index: Index number for uniqueness
            
        Returns:
            Path to saved temporary file
        """
        temp_path = self.output_dir / f"temp_{prefix}_{index}.png"
        image.save(temp_path, format='PNG', dpi=(self.dpi, self.dpi))
        return temp_path
    
    def _cleanup_temp_file(self, path: Path) -> None:
        """
        Safely remove temporary file.
        
        Args:
            path: Path to file to remove
        """
        try:
            if path.exists():
                path.unlink()
        except OSError as e:
            logger.warning(f"Failed to remove temp file {path}: {e}")
    
    def _get_cell_position(
        self, 
        index: int, 
        dims: Dict[str, float]
    ) -> Tuple[float, float, float, float]:
        """
        Calculate position for a flag at given grid index.
        
        Args:
            index: 0-based index in the grid (0-11)
            dims: Cell dimensions dictionary from _calculate_cell_dimensions
            
        Returns:
            Tuple of (x, y, width, height) for the flag image position
        """
        row = index // self.GRID_COLUMNS
        col = index % self.GRID_COLUMNS
        
        x = dims['start_x'] + (col * (dims['cell_width'] + self.CELL_HORIZONTAL_MARGIN_MM))
        y = dims['start_y'] + (row * (dims['cell_height'] + self.CELL_VERTICAL_MARGIN_MM + self.NAME_HEIGHT_MM))
        
        return (x, y, dims['cell_width'], dims['cell_height'])
    
    def _get_name_position(
        self, 
        index: int, 
        dims: Dict[str, float],
        cell_dims: Tuple[float, float, float, float]
    ) -> Tuple[float, float]:
        """
        Calculate position for country name text.
        
        Args:
            index: 0-based index in the grid
            dims: Cell dimensions dictionary
            cell_dims: Tuple of (x, y, width, height) from _get_cell_position
            
        Returns:
            Tuple of (x, y) for text baseline position
        """
        x = cell_dims[0] + (cell_dims[2] / 2)  # Center horizontally
        y = cell_dims[1] + cell_dims[3] + (self.NAME_HEIGHT_MM / 2)  # Below image
        return (x, y)
    
    def create_sheet(
        self,
        flags_data: List[Tuple[Image.Image, str]],
        sheet_number: int = 1
    ) -> FPDF:
        """
        Create an A4 sheet PDF with a grid of flags.
        
        Args:
            flags_data: List of tuples (flag_image, country_name)
                       Maximum 12 items per sheet
            sheet_number: Sheet number for tracking/logging
            
        Returns:
            FPDF object containing the generated sheet
            
        Raises:
            A4SheetGenerationError: If sheet creation fails
        """
        if len(flags_data) > self.FLAGS_PER_SHEET:
            raise A4SheetGenerationError(
                f"Maximum {self.FLAGS_PER_SHEET} flags per sheet. "
                f"Received: {len(flags_data)}"
            )
        
        try:
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.add_page()
            
            # Set up fonts
            pdf.set_font('Helvetica', style='B', size=10)
            
            # Calculate cell dimensions
            dims = self._calculate_cell_dimensions()
            
            # Process and place each flag
            for idx, (flag_image, country_name) in enumerate(flags_data):
                # Calculate target size in pixels (approximate for mm to px conversion)
                px_per_mm = self.dpi / 25.4
                target_width_px = int(dims['cell_width'] * px_per_mm * 0.9)
                target_height_px = int(dims['cell_height'] * px_per_mm * 0.9)
                target_size = (target_width_px, target_height_px)
                
                # Process image
                processed = self._process_flag_image(flag_image, target_size)
                temp_path = self._save_temp_image(processed, "sheet", idx)
                
                # Get positions
                cell_pos = self._get_cell_position(idx, dims)
                name_pos = self._get_name_position(idx, dims, cell_pos)
                
                # Add flag image (centered in cell)
                img_width = min(cell_pos[2] * 0.9, dims['cell_width'])
                img_height = min(cell_pos[3] * 0.9, dims['cell_height'])
                
                # Center image within cell
                img_x = cell_pos[0] + (cell_pos[2] - img_width) / 2
                img_y = cell_pos[1] + (cell_pos[3] - img_height) / 2
                
                pdf.image(
                    str(temp_path),
                    x=img_x,
                    y=img_y,
                    w=img_width,
                    h=img_height
                )
                
                # Add country name (centered below flag)
                pdf.set_xy(name_pos[0] - (cell_pos[2] / 2), name_pos[1] - 3)
                pdf.cell(
                    w=cell_pos[2],
                    h=self.NAME_HEIGHT_MM,
                    text=country_name[:30],  # Truncate long names
                    align='C'
                )
                
                self._cleanup_temp_file(temp_path)
            
            logger.info(f"A4 sheet #{sheet_number} created with {len(flags_data)} flags")
            return pdf
            
        except Exception as e:
            raise A4SheetGenerationError(
                f"Error creating A4 sheet #{sheet_number}: {e}"
            )
    
    def create_sheets_from_flags(
        self,
        flags_data: List[Tuple[Image.Image, str]]
    ) -> List[FPDF]:
        """
        Create multiple A4 sheets from a large list of flags.
        
        Splits the input list into chunks of 12 flags and creates
        one A4 sheet per chunk.
        
        Args:
            flags_data: List of tuples (flag_image, country_name)
            
        Returns:
            List of FPDF objects, one per sheet
        """
        sheets = []
        total_flags = len(flags_data)
        
        for sheet_idx in range(0, total_flags, self.FLAGS_PER_SHEET):
            chunk = flags_data[sheet_idx:sheet_idx + self.FLAGS_PER_SHEET]
            sheet_number = (sheet_idx // self.FLAGS_PER_SHEET) + 1
            sheet = self.create_sheet(chunk, sheet_number)
            sheets.append(sheet)
        
        logger.info(
            f"Created {len(sheets)} A4 sheets from {total_flags} flags"
        )
        return sheets
    
    def save_pdf(self, pdf: FPDF, filename: str) -> Path:
        """
        Save PDF to disk.
        
        Args:
            pdf: FPDF document instance
            filename: Output filename
            
        Returns:
            Path to saved file
            
        Raises:
            A4SheetGenerationError: If saving fails
        """
        output_path = self.output_dir / filename
        try:
            pdf.output(str(output_path))
            logger.info(f"A4 sheet PDF saved: {output_path}")
            return output_path
        except Exception as e:
            raise A4SheetGenerationError(
                f"Error saving A4 sheet PDF '{filename}': {e}"
            )
    
    def download_file_colab(
        self, 
        filepath: Union[str, Path]
    ) -> bool:
        """
        Attempt to trigger file download in Google Colab environment.
        
        Args:
            filepath: Path to file to download
            
        Returns:
            True if download was triggered, False otherwise
        """
        try:
            from google.colab import files
            files.download(str(filepath))
            logger.info(f"Download initiated: {filepath}")
            return True
        except ImportError:
            logger.debug("Colab environment not detected - download skipped")
            return False
        except Exception as e:
            logger.error(f"Error in Colab download: {e}")
            return False
