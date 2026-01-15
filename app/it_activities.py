"""
IT Activities - Tools for IT namespace
Simple implementations, called via Nexus from orchestrator
"""
import logging

from temporalio import activity

logger = logging.getLogger(__name__)


class ITActivities:
    """IT department activities"""

    @activity.defn(name="jira_metrics")
    async def jira_metrics(self, project: str) -> str:
        """Get JIRA project metrics"""
        logger.info(f"Getting JIRA metrics for project: {project}")

        # Mock implementation
        return f"JIRA metrics for {project}: 23 open issues, 45 closed, 68 total"

    @activity.defn(name="get_ip")
    async def get_ip(self) -> str:
        """Get current IP address"""
        logger.info("Getting IP address")

        # Mock implementation
        return "Current IP address: 192.168.1.100"
