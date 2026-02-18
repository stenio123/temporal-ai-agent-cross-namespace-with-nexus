"""
IT Nexus Service Definition
Defines individual operations for each IT tool (idiomatic Nexus approach)
"""
import nexusrpc

from app.it_models import GetIPInput, JiraMetricsInput


@nexusrpc.service
class ITService:
    """IT tools service contract - individual operations per tool"""

    # Each tool is its own operation with explicit types
    # Using Pydantic models for all inputs (Temporal best practice)
    jira_metrics: nexusrpc.Operation[JiraMetricsInput, str]  # (input, output)
    get_ip: nexusrpc.Operation[GetIPInput, str]  # (input, output)
