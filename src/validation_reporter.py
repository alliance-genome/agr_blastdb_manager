"""
validation_reporter.py

HTML and JSON report generation for database validation results.
Provides visual dashboards and machine-readable exports.

Authors: Paulo Nuin, Adam Wright
Date: January 2025
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ValidationReporter:
    """Generate comprehensive HTML and JSON reports from validation results."""

    def __init__(self, report_dir: str = "../reports"):
        """
        Initialize the reporter.

        Args:
            report_dir: Directory for saving reports
        """
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True, parents=True)

    def generate_html_report(
        self, validation_results: Dict, output_file: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive HTML report from validation results.

        Args:
            validation_results: Dictionary containing validation results
            output_file: Optional output filename

        Returns:
            Path to generated HTML report
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mod = validation_results.get("mod", "all_mods")
            output_file = f"validation_report_{mod}_{timestamp}.html"

        report_path = self.report_dir / output_file
        html_content = self._generate_html_content(validation_results)

        with open(report_path, "w") as f:
            f.write(html_content)

        return str(report_path)

    def generate_json_export(
        self, validation_results: Dict, output_file: Optional[str] = None
    ) -> str:
        """
        Export validation results as JSON for CI/CD integration.

        Args:
            validation_results: Dictionary containing validation results
            output_file: Optional output filename

        Returns:
            Path to generated JSON file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mod = validation_results.get("mod", "all_mods")
            output_file = f"validation_export_{mod}_{timestamp}.json"

        export_path = self.report_dir / output_file

        # Add metadata
        export_data = {
            "generated_at": datetime.now().isoformat(),
            "format_version": "1.0",
            **validation_results,
        }

        with open(export_path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        return str(export_path)

    def _generate_html_content(self, results: Dict) -> str:
        """
        Generate HTML content for validation report.

        Args:
            results: Validation results dictionary

        Returns:
            HTML string
        """
        # Extract data
        mod = results.get("mod", "All MODs")
        timestamp = results.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Calculate statistics from all_results if present
        if "all_results" in results:
            all_mod_results = results["all_results"]
            total_dbs = sum(r.get("total", 0) for r in all_mod_results.values())
            total_passed = sum(r.get("passed", 0) for r in all_mod_results.values())
            total_failed = sum(r.get("failed", 0) for r in all_mod_results.values())
        else:
            # Single MOD results
            total_dbs = results.get("total_databases", 0)
            total_passed = results.get("passed", 0)
            total_failed = results.get("failed", 0)

        success_rate = (total_passed / max(1, total_dbs)) * 100
        duration = results.get("duration", "N/A")

        # Determine status color
        if success_rate >= 95:
            status_color = "#28a745"  # green
            status_text = "EXCELLENT"
        elif success_rate >= 80:
            status_color = "#ffc107"  # yellow
            status_text = "GOOD"
        elif success_rate >= 50:
            status_color = "#ff9900"  # orange
            status_text = "NEEDS ATTENTION"
        else:
            status_color = "#dc3545"  # red
            status_text = "CRITICAL"

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database Validation Report - {mod}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; font-weight: 700; }}
        .header .subtitle {{ font-size: 1.1em; opacity: 0.9; }}
        .content {{ padding: 40px; }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            border-left: 5px solid #007bff;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .stat-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        }}
        .stat-card.success {{ border-left-color: #28a745; }}
        .stat-card.warning {{ border-left-color: #ffc107; }}
        .stat-card.error {{ border-left-color: #dc3545; }}
        .stat-card.info {{ border-left-color: #17a2b8; }}

        .stat-value {{
            font-size: 3em;
            font-weight: bold;
            color: #333;
            margin: 10px 0;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .status-badge {{
            display: inline-block;
            padding: 10px 30px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.2em;
            margin: 20px 0;
        }}

        .progress-section {{
            margin: 30px 0;
            padding: 25px;
            background: #f8f9fa;
            border-radius: 10px;
        }}
        .progress-bar-container {{
            background: #e9ecef;
            border-radius: 10px;
            height: 40px;
            overflow: hidden;
            margin: 15px 0;
            position: relative;
        }}
        .progress-bar {{
            height: 100%;
            background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
            transition: width 1s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }}

        .section {{
            margin: 40px 0;
        }}
        .section-title {{
            font-size: 1.8em;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}

        .mod-results {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .mod-card {{
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            transition: all 0.3s;
        }}
        .mod-card:hover {{
            border-color: #667eea;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2);
        }}
        .mod-card.passed {{ border-left: 5px solid #28a745; }}
        .mod-card.failed {{ border-left: 5px solid #dc3545; }}
        .mod-card.partial {{ border-left: 5px solid #ffc107; }}

        .mod-name {{
            font-size: 1.4em;
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
        }}
        .mod-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 15px;
        }}
        .mod-stat {{
            text-align: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        .mod-stat-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
        }}
        .mod-stat-label {{
            font-size: 0.85em;
            color: #666;
            margin-top: 5px;
        }}

        .database-list {{
            margin-top: 20px;
        }}
        .database-item {{
            padding: 12px;
            margin: 8px 0;
            background: #f8f9fa;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .database-item.passed {{ border-left: 3px solid #28a745; }}
        .database-item.failed {{ border-left: 3px solid #dc3545; }}

        .status-icon {{
            font-size: 1.2em;
            font-weight: bold;
        }}
        .status-icon.passed {{ color: #28a745; }}
        .status-icon.failed {{ color: #dc3545; }}

        .footer {{
            background: #f8f9fa;
            padding: 25px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
            border-top: 1px solid #e9ecef;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔬 Database Validation Report</h1>
            <div class="subtitle">{mod} - Generated {timestamp}</div>
        </div>

        <div class="content">
            <!-- Status Badge -->
            <div style="text-align: center;">
                <div class="status-badge" style="background-color: {status_color}; color: white;">
                    {status_text}
                </div>
            </div>

            <!-- Summary Statistics -->
            <div class="summary-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Databases</div>
                    <div class="stat-value">{total_dbs}</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-label">Passed</div>
                    <div class="stat-value">{total_passed}</div>
                </div>
                <div class="stat-card error">
                    <div class="stat-label">Failed</div>
                    <div class="stat-value">{total_failed}</div>
                </div>
                <div class="stat-card info">
                    <div class="stat-label">Success Rate</div>
                    <div class="stat-value">{success_rate:.1f}%</div>
                </div>
            </div>

            <!-- Progress Bar -->
            <div class="progress-section">
                <h3>Overall Validation Progress</h3>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: {success_rate}%;">
                        {total_passed}/{total_dbs} Passed ({success_rate:.1f}%)
                    </div>
                </div>
                <p style="color: #666; margin-top: 10px;">
                    Duration: {duration} | E-value: {results.get('evalue', '10')} |
                    Word Size: {results.get('word_size', '7')}
                </p>
            </div>

            {self._generate_mod_results_html(results)}

            {self._generate_details_table_html(results)}
        </div>

        <div class="footer">
            <p>Generated by AGR BLAST Database Manager - Validation System v1.0</p>
            <p style="margin-top: 10px;">Report ID: {timestamp.replace(' ', '_').replace(':', '-')}</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _generate_mod_results_html(self, results: Dict) -> str:
        """Generate HTML for per-MOD results."""
        if "all_results" not in results:
            return ""

        html = '<div class="section"><h2 class="section-title">Per-MOD Results</h2><div class="mod-results">'

        for mod, mod_stats in sorted(results["all_results"].items()):
            total = mod_stats.get("total", 0)
            passed = mod_stats.get("passed", 0)
            failed = mod_stats.get("failed", 0)
            pass_rate = (passed / max(1, total)) * 100

            # Determine card class
            if failed == 0:
                card_class = "passed"
            elif passed == 0:
                card_class = "failed"
            else:
                card_class = "partial"

            html += f"""
            <div class="mod-card {card_class}">
                <div class="mod-name">{mod}</div>
                <div class="mod-stats">
                    <div class="mod-stat">
                        <div class="mod-stat-value">{total}</div>
                        <div class="mod-stat-label">Total</div>
                    </div>
                    <div class="mod-stat">
                        <div class="mod-stat-value" style="color: #28a745;">{passed}</div>
                        <div class="mod-stat-label">Passed</div>
                    </div>
                    <div class="mod-stat">
                        <div class="mod-stat-value" style="color: #dc3545;">{failed}</div>
                        <div class="mod-stat-label">Failed</div>
                    </div>
                </div>
                <div style="margin-top: 15px; text-align: center;">
                    <strong>Pass Rate: {pass_rate:.1f}%</strong>
                </div>
            </div>
            """

        html += "</div></div>"
        return html

    def _generate_details_table_html(self, results: Dict) -> str:
        """Generate HTML table with detailed database results."""
        if "all_results" not in results:
            return ""

        html = '<div class="section"><h2 class="section-title">Detailed Results</h2>'

        for mod, mod_stats in sorted(results["all_results"].items()):
            if "results" not in mod_stats:
                continue

            html += f'<h3 style="margin-top: 30px; color: #667eea;">{mod} Databases</h3>'
            html += '<table><thead><tr>'
            html += '<th>Database</th><th>Status</th><th>Conserved Hits</th>'
            html += '<th>Specific Hits</th><th>Total Hits</th><th>Hit Rate</th>'
            html += '</tr></thead><tbody>'

            for result in mod_stats["results"]:
                status = "✓ PASSED" if result.success else "✗ FAILED"
                status_class = "passed" if result.success else "failed"
                hit_rate = result.get_hit_rate()

                html += f"""
                <tr>
                    <td><strong>{result.db_name}</strong></td>
                    <td><span class="status-icon {status_class}">{status}</span></td>
                    <td>{result.conserved_hits}</td>
                    <td>{result.specific_hits}</td>
                    <td>{result.total_hits}</td>
                    <td>{hit_rate:.1f}%</td>
                </tr>
                """

            html += '</tbody></table>'

        html += '</div>'
        return html

    def generate_multi_mod_dashboard(
        self, all_mod_results: Dict[str, Dict], output_file: Optional[str] = None
    ) -> str:
        """
        Generate a dashboard view for multiple MODs.

        Args:
            all_mod_results: Dictionary mapping MOD names to their results
            output_file: Optional output filename

        Returns:
            Path to generated dashboard HTML
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"validation_dashboard_{timestamp}.html"

        # Aggregate results
        aggregated = {
            "mod": "Multi-MOD Dashboard",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "all_results": all_mod_results,
        }

        return self.generate_html_report(aggregated, output_file)
