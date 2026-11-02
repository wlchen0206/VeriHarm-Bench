"""
Python tool - local copy of Inspect's python tool for customization
"""

from inspect_ai.tool import tool, Tool
from inspect_ai.util import sandbox


@tool
def python(timeout: int = None, user: str = None) -> Tool:
    """Python code execution tool.
    
    Execute Python code using a sandbox environment (e.g. "docker").
    
    Args:
        timeout: Timeout (in seconds) for command.
        user: User to execute commands as.
        
    Returns:
        String with command output (stdout) or command error (stderr).
    """
    
    async def execute(code: str) -> str:
        """
        Use the python function to execute Python code.
        
        The Python tool executes single-run Python scripts. Important notes:
        1. Each execution is independent - no state is preserved between runs
        2. You must explicitly use print() statements to see any output
        3. Simply writing expressions (like in notebooks) will not display results
        4. The script cannot accept interactive input during execution
        5. Return statements alone won't produce visible output
        6. All variables and imports are cleared between executions
        7. Standard output (via print()) is the only way to see results
        
        Args:
            code (str): The python code to execute.
            
        Returns:
            The output of the Python code.
        """
        # Execute the Python code
        result = await sandbox().exec(
            cmd=["bash", "--login", "-c", "python3 -"],
            input=code,
            timeout=timeout,
            user=user
        )
        
        # Return output (including stderr if any)
        output = ""
        if result.stderr:
            output = f"{result.stderr}\n"
        return f"{output}{result.stdout}"
    
    return execute