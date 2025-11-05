"""
Agent Access Control Service.

This service handles all agent access control operations including
checking permissions, managing whitelists, and configuring agent access.
"""

from typing import Optional, Tuple, Dict, List
from datetime import datetime
from models import User, AgentAccess, AgentWhitelist, db
import logging

logger = logging.getLogger(__name__)


class AgentAccessService:
    """Service for agent access control operations."""

    @staticmethod
    def can_user_access_agent(user: User, agent_type: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a user can access a specific agent.

        Args:
            user: User object
            agent_type: Type of agent (e.g., 'market', 'price', 'news')

        Returns:
            Tuple of (can_access: bool, reason: str or None)
            - (True, None) if user has access
            - (False, reason) if user doesn't have access with explanation
        """
        try:
            # Get agent access configuration
            agent_config = AgentAccess.query.filter_by(agent_type=agent_type).first()

            # If no configuration exists, allow access (backward compatibility)
            if not agent_config:
                logger.warning(f"No access configuration found for agent '{agent_type}', allowing access")
                return True, None

            # Check if agent is globally disabled
            if not agent_config.is_enabled:
                return False, f"The {agent_type} agent is currently unavailable"

            # Admins always have access
            if user.role == 'admin':
                return True, None

            # Check whitelist first (highest priority)
            whitelist_entry = AgentWhitelist.query.filter_by(
                agent_type=agent_type,
                user_id=user.id,
                is_active=True
            ).first()

            if whitelist_entry:
                # Check if whitelist entry has expired
                if whitelist_entry.expires_at and whitelist_entry.expires_at < datetime.utcnow():
                    return False, f"Your special access to the {agent_type} agent has expired"
                return True, None

            # Grandfather clause: Check if user already has this agent hired
            # This allows existing users to continue using agents they hired before restrictions
            from models import HiredAgent
            existing_hire = HiredAgent.query.filter_by(
                user_id=user.id,
                agent_type=agent_type,
                is_active=True
            ).first()

            if existing_hire:
                logger.info(f"User {user.id} grandfathered for agent {agent_type} (hired before access control)")
                return True, None

            # Check plan-based access
            plan_hierarchy = {
                'free': 0,
                'premium': 1,
                'max': 2,
                'admin': 3
            }

            user_plan_level = plan_hierarchy.get(user.plan_type, 0)
            required_plan_level = plan_hierarchy.get(agent_config.required_plan, 0)

            if user_plan_level >= required_plan_level:
                return True, None
            else:
                # User doesn't have required plan
                required_plan = agent_config.required_plan.capitalize()
                return False, f"This agent requires a {required_plan} plan or higher"

        except Exception as e:
            logger.error(f"Error checking agent access for user {user.id}, agent {agent_type}: {e}")
            # Fail open for now to prevent breaking existing functionality
            return True, None

    @staticmethod
    def get_user_accessible_agents(user: User) -> List[Dict[str, any]]:
        """
        Get list of all agents with their access status for a user.

        Args:
            user: User object

        Returns:
            List of dicts with agent info and access status
        """
        try:
            # Get all agent configurations
            all_agents = AgentAccess.query.all()

            result = []
            for agent in all_agents:
                can_access, reason = AgentAccessService.can_user_access_agent(user, agent.agent_type)

                # Check if user is whitelisted
                is_whitelisted = AgentWhitelist.query.filter_by(
                    agent_type=agent.agent_type,
                    user_id=user.id,
                    is_active=True
                ).first() is not None

                result.append({
                    'agent_type': agent.agent_type,
                    'required_plan': agent.required_plan,
                    'is_enabled': agent.is_enabled,
                    'can_access': can_access,
                    'access_reason': reason,
                    'is_whitelisted': is_whitelisted,
                    'description': agent.description
                })

            return result

        except Exception as e:
            logger.error(f"Error getting accessible agents for user {user.id}: {e}")
            return []

    @staticmethod
    def grant_user_access(
        agent_type: str,
        user_id: int,
        granted_by_id: int,
        expires_at: Optional[datetime] = None,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Grant a user access to a specific agent (add to whitelist).

        Args:
            agent_type: Type of agent
            user_id: User ID to grant access to
            granted_by_id: Admin user ID granting access
            expires_at: Optional expiration date
            reason: Optional reason for granting access

        Returns:
            Tuple of (success: bool, error_message: str or None)
        """
        try:
            # Verify agent exists
            agent_config = AgentAccess.query.filter_by(agent_type=agent_type).first()
            if not agent_config:
                return False, f"Agent '{agent_type}' not found"

            # Verify user exists
            user = User.query.get(user_id)
            if not user:
                return False, f"User with ID {user_id} not found"

            # Verify granter is admin
            granter = User.query.get(granted_by_id)
            if not granter or granter.role != 'admin':
                return False, "Only admins can grant agent access"

            # Check if whitelist entry already exists
            existing = AgentWhitelist.query.filter_by(
                agent_type=agent_type,
                user_id=user_id
            ).first()

            if existing:
                # Update existing entry
                existing.is_active = True
                existing.granted_by = granted_by_id
                existing.granted_at = datetime.utcnow()
                existing.expires_at = expires_at
                existing.reason = reason
                logger.info(f"Updated whitelist entry for user {user_id}, agent {agent_type}")
            else:
                # Create new entry
                whitelist_entry = AgentWhitelist(
                    agent_type=agent_type,
                    user_id=user_id,
                    granted_by=granted_by_id,
                    granted_at=datetime.utcnow(),
                    expires_at=expires_at,
                    is_active=True,
                    reason=reason
                )
                db.session.add(whitelist_entry)
                logger.info(f"Created whitelist entry for user {user_id}, agent {agent_type}")

            db.session.commit()
            return True, None

        except Exception as e:
            logger.error(f"Error granting agent access: {e}")
            db.session.rollback()
            return False, "Failed to grant agent access"

    @staticmethod
    def revoke_user_access(
        agent_type: str,
        user_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Revoke a user's whitelist access to a specific agent.

        Args:
            agent_type: Type of agent
            user_id: User ID to revoke access from

        Returns:
            Tuple of (success: bool, error_message: str or None)
        """
        try:
            whitelist_entry = AgentWhitelist.query.filter_by(
                agent_type=agent_type,
                user_id=user_id
            ).first()

            if not whitelist_entry:
                return False, "User is not whitelisted for this agent"

            whitelist_entry.is_active = False
            db.session.commit()

            logger.info(f"Revoked whitelist access for user {user_id}, agent {agent_type}")
            return True, None

        except Exception as e:
            logger.error(f"Error revoking agent access: {e}")
            db.session.rollback()
            return False, "Failed to revoke agent access"

    @staticmethod
    def update_agent_config(
        agent_type: str,
        required_plan: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        description: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Update agent access configuration.

        Args:
            agent_type: Type of agent
            required_plan: New required plan level
            is_enabled: Enable/disable agent globally
            description: Description of access requirements

        Returns:
            Tuple of (success: bool, error_message: str or None)
        """
        try:
            agent_config = AgentAccess.query.filter_by(agent_type=agent_type).first()

            if not agent_config:
                return False, f"Agent '{agent_type}' not found"

            # Update fields if provided
            if required_plan is not None:
                if required_plan not in ['free', 'premium', 'max', 'admin']:
                    return False, "Invalid plan type"
                agent_config.required_plan = required_plan

            if is_enabled is not None:
                agent_config.is_enabled = is_enabled

            if description is not None:
                agent_config.description = description

            agent_config.updated_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"Updated agent config for {agent_type}")
            return True, None

        except Exception as e:
            logger.error(f"Error updating agent config: {e}")
            db.session.rollback()
            return False, "Failed to update agent configuration"

    @staticmethod
    def get_whitelisted_users(agent_type: str) -> List[Dict[str, any]]:
        """
        Get all users whitelisted for a specific agent.

        Args:
            agent_type: Type of agent

        Returns:
            List of dicts with user and whitelist info
        """
        try:
            whitelist_entries = AgentWhitelist.query.filter_by(
                agent_type=agent_type,
                is_active=True
            ).all()

            result = []
            for entry in whitelist_entries:
                result.append({
                    'user_id': entry.user_id,
                    'username': entry.user.username,
                    'full_name': entry.user.full_name,
                    'granted_at': entry.granted_at,
                    'expires_at': entry.expires_at,
                    'reason': entry.reason,
                    'granted_by': entry.granter.full_name if entry.granter else None
                })

            return result

        except Exception as e:
            logger.error(f"Error getting whitelisted users for agent {agent_type}: {e}")
            return []
