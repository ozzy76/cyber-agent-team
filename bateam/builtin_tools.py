"""Built-in file and execute tools for BATeam agents.

Exposes ReadFile, WriteFile, EditFile, and Execute as ADK tools. All file
operations are confined to a workspace root (env: ``BATEAM_WORKSPACE``,
default: current working directory) so an agent cannot touch host paths
outside the project tree.

Disable the entire set with ``BATEAM_FILE_TOOLS=disabled`` (e.g. when running
in a managed prod environment that should not exec or write to the host FS).
"""

from __future__ import annotations

import os
import pathlib
from typing import Any

from google.adk.tools import BaseTool, FunctionTool
from google.adk.tools.bash_tool import ExecuteBashTool

from bateam.artifact_tools import list_artifacts, read_artifact


def _workspace_root() -> pathlib.Path:
    return pathlib.Path(os.getenv("BATEAM_WORKSPACE", os.getcwd())).resolve()


def _resolve_within_workspace(path: str) -> pathlib.Path:
    p = pathlib.Path(path).expanduser()
    if not p.is_absolute():
        p = _workspace_root() / p
    p = p.resolve()
    root = _workspace_root()
    if not (p == root or root in p.parents):
        raise ValueError(f"Path '{p}' is outside the workspace '{root}'.")
    return p


def read_file(path: str) -> dict[str, Any]:
    """Read an existing UTF-8 text file from the agent workspace.

    Use when the user asks the agent to look at a file that already exists,
    or when a SKILL.md instructs the agent to consult a workspace file.

    Args:
        path: Path to the file. Relative paths resolve under the workspace
            root; absolute paths must lie inside the workspace.

    Returns:
        ``{"path": "...", "content": "..."}`` on success, or ``{"error": "..."}``.
    """
    try:
        p = _resolve_within_workspace(path)
    except ValueError as e:
        return {"error": str(e)}
    try:
        return {"path": str(p), "content": p.read_text(encoding="utf-8")}
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except IsADirectoryError:
        return {"error": f"Path is a directory, not a file: {path}"}
    except UnicodeDecodeError:
        return {"error": f"File is not UTF-8 text: {path}"}
    except OSError as e:
        return {"error": f"OS error reading {path}: {e}"}


def write_file(path: str, content: str) -> dict[str, Any]:
    """Create a new UTF-8 text file, or overwrite an existing one.

    Use when the user asks the agent to produce a deliverable on disk
    (a draft, a report, a brief). Parent directories are created as needed.

    Args:
        path: Destination path, relative to the workspace root or absolute
            inside the workspace.
        content: Full file content. Existing content is replaced.

    Returns:
        ``{"path": "...", "bytes_written": N}`` on success, or ``{"error": "..."}``.
    """
    try:
        p = _resolve_within_workspace(path)
    except ValueError as e:
        return {"error": str(e)}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": str(p), "bytes_written": len(content)}
    except OSError as e:
        return {"error": f"OS error writing {path}: {e}"}


def edit_file(path: str, old_string: str, new_string: str) -> dict[str, Any]:
    """Replace one exact occurrence of ``old_string`` with ``new_string``.

    Use for in-place edits to an existing file. Fails if ``old_string`` does
    not appear, or appears more than once — narrow the match in that case.

    Args:
        path: Path of the file to edit (workspace-relative or workspace-internal absolute).
        old_string: Text to find. Must occur exactly once.
        new_string: Replacement text.

    Returns:
        ``{"path": "...", "edits": 1}`` on success, or ``{"error": "..."}``.
    """
    try:
        p = _resolve_within_workspace(path)
    except ValueError as e:
        return {"error": str(e)}
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except UnicodeDecodeError:
        return {"error": f"File is not UTF-8 text: {path}"}
    except OSError as e:
        return {"error": f"OS error reading {path}: {e}"}

    occurrences = text.count(old_string)
    if occurrences == 0:
        return {"error": f"old_string not found in {path}"}
    if occurrences > 1:
        return {
            "error": (
                f"old_string is not unique in {path} ({occurrences} matches);"
                " expand the match with surrounding context."
            )
        }
    try:
        p.write_text(text.replace(old_string, new_string, 1), encoding="utf-8")
    except OSError as e:
        return {"error": f"OS error writing {path}: {e}"}
    return {"path": str(p), "edits": 1}


def make_builtin_tools() -> list[BaseTool]:
    """Return the read/write/edit/execute tools every BATeam agent receives.

    Returns an empty list when ``BATEAM_FILE_TOOLS=disabled``, so a managed
    deployment can opt out without touching the agent definitions.
    """
    if os.getenv("BATEAM_FILE_TOOLS", "").lower() == "disabled":
        return []
    return [
        FunctionTool(read_file),
        FunctionTool(write_file),
        FunctionTool(edit_file),
        FunctionTool(list_artifacts),
        FunctionTool(read_artifact),
        ExecuteBashTool(workspace=_workspace_root()),
    ]
