"""
IT Nexus Service Definition
Defines the contract for IT tools service
"""
from typing import Any, Dict, List

import nexusrpc


@nexusrpc.service
class ITService:
    """IT tools service contract"""
    list_tools: nexusrpc.Operation[None, List[Dict[str, Any]]]
    execute_tool: nexusrpc.Operation[Dict[str, Any], Dict[str, Any]]
