"""MCP server exposing gams-tools to Copilot (VS Code agent mode, cloud agent, Copilot CLI).

All tools are read-only with respect to the repository: GAMS writes only into the
scratch folder `.gams-agent/`, runs use execMode and the limits from `.gams-agent.yaml`,
and only allowlisted test cases can be executed.
"""

from __future__ import annotations

from typing import Optional

from . import docs, service
from .config import Config, load_config


def serve(config_path: Optional[str] = None) -> None:
    try:  # MCP Python SDK 2.x
        from mcp.server.mcpserver import MCPServer as Server
    except ImportError:
        try:  # MCP Python SDK 1.x
            from mcp.server.fastmcp import FastMCP as Server
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise SystemExit("the MCP server needs the 'mcp' extra: pip install 'gams-tools[mcp]'") from exc
    try:
        from mcp.types import ToolAnnotations

        read_only = {"annotations": ToolAnnotations(readOnlyHint=True, openWorldHint=False)}
    except ImportError:  # pragma: no cover
        read_only = {}

    server = Server(
        "gams-tools",
        instructions=(
            "Tools backed by the pinned GAMS installation. Prefer these over recalling GAMS/CPLEX facts: "
            "compile after every edit to GAMS code, validate solver options before recommending them, "
            "and run only allowlisted test cases. Cite tool output as evidence in reviews."
        ),
    )

    def cfg() -> Config:
        return load_config(config_path)

    @server.tool(**read_only)
    def gams_environment() -> dict:
        """Installed vs. pinned GAMS version, exec mode, entry points and allowlisted test cases."""
        return service.environment(cfg())

    @server.tool(**read_only)
    def gams_compile(entry: str, defines: Optional[dict[str, str]] = None) -> dict:
        """Compile an entry point listed in .gams-agent.yaml (GAMS action=c).

        Returns structured compilation errors with the file and line local to the file
        that contains the error (include files resolved), error code, message and a hint.
        """
        return service.compile_entry(cfg(), entry, defines)

    @server.tool(**read_only)
    def gams_run(case: str) -> dict:
        """Run an allowlisted test case from .gams-agent.yaml with enforced limits.

        Returns solve summaries (solver/model status, objective), execution errors, the
        conflict set if CPLEX's conflict refiner ran, a CPLEX log digest, coefficient-range
        warnings and, when a baseline GDX is configured, the differences from it.
        """
        return service.run_case(cfg(), case)

    @server.tool(**read_only)
    def listing_summary(path: str) -> dict:
        """Summarize a GAMS listing (.lst) file in the repository or the .gams-agent scratch folder."""
        return service.listing_summary(cfg(), path)

    @server.tool(**read_only)
    def log_summary(path: str) -> dict:
        """Summarize a GAMS/CPLEX log: model size, coefficient ranges, option-file handling,
        solver statuses, MIP progress (root bound, incumbents, gap), conflict set and errors."""
        return service.log_summary(cfg(), path)

    @server.tool(**read_only)
    def gdx_inspect(path: str, symbol: Optional[str] = None, limit: int = 20) -> dict:
        """List the symbols in a GDX file, or show the domains, fields and a sample of one symbol."""
        return service.gdx_inspect(cfg(), path, symbol, limit)

    @server.tool(**read_only)
    def gdx_diff(a: str, b: str, rel: float = 1e-6, abs: float = 1e-6, symbols: Optional[list[str]] = None) -> dict:
        """Compare two GDX files with relative/absolute tolerances. Missing records count as
        GAMS defaults (zero). Reports differing symbols and the largest deviations."""
        return service.gdx_diff(cfg(), a, b, rel, abs, symbols)

    @server.tool(**read_only)
    def symbol_xref(entry: str, symbol: Optional[str] = None) -> dict:
        """Cross-reference an entry point: unused symbols, parameters used but never assigned,
        equations defined but not in any solved model, symbols without explanatory text,
        and where a given symbol is declared, defined, assigned and used."""
        return service.symbol_xref(cfg(), entry, symbol)

    @server.tool(**read_only)
    def option_validate(path: Optional[str] = None, text: Optional[str] = None, solver: str = "cplex") -> dict:
        """Validate a solver option file (or option text) against the option definitions of the
        installed GAMS release: unknown names, deprecated synonyms, internal options, bad values."""
        return service.option_validate(cfg(), solver, path=path, text=text)

    @server.tool(**read_only)
    def option_info(name: str, solver: str = "cplex") -> dict:
        """Describe a solver option as the installed GAMS release defines it: type, default, range,
        allowed values, deprecation. Use before recommending any option."""
        return service.option_info(cfg(), name, solver)

    @server.tool(**read_only)
    def error_lookup(code: int) -> dict:
        """Explain a GAMS compilation/execution error code using the installed error catalog."""
        return service.error_lookup(cfg(), code)

    @server.tool(**read_only)
    def docs_search(query: str, scope: Optional[str] = None) -> dict:
        """Search the version-pinned documentation folders configured in .gams-agent.yaml."""
        return docs.search(cfg(), query, scope)

    server.run()
