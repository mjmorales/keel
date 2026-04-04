"""Keel CLI entry point."""

import click

from keel_cli.check import check
from keel_cli.audit import audit
from keel_cli.map_cmd import map_cmd
from keel_cli.tree import tree
from keel_cli.status import status
from keel_cli.decisions import decisions
from keel_cli.decide import decide
from keel_cli.install import install_skill


@click.group()
@click.version_option(package_name="keel-cli")
@click.option("--project", "-p", default=".", help="Project root directory.")
@click.pass_context
def cli(ctx, project):
    """Keel — architectural contract enforcement for LLM-driven codebases."""
    ctx.ensure_object(dict)
    ctx.obj["project"] = project


cli.add_command(check)
cli.add_command(audit)
cli.add_command(map_cmd, name="map")
cli.add_command(tree)
cli.add_command(status)
cli.add_command(decisions)
cli.add_command(decide)
cli.add_command(install_skill)
