"""
Grid PDF Generator - Creates structured grid PDFs with flags.

This module generates two distinct PDF files:
1. Colored flags in a 3x4 grid (3 rows × 4 columns)
2. Outline/coloring version flags in a 3x4 grid

Each flag is accompanied by its full country name, positioned close
to the image with proper alignment and spacing.
"""

from fpdf import FPDF
from PIL import Image, ImageOps, ImageFilter
from pathlib import Path
from typing import List, Tuple, Union, Optional, Dict
import logging
import tempfile
import os

logger = logging.getLogger(__name__)


class GridPDFGenerationError(Exception):
    """Custom exception for grid PDF generation errors."""
    pass


class GridPDFGenerator:
    """
    View: Responsible for generating structured grid PDFs with flags.
    
    This class creates two separate PDF files:
    - One with colored flags in a 4x3 grid
    - One with outline/coloring flags in a 4x3 grid
    
    Each page contains exactly 12 flags (4 columns × 3 rows) with
    country names positioned directly below each flag.
    
    Attributes:
        output_dir: Directory path for output files
        dpi: Resolution for image rendering (default: 300 for print quality)
    """
    
    # A4 dimensions in mm
    A4_WIDTH_MM = 210
    A4_HEIGHT_MM = 297
    
    # Strict grid configuration: 4 columns × 3 rows
    GRID_COLUMNS = 4
    GRID_ROWS = 3
    FLAGS_PER_PAGE = 12
    
    # Margins and spacing (in mm) - optimized for clean layout
    PAGE_MARGIN_TOP_MM = 15
    PAGE_MARGIN_BOTTOM_MM = 10
    PAGE_MARGIN_LEFT_MM = 10
    PAGE_MARGIN_RIGHT_MM = 10
    CELL_HORIZONTAL_GAP_MM = 5
    CELL_VERTICAL_GAP_MM = 8
    NAME_HEIGHT_MM = 10  # Reduced height for name area
    NAME_FONT_SIZE = 9   # Font size for country names
    NAME_TO_FLAG_GAP_MM = 2  # Reduced gap between flag and name
    
    def __init__(self, output_dir: Union[str, Path] = ".", dpi: int = 300):
        """
        Initialize the GridPDFGenerator.
        
        Args:
            output_dir: Directory path for saving generated PDFs
            dpi: Dots per inch for image rendering (higher = better print quality)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi
    
    def _calculate_cell_dimensions(self) -> Dict[str, float]:
        """
        Calculate dimensions for each grid cell with strict proportions.
        
        Returns:
            Dictionary containing cell width, height, and positioning values
        """
        # Available width after side margins
        available_width = (
            self.A4_WIDTH_MM - 
            self.PAGE_MARGIN_LEFT_MM - 
            self.PAGE_MARGIN_RIGHT_MM -
            ((self.GRID_COLUMNS + 1) * self.CELL_HORIZONTAL_GAP_MM)
        )
        cell_width = available_width / self.GRID_COLUMNS
        
        # Available height after top/bottom margins and name areas
        total_name_height = self.NAME_HEIGHT_MM * self.GRID_ROWS
        total_name_gap = self.NAME_TO_FLAG_GAP_MM * self.GRID_ROWS
        available_height = (
            self.A4_HEIGHT_MM - 
            self.PAGE_MARGIN_TOP_MM - 
            self.PAGE_MARGIN_BOTTOM_MM -
            ((self.GRID_ROWS + 1) * self.CELL_VERTICAL_GAP_MM) -
            total_name_height -
            total_name_gap
        )
        cell_height = available_height / self.GRID_ROWS
        
        return {
            'cell_width': cell_width,
            'cell_height': cell_height,
            'start_x': self.PAGE_MARGIN_LEFT_MM + self.CELL_HORIZONTAL_GAP_MM,
            'start_y': self.PAGE_MARGIN_TOP_MM + self.CELL_VERTICAL_GAP_MM
        }
    
    def _process_color_image(self, image: Image.Image) -> Image.Image:
        """
        Process colored flag image for grid placement.
        
        Args:
            image: Original PIL Image of the flag
            
        Returns:
            Processed image with subtle border
        """
        image_copy = image.copy()
        # Add subtle border for definition
        bordered = ImageOps.expand(image_copy, border=2, fill='black')
        return bordered
    
    def _process_outline_image(self, image: Image.Image) -> Image.Image:
        """
        Convert image to outline/coloring version.
        
        Args:
            image: Original PIL Image of the flag
            
        Returns:
            Outline version suitable for coloring
        """
        # Convert to grayscale
        gray = image.convert("L")
        # Apply edge detection
        edges = gray.filter(ImageFilter.FIND_EDGES)
        # Invert and threshold for clean outline
        outline = ImageOps.invert(edges).point(
            lambda x: 0 if x < 200 else 255
        )
        # Add border
        bordered = ImageOps.expand(outline, border=2, fill='black')
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
            prefix: Filename prefix for identification
            index: Index number for uniqueness
            
        Returns:
            Path to saved temporary file
        """
        temp_path = self.output_dir / f"temp_grid_{prefix}_{index}.png"
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
        
        # Calculate Y position accounting for name areas of previous rows
        y_offset = row * (self.NAME_HEIGHT_MM + self.NAME_TO_FLAG_GAP_MM)
        
        x = dims['start_x'] + (col * (dims['cell_width'] + self.CELL_HORIZONTAL_GAP_MM))
        y = dims['start_y'] + y_offset + (row * (dims['cell_height'] + self.CELL_VERTICAL_GAP_MM))
        
        return (x, y, dims['cell_width'], dims['cell_height'])
    
    def _get_name_position(
        self, 
        cell_dims: Tuple[float, float, float, float]
    ) -> Tuple[float, float]:
        """
        Calculate position for country name text directly below flag.
        
        Args:
            cell_dims: Tuple of (x, y, width, height) from _get_cell_position
            
        Returns:
            Tuple of (x, y) for text baseline position
        """
        x = cell_dims[0] + (cell_dims[2] / 2)  # Center horizontally
        y = cell_dims[1] + cell_dims[3] + self.NAME_TO_FLAG_GAP_MM + (self.NAME_HEIGHT_MM / 2)
        return (x, y)
    
    def _create_grid_page(
        self,
        pdf: FPDF,
        flags_data: List[Tuple[Image.Image, str]],
        page_type: str,
        page_number: int
    ) -> None:
        """
        Create a single page with a grid of flags.
        
        Args:
            pdf: FPDF instance to add page to
            flags_data: List of tuples (flag_image, country_name)
                       Maximum 12 items per page
            page_type: 'color' or 'outline'
            page_number: Page number for logging
            
        Raises:
            GridPDFGenerationError: If page creation fails
        """
        if len(flags_data) > self.FLAGS_PER_PAGE:
            raise GridPDFGenerationError(
                f"Maximum {self.FLAGS_PER_PAGE} flags per page. "
                f"Received: {len(flags_data)}"
            )
        
        try:
            pdf.add_page()
            
            # Set up font for names
            pdf.set_font('Helvetica', style='B', size=self.NAME_FONT_SIZE)
            
            # Calculate cell dimensions
            dims = self._calculate_cell_dimensions()
            
            # Process and place each flag
            for idx, (flag_image, country_name) in enumerate(flags_data):
                # Process image based on type
                if page_type == 'color':
                    processed = self._process_color_image(flag_image)
                else:  # outline
                    processed = self._process_outline_image(flag_image)
                
                # Calculate target size in pixels
                px_per_mm = self.dpi / 25.4
                target_width_px = int(dims['cell_width'] * px_per_mm * 0.95)
                target_height_px = int(dims['cell_height'] * px_per_mm * 0.95)
                target_size = (target_width_px, target_height_px)
                
                # Resize maintaining aspect ratio
                processed_copy = processed.copy()
                processed_copy.thumbnail(target_size, Image.Resampling.LANCZOS)
                
                # Save temp image
                temp_path = self._save_temp_image(
                    processed_copy, 
                    f"{page_type}_p{page_number}", 
                    idx
                )
                
                # Get positions
                cell_pos = self._get_cell_position(idx, dims)
                name_pos = self._get_name_position(cell_pos)
                
                # Calculate image dimensions (fit within cell)
                img_width = min(cell_pos[2] * 0.95, dims['cell_width'])
                img_height = min(cell_pos[3] * 0.95, dims['cell_height'])
                
                # Center image within cell
                img_x = cell_pos[0] + (cell_pos[2] - img_width) / 2
                img_y = cell_pos[1] + (cell_pos[3] - img_height) / 2
                
                # Add flag image
                pdf.image(
                    str(temp_path),
                    x=img_x,
                    y=img_y,
                    w=img_width,
                    h=img_height
                )
                
                # Add country name (centered below flag, close proximity)
                pdf.set_xy(name_pos[0] - (cell_pos[2] / 2), name_pos[1] - 4)
                # Truncate very long names but keep full names when possible
                display_name = country_name[:40] + "..." if len(country_name) > 40 else country_name
                pdf.cell(
                    w=cell_pos[2],
                    h=self.NAME_HEIGHT_MM,
                    text=display_name,
                    align='C'
                )
                
                # Cleanup temp file
                self._cleanup_temp_file(temp_path)
            
            logger.info(
                f"Grid page #{page_number} ({page_type}) created with {len(flags_data)} flags"
            )
            
        except Exception as e:
            raise GridPDFGenerationError(
                f"Error creating grid page #{page_number} ({page_type}): {e}"
            )
    
    def create_color_grid_pdf(
        self,
        flags_data: List[Tuple[Image.Image, str]]
    ) -> FPDF:
        """
        Create PDF with colored flags in grid format.
        
        Args:
            flags_data: List of tuples (flag_image, country_name)
            
        Returns:
            FPDF object containing all pages
        """
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        total_pages = (len(flags_data) + self.FLAGS_PER_PAGE - 1) // self.FLAGS_PER_PAGE
        
        for page_idx in range(0, len(flags_data), self.FLAGS_PER_PAGE):
            chunk = flags_data[page_idx:page_idx + self.FLAGS_PER_PAGE]
            page_number = (page_idx // self.FLAGS_PER_PAGE) + 1
            self._create_grid_page(pdf, chunk, 'color', page_number)
        
        logger.info(f"Created colored grid PDF with {total_pages} page(s)")
        return pdf
    
    def create_outline_grid_pdf(
        self,
        flags_data: List[Tuple[Image.Image, str]]
    ) -> FPDF:
        """
        Create PDF with outline/coloring flags in grid format.
        
        Args:
            flags_data: List of tuples (flag_image, country_name)
            
        Returns:
            FPDF object containing all pages
        """
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        total_pages = (len(flags_data) + self.FLAGS_PER_PAGE - 1) // self.FLAGS_PER_PAGE
        
        for page_idx in range(0, len(flags_data), self.FLAGS_PER_PAGE):
            chunk = flags_data[page_idx:page_idx + self.FLAGS_PER_PAGE]
            page_number = (page_idx // self.FLAGS_PER_PAGE) + 1
            self._create_grid_page(pdf, chunk, 'outline', page_number)
        
        logger.info(f"Created outline grid PDF with {total_pages} page(s)")
        return pdf
    
    def save_pdf(self, pdf: FPDF, filename: str) -> Path:
        """
        Save PDF to disk.
        
        Args:
            pdf: FPDF document instance
            filename: Output filename
            
        Returns:
            Path to saved file
            
        Raises:
            GridPDFGenerationError: If saving fails
        """
        output_path = self.output_dir / filename
        try:
            pdf.output(str(output_path))
            logger.info(f"Grid PDF saved: {output_path}")
            return output_path
        except Exception as e:
            raise GridPDFGenerationError(
                f"Error saving grid PDF '{filename}': {e}"
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
