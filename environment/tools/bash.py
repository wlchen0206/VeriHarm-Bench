"""
Bash tool - local copy of Inspect's bash tool for customization
"""

from inspect_ai.tool import tool, Tool
from inspect_ai.util import sandbox


@tool
def bash(timeout: int = None, user: str = None) -> Tool:
    """Bash shell command execution tool.
    
    Execute bash shell commands using a sandbox environment (e.g. "docker").
    
    Args:
        timeout: Timeout (in seconds) for command.
        user: User to execute commands as.
        
    Returns:
        String with command output (stdout) or command error (stderr).
    """
    
    async def execute(cmd: str) -> str:
        """
        Use this function to execute bash commands.
        
        Args:
            cmd (str): The bash command to execute.
            
        Returns:
            The output of the command.
        """
        # Execute the command
        result = await sandbox().exec(
            cmd=["bash", "--login", "-c", cmd],
            timeout=timeout,
            user=user
        )
        
        # Return output (including stderr if any)
        output = ""
        if result.stderr:
            output = f"{result.stderr}\n"
        return f"{output}{result.stdout}"
    
    return execute