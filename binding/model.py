"""Shared binding model types for LVGL code generation."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GenerationResult:
    """State produced by binding generation, used for metadata export."""

    module_name: str
    module_prefix: str
    obj_names: List[str]
    obj_metadata: Dict[str, Any]
    func_metadata: Dict[str, Any]
    module_funcs: List[Any]
    enums: Dict[str, Any]
    enum_referenced: Dict[str, Any]
    generated_structs: Dict[str, Any]
    struct_aliases: Dict[str, Any]
    generated_globals: List[str]
    int_constants: List[str]
    headers: List[str] = field(default_factory=list)
    pp_cmd: str = ""
    cmd_line: str = ""
