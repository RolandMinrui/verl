from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from mcp.server.fastmcp import FastMCP
import os
import base64
import mimetypes
import glob
import json
from datetime import datetime

# Section 1: Schema
class FileEntry(BaseModel):
    """Represents a file or directory entry."""
    name: str = Field(..., description="Name of the file or directory")
    type: str = Field(..., description="Type: 'file' or 'directory'")
    size: int = Field(..., ge=0, description="Size in bytes")

class FileInfo(BaseModel):
    """Detailed file metadata."""
    path: str = Field(..., description="Full path to file/directory")
    type: str = Field(..., description="Type: 'file' or 'directory'")
    size: int = Field(..., ge=0, description="Size in bytes")
    created_time: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", description="Creation timestamp ISO 8601")
    modified_time: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", description="Modification timestamp ISO 8601")
    access_time: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", description="Access timestamp ISO 8601")
    permissions: str = Field(..., description="File permissions in symbolic notation")

class FileResult(BaseModel):
    """Result for individual file read operation."""
    path: str = Field(..., description="File path")
    content: Optional[str] = Field(default=None, description="File content if successful")
    error: Optional[str] = Field(default=None, description="Error message if failed")

class TreeNode(BaseModel):
    """Node in directory tree structure."""
    name: str = Field(..., description="Name of file/directory")
    type: str = Field(..., description="Type: 'file' or 'directory'")
    children: Optional[List['TreeNode']] = Field(default=None, description="Nested entries for directories")

class FilesystemScenario(BaseModel):
    """Main scenario model for filesystem operations."""
    allowed_extensions: List[str] = Field(default=[".txt", ".md", ".py", ".json", ".csv", ".xml", ".html", ".css", ".js", ".ts"], description="Allowed file extensions for text operations")
    max_file_size: int = Field(default=10485760, ge=0, description="Maximum file size in bytes (10MB)")
    binary_extensions: List[str] = Field(default=[".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".mp3", ".wav", ".mp4", ".avi", ".pdf", ".zip"], description="Binary file extensions for media operations")
    exclude_patterns_default: List[str] = Field(default=["*.pyc", "__pycache__", ".git", ".DS_Store", "node_modules"], description="Default exclusion patterns")
    mime_types_map: Dict[str, str] = Field(default={
        ".txt": "text/plain", ".md": "text/markdown", ".py": "text/x-python", ".json": "application/json",
        ".csv": "text/csv", ".xml": "application/xml", ".html": "text/html", ".css": "text/css",
        ".js": "application/javascript", ".ts": "application/typescript", ".png": "image/png",
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".bmp": "image/bmp",
        ".ico": "image/x-icon", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".mp4": "video/mp4",
        ".avi": "video/x-msvideo", ".pdf": "application/pdf", ".zip": "application/zip"
    }, description="MIME type mapping by file extension")

Scenario_Schema = [FileEntry, FileInfo, FileResult, TreeNode, FilesystemScenario]

# Section 2: Class
class FilesystemAPI:
    def __init__(self):
        """Initialize filesystem API with default settings."""
        self.allowed_extensions: List[str] = []
        self.max_file_size: int = 0
        self.binary_extensions: List[str] = []
        self.exclude_patterns_default: List[str] = []
        self.mime_types_map: Dict[str, str] = {}

    def load_scenario(self, scenario: dict) -> None:
        """Load scenario configuration into the API instance."""
        model = FilesystemScenario(**scenario)
        self.allowed_extensions = model.allowed_extensions
        self.max_file_size = model.max_file_size
        self.binary_extensions = model.binary_extensions
        self.exclude_patterns_default = model.exclude_patterns_default
        self.mime_types_map = model.mime_types_map

    def save_scenario(self) -> dict:
        """Save current configuration as scenario dictionary."""
        return {
            "allowed_extensions": self.allowed_extensions,
            "max_file_size": self.max_file_size,
            "binary_extensions": self.binary_extensions,
            "exclude_patterns_default": self.exclude_patterns_default,
            "mime_types_map": self.mime_types_map
        }

    def read_text_file(self, path: str, head: Optional[int] = None, tail: Optional[int] = None) -> dict:
        """Read text file content with optional line filtering."""
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if head is not None:
            lines = lines[:head]
        elif tail is not None:
            lines = lines[-tail:]
        
        return {"file_content": ''.join(lines)}

    def read_media_file(self, path: str) -> dict:
        """Read binary media file and return base64 encoded data."""
        with open(path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
        
        mime_type = self._get_mime_type(path)
        return {"data": data, "mime_type": mime_type}

    def read_multiple_files(self, paths: List[str]) -> dict:
        """Read multiple files and return results with errors."""
        results = []
        for path in paths:
            try:
                if self._is_binary_file(path):
                    result = self.read_media_file(path)
                    content = f"[Binary file: {result['mime_type']}, {len(result['data'])} bytes]"
                else:
                    result = self.read_text_file(path)
                    content = result['file_content']
                results.append({"path": path, "content": content, "error": None})
            except Exception as e:
                results.append({"path": path, "content": None, "error": str(e)})
        return {"results": results}

    def write_file(self, path: str, content: str) -> dict:
        """Create or overwrite file with specified content."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"path": path, "success": "File written successfully"}

    def edit_file(self, path: str, oldText: Optional[str] = None, newText: Optional[str] = None, dryRun: bool = False) -> dict:
        """Edit file with pattern matching and optional dry run."""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        matches = []
        
        if oldText is not None and newText is not None:
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if oldText in line:
                    matches.append({"line_number": i, "context": line.strip()})
            
            if not dryRun:
                content = content.replace(oldText, newText)
        
        if not dryRun and content != original_content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        import difflib
        diff = '\n'.join(difflib.unified_diff(
            original_content.split('\n'),
            content.split('\n'),
            fromfile=path,
            tofile=path,
            lineterm=''
        ))
        
        return {"diff": diff, "matches": matches, "applied": not dryRun and content != original_content}

    def create_directory(self, path: str) -> dict:
        """Create directory or ensure it exists."""
        created = not os.path.exists(path)
        os.makedirs(path, exist_ok=True)
        return {"path": path, "created": created}

    def list_directory(self, path: str) -> dict:
        """List directory contents with metadata."""
        entries = []
        for name in os.listdir(path):
            full_path = os.path.join(path, name)
            stat = os.stat(full_path)
            entry_type = "DIR" if os.path.isdir(full_path) else "FILE"
            entries.append({
                "name": name,
                "type": entry_type,
                "size": stat.st_size
            })
        return {"entries": entries}

    def move_file(self, source: str, destination: str) -> dict:
        """Move or rename file/directory."""
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        os.rename(source, destination)
        return {"source": source, "destination": destination, "success": True}

    def search_files(self, path: str, pattern: str, excludePatterns: Optional[List[str]] = None) -> dict:
        """Search for files matching glob pattern with exclusions."""
        if excludePatterns is None:
            excludePatterns = self.exclude_patterns_default
        
        matches = []
        for root, dirs, files in os.walk(path):
            for name in files + dirs:
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, path)
                
                if glob.fnmatch.fnmatch(rel_path, pattern):
                    excluded = False
                    for exclude_pattern in excludePatterns:
                        if glob.fnmatch.fnmatch(rel_path, exclude_pattern):
                            excluded = True
                            break
                    
                    if not excluded:
                        matches.append(full_path)
        
        return {"matches": matches}

    def directory_tree(self, path: str, excludePatterns: Optional[List[str]] = None) -> dict:
        """Generate recursive directory tree structure."""
        if excludePatterns is None:
            excludePatterns = self.exclude_patterns_default
        
        def build_tree(current_path: str) -> List[dict]:
            tree = []
            try:
                for name in sorted(os.listdir(current_path)):
                    full_path = os.path.join(current_path, name)
                    rel_path = os.path.relpath(full_path, path)
                    
                    excluded = False
                    for pattern in excludePatterns:
                        if glob.fnmatch.fnmatch(rel_path, pattern):
                            excluded = True
                            break
                    
                    if excluded:
                        continue
                    
                    if os.path.isdir(full_path):
                        node = {
                            "name": name,
                            "type": "directory",
                            "children": build_tree(full_path)
                        }
                    else:
                        node = {
                            "name": name,
                            "type": "file"
                        }
                    tree.append(node)
            except PermissionError:
                pass
            return tree
        
        return {"tree": build_tree(path)}

    def get_file_info(self, path: str) -> dict:
        """Get detailed file/directory metadata."""
        stat = os.stat(path)
        mode = stat.st_mode
        permissions = self._get_permissions(mode)
        
        return {
            "path": path,
            "type": "directory" if os.path.isdir(path) else "file",
            "size": stat.st_size,
            "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "access_time": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "permissions": permissions
        }

    def _get_mime_type(self, path: str) -> str:
        """Get MIME type for file path."""
        ext = os.path.splitext(path)[1].lower()
        return self.mime_types_map.get(ext, "application/octet-stream")

    def _is_binary_file(self, path: str) -> bool:
        """Check if file should be treated as binary."""
        ext = os.path.splitext(path)[1].lower()
        return ext in self.binary_extensions

    def _get_permissions(self, mode: int) -> str:
        """Convert file mode to symbolic permissions string."""
        perms = []
        perms.append('r' if mode & 0o400 else '-')
        perms.append('w' if mode & 0o200 else '-')
        perms.append('x' if mode & 0o100 else '-')
        perms.append('r' if mode & 0o040 else '-')
        perms.append('w' if mode & 0o020 else '-')
        perms.append('x' if mode & 0o010 else '-')
        perms.append('r' if mode & 0o004 else '-')
        perms.append('w' if mode & 0o002 else '-')
        perms.append('x' if mode & 0o001 else '-')
        return ''.join(perms)

# Section 3: MCP Tools
mcp = FastMCP(name="FilesystemAPI")
api = FilesystemAPI()

@mcp.tool()
def load_scenario(scenario: dict) -> str:
    """Load filesystem configuration scenario.
    
    Args:
        scenario (dict): Configuration dictionary matching FilesystemScenario schema.
    
    Returns:
        success_message (str): Success confirmation.
    """
    try:
        if not isinstance(scenario, dict):
            raise ValueError("Scenario must be a dictionary")
        api.load_scenario(scenario)
        return "Successfully loaded scenario"
    except Exception as e:
        raise e

@mcp.tool()
def save_scenario() -> dict:
    """Save current filesystem configuration.
    
    Returns:
        scenario (dict): Current configuration dictionary.
    """
    try:
        return api.save_scenario()
    except Exception as e:
        raise e

@mcp.tool()
def read_text_file(path: str, head: Optional[int] = None, tail: Optional[int] = None) -> dict:
    """Read text file with optional line filtering.
    
    Args:
        path (str): File path to read.
        head (int): [Optional] Number of lines from start.
        tail (int): [Optional] Number of lines from end.
    
    Returns:
        file_content (str): File contents as text.
    """
    try:
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")
        if head is not None and (not isinstance(head, int) or head < 0):
            raise ValueError("Head must be non-negative integer")
        if tail is not None and (not isinstance(tail, int) or tail < 0):
            raise ValueError("Tail must be non-negative integer")
        return api.read_text_file(path, head, tail)
    except Exception as e:
        raise e

@mcp.tool()
def read_media_file(path: str) -> dict:
    """Read binary media file as base64.
    
    Args:
        path (str): Media file path.
    
    Returns:
        data (str): Base64 encoded content.
        mime_type (str): MIME type of file.
    """
    try:
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")
        return api.read_media_file(path)
    except Exception as e:
        raise e

@mcp.tool()
def read_multiple_files(paths: List[str]) -> dict:
    """Read multiple files simultaneously.
    
    Args:
        paths (list): List of file paths to read.
    
    Returns:
        results (list): List of results with content or error for each file.
    """
    try:
        if not isinstance(paths, list):
            raise ValueError("Paths must be a list")
        return api.read_multiple_files(paths)
    except Exception as e:
        raise e

@mcp.tool()
def write_file(path: str, content: str) -> dict:
    """Write content to file.
    
    Args:
        path (str): Destination file path.
        content (str): Text content to write.
    
    Returns:
        path (str): File path where written.
        success (str): Success message.
    """
    try:
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")
        if content is None:
            raise ValueError("Content cannot be None")
        return api.write_file(path, content)
    except Exception as e:
        raise e

@mcp.tool()
def edit_file(path: str, oldText: Optional[str] = None, newText: Optional[str] = None, dryRun: bool = False) -> dict:
    """Edit file with pattern matching.
    
    Args:
        path (str): File path to edit.
        oldText (str): [Optional] Text pattern to search.
        newText (str): [Optional] Replacement text.
        dryRun (bool): [Optional] Preview changes without applying.
    
    Returns:
        diff (str): Unified diff of changes.
        matches (list): List of matches found.
        applied (bool): Whether changes were applied.
    """
    try:
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")
        return api.edit_file(path, oldText, newText, dryRun)
    except Exception as e:
        raise e

@mcp.tool()
def create_directory(path: str) -> dict:
    """Create directory.
    
    Args:
        path (str): Directory path to create.
    
    Returns:
        path (str): Created directory path.
        created (bool): Whether new directory was created.
    """
    try:
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")
        return api.create_directory(path)
    except Exception as e:
        raise e

@mcp.tool()
def list_directory(path: str) -> dict:
    """List directory contents.
    
    Args:
        path (str): Directory path to list.
    
    Returns:
        entries (list): List of directory entries with metadata.
    """
    try:
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")
        if not os.path.exists(path):
            raise ValueError(f"Directory {path} not found")
        return api.list_directory(path)
    except Exception as e:
        raise e

@mcp.tool()
def move_file(source: str, destination: str) -> dict:
    """Move or rename file/directory.
    
    Args:
        source (str): Source path.
        destination (str): Destination path.
    
    Returns:
        source (str): Original path.
        destination (str): New path.
        success (bool): Operation success status.
    """
    try:
        if not source or not isinstance(source, str):
            raise ValueError("Source must be a non-empty string")
        if not destination or not isinstance(destination, str):
            raise ValueError("Destination must be a non-empty string")
        if not os.path.exists(source):
            raise ValueError(f"Source {source} not found")
        return api.move_file(source, destination)
    except Exception as e:
        raise e

@mcp.tool()
def search_files(path: str, pattern: str, excludePatterns: Optional[List[str]] = None) -> dict:
    """Search files with glob pattern.
    
    Args:
        path (str): Search starting directory.
        pattern (str): Glob pattern to match.
        excludePatterns (list): [Optional] Patterns to exclude.
    
    Returns:
        matches (list): List of matching file paths.
    """
    try:
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")
        if not pattern or not isinstance(pattern, str):
            raise ValueError("Pattern must be a non-empty string")
        if not os.path.exists(path):
            raise ValueError(f"Directory {path} not found")
        return api.search_files(path, pattern, excludePatterns)
    except Exception as e:
        raise e

@mcp.tool()
def directory_tree(path: str, excludePatterns: Optional[List[str]] = None) -> dict:
    """Generate directory tree structure.
    
    Args:
        path (str): Root directory path.
        excludePatterns (list): [Optional] Patterns to exclude.
    
    Returns:
        tree (list): Hierarchical tree structure.
    """
    try:
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")
        if not os.path.exists(path):
            raise ValueError(f"Directory {path} not found")
        return api.directory_tree(path, excludePatterns)
    except Exception as e:
        raise e

@mcp.tool()
def get_file_info(path: str) -> dict:
    """Get detailed file metadata.
    
    Args:
        path (str): File/directory path.
    
    Returns:
        path (str): Inspected path.
        type (str): Entry type.
        size (int): Size in bytes.
        created_time (str): Creation timestamp.
        modified_time (str): Modification timestamp.
        access_time (str): Access timestamp.
        permissions (str): File permissions.
    """
    try:
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")
        if not os.path.exists(path):
            raise ValueError(f"Path {path} not found")
        return api.get_file_info(path)
    except Exception as e:
        raise e

# Section 4: Entry Point
if __name__ == "__main__":
    mcp.run()