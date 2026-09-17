import click
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the root directory (one level up from USA)
env_path = Path(__file__).resolve().parents[3] / '.env'
load_dotenv(dotenv_path=env_path)

from .config.loader import load_config
from .orchestrator import PipelineOrchestrator
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
    orchestrator = PipelineOrchestrator(cfg)
    orchestrator.download()

@main.command()
@click.option('--config', default='configs', help='Path to configs directory')
def build_geography(config):
    """Build geography mappings"""
    cfg = load_config(config)
    click.echo("Building geography...")
    orchestrator = PipelineOrchestrator(cfg)
    orchestrator.build_geography()

@main.command()
@click.option('--config', default='configs', help='Path to configs directory')
def build_features(config):
    """Build derived features"""
    cfg = load_config(config)
    click.echo("Building features...")
    orchestrator = PipelineOrchestrator(cfg)
    orchestrator.build_features()

@main.command()
@click.option('--config', default='configs', help='Path to configs directory')
def validate(config):
    """Validate final dataset"""
    cfg = load_config(config)
    click.echo("Validating dataset...")
    orchestrator = PipelineOrchestrator(cfg)
    orchestrator.validate()

@main.command()
@click.option('--config', default='configs', help='Path to configs directory')
@click.option('--output', default='data/processed/usa_city_features.csv', help='Output path')
def export(config, output):
    """Export final dataset"""
    cfg = load_config(config)
    click.echo(f"Exporting to {output}...")
    orchestrator = PipelineOrchestrator(cfg)
    orchestrator.export(output)

@main.command()
@click.option('--config', default='configs', help='Path to configs directory')
@click.option('--offline', is_flag=True, help='Run in offline mode')
@click.option('--output', default='data/processed/usa_city_features.csv', help='Output path')
def run(config, offline, output):
    """Run full pipeline"""
    cfg = load_config(config)
    click.echo(f"Running pipeline (offline={offline})...")
    orchestrator = PipelineOrchestrator(cfg)
    orchestrator.run(offline=offline, output_path=output)

@main.command("split-completeness")
@click.option(
    "--input",
    "input_path",
    default="data/processed/usa_city_features_v2.csv",
    help="Input CSV to split",
)
@click.option(
    "--valid-output",
    default="data/processed/usa_city_features_valid.csv",
    help="Output path for complete/final records",
)
@click.option(
    "--invalid-output",
    default="data/processed/usa_city_features_invalid.csv",
    help="Output path for incomplete records needing enrichment",
)
def split_completeness(input_path, valid_output, invalid_output):
    """Split dataset into complete valid records vs incomplete enrichment backlog."""
    import json
    import pandas as pd
    from .validation.schema_validator import split_complete_records, generate_quality_report

    df = pd.read_csv(input_path)
    valid_df, invalid_df, summary = split_complete_records(df)

    Path(valid_output).parent.mkdir(parents=True, exist_ok=True)
    valid_df.to_csv(valid_output, index=False)
    invalid_df.to_csv(invalid_output, index=False)

    report_path = Path(valid_output).with_name("usa_city_features_completeness_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                **summary,
                "paths": {
                    "source": input_path,
                    "valid": valid_output,
                    "invalid": invalid_output,
                },
            },
            f,
            indent=2,
        )

    click.echo(
        f"Split complete: {summary['valid_complete_records']} valid, "
        f"{summary['invalid_incomplete_records']} invalid"
    )
    click.echo(f"Valid:   {valid_output}")
    click.echo(f"Invalid: {invalid_output}")
    click.echo(f"Report:  {report_path}")

@main.command()
@click.option('--zcta', required=True, help='ZCTA to inspect')
def inspect(zcta):
    """Inspect a single ZCTA"""
    click.echo(f"Inspecting ZCTA: {zcta}")
    # TODO: Implement inspection

if __name__ == '__main__':
    main()
