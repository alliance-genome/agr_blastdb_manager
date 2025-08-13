"""
visual_regression.py

Visual regression testing tools for the BLAST web interface.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
from PIL import Image, ImageChops
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class VisualRegressionTester:
    """Handles visual regression testing by comparing screenshots."""

    def __init__(self, baseline_dir: Path, current_dir: Path, output_dir: Path):
        self.baseline_dir = baseline_dir
        self.current_dir = current_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def calculate_image_hash(self, image_path: Path) -> str:
        """Calculate hash of an image file."""
        try:
            with open(image_path, 'rb') as f:
                image_hash = hashlib.md5(f.read()).hexdigest()
            return image_hash
        except Exception as e:
            console.log(f"[red]Error calculating hash for {image_path}: {str(e)}[/red]")
            return ""

    def compare_images(self, baseline_path: Path, current_path: Path, 
                      threshold: float = 0.1) -> Tuple[bool, float, Optional[Path]]:
        """
        Compare two images and return similarity score.
        
        Args:
            baseline_path: Path to baseline image
            current_path: Path to current image
            threshold: Similarity threshold (0.0 = identical, 1.0 = completely different)
            
        Returns:
            Tuple of (images_similar, difference_score, diff_image_path)
        """
        try:
            baseline_img = Image.open(baseline_path)
            current_img = Image.open(current_path)
            
            # Ensure images are same size
            if baseline_img.size != current_img.size:
                console.log(f"[yellow]Size mismatch: baseline {baseline_img.size} vs current {current_img.size}[/yellow]")
                current_img = current_img.resize(baseline_img.size, Image.Resampling.LANCZOS)
            
            # Convert to same mode
            if baseline_img.mode != current_img.mode:
                current_img = current_img.convert(baseline_img.mode)
            
            # Calculate difference
            diff = ImageChops.difference(baseline_img, current_img)
            
            # Calculate difference score
            histogram = diff.histogram()
            total_pixels = baseline_img.size[0] * baseline_img.size[1]
            
            if baseline_img.mode == 'RGB':
                # For RGB, histogram has 256*3 values
                non_zero_pixels = sum(histogram[1:])  # Skip first bin (identical pixels)
                difference_score = non_zero_pixels / (total_pixels * 3)
            else:
                # For grayscale
                non_zero_pixels = sum(histogram[1:])
                difference_score = non_zero_pixels / total_pixels
            
            images_similar = difference_score <= threshold
            
            # Save difference image if significant difference
            diff_image_path = None
            if not images_similar:
                diff_image_path = self.output_dir / f"diff_{current_path.stem}.png"
                
                # Enhance difference for visibility
                enhanced_diff = diff.point(lambda x: x * 10 if x < 128 else 255)
                enhanced_diff.save(diff_image_path)
                
                console.log(f"Difference image saved: {diff_image_path}")
            
            return images_similar, difference_score, diff_image_path
            
        except Exception as e:
            console.log(f"[red]Error comparing images: {str(e)}[/red]")
            return False, 1.0, None

    def run_visual_regression_test(self, test_name: str = "visual_regression") -> Dict:
        """Run visual regression test comparing baseline and current screenshots."""
        results = {
            "total_comparisons": 0,
            "identical": 0,
            "similar": 0,
            "different": 0,
            "missing_baseline": 0,
            "missing_current": 0,
            "details": []
        }
        
        # Get all baseline images
        baseline_images = list(self.baseline_dir.glob("*.png"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Comparing images...", total=len(baseline_images))
            
            for baseline_path in baseline_images:
                current_path = self.current_dir / baseline_path.name
                
                comparison_result = {
                    "baseline": str(baseline_path),
                    "current": str(current_path),
                    "status": "",
                    "difference_score": 0.0,
                    "diff_image": None
                }
                
                if not current_path.exists():
                    comparison_result["status"] = "missing_current"
                    results["missing_current"] += 1
                    console.log(f"[yellow]Missing current image: {current_path.name}[/yellow]")
                else:
                    # Compare images
                    similar, diff_score, diff_image = self.compare_images(
                        baseline_path, current_path, threshold=0.01
                    )
                    
                    comparison_result["difference_score"] = diff_score
                    comparison_result["diff_image"] = str(diff_image) if diff_image else None
                    
                    if diff_score == 0.0:
                        comparison_result["status"] = "identical"
                        results["identical"] += 1
                        console.log(f"[green]✓ Identical: {baseline_path.name}[/green]")
                    elif similar:
                        comparison_result["status"] = "similar"
                        results["similar"] += 1
                        console.log(f"[blue]≈ Similar: {baseline_path.name} (diff: {diff_score:.4f})[/blue]")
                    else:
                        comparison_result["status"] = "different"
                        results["different"] += 1
                        console.log(f"[red]✗ Different: {baseline_path.name} (diff: {diff_score:.4f})[/red]")
                
                results["details"].append(comparison_result)
                results["total_comparisons"] += 1
                progress.update(task, advance=1)
        
        # Check for current images without baselines
        current_images = set(img.name for img in self.current_dir.glob("*.png"))
        baseline_images_names = set(img.name for img in baseline_images)
        
        for missing_baseline in current_images - baseline_images_names:
            results["missing_baseline"] += 1
            results["details"].append({
                "baseline": "missing",
                "current": str(self.current_dir / missing_baseline),
                "status": "missing_baseline",
                "difference_score": 0.0,
                "diff_image": None
            })
            console.log(f"[yellow]Missing baseline: {missing_baseline}[/yellow]")
        
        return results

    def generate_report(self, results: Dict, output_file: Path):
        """Generate HTML report of visual regression test results."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Visual Regression Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 30px; }}
        .comparison {{ border: 1px solid #ddd; margin-bottom: 20px; padding: 15px; }}
        .identical {{ background: #d4edda; }}
        .similar {{ background: #d1ecf1; }}
        .different {{ background: #f8d7da; }}
        .missing {{ background: #fff3cd; }}
        .images {{ display: flex; gap: 20px; margin-top: 10px; }}
        .image-container {{ text-align: center; }}
        .image-container img {{ max-width: 300px; max-height: 200px; border: 1px solid #ccc; }}
        .score {{ font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Visual Regression Test Report</h1>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Comparisons:</strong> {results['total_comparisons']}</p>
        <p><strong>Identical:</strong> {results['identical']}</p>
        <p><strong>Similar:</strong> {results['similar']}</p>
        <p><strong>Different:</strong> {results['different']}</p>
        <p><strong>Missing Baseline:</strong> {results['missing_baseline']}</p>
        <p><strong>Missing Current:</strong> {results['missing_current']}</p>
    </div>
    
    <h2>Detailed Results</h2>
"""
        
        for detail in results['details']:
            status_class = detail['status']
            html_content += f"""
    <div class="comparison {status_class}">
        <h3>{Path(detail['current']).name if detail['current'] != 'missing' else Path(detail['baseline']).name}</h3>
        <p><strong>Status:</strong> {detail['status'].replace('_', ' ').title()}</p>
        <p><strong>Difference Score:</strong> <span class="score">{detail['difference_score']:.6f}</span></p>
"""
            
            if detail['status'] not in ['missing_baseline', 'missing_current']:
                html_content += f"""
        <div class="images">
            <div class="image-container">
                <h4>Baseline</h4>
                <img src="{Path(detail['baseline']).name}" alt="Baseline">
            </div>
            <div class="image-container">
                <h4>Current</h4>
                <img src="{Path(detail['current']).name}" alt="Current">
            </div>
"""
                
                if detail['diff_image']:
                    html_content += f"""
            <div class="image-container">
                <h4>Difference</h4>
                <img src="{Path(detail['diff_image']).name}" alt="Difference">
            </div>
"""
                
                html_content += "        </div>"
            
            html_content += "    </div>"
        
        html_content += """
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        console.log(f"[green]HTML report generated: {output_file}[/green]")


@click.command()
@click.option("-b", "--baseline", type=click.Path(exists=True), required=True,
              help="Directory containing baseline screenshots")
@click.option("-c", "--current", type=click.Path(exists=True), required=True,
              help="Directory containing current screenshots")
@click.option("-o", "--output", type=click.Path(), default="visual_regression_output",
              help="Output directory for comparison results")
@click.option("-r", "--report", type=click.Path(), default="visual_regression_report.html",
              help="Output HTML report file")
@click.option("-t", "--threshold", type=float, default=0.01,
              help="Similarity threshold (0.0-1.0)")
def run_visual_regression(baseline: str, current: str, output: str, 
                         report: str, threshold: float):
    """Run visual regression testing comparing baseline and current screenshots."""
    
    baseline_dir = Path(baseline)
    current_dir = Path(current)
    output_dir = Path(output)
    report_path = Path(report)
    
    console.log(f"[blue]Starting visual regression test[/blue]")
    console.log(f"Baseline directory: {baseline_dir}")
    console.log(f"Current directory: {current_dir}")
    console.log(f"Output directory: {output_dir}")
    console.log(f"Threshold: {threshold}")
    
    tester = VisualRegressionTester(baseline_dir, current_dir, output_dir)
    results = tester.run_visual_regression_test()
    
    # Print summary
    console.log(f"\n[bold]Visual Regression Test Summary:[/bold]")
    console.log(f"Total comparisons: {results['total_comparisons']}")
    console.log(f"[green]Identical: {results['identical']}[/green]")
    console.log(f"[blue]Similar: {results['similar']}[/blue]")
    console.log(f"[red]Different: {results['different']}[/red]")
    console.log(f"[yellow]Missing baseline: {results['missing_baseline']}[/yellow]")
    console.log(f"[yellow]Missing current: {results['missing_current']}[/yellow]")
    
    # Generate report
    tester.generate_report(results, report_path)
    
    # Save results as JSON
    json_report = output_dir / "results.json"
    with open(json_report, 'w') as f:
        json.dump(results, f, indent=2)
    console.log(f"[green]JSON results saved: {json_report}[/green]")
    
    # Exit with error code if there are differences
    if results['different'] > 0 or results['missing_baseline'] > 0 or results['missing_current'] > 0:
        console.log(f"[red]Visual regression test failed - differences detected[/red]")
        raise click.Abort()
    else:
        console.log(f"[green]Visual regression test passed - no significant differences[/green]")


if __name__ == "__main__":
    run_visual_regression()