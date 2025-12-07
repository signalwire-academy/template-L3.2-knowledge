#!/usr/bin/env python3
"""Technical support agent with RAG capabilities.

Lab 3.2 Deliverable: Demonstrates knowledge management with search skill,
live data integration via DataMap, and ticket creation.
"""

import os
from datetime import datetime
from signalwire_agents import AgentBase, SwaigFunctionResult
from signalwire_agents.core.data_map import DataMap
from signalwire_agents.core.function_result import SwaigFunctionResult as DmResult


class SupportAgent(AgentBase):
    """Technical support agent with RAG and live data integration."""

    def __init__(self, kb_path: str = None):
        super().__init__(name="support-agent")

        self.prompt_add_section(
            "Role",
            "Technical support agent for ExampleSoft. "
            "Answer questions using the knowledge base. "
            "If information isn't in the knowledge base, say so."
        )

        self.prompt_add_section(
            "Instructions",
            bullets=[
                "Search the knowledge base before answering",
                "Cite sources when providing information",
                "Admit when you don't have information",
                "Offer to escalate complex issues",
                "Create tickets for unresolved problems"
            ]
        )

        self.add_language("English", "en-US", "rime.spore")

        # Add search skill with knowledge base (if available)
        if kb_path and os.path.exists(kb_path):
            self.add_skill(
                "search",
                {
                    "index_path": kb_path,
                    "count": 3,
                    "distance": 0.7
                }
            )

        self._setup_datamaps()
        self._setup_functions()

    def _setup_datamaps(self):
        """Configure DataMaps for live data queries."""

        # License status lookup
        check_license_dm = (
            DataMap("check_license")
            .description("Check customer license status by license key")
            .parameter("license_key", "string", "Customer's license key", required=True)
            .webhook(
                "GET",
                "https://api.example.com/licenses/${args.license_key}"
            )
            .output(DmResult(
                "License status: ${status}. Expires: ${expires}."
            ))
            .fallback_output(DmResult(
                "I couldn't find that license key. Please verify and try again."
            ))
        )
        self.register_swaig_function(check_license_dm.to_swaig_function())

        # Version check
        check_version_dm = (
            DataMap("check_version")
            .description("Check if a software version is current")
            .parameter("current_version", "string", "Customer's current version", required=True)
            .webhook(
                "GET",
                "https://api.example.com/versions/latest"
            )
            .output(DmResult(
                "Latest version is ${latest}. You have ${args.current_version}."
            ))
            .fallback_output(DmResult(
                "Unable to check version information."
            ))
        )
        self.register_swaig_function(check_version_dm.to_swaig_function())

    def _setup_functions(self):
        """Define support functions."""

        @self.tool(description="Get installation help")
        def installation_help(args: dict, raw_data: dict = None) -> SwaigFunctionResult:
            raw_data = raw_data or {}
            global_data = raw_data.get("global_data", {})
            return SwaigFunctionResult(
                "For installation: Download from our website and run the installer. "
                "Windows users should run as Administrator. "
                "System requirements: Windows 10+, macOS 10.15+, or Ubuntu 20.04+. "
                "8GB RAM minimum, 500MB disk space. "
                "Need help with activation or system requirements?"
            )

        @self.tool(
            description="Troubleshoot a specific issue",
            parameters={
                "type": "object",
                "properties": {
                    "issue": {
                        "type": "string",
                        "description": "Description of the issue"
                    }
                },
                "required": ["issue"]
            },
            fillers=["Let me search our knowledge base..."]
        )
        def troubleshoot(args: dict, raw_data: dict = None) -> SwaigFunctionResult:
            """Troubleshoot common issues."""
            issue = args.get("issue", "")
            raw_data = raw_data or {}
            global_data = raw_data.get("global_data", {})
            issue_lower = issue.lower()

            # Common issue patterns
            if any(word in issue_lower for word in ["start", "launch", "open", "won't run"]):
                return SwaigFunctionResult(
                    "For startup issues, try: "
                    "1) Restart your computer, "
                    "2) Run as administrator (Windows), "
                    "3) Check for conflicting software, "
                    "4) Reinstall if needed. "
                    "Did any of these help?"
                )

            if any(word in issue_lower for word in ["license", "activate", "key"]):
                return SwaigFunctionResult(
                    "For license issues: "
                    "Check your license at account.example.com. "
                    "Make sure it hasn't expired and isn't used on too many devices. "
                    "Would you like me to check your license status?"
                )

            if any(word in issue_lower for word in ["slow", "performance", "lag"]):
                return SwaigFunctionResult(
                    "For performance issues: "
                    "1) Close other applications, "
                    "2) Verify system requirements (8GB RAM minimum), "
                    "3) Clear cache (Settings > Advanced > Clear Cache), "
                    "4) Update to latest version. "
                    "Which of these would you like help with?"
                )

            if any(word in issue_lower for word in ["password", "login", "forgot"]):
                return SwaigFunctionResult(
                    "For password reset: "
                    "Click 'Forgot Password' on the login screen, "
                    "enter your email, and check your inbox for a reset link. "
                    "The link arrives within 5 minutes. "
                    "Still having trouble?"
                )

            # Generic response for unknown issues
            return SwaigFunctionResult(
                "I'll search our knowledge base for that issue. "
                "If I can't find a solution, I can create a support ticket. "
                "Could you provide more details about what's happening?"
            )

        @self.tool(
            description="Create a support ticket",
            parameters={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the issue"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Ticket priority"
                    }
                },
                "required": ["description"]
            }
        )
        def create_ticket(args: dict, raw_data: dict = None) -> SwaigFunctionResult:
            description = args.get("description", "")
            priority = args.get("priority", "medium")
            raw_data = raw_data or {}
            global_data = raw_data.get("global_data", {})
            ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            return (
                SwaigFunctionResult(
                    f"Created ticket {ticket_id} with {priority} priority. "
                    "Our team will respond within 24 hours for standard issues, "
                    "or 4 hours for high priority. "
                    "Is there anything else I can help with?"
                )
                .update_global_data({
                    "ticket_id": ticket_id,
                    "ticket_description": description,
                    "ticket_priority": priority,
                    "ticket_created": datetime.now().isoformat()
                })
            )

        @self.tool(
            description="Report incorrect or incomplete answer",
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The original question"
                    },
                    "feedback": {
                        "type": "string",
                        "description": "What was wrong or missing"
                    }
                },
                "required": ["question", "feedback"]
            }
        )
        def report_feedback(args: dict, raw_data: dict = None) -> SwaigFunctionResult:
            """Log feedback for knowledge base improvement."""
            question = args.get("question", "")
            feedback = args.get("feedback", "")
            raw_data = raw_data or {}
            global_data = raw_data.get("global_data", {})
            return (
                SwaigFunctionResult(
                    "Thank you for the feedback. I've logged this for our team to review. "
                    "Your input helps us improve. "
                    "Would you like me to create a ticket for further assistance?"
                )
                .update_global_data({
                    "feedback_question": question,
                    "feedback_content": feedback,
                    "feedback_time": datetime.now().isoformat()
                })
            )

        @self.tool(description="Escalate to human support")
        def escalate_to_human(args: dict, raw_data: dict = None) -> SwaigFunctionResult:
            """Transfer to human support agent."""
            raw_data = raw_data or {}
            global_data = raw_data.get("global_data", {})
            ticket_id = global_data.get("ticket_id")

            context = f"Ticket {ticket_id}" if ticket_id else "New inquiry"

            return (
                SwaigFunctionResult(
                    "I'm connecting you with a human support agent. "
                    "Please hold while I transfer your call.",
                    post_process=True
                )
                .update_global_data({
                    "escalated": True,
                    "escalation_time": datetime.now().isoformat()
                })
                .swml_transfer("/human-support", "Goodbye!", final=True)
            )


if __name__ == "__main__":
    kb_path = os.getenv("KB_PATH", "./support_kb.index")
    agent = SupportAgent(kb_path=kb_path)
    agent.run()
