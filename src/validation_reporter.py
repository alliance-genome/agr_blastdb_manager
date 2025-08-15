#!/usr/bin/env python3
"""
Database Validation Reporter

Generates comprehensive HTML and text reports from database validation logs.
Provides summary dashboards and detailed analysis of database health.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ValidationReporter:
    """Generate comprehensive reports from validation results"""
    
    def __init__(self, log_dir: str = "../logs", report_dir: str = "../reports"):
        self.log_dir = Path(log_dir)
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True, parents=True)
    
    def generate_html_report(self, validation_results: Dict, output_file: Optional[str] = None) -> str:
        """Generate comprehensive HTML report"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mod = validation_results.get('mod', 'unknown')
            release = validation_results.get('release', 'unknown')
            output_file = f"validation_report_{mod}_{release}_{timestamp}.html"
        
        report_path = self.report_dir / output_file
        
        html_content = self._generate_html_content(validation_results)
        
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        return str(report_path)
    
    def _generate_html_content(self, results: Dict) -> str:
        """Generate HTML content for validation report"""
        mod = results.get('mod', 'Unknown')
        release = results.get('release', 'Unknown')
        summary = results.get('summary', {})
        databases = results.get('databases', [])
        
        # Calculate statistics
        total_dbs = summary.get('passed', 0) + summary.get('failed', 0)
        success_rate = (summary.get('passed', 0) / max(1, total_dbs)) * 100
        
        # Categorize results
        passed_dbs = [db for db in databases if db['overall_status'] == 'PASSED']
        failed_dbs = [db for db in databases if db['overall_status'] == 'FAILED']
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database Validation Report - {mod} {release}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }}
        .stat-value {{ font-size: 2.5em; font-weight: bold; color: #333; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        .success {{ border-left-color: #28a745; }}
        .warning {{ border-left-color: #ffc107; }}
        .error {{ border-left-color: #dc3545; }}
        .section {{ margin-bottom: 30px; }}
        .section h2 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .database-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }}
        .db-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #ccc; }}
        .db-card.passed {{ border-left-color: #28a745; }}
        .db-card.failed {{ border-left-color: #dc3545; }}
        .db-name {{ font-weight: bold; margin-bottom: 10px; color: #333; }}
        .db-stats {{ font-size: 0.9em; color: #666; }}
        .timestamp {{ color: #888; font-size: 0.9em; }}
        .progress-bar {{ background: #e9ecef; border-radius: 4px; height: 20px; margin: 10px 0; }}
        .progress-fill {{ background: #28a745; height: 100%; border-radius: 4px; transition: width 0.3s; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f1f3f4; font-weight: bold; }}
        .status-passed {{ color: #28a745; font-weight: bold; }}
        .status-failed {{ color: #dc3545; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Database Validation Report</h1>
            <p>{mod} {release} - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="stat-card success">
                <div class="stat-value">{summary.get('passed', 0)}</div>
                <div class="stat-label">Passed</div>
            </div>
            <div class="stat-card error">
                <div class="stat-value">{summary.get('failed', 0)}</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_dbs}</div>
                <div class="stat-label">Total Databases</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{success_rate:.1f}%</div>
                <div class="stat-label">Success Rate</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Overview</h2>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {success_rate}%;"></div>
            </div>
            <p><strong>Validation Period:</strong> {results.get('validation_start', 'Unknown')} to {results.get('validation_end', 'Unknown')}</p>
            <p><strong>Total Time:</strong> {summary.get('total_time_seconds', 0):.1f} seconds</p>
            <p><strong>Average Time per Database:</strong> {(summary.get('total_time_seconds', 0) / max(1, total_dbs)):.1f} seconds</p>
        </div>
"""
        
        # Failed databases section
        if failed_dbs:
            html += f"""
        <div class="section">
            <h2>Failed Databases ({len(failed_dbs)})</h2>
            <div class="database-grid">
"""
            for db in failed_dbs[:10]:  # Show first 10 failures
                db_name = Path(db['database_path']).name
                file_check = db.get('file_check', {})
                integrity_check = db.get('integrity_check', {})
                
                html += f"""
                <div class="db-card failed">
                    <div class="db-name">{db_name}</div>
                    <div class="db-stats">
                        <strong>File Check:</strong> {'✓' if file_check.get('passed') else '✗'} {file_check.get('message', '')}<br>
                        <strong>Integrity:</strong> {'✓' if integrity_check.get('passed') else '✗'} {integrity_check.get('message', '')}<br>
                        <strong>Time:</strong> {db.get('validation_time_seconds', 0):.1f}s
                    </div>
                </div>
"""
            
            if len(failed_dbs) > 10:
                html += f"<p><em>... and {len(failed_dbs) - 10} more failed databases</em></p>"
                
            html += """
            </div>
        </div>
"""
        
        # Passed databases summary
        html += f"""
        <div class="section">
            <h2>Successful Databases ({len(passed_dbs)})</h2>
            <table>
                <thead>
                    <tr>
                        <th>Database</th>
                        <th>Sequences</th>
                        <th>Hits Found</th>
                        <th>Validation Time</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for db in passed_dbs[:20]:  # Show first 20 successful databases
            db_name = Path(db['database_path']).name
            integrity_info = db.get('integrity_check', {}).get('info', {})
            func_results = db.get('functionality_test', {}).get('results', {})
            sequences = integrity_info.get('sequences', 'N/A')
            hits = func_results.get('total_hits', 0)
            
            html += f"""
                    <tr>
                        <td>{db_name}</td>
                        <td>{sequences:,} sequences</td>
                        <td>{hits} hits</td>
                        <td>{db.get('validation_time_seconds', 0):.1f}s</td>
                        <td class="status-passed">PASSED</td>
                    </tr>
"""
        
        if len(passed_dbs) > 20:
            html += f"""
                    <tr>
                        <td colspan="5"><em>... and {len(passed_dbs) - 20} more successful databases</em></td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>Technical Details</h2>
            <p><strong>Test Sequences Used:</strong> Universal conserved sequences (18S/28S rRNA, COI, actin, GAPDH, histone H3, EF-1α, U6 snRNA)</p>
            <p><strong>BLAST Parameters:</strong> E-value ≤ 10, word size 7, max targets 5</p>
            <p><strong>Validation Criteria:</strong> File integrity, database functionality, sequence search capability</p>
        </div>
        
        <div class="timestamp">
            <p><em>Report generated by AGR BLAST Database Manager on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def generate_text_summary(self, validation_results: Dict) -> str:
        """Generate concise text summary for logs/notifications"""
        mod = validation_results.get('mod', 'Unknown')
        release = validation_results.get('release', 'Unknown')
        summary = validation_results.get('summary', {})
        
        total = summary.get('passed', 0) + summary.get('failed', 0)
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        success_rate = (passed / max(1, total)) * 100
        
        text = f"""
=== Database Validation Summary ===
MOD: {mod}
Release: {release}
Total Databases: {total}
Passed: {passed}
Failed: {failed}
Success Rate: {success_rate:.1f}%
Validation Time: {summary.get('total_time_seconds', 0):.1f} seconds

Status: {'✓ ALL PASSED' if failed == 0 else f'⚠ {failed} FAILURES'}
"""
        return text
    
    def find_latest_validation_results(self, mod: str, release: str) -> Optional[Dict]:
        """Find the most recent validation results for a MOD/release"""
        pattern = f"validation_report_{mod}_{release}_*.json"
        
        matching_files = list(self.log_dir.glob(pattern))
        if not matching_files:
            return None
        
        # Get the most recent file
        latest_file = max(matching_files, key=lambda f: f.stat().st_mtime)
        
        try:
            with open(latest_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def generate_dashboard_report(self, mods: List[str] = None) -> str:
        """Generate multi-MOD dashboard report"""
        if mods is None:
            mods = ['FB', 'SGD', 'WB', 'ZFIN', 'RGD']
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dashboard_file = f"validation_dashboard_{timestamp}.html"
        dashboard_path = self.report_dir / dashboard_file
        
        # Collect latest results for each MOD
        mod_results = {}
        for mod in mods:
            # Find latest validation results for this MOD
            latest_files = list(self.log_dir.glob(f"validation_report_{mod}_*.json"))
            if latest_files:
                latest_file = max(latest_files, key=lambda f: f.stat().st_mtime)
                try:
                    with open(latest_file, 'r') as f:
                        mod_results[mod] = json.load(f)
                except Exception:
                    continue
        
        # Generate dashboard HTML
        html = self._generate_dashboard_html(mod_results)
        
        with open(dashboard_path, 'w') as f:
            f.write(html)
        
        return str(dashboard_path)
    
    def _generate_dashboard_html(self, mod_results: Dict) -> str:
        """Generate HTML dashboard for multiple MODs"""
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AGR Database Validation Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; text-align: center; }}
        .mod-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .mod-card {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.2s; }}
        .mod-card:hover {{ transform: translateY(-2px); }}
        .mod-header {{ font-size: 1.5em; font-weight: bold; margin-bottom: 15px; color: #333; }}
        .mod-stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }}
        .stat {{ text-align: center; padding: 15px; border-radius: 8px; }}
        .stat-success {{ background: linear-gradient(135deg, #d4edda, #c3e6cb); color: #155724; }}
        .stat-warning {{ background: linear-gradient(135deg, #fff3cd, #ffeaa7); color: #856404; }}
        .stat-error {{ background: linear-gradient(135deg, #f8d7da, #f5c6cb); color: #721c24; }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .stat-label {{ font-size: 0.9em; margin-top: 5px; }}
        .mod-status {{ padding: 10px; border-radius: 8px; text-align: center; margin-top: 15px; font-weight: bold; }}
        .status-healthy {{ background: #d4edda; color: #155724; }}
        .status-warning {{ background: #fff3cd; color: #856404; }}
        .status-critical {{ background: #f8d7da; color: #721c24; }}
        .no-data {{ color: #666; font-style: italic; text-align: center; }}
        .timestamp {{ text-align: center; color: #888; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔬 AGR Database Validation Dashboard</h1>
            <p>Real-time status of BLAST database health across all Model Organism Databases</p>
            <p><strong>Last Updated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="mod-grid">
"""
        
        for mod in ['FB', 'SGD', 'WB', 'ZFIN', 'RGD']:
            results = mod_results.get(mod)
            
            if not results:
                html += f"""
            <div class="mod-card">
                <div class="mod-header">{mod}</div>
                <div class="no-data">No recent validation data available</div>
            </div>
"""
                continue
            
            summary = results.get('summary', {})
            total = summary.get('passed', 0) + summary.get('failed', 0)
            passed = summary.get('passed', 0)
            failed = summary.get('failed', 0)
            success_rate = (passed / max(1, total)) * 100
            
            # Determine status
            if failed == 0 and total > 0:
                status_class = "status-healthy"
                status_text = "✓ HEALTHY"
            elif failed <= total * 0.1:  # Less than 10% failure
                status_class = "status-warning" 
                status_text = "⚠ WARNING"
            else:
                status_class = "status-critical"
                status_text = "✗ CRITICAL"
            
            html += f"""
            <div class="mod-card">
                <div class="mod-header">{mod} ({results.get('release', 'Unknown')})</div>
                
                <div class="mod-stats">
                    <div class="stat stat-success">
                        <div class="stat-value">{passed}</div>
                        <div class="stat-label">Passed</div>
                    </div>
                    <div class="stat stat-error">
                        <div class="stat-value">{failed}</div>
                        <div class="stat-label">Failed</div>
                    </div>
                </div>
                
                <div class="stat stat-success">
                    <div class="stat-value">{success_rate:.1f}%</div>
                    <div class="stat-label">Success Rate</div>
                </div>
                
                <div class="mod-status {status_class}">
                    {status_text}
                </div>
                
                <p style="margin-top: 15px; font-size: 0.9em; color: #666;">
                    <strong>Total:</strong> {total} databases<br>
                    <strong>Validated:</strong> {results.get('validation_start', 'Unknown')}<br>
                    <strong>Duration:</strong> {summary.get('total_time_seconds', 0):.1f}s
                </p>
            </div>
"""
        
        html += f"""
        </div>
        
        <div class="timestamp">
            <p><em>Dashboard generated by AGR BLAST Database Manager</em></p>
        </div>
    </div>
</body>
</html>
"""
        
        return html