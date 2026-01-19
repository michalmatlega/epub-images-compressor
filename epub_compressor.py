import zipfile
import os
import tempfile
import shutil
from pathlib import Path
from PIL import Image
from io import BytesIO


class EPUBImageCompressor:
    """Service to reduce image quality in EPUB files."""
    
    def __init__(self, quality=60, max_width=None):
        """
        Initialize the compressor.
        
        Args:
            quality: JPEG quality (1-100, lower = smaller file)
            max_width: Maximum image width in pixels
        """
        self.quality = quality
        self.max_width = max_width
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    def process_epub(self, input_path, output_path=None):
        """
        Process an EPUB file and reduce image quality.
        
        Args:
            input_path: Path to input EPUB file
            output_path: Path for output EPUB (optional)
        
        Returns:
            Path to the processed EPUB file
        """
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_compressed{ext}"
        
        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract EPUB (which is a ZIP file)
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Process all images in the extracted content
            processed_count = self._process_images_in_directory(temp_dir)
            
            # Repackage as EPUB
            self._create_epub(temp_dir, output_path)
            
            print(f"Processed {processed_count} images")
            print(f"Output saved to: {output_path}")
            
        return output_path
    
    def _process_images_in_directory(self, directory):
        """Process all images in a directory recursively."""
        count = 0
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                
                if ext in self.image_extensions:
                    try:
                        self._compress_image(file_path)
                        count += 1
                        print(f"Compressed: {file}")
                    except Exception as e:
                        print(f"Error processing {file}: {e}")
        
        return count
    
    def _compress_image(self, image_path):
        """Compress a single image file."""
        # Open image
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if saving as JPEG
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            
            # Resize if image is too large
            if self.max_width and img.width > self.max_width:
                ratio = self.max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((self.max_width, new_height), Image.Resampling.LANCZOS)
            
            # Save with reduced quality
            # Always save as JPEG for better compression
            img.save(image_path, 'JPEG', quality=self.quality, optimize=True)
    
    def _create_epub(self, source_dir, output_path):
        """Create EPUB file from directory."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            # EPUB requires mimetype to be first and uncompressed
            mimetype_path = os.path.join(source_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                epub.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            
            # Add all other files
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    if file == 'mimetype':
                        continue
                    
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    epub.write(file_path, arcname)


def main():
    """Example usage of the EPUB image compressor."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Reduce image quality in EPUB files')
    parser.add_argument('input', help='Input EPUB file path')
    parser.add_argument('-o', '--output', help='Output EPUB file path')
    parser.add_argument('-q', '--quality', type=int, default=60, 
                       help='JPEG quality (1-100, default: 60)')
    parser.add_argument('-w', '--max-width', type=int, default=1200,
                       help='Maximum image width in pixels (default: 1200)')
    
    args = parser.parse_args()
    
    # Create compressor and process EPUB
    compressor = EPUBImageCompressor(quality=args.quality, max_width=args.max_width)
    compressor.process_epub(args.input, args.output)


if __name__ == '__main__':
    main()