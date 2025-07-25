#!/usr/bin/env python3
"""
CMEMS Dataset Validity Monitor

Monitors the validity of CMEMS datasets and alerts about upcoming expirations.
Part of the Ocean Data Management System.

Usage:
    python monitor_dataset_validity.py [--json] [--check-all]
"""

import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Add backend directory to path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.append(str(BACKEND_DIR))

from downloaders.waves_downloader import WavesDownloader


class DatasetValidityMonitor:
    """Monitor CMEMS dataset validity and expiration dates."""
    
    def __init__(self):
        """Initialize the monitor."""
        self.monitored_datasets = {
            "waves": {
                "downloader_class": WavesDownloader,
                "description": "CMEMS Global Ocean Waves Analysis and Forecast"
            }
            # Add other datasets here as they're implemented
        }
    
    def check_dataset_status(self, dataset_name: str) -> Dict[str, Any]:
        """Check the status of a specific dataset."""
        if dataset_name not in self.monitored_datasets:
            raise ValueError(f"Unknown dataset: {dataset_name}")
        
        config = self.monitored_datasets[dataset_name]
        downloader_class = config["downloader_class"]
        
        try:
            downloader = downloader_class()
            return downloader.get_dataset_status()
        except Exception as e:
            return {
                "dataset_name": dataset_name,
                "status": "error",
                "error": str(e),
                "description": config["description"]
            }
    
    def check_all_datasets(self) -> Dict[str, Dict[str, Any]]:
        """Check the status of all monitored datasets."""
        results = {}
        
        for dataset_name in self.monitored_datasets:
            results[dataset_name] = self.check_dataset_status(dataset_name)
            results[dataset_name]["description"] = self.monitored_datasets[dataset_name]["description"]
        
        return results
    
    def generate_report(self, results: Dict[str, Dict[str, Any]]) -> str:
        """Generate a human-readable report."""
        report_lines = []
        report_lines.append("🌊 OCEAN DATA DATASET VALIDITY REPORT")
        report_lines.append("=" * 50)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        for dataset_name, status in results.items():
            report_lines.append(f"📊 {dataset_name.upper()}: {status.get('description', 'N/A')}")
            report_lines.append("-" * 40)
            
            if status.get("status") == "error":
                report_lines.append(f"❌ Error: {status.get('error')}")
            else:
                dataset_id = status.get("dataset_id", "Unknown")
                days_left = status.get("days_until_expiry", 0)
                expiry_date = status.get("expiry_date", "Unknown")
                current_status = status.get("status", "unknown")
                
                # Status emoji
                if current_status == "expired":
                    emoji = "💀"
                elif current_status == "critical":
                    emoji = "🚨"
                elif current_status == "warning":
                    emoji = "⚠️"
                else:
                    emoji = "✅"
                
                report_lines.append(f"{emoji} Dataset ID: {dataset_id}")
                report_lines.append(f"📅 Expiry Date: {expiry_date[:10] if expiry_date != 'Unknown' else expiry_date}")
                report_lines.append(f"⏰ Days Until Expiry: {days_left}")
                report_lines.append(f"🔍 Status: {current_status.upper()}")
                
                if status.get("needs_attention"):
                    report_lines.append("")
                    report_lines.append("🎯 ACTION REQUIRED:")
                    if status.get("critical"):
                        report_lines.append("  • URGENT: Dataset expires within 30 days!")
                        report_lines.append("  • Check CMEMS roadmap for replacement")
                        report_lines.append("  • Prepare transition to alternative dataset")
                    else:
                        report_lines.append("  • Monitor CMEMS announcements")
                        report_lines.append("  • Plan transition strategy")
                    
                    alternatives = status.get("alternatives", {})
                    if alternatives.get("reanalysis"):
                        report_lines.append(f"  • Alternative: {alternatives['reanalysis']}")
                    if alternatives.get("roadmap_url"):
                        report_lines.append(f"  • Roadmap: {alternatives['roadmap_url']}")
            
            report_lines.append("")
        
        # Summary
        total_datasets = len(results)
        healthy = sum(1 for s in results.values() if s.get("status") == "healthy")
        warning = sum(1 for s in results.values() if s.get("status") == "warning")
        critical = sum(1 for s in results.values() if s.get("status") == "critical")
        expired = sum(1 for s in results.values() if s.get("status") == "expired")
        errors = sum(1 for s in results.values() if s.get("status") == "error")
        
        report_lines.append("📋 SUMMARY")
        report_lines.append("-" * 20)
        report_lines.append(f"Total Datasets: {total_datasets}")
        report_lines.append(f"✅ Healthy: {healthy}")
        report_lines.append(f"⚠️  Warning: {warning}")
        report_lines.append(f"🚨 Critical: {critical}")
        report_lines.append(f"💀 Expired: {expired}")
        report_lines.append(f"❌ Errors: {errors}")
        
        if critical > 0 or expired > 0:
            report_lines.append("")
            report_lines.append("🚨 IMMEDIATE ATTENTION REQUIRED!")
            report_lines.append("Check dataset roadmaps and plan transitions.")
        elif warning > 0:
            report_lines.append("")
            report_lines.append("⚠️  Monitor for updates and plan ahead.")
        
        return "\n".join(report_lines)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Monitor CMEMS dataset validity")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--check-all", action="store_true", help="Check all datasets (default)")
    parser.add_argument("--dataset", type=str, help="Check specific dataset only")
    
    args = parser.parse_args()
    
    monitor = DatasetValidityMonitor()
    
    try:
        if args.dataset:
            # Check specific dataset
            results = {args.dataset: monitor.check_dataset_status(args.dataset)}
        else:
            # Check all datasets
            results = monitor.check_all_datasets()
        
        if args.json:
            # JSON output
            output = {
                "timestamp": datetime.now().isoformat(),
                "datasets": results
            }
            print(json.dumps(output, indent=2))
        else:
            # Human-readable report
            report = monitor.generate_report(results)
            print(report)
        
        # Exit with appropriate code
        has_critical = any(s.get("status") in ["critical", "expired"] for s in results.values())
        has_errors = any(s.get("status") == "error" for s in results.values())
        
        if has_critical or has_errors:
            sys.exit(1)  # Error exit code for CI/CD alerts
        else:
            sys.exit(0)  # Success
            
    except Exception as e:
        print(f"Error running dataset validity monitor: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()