"""
Text editor tool - local implementation with undo support
"""

from inspect_ai.tool import tool, Tool
from inspect_ai.util import sandbox
from typing import Literal, Optional, List


# Global edit history for undo functionality
# In production, this would be stored per-sandbox/session
_edit_history = {}


@tool
def text_editor(timeout: int = 180, user: str = None) -> Tool:
    """Custom editing tool for viewing, creating and editing files.
    
    Perform text editor operations using a sandbox environment (e.g. "docker").
    
    Args:
        timeout: Timeout (in seconds) for command. Defaults to 180 if not provided.
        user: User to execute commands as.
        
    Returns:
        String with command output (stdout) or command error (stderr).
    """
    
    async def execute(
        command: Literal["view", "create", "str_replace", "insert", "undo_edit"],
        path: str,
        file_text: Optional[str] = None,
        insert_line: Optional[int] = None,
        new_str: Optional[str] = None,
        old_str: Optional[str] = None,
        view_range: Optional[List[int]] = None,
    ) -> str:
        """Use this function to execute text editing commands.
        
        Args:
            command (Literal): The command to execute.
            path (str): Absolute path to file or directory, e.g. `/repo/file.py` or `/repo`.
            file_text (Optional[str]): Required parameter of `create` command, with the content of the file to be created.
            insert_line (Optional[int]): Required parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`.
            new_str (Optional[str]): Optional parameter of `str_replace` command containing the new string (if not given, no string will be added). Required parameter of `insert` command containing the string to insert.
            old_str (Optional[str]): Required parameter of `str_replace` command containing the string in `path` to replace.
            view_range (Optional[List[int]]): Optional parameter of `view` command when `path` points to a file. If none is given, the full file is shown. If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.
            
        Returns:
            The output of the command.
        """
        global _edit_history  # Declare at the beginning so we can modify it throughout
        sb = sandbox()
        
        try:
            if command == "view":
                # Read the file
                result = await sb.exec(
                    cmd=["cat", path],
                    timeout=timeout,
                    user=user
                )
                
                if result.returncode != 0:
                    return f"Error reading file: {result.stderr}"
                
                content = result.stdout
                
                # Apply view range if specified
                if view_range:
                    lines = content.split('\n')
                    start = max(0, view_range[0] - 1)  # Convert to 0-indexed
                    end = view_range[1] if view_range[1] != -1 else len(lines)
                    selected_lines = lines[start:end]
                    
                    # Add line numbers
                    numbered = []
                    for i, line in enumerate(selected_lines, start=start+1):
                        numbered.append(f"{i:4d} | {line}")
                    return '\n'.join(numbered)
                
                # Return full content with line numbers
                lines = content.split('\n')
                numbered = []
                for i, line in enumerate(lines, start=1):
                    numbered.append(f"{i:4d} | {line}")
                return '\n'.join(numbered)
            
            elif command == "create":
                if not file_text:
                    return "Error: file_text is required for create command"
                
                # Save current state for undo (None means file didn't exist)
                if path not in _edit_history:
                    _edit_history[path] = []
                _edit_history[path].append(None)
                
                # Create the file
                await sb.write_file(path, file_text)
                return f"File created: {path}"
            
            elif command == "str_replace":
                if not old_str:
                    return "Error: old_str is required for str_replace command"
                
                # Read the current file
                result = await sb.exec(
                    cmd=["cat", path],
                    timeout=timeout,
                    user=user
                )
                
                if result.returncode != 0:
                    return f"Error reading file: {result.stderr}"
                
                content = result.stdout
                
                # Check if old_str exists
                if old_str not in content:
                    return f"Error: old_str not found in {path}"
                
                # Save current state for undo
                if path not in _edit_history:
                    _edit_history[path] = []
                _edit_history[path].append(content)
                
                # Replace and write back
                new_content = content.replace(old_str, new_str if new_str else "")
                await sb.write_file(path, new_content)
                
                count = content.count(old_str)
                return f"Replaced {count} occurrence(s) in {path}"
            
            elif command == "insert":
                if insert_line is None or new_str is None:
                    return "Error: insert_line and new_str are required for insert command"
                
                # Read the current file
                result = await sb.exec(
                    cmd=["cat", path],
                    timeout=timeout,
                    user=user
                )
                
                if result.returncode != 0:
                    return f"Error reading file: {result.stderr}"
                
                content = result.stdout
                lines = content.split('\n')
                
                # Validate line number
                if insert_line < 0 or insert_line > len(lines):
                    return f"Error: insert_line {insert_line} out of range (file has {len(lines)} lines)"
                
                # Save current state for undo
                if path not in _edit_history:
                    _edit_history[path] = []
                _edit_history[path].append(content)
                
                # Insert the new line after insert_line
                lines.insert(insert_line, new_str)
                new_content = '\n'.join(lines)
                
                # Write back
                await sb.write_file(path, new_content)
                return f"Inserted at line {insert_line} in {path}"
            
            elif command == "undo_edit":
                # Check if we have edit history for this file
                if path not in _edit_history or not _edit_history[path]:
                    return f"No edit history for {path}"
                
                # Get the previous state
                previous_content = _edit_history[path].pop()
                
                if previous_content is None:
                    # File didn't exist before, so delete it
                    result = await sb.exec(
                        cmd=["rm", path],
                        timeout=timeout,
                        user=user
                    )
                    if result.returncode != 0:
                        return f"Error deleting file: {result.stderr}"
                    return f"File deleted (undone creation): {path}"
                else:
                    # Restore previous content
                    await sb.write_file(path, previous_content)
                    return f"Undone last edit to {path}"
            
            else:
                return f"Error: Unknown command '{command}'"
                
        except Exception as e:
            return f"Error executing {command}: {str(e)}"
    
    return execute