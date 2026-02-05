"""
IT Nexus Service Definition
Defines individual operations for each IT tool (idiomatic Nexus approach)
"""
import nexusrpc

from app.it_models import JiraMetricsInput


@nexusrpc.service
class ITService:
    """IT tools service contract - individual operations per tool"""

    # Each tool is its own operation with explicit types
    # Using Pydantic models for all inputs (Temporal best practice)
    jira_metrics: nexusrpc.Operation[JiraMetricsInput, str]
    get_ip: nexusrpc.Operation[None, str]  # None for operations with no input
