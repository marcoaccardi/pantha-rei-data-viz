#!/usr/bin/env python3
"""
File operation utilities for NOAA Climate Data System.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
import tempfile
import zipfile
import hashlib

import config

class FileOperations:
    """Handle file operations and management."""
    
    def __init__(self):
        """Initialize file operations manager."""
        self.paths = config.PATHS
    
    def ensure_directory(self, directory: Path) -> bool:
        """
        Ensure directory exists, create if necessary.
        
        Args:
            directory: Path to directory
            
        Returns:
            True if directory exists or was created successfully
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"❌ Failed to create directory {directory}: {e}")
            return False
    
    def clean_filename(self, filename: str) -> str:
        """
        Clean filename for safe filesystem usage.
        
        Args:
            filename: Original filename
            
        Returns:
            Cleaned filename
        """
        # Remove invalid characters
        invalid_chars = '<>:"|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove extra spaces and periods
        filename = filename.strip().strip('.')
        
        # Ensure not empty
        if not filename:
            filename = "unnamed_file"
        
        return filename
    
    def get_file_hash(self, file_path: Path) -> Optional[str]:
        """
        Get MD5 hash of file for integrity checking.
        
        Args:
            file_path: Path to file
            
        Returns:
            MD5 hash string or None if failed
        """
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"❌ Failed to hash file {file_path}: {e}")
            return None
    
    def copy_file_safe(self, src: Path, dst: Path, verify: bool = True) -> bool:
        """
        Safely copy file with verification.
        
        Args:
            src: Source file path
            dst: Destination file path
            verify: Whether to verify copy integrity
            
        Returns:
            True if copy successful
        """
        try:
            # Ensure destination directory exists
            self.ensure_directory(dst.parent)
            
            # Get source hash if verification requested
            src_hash = None
            if verify:
                src_hash = self.get_file_hash(src)
            
            # Copy file
            shutil.copy2(src, dst)
            
            # Verify copy if requested
            if verify and src_hash:
                dst_hash = self.get_file_hash(dst)
                if src_hash != dst_hash:
                    print(f"❌ Copy verification failed: {src} -> {dst}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to copy file {src} -> {dst}: {e}")
            return False
    
    def move_file_safe(self, src: Path, dst: Path) -> bool:
        """
        Safely move file.
        
        Args:
            src: Source file path
            dst: Destination file path
            
        Returns:
            True if move successful
        """
        try:
            # Ensure destination directory exists
            self.ensure_directory(dst.parent)
            
            # Move file
            shutil.move(str(src), str(dst))
            return True
            
        except Exception as e:
            print(f"❌ Failed to move file {src} -> {dst}: {e}")
            return False
    
    def delete_file_safe(self, file_path: Path) -> bool:
        """
        Safely delete file.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if deletion successful
        """
        try:
            if file_path.exists():
                file_path.unlink()
                return True
            return True  # File doesn't exist, consider success
            
        except Exception as e:
            print(f"❌ Failed to delete file {file_path}: {e}")
            return False
    
    def extract_archive(self, archive_path: Path, extract_to: Path) -> bool:
        """
        Extract archive file.
        
        Args:
            archive_path: Path to archive file
            extract_to: Directory to extract to
            
        Returns:
            True if extraction successful
        """
        try:
            # Ensure extraction directory exists
            self.ensure_directory(extract_to)
            
            # Extract based on file type
            if archive_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
                return True
            else:
                print(f"❌ Unsupported archive format: {archive_path.suffix}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to extract archive {archive_path}: {e}")
            return False
    
    def find_files(self, directory: Path, pattern: str = "*", recursive: bool = True) -> List[Path]:
        """
        Find files matching pattern.
        
        Args:
            directory: Directory to search in
            pattern: File pattern to match
            recursive: Whether to search recursively
            
        Returns:
            List of matching file paths
        """
        try:
            if recursive:
                return list(directory.rglob(pattern))
            else:
                return list(directory.glob(pattern))
        except Exception as e:
            print(f"❌ Failed to find files in {directory}: {e}")
            return []
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get comprehensive file information.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file information
        """
        info = {
            'exists': False,
            'size_bytes': 0,
            'size_mb': 0.0,
            'modified_time': None,
            'is_readable': False,
            'is_writable': False,
            'extension': '',
            'hash': None
        }
        
        try:
            if file_path.exists():
                info['exists'] = True
                stat = file_path.stat()
                info['size_bytes'] = stat.st_size
                info['size_mb'] = stat.st_size / (1024 * 1024)
                info['modified_time'] = stat.st_mtime
                info['is_readable'] = os.access(file_path, os.R_OK)
                info['is_writable'] = os.access(file_path, os.W_OK)
                info['extension'] = file_path.suffix
                info['hash'] = self.get_file_hash(file_path)
                
        except Exception as e:
            print(f"❌ Failed to get file info for {file_path}: {e}")
        
        return info
    
    def organize_outputs(self) -> Dict[str, List[Path]]:
        """
        Organize and categorize output files.
        
        Returns:
            Dictionary mapping categories to file lists
        """
        categories = {
            'earth_textures': [],
            'sst_textures': [],
            'microplastics_textures': [],
            'station_data': [],
            'reports': []
        }
        
        try:
            # Find Earth textures
            earth_dir = self.paths['earth_textures_dir']
            if earth_dir.exists():
                categories['earth_textures'] = self.find_files(earth_dir, "*.{jpg,jpeg,png}")
            
            # Find SST textures
            sst_dir = self.paths['sst_textures_dir']
            if sst_dir.exists():
                categories['sst_textures'] = self.find_files(sst_dir, "*.{jpg,jpeg,png}")
            
            # Find microplastics textures
            mp_dir = self.paths['microplastics_textures_dir']
            if mp_dir.exists():
                categories['microplastics_textures'] = self.find_files(mp_dir, "*.{jpg,jpeg,png}")
            
            # Find station data
            station_dir = self.paths['station_data_dir']
            if station_dir.exists():
                categories['station_data'] = self.find_files(station_dir, "*.csv")
            
            # Find reports
            reports_dir = self.paths['reports_output_dir']
            if reports_dir.exists():
                categories['reports'] = self.find_files(reports_dir, "*")
                
        except Exception as e:
            print(f"❌ Failed to organize outputs: {e}")
        
        return categories
    
    def cleanup_temp_files(self, temp_dir: Optional[Path] = None) -> int:
        """
        Clean up temporary files.
        
        Args:
            temp_dir: Specific temporary directory to clean
            
        Returns:
            Number of files cleaned up
        """
        cleaned_count = 0
        
        try:
            if temp_dir and temp_dir.exists():
                temp_files = self.find_files(temp_dir, "*")
                for temp_file in temp_files:
                    if self.delete_file_safe(temp_file):
                        cleaned_count += 1
            
        except Exception as e:
            print(f"❌ Failed to cleanup temp files: {e}")
        
        return cleaned_count