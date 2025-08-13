#!/usr/bin/env python3
"""
generate_ui_config_simple.py

Generate UI test configuration from filesystem data and known patterns.
"""

import json
import re
from pathlib import Path
from typing import Dict, List

from rich.console import Console

console = Console()


def get_latest_releases() -> Dict[str, str]:
    """Get the latest release for each MOD from the filesystem."""
    releases = {}
    blast_path = Path("/var/sequenceserver-data/blast")
    
    if not blast_path.exists():
        console.log(f"[red]BLAST data path not found: {blast_path}[/red]")
        return releases
    
    console.log("[blue]Finding latest releases...[/blue]")
    
    # Check each MOD directory
    for mod_dir in blast_path.iterdir():
        if not mod_dir.is_dir():
            continue
            
        mod_name = mod_dir.name
        console.log(f"Checking {mod_name}...")
        
        # Get all release directories for this MOD
        release_dirs = []
        for release_dir in mod_dir.iterdir():
            if release_dir.is_dir():
                release_dirs.append(release_dir.name)
        
        if not release_dirs:
            console.log(f"[yellow]No releases found for {mod_name}[/yellow]")
            continue
        
        # Sort to get the latest
        if mod_name == "FB":
            # FB uses format FB2025_01, FB2025_03, etc.
            latest = max(release_dirs, key=lambda x: (
                int(re.search(r'FB(\d{4})', x).group(1)) if re.search(r'FB(\d{4})', x) else 0,
                int(re.search(r'_(\d+)', x).group(1)) if re.search(r'_(\d+)', x) else 0
            ))
        elif mod_name == "WB":
            # WB uses WS292, WS293, etc. (exclude 'dev')
            ws_releases = [r for r in release_dirs if r.startswith('WS') and r != 'dev']
            if ws_releases:
                latest = max(ws_releases, key=lambda x: int(re.search(r'WS(\d+)', x).group(1)))
            else:
                latest = "dev"
        else:
            # For SGD (main/fungal), RGD (production), ZFIN (prod)
            if "main" in release_dirs:
                latest = "main"
            elif "fungal" in release_dirs:
                latest = "fungal"  
            elif "production" in release_dirs:
                latest = "production"
            elif "prod" in release_dirs:
                latest = "prod"
            else:
                latest = max(release_dirs)  # Fallback to alphabetically last
        
        releases[mod_name] = latest
        console.log(f"[green]✓ {mod_name}: {latest}[/green]")
    
    return releases


def get_database_names_from_filesystem(mod: str, release: str) -> List[str]:
    """Get database names from filesystem and convert to likely anchor names."""
    blast_path = Path(f"/var/sequenceserver-data/blast/{mod}/{release}/databases")
    
    if not blast_path.exists():
        console.log(f"[yellow]Database path not found: {blast_path}[/yellow]")
        return []
    
    database_names = []
    
    # Get genus-level directories (first level under databases/)
    for genus_dir in blast_path.iterdir():
        if genus_dir.is_dir():
            genus_name = genus_dir.name
            # Convert to anchor format: Genus_anchor
            anchor_name = f"{genus_name}_anchor"
            database_names.append(anchor_name)
    
    console.log(f"Found {len(database_names)} databases in {mod}/{release}")
    
    return sorted(database_names)


def generate_config() -> Dict:
    """Generate complete UI test configuration."""
    console.log("[bold blue]Generating UI test configuration from filesystem...[/bold blue]")
    
    config = {}
    releases = get_latest_releases()
    
    # Standard test sequences (immutable as requested)
    test_sequences = {
        "nucl": "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC",
        "prot": "MKLLIVDDSSGKVRAEIKQLLKQGVNPEMKLLIVDDSSGKVRAEIKQLLKQGVNPE"
    }
    
    if not releases:
        console.log("[red]No releases found![/red]")
        return config
    
    for mod, release in releases.items():
        console.log(f"Processing {mod}/{release}...")
        
        database_anchors = get_database_names_from_filesystem(mod, release)
        
        if database_anchors:
            config[mod] = {
                release: {
                    "url": f"https://blast.alliancegenome.org/blast/{mod}/{release}",
                    "nucl": test_sequences["nucl"],
                    "prot": test_sequences["prot"],
                    "items": database_anchors
                }
            }
            console.log(f"[green]✓ {mod}/{release}: {len(database_anchors)} databases[/green]")
        else:
            console.log(f"[yellow]⚠ {mod}/{release}: No databases found[/yellow]")
    
    return config


def save_config(config: Dict, output_path: str = "tests/UI/config.json") -> None:
    """Save configuration to file."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2, sort_keys=True)
    
    console.log(f"[green]✓ Configuration saved to: {output_file}[/green]")


def print_summary(config: Dict) -> None:
    """Print configuration summary."""
    console.log("[bold]Configuration Summary:[/bold]")
    
    total_databases = 0
    
    for mod, mod_data in config.items():
        for release, release_data in mod_data.items():
            db_count = len(release_data.get("items", []))
            total_databases += db_count
            console.log(f"[cyan]{mod}/{release}[/cyan]: {db_count} databases")
            
            # Show first few database names as examples
            if release_data.get("items"):
                examples = release_data["items"][:3]
                examples_str = ", ".join(examples)
                if len(release_data["items"]) > 3:
                    examples_str += f" (and {len(release_data['items']) - 3} more)"
                console.log(f"  Examples: {examples_str}")
    
    console.log(f"[bold green]Total databases: {total_databases}[/bold green]")
    
    console.log("\n[bold]Usage examples:[/bold]")
    for mod, mod_data in config.items():
        for release in mod_data.keys():
            console.log(f"python tests/UI/test_ui.py -m {mod} -t {release} -s 3 -c tests/UI/config.json")


def main():
    """Main function."""
    try:
        config = generate_config()
        
        if config:
            save_config(config)
            print_summary(config)
            console.log("[bold green]🎉 UI configuration generated successfully![/bold green]")
        else:
            console.log("[red]❌ Failed to generate configuration[/red]")
            
    except Exception as e:
        console.log(f"[red]Error: {str(e)}[/red]")
        raise


if __name__ == "__main__":
    main()