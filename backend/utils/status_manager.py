#!/usr/bin/env python3
"""
Status management utilities for tracking download progress and system health.
"""

import json
import os
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

class StatusManager:
    """Manages status tracking for all datasets and system health."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize status manager.
        
        Args:
            config_path: Path to config directory containing status.json
        """
        self.config_path = config_path or Path(__file__).parent.parent / "config"
        self.status_file = self.config_path / "status.json"
        
    def get_full_status(self) -> Dict[str, Any]:
        """Get complete status for all datasets and system."""
        if not self.status_file.exists():
            return self._initialize_status()
        
        with open(self.status_file, 'r') as f:
            return json.load(f)
    
    def get_dataset_status(self, dataset: str) -> Dict[str, Any]:
        """Get status for a specific dataset."""
        status = self.get_full_status()
        return status.get("datasets", {}).get(dataset, {})
    
    def update_dataset_status(self, dataset: str, **kwargs):
        """Update status for a specific dataset."""
        status = self.get_full_status()
        
        if "datasets" not in status:
            status["datasets"] = {}
        if dataset not in status["datasets"]:
            status["datasets"][dataset] = {}
            
        status["datasets"][dataset].update(kwargs)
        status["last_updated"] = datetime.now().isoformat()
        
        self._save_status(status)
    
    def update_system_status(self, **kwargs):
        """Update system-level status."""
        status = self.get_full_status()
        
        if "system" not in status:
            status["system"] = {}
            
        status["system"].update(kwargs)
        status["last_updated"] = datetime.now().isoformat()
        
        self._save_status(status)
    
    def get_storage_info(self, base_path: Path) -> Dict[str, float]:
        """Get storage information for the data directory."""
        try:
            # Get disk usage for the data directory
            usage = psutil.disk_usage(str(base_path))
            
            # Calculate used space by our data
            total_our_data = 0
            if base_path.exists():
                for file_path in base_path.rglob("*"):
                    if file_path.is_file():
                        total_our_data += file_path.stat().st_size
            
            return {
                "total_disk_gb": usage.total / (1024**3),
                "available_disk_gb": usage.free / (1024**3),
                "used_disk_gb": usage.used / (1024**3),
                "our_data_gb": total_our_data / (1024**3),
                "disk_usage_percent": (usage.used / usage.total) * 100
            }
        except Exception as e:
            return {
                "error": str(e),
                "total_disk_gb": 0,
                "available_disk_gb": 0,
                "used_disk_gb": 0,
                "our_data_gb": 0,
                "disk_usage_percent": 0
            }
    
    def perform_health_check(self, base_path: Path) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "issues": [],
            "storage": self.get_storage_info(base_path),
            "datasets": {}
        }
        
        status = self.get_full_status()
        
        # Check each dataset
        for dataset_name, dataset_status in status.get("datasets", {}).items():
            dataset_health = {
                "status": dataset_status.get("status", "unknown"),
                "last_success": dataset_status.get("last_success"),
                "last_error": dataset_status.get("last_error"),
                "total_files": dataset_status.get("total_files", 0),
                "issues": []
            }
            
            # Check for recent errors
            if dataset_status.get("last_error"):
                last_error_time = dataset_status.get("last_error")
                if last_error_time:
                    try:
                        error_time = datetime.fromisoformat(last_error_time.split(":")[0])
                        if (datetime.now() - error_time).days < 1:
                            dataset_health["issues"].append("Recent error within 24 hours")
                    except:
                        pass
            
            # Check for stale data
            last_success = dataset_status.get("last_success")
            if last_success:
                try:
                    success_time = datetime.fromisoformat(last_success)
                    days_since_success = (datetime.now() - success_time).days
                    if days_since_success > 2:
                        dataset_health["issues"].append(f"Last successful download was {days_since_success} days ago")
                except:
                    pass
            
            health["datasets"][dataset_name] = dataset_health
            
            # Add to overall issues
            if dataset_health["issues"]:
                health["issues"].extend([f"{dataset_name}: {issue}" for issue in dataset_health["issues"]])
        
        # Check storage
        if health["storage"].get("disk_usage_percent", 0) > 90:
            health["issues"].append(f"Disk usage is {health['storage']['disk_usage_percent']:.1f}%")
        
        if health["storage"].get("available_disk_gb", 0) < 10:
            health["issues"].append(f"Only {health['storage']['available_disk_gb']:.1f} GB available")
        
        # Set overall status
        if health["issues"]:
            health["overall_status"] = "warning" if len(health["issues"]) < 5 else "critical"
        
        # Update system status
        self.update_system_status(
            last_health_check=health["timestamp"],
            total_storage_gb=health["storage"]["our_data_gb"],
            available_storage_gb=health["storage"]["available_disk_gb"],
            health_status=health["overall_status"]
        )
        
        return health
    
    def get_download_summary(self) -> Dict[str, Any]:
        """Get summary of all downloads."""
        status = self.get_full_status()
        
        summary = {
            "total_datasets": len(status.get("datasets", {})),
            "active_datasets": 0,
            "total_files": 0,
            "total_storage_gb": 0.0,
            "last_activity": None,
            "datasets": {}
        }
        
        latest_activity = None
        
        for dataset_name, dataset_status in status.get("datasets", {}).items():
            dataset_summary = {
                "status": dataset_status.get("status", "unknown"),
                "last_date": dataset_status.get("last_date"),
                "total_files": dataset_status.get("total_files", 0),
                "storage_gb": dataset_status.get("storage_gb", 0.0),
                "last_success": dataset_status.get("last_success")
            }
            
            summary["datasets"][dataset_name] = dataset_summary
            summary["total_files"] += dataset_summary["total_files"]
            summary["total_storage_gb"] += dataset_summary["storage_gb"]
            
            if dataset_summary["status"] in ["active", "up_to_date"]:
                summary["active_datasets"] += 1
            
            # Track latest activity
            if dataset_summary["last_success"]:
                try:
                    success_time = datetime.fromisoformat(dataset_summary["last_success"])
                    if not latest_activity or success_time > latest_activity:
                        latest_activity = success_time
                except:
                    pass
        
        if latest_activity:
            summary["last_activity"] = latest_activity.isoformat()
        
        return summary
    
    def _initialize_status(self) -> Dict[str, Any]:
        """Initialize empty status structure."""
        return {
            "last_updated": None,
            "datasets": {
                "sst": {
                    "last_date": None,
                    "total_files": 0,
                    "storage_gb": 0.0,
                    "last_success": None,
                    "last_error": None,
                    "status": "not_started"
                },
                "currents": {
                    "last_date": None,
                    "total_files": 0,
                    "storage_gb": 0.0,
                    "last_success": None,
                    "last_error": None,
                    "status": "not_started"
                },
                "acidity": {
                    "last_date": None,
                    "total_files": 0,
                    "storage_gb": 0.0,
                    "last_success": None,
                    "last_error": None,
                    "status": "not_started"
                },
                "microplastics": {
                    "last_date": None,
                    "total_files": 0,
                    "storage_mb": 0.0,
                    "last_success": None,
                    "last_error": None,
                    "status": "not_started"
                }
            },
            "system": {
                "total_storage_gb": 0.0,
                "available_storage_gb": None,
                "last_health_check": None
            }
        }
    
    def _save_status(self, status: Dict[str, Any]):
        """Save status to file."""
        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2)
    
    def reset_dataset_status(self, dataset: str):
        """Reset status for a specific dataset."""
        self.update_dataset_status(
            dataset,
            last_date=None,
            total_files=0,
            storage_gb=0.0,
            last_success=None,
            last_error=None,
            status="not_started"
        )
    
    def mark_dataset_error(self, dataset: str, error_message: str):
        """Mark a dataset as having an error."""
        self.update_dataset_status(
            dataset,
            last_error=f"{datetime.now().isoformat()}: {error_message}",
            status="error"
        )