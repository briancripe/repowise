"""VS Code setup integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repowise.cli.agent_targets.targets import vscode as vscode_target
from repowise.cli.editor_setup import EditorSetupOptions


class VSCodeSetup:
    """Project-local VS Code setup integration.

    Writes the workspace MCP server config (.vscode/mcp.json) and recommends the
    repowise extension (.vscode/extensions.json). Both are repo-shared files, so
    they use the bare ``repowise`` command like the committed ``.mcp.json``.
    """

    #: Read from the descriptor rather than restated, so the ids have one home.
    integration_id = vscode_target.ID
    project_file_id = vscode_target.PROJECT_FILE_ID

    def write_project_files(
        self,
        console_obj: Any,
        repo_path: Path,
        options: EditorSetupOptions,
    ) -> list[Path]:
        if self.project_file_id in options.disabled_project_files:
            persist_vscode_disabled(repo_path)
            return []
        return _write_vscode_files(console_obj, repo_path)

    def register_client(self, console_obj: Any, repo_path: Path) -> None:
        """VS Code reads the workspace .vscode/mcp.json; no user-level setup needed."""

        return None

    def refresh_project_files(
        self,
        console_obj: Any,
        repo_path: Path,
        options: EditorSetupOptions,
    ) -> None:
        if self.project_file_id in options.disabled_project_files:
            return
        if not _vscode_enabled(repo_path):
            return
        _write_vscode_files(console_obj, repo_path)


def _vscode_enabled(repo_path: Path) -> bool:
    from repowise.cli.helpers import load_config

    cfg = load_config(repo_path)
    return bool(cfg.get("editor_files", {}).get("vscode", True))


def persist_vscode_disabled(repo_path: Path) -> None:
    """Persist the opt-out so 'repowise update' doesn't resurrect .vscode/*.

    Public because ``init``'s worktree-seed path returns early, before the
    editor-setup pass that would otherwise record this, and has to persist the
    opt-out itself before delegating to ``update``.
    """

    from repowise.cli.helpers import load_config

    cfg = load_config(repo_path)
    ef_cfg = dict(cfg.get("editor_files", {}))
    ef_cfg["vscode"] = False
    cfg["editor_files"] = ef_cfg
    try:
        import yaml  # type: ignore[import-untyped]

        cfg_path = repo_path / ".repowise" / "config.yaml"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(
            yaml.dump(cfg, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
    except ImportError:
        pass


def _write_vscode_files(console_obj: Any, repo_path: Path) -> list[Path]:
    """Write or merge the managed .vscode files, skipping any JSONC file safely.

    Returns the paths actually written. A file we declined to touch is not in
    the list, which is what keeps the end-of-run manifest a record of what
    happened rather than a restatement of what we intended.
    """

    from repowise.cli.mcp_config import (
        save_vscode_extensions_config,
        save_vscode_mcp_config,
    )
    from repowise.cli.ui.brand import OK, WARN

    written: list[Path] = []
    try:
        mcp_path = save_vscode_mcp_config(repo_path)
        console_obj.print(f"  [{OK}]✓[/] VS Code MCP configured ({mcp_path})")
        written.append(Path(mcp_path))
    except ValueError:
        console_obj.print(
            f"  [{WARN}].vscode/mcp.json left unchanged (not valid JSON; it may contain "
            'comments). Add a "repowise" server under "servers" manually.[/]'
        )

    try:
        ext_path = save_vscode_extensions_config(repo_path)
        console_obj.print(f"  [{OK}]✓[/] VS Code extension recommended ({ext_path})")
        written.append(Path(ext_path))
    except ValueError:
        console_obj.print(
            f"  [{WARN}].vscode/extensions.json left unchanged (not valid JSON; it may "
            'contain comments). Add "repowise-dev.repowise" to "recommendations" '
            "manually.[/]"
        )
    return written
