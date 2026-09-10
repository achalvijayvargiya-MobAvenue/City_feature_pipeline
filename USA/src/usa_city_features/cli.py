import click
import os
from .config.loader import load_config

@click.group()
def main():
    """USA City Features Pipeline CLI"""
    pass

@main.command()
@click.option('--config', default='configs', help='Path to configs directory')
def download(config):
    """Download source datasets"""
    cfg = load_config(config)
    click.echo("Downloading sources...")
    # TODO: Implement download logic

@main.command()
@click.option('--config', default='configs', help='Path to configs directory')
def build_geography(config):
    """Build geography mappings"""
    cfg = load_config(config)
    click.echo("Building geography...")
    # TODO: Implement geography building

@main.command()
@click.option('--config', default='configs', help='Path to configs directory')
def build_features(config):
    """Build derived features"""
    cfg = load_config(config)
    click.echo("Building features...")
    # TODO: Implement feature building

@main.command()
@click.option('--config', default='configs', help='Path to configs directory')
def validate(config):
    """Validate final dataset"""
    cfg = load_config(config)
    click.echo("Validating dataset...")
    # TODO: Implement validation

@main.command()
@click.option('--config', default='configs', help='Path to configs directory')
@click.option('--output', default='data/processed/usa_city_features.csv', help='Output path')
def export(config, output):
    """Export final dataset"""
    cfg = load_config(config)
    click.echo(f"Exporting to {output}...")
    # TODO: Implement export

@main.command()
@click.option('--config', default='configs', help='Path to configs directory')
@click.option('--offline', is_flag=True, help='Run in offline mode')
def run(config, offline):
    """Run full pipeline"""
    cfg = load_config(config)
    click.echo(f"Running pipeline (offline={offline})...")
    # TODO: Implement full run

@main.command()
@click.option('--zcta', required=True, help='ZCTA to inspect')
def inspect(zcta):
    """Inspect a single ZCTA"""
    click.echo(f"Inspecting ZCTA: {zcta}")
    # TODO: Implement inspection

if __name__ == '__main__':
    main()
