"""
Chat interface routes blueprint.

This blueprint handles the main chat interface and query processing.
"""

from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user
from app.services.agent_service import AgentService
from app.services.conversation_service import ConversationService
from app.extensions import limiter, csrf
import json
import logging

logger = logging.getLogger(__name__)

# Create blueprint
chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/')
@chat_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Main chat interface.

    Displays the main chat dashboard with hired agents.
    """
    from models import HiredAgent

    # Get user's hired agents
    hired_agents = HiredAgent.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    hired_agent_types = [agent.agent_type for agent in hired_agents]

    return render_template('index.html', hired_agents=hired_agent_types)


@chat_bp.route('/agents')
@login_required
def agents():
    """
    Agent selection page.

    Displays available agents for hiring with access control information.
    """
    from models import HiredAgent
    from app.services.agent_access_service import AgentAccessService

    # Get user's hired agents
    hired_agents = HiredAgent.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    hired_agent_types = [agent.agent_type for agent in hired_agents]

    # Get agent access information for the user
    agent_access_info = AgentAccessService.get_user_accessible_agents(current_user)

    return render_template('agents.html',
                         hired_agents=hired_agent_types,
                         agent_access_info=agent_access_info)


@chat_bp.route('/query', methods=['POST'])
@chat_bp.route('/chat', methods=['POST'])
@login_required
@limiter.exempt  # Match original chat endpoint rate limiting
def query():
    """
    Process user query with AI agents.

    This endpoint handles chat requests with full agent processing and streaming.

    Returns:
        Response: SSE stream or JSON error
    """
    try:
        from app.services.chat_processing import process_chat_request

        # Process the chat request using the refactored service layer
        return process_chat_request(request, current_user)
    except Exception as e:
        logger.error(f"❌ CHAT ENDPOINT ERROR: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Internal server error',
            'details': str(e),
            'type': type(e).__name__
        }), 500


@chat_bp.route('/available-agents')
@login_required
def available_agents():
    """
    Get list of available agents for the user.

    Returns:
        JSON: List of agent information
    """
    try:
        agents = AgentService.get_available_agents(current_user)
        return jsonify({'agents': agents})

    except Exception as e:
        logger.error(f"Error getting available agents: {e}")
        return jsonify({'error': 'Failed to get agents'}), 500


@chat_bp.route('/agent-usage')
@login_required
def agent_usage():
    """
    Get user's agent usage statistics.

    Returns:
        JSON: Usage statistics
    """
    try:
        stats = AgentService.get_agent_usage_stats(current_user)
        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting usage stats: {e}")
        return jsonify({'error': 'Failed to get usage statistics'}), 500


@chat_bp.route('/hire-agent', methods=['POST'])
@login_required
def hire_agent():
    """
    Hire an agent for the user.

    Returns:
        JSON: Success status
    """
    try:
        data = request.get_json()
        agent_type = data.get('agent_type')

        if not agent_type:
            return jsonify({'error': 'agent_type is required'}), 400

        # Check if user has access to this agent
        from app.services.agent_access_service import AgentAccessService
        can_access, access_reason = AgentAccessService.can_user_access_agent(current_user, agent_type)

        if not can_access:
            return jsonify({
                'error': access_reason or 'You do not have access to this agent',
                'requires_upgrade': True,
                'agent_type': agent_type
            }), 403

        success, error = AgentService.hire_agent(current_user, agent_type)

        if success:
            return jsonify({'success': True, 'message': f'Agent {agent_type} hired successfully'})
        else:
            return jsonify({'error': error}), 400

    except Exception as e:
        logger.error(f"Error hiring agent: {e}")
        return jsonify({'error': 'Failed to hire agent'}), 500


@chat_bp.route('/release-agent', methods=['POST'])
@login_required
def release_agent():
    """
    Release an agent for the user.

    Returns:
        JSON: Success status
    """
    try:
        data = request.get_json()
        agent_type = data.get('agent_type')

        if not agent_type:
            return jsonify({'error': 'agent_type is required'}), 400

        success, error = AgentService.release_agent(current_user, agent_type)

        if success:
            return jsonify({'success': True, 'message': f'Agent {agent_type} released successfully'})
        else:
            return jsonify({'error': error}), 400

    except Exception as e:
        logger.error(f"Error releasing agent: {e}")
        return jsonify({'error': 'Failed to release agent'}), 500


@chat_bp.route('/api/agents/hire', methods=['POST'])
@login_required
def api_hire_agent():
    """
    API endpoint to hire an agent (matches original app.py route).

    Returns:
        JSON: Success status with agent_type
    """
    try:
        from models import HiredAgent
        from app.extensions import db
        from app.services.agent_access_service import AgentAccessService

        data = request.get_json()
        agent_type = data.get('agent_type')

        # Validate agent type
        valid_agents = ['market', 'price', 'news', 'digitalization', 'nzia_policy', 'nzia_market_impact', 'manufacturer_financial', 'om']
        if agent_type not in valid_agents:
            return jsonify({'success': False, 'message': 'Invalid agent type'}), 400

        # Check if user has access to this agent
        can_access, reason = AgentAccessService.can_user_access_agent(current_user, agent_type)
        if not can_access:
            return jsonify({'success': False, 'message': reason or 'Access denied'}), 403

        # Check if agent exists (active or inactive)
        existing = HiredAgent.query.filter_by(
            user_id=current_user.id,
            agent_type=agent_type
        ).first()

        if existing:
            # If already active, return error
            if existing.is_active:
                return jsonify({'success': False, 'message': 'Agent already hired'}), 400
            # If inactive, reactivate it
            else:
                existing.is_active = True
                existing.hired_at = db.func.now()
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'Agent hired successfully',
                    'agent_type': agent_type
                })

        # Create new hired agent record
        hired_agent = HiredAgent(
            user_id=current_user.id,
            agent_type=agent_type
        )
        db.session.add(hired_agent)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Agent hired successfully',
            'agent_type': agent_type
        })

    except Exception as e:
        from app.extensions import db
        db.session.rollback()
        logger.error(f"Error hiring agent: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Failed to hire agent: {str(e)}'}), 500


@chat_bp.route('/api/agents/unhire', methods=['POST'])
@login_required
def api_unhire_agent():
    """
    API endpoint to unhire an agent (matches original app.py route).

    Returns:
        JSON: Success status with agent_type
    """
    try:
        from models import HiredAgent
        from app.extensions import db

        data = request.get_json()
        agent_type = data.get('agent_type')

        # Find hired agent
        hired_agent = HiredAgent.query.filter_by(
            user_id=current_user.id,
            agent_type=agent_type,
            is_active=True
        ).first()

        if not hired_agent:
            return jsonify({'success': False, 'message': 'Agent not found'}), 404

        # Mark as inactive (soft delete)
        hired_agent.is_active = False
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Agent removed successfully',
            'agent_type': agent_type
        })

    except Exception as e:
        from app.extensions import db
        db.session.rollback()
        logger.error(f"Error unhiring agent: {e}")
        return jsonify({'success': False, 'message': 'Failed to remove agent'}), 500


@chat_bp.route('/api/agents/hired', methods=['GET'])
@login_required
def api_get_hired_agents():
    """
    API endpoint to get list of hired agents (matches original app.py route).

    Returns:
        JSON: List of hired agent types
    """
    try:
        from models import HiredAgent

        hired_agents = HiredAgent.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).all()

        agent_types = [agent.agent_type for agent in hired_agents]

        return jsonify({
            'success': True,
            'hired_agents': agent_types
        })

    except Exception as e:
        logger.error(f"Error getting hired agents: {e}")
        return jsonify({'success': False, 'message': 'Failed to get hired agents'}), 500


@chat_bp.route('/submit-user-survey', methods=['POST'])
@login_required
@limiter.limit("5 per hour")
def submit_user_survey():
    """Handle user profiling survey submission (FIRST survey - Simple) and grant 5 extra queries"""
    try:
        from models import UserSurvey
        from app.extensions import db

        data = request.get_json()

        # Validate required fields
        required_fields = ['role', 'regions', 'familiarity', 'insights']
        for field in required_fields:
            if not data or field not in data:
                return jsonify({'error': f'{field} is required'}), 400

        # Check if user has already submitted this survey
        existing_survey = UserSurvey.query.filter_by(user_id=current_user.id).first()
        if existing_survey:
            return jsonify({
                'success': False,
                'message': 'You have already completed the survey and received your bonus queries.'
            }), 400

        # Create survey record
        survey = UserSurvey(
            user_id=current_user.id,
            role=data.get('role'),
            role_other=data.get('role_other'),
            regions=json.dumps(data.get('regions')),
            familiarity=data.get('familiarity'),
            insights=json.dumps(data.get('insights')),
            tailored=data.get('tailored'),
            bonus_queries_granted=5
        )

        db.session.add(survey)
        db.session.commit()

        # Calculate new query count (the get_query_limit() method now includes survey bonuses)
        new_query_limit = current_user.get_query_limit()
        new_query_count = new_query_limit - current_user.monthly_query_count

        logger.info(f"User survey submitted: user_id={current_user.id}, bonus_queries=5, new_limit={new_query_limit}")

        return jsonify({
            'success': True,
            'message': 'Survey completed! 5 extra queries unlocked.',
            'new_query_count': int(new_query_count) if new_query_count != float('inf') else 'unlimited',
            'new_query_limit': int(new_query_limit) if new_query_limit != float('inf') else 'unlimited'
        }), 200

    except Exception as e:
        from app.extensions import db
        db.session.rollback()
        logger.error(f"Error submitting user survey: {e}")
        return jsonify({'error': 'Failed to submit survey'}), 500


@chat_bp.route('/submit-user-survey-stage2', methods=['POST'])
@login_required
@limiter.limit("5 per hour")
def submit_user_survey_stage2():
    """Handle Stage 2 survey submission (Market Activity & Behaviour) - SECOND survey (Advanced) - and grant 5 extra queries"""
    try:
        from models import UserSurvey, UserSurveyStage2
        from app.extensions import db

        data = request.get_json()

        # Validate required fields
        required_fields = ['work_focus', 'pv_segments', 'technologies', 'challenges']
        for field in required_fields:
            if not data or field not in data:
                return jsonify({'error': f'{field} is required'}), 400

        # Check if user has completed Stage 1 (User Profiling) first - this is now required
        stage1_survey = UserSurvey.query.filter_by(user_id=current_user.id).first()
        if not stage1_survey:
            return jsonify({
                'success': False,
                'message': 'Please complete the User Profiling survey before accessing this survey.'
            }), 400

        # Check if user has already submitted Stage 2 survey
        existing_survey = UserSurveyStage2.query.filter_by(user_id=current_user.id).first()
        if existing_survey:
            return jsonify({
                'success': False,
                'message': 'You have already completed the Stage 2 survey and received your bonus queries.'
            }), 400

        # Validate challenges (must be exactly 3 or allow less)
        challenges = data.get('challenges', [])
        if len(challenges) > 3:
            return jsonify({'error': 'Please select a maximum of 3 challenges'}), 400

        # Create Stage 2 survey record
        survey = UserSurveyStage2(
            user_id=current_user.id,
            work_focus=data.get('work_focus'),
            work_focus_other=data.get('work_focus_other'),
            pv_segments=json.dumps(data.get('pv_segments')),
            technologies=json.dumps(data.get('technologies')),
            technologies_other=data.get('technologies_other'),
            challenges=json.dumps(challenges),
            weekly_insight=data.get('weekly_insight'),
            bonus_queries_granted=5
        )

        db.session.add(survey)
        db.session.commit()

        # Calculate new query count (the get_query_limit() method now includes survey bonuses)
        new_query_limit = current_user.get_query_limit()
        new_query_count = new_query_limit - current_user.monthly_query_count

        logger.info(f"User Stage 2 survey submitted: user_id={current_user.id}, bonus_queries=5, new_limit={new_query_limit}")

        return jsonify({
            'success': True,
            'message': 'Stage 2 survey completed! 5 extra queries unlocked.',
            'new_query_count': int(new_query_count) if new_query_count != float('inf') else 'unlimited',
            'new_query_limit': int(new_query_limit) if new_query_limit != float('inf') else 'unlimited'
        }), 200

    except Exception as e:
        from app.extensions import db
        db.session.rollback()
        logger.error(f"Error submitting Stage 2 survey: {e}")
        return jsonify({'error': 'Failed to submit survey'}), 500


@chat_bp.route('/check-survey-status', methods=['GET'])
@login_required
def check_survey_status():
    """Check which surveys the user has completed"""
    try:
        from models import UserSurvey, UserSurveyStage2

        stage1_completed = UserSurvey.query.filter_by(user_id=current_user.id).first() is not None
        stage2_completed = UserSurveyStage2.query.filter_by(user_id=current_user.id).first() is not None

        return jsonify({
            'stage1_completed': stage1_completed,
            'stage2_completed': stage2_completed
        }), 200

    except Exception as e:
        logger.error(f"Error checking survey status: {e}")
        return jsonify({'error': 'Failed to check survey status'}), 500


@chat_bp.route('/download-table-data', methods=['POST'])
@login_required
def download_table_data():
    """Download table data as CSV"""
    try:
        data = request.json
        table_data = data.get('table_data')
        filename = data.get('filename', 'table_data.csv')

        if not table_data:
            return jsonify({'error': 'No table data provided'}), 400

        # Convert JSON data back to DataFrame
        import pandas as pd
        df = pd.DataFrame(table_data)

        # Create CSV content
        csv_content = df.to_csv(index=False)

        # Return CSV as response
        from flask import Response
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )

    except Exception as e:
        logger.error(f"Error generating CSV download: {e}")
        return jsonify({'error': 'Failed to generate CSV'}), 500


@chat_bp.route('/generate-ppt', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def generate_ppt():
    """Generate PowerPoint presentation from selected messages"""
    try:
        import tempfile
        import os
        from flask import send_file

        data = request.json
        if not data or 'items' not in data:
            return jsonify({'error': 'No conversation data provided'}), 400

        # Filter for plot items only
        plot_items = [item for item in data['items'] if item.get('type') == 'plot']
        if not plot_items:
            return jsonify({'error': 'No plots found in selected messages'}), 400

        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_json:
            # Prepare data in the format expected by ppt_gen.py
            ppt_data = {
                'conversation_id': data.get('conversation_id'),
                'export_timestamp': data.get('export_timestamp'),
                'total_messages': len(plot_items),
                'total_downloaded_files': 0,
                'export_note': f'{len(plot_items)} plot(s) for PPT generation',
                'items': plot_items
            }

            json.dump(ppt_data, temp_json, indent=2)
            temp_json_path = temp_json.name

        # Create temporary output file
        temp_ppt_path = tempfile.mktemp(suffix='.pptx')

        try:
            # Check if ppt_gen module exists
            try:
                from ppt_gen import create_powerpoint_from_json_all_plots
            except ImportError:
                logger.error("ppt_gen module not found")
                return jsonify({'error': 'PowerPoint generation not available'}), 501

            # Check if template exists
            template_path = 'template.pptx'
            if not os.path.exists(template_path):
                logger.error(f"Template not found: {template_path}")
                return jsonify({'error': 'PowerPoint template not found'}), 500

            # Generate PowerPoint
            create_powerpoint_from_json_all_plots(temp_json_path, temp_ppt_path, template_path)

            # Send file
            return send_file(
                temp_ppt_path,
                mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
                as_attachment=True,
                download_name=f'solar_intelligence_export_{data.get("conversation_id", "unknown")}.pptx'
            )

        finally:
            # Clean up temporary JSON file
            try:
                os.unlink(temp_json_path)
            except:
                pass

    except Exception as e:
        logger.error(f"Error generating PowerPoint: {e}", exc_info=True)
        return jsonify({'error': f'Failed to generate PowerPoint: {str(e)}'}), 500


@chat_bp.route('/contact/submit', methods=['POST'])
@login_required
@csrf.exempt  # Exempt from CSRF for JSON API
def submit_expert_contact():
    """
    Handle expert contact form submission from artifact panel.

    Request JSON:
        {
            "name": str,
            "email": str,
            "company": str (optional),
            "message": str,
            "selected_experts": list (optional)
        }

    Returns:
        JSON: Success status and message
    """
    try:
        data = request.get_json()

        if not data:
            logger.error("No JSON data in contact form submission")
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        company = data.get('company', '').strip()
        message = data.get('message', '').strip()
        selected_experts = data.get('selected_experts', [])  # Get selected expert IDs

        # Validate required fields
        if not all([name, email, message]):
            return jsonify({'success': False, 'message': 'Name, email, and message are required'}), 400

        # Save to database
        from models import ContactRequest
        from app.extensions import db

        contact_request = ContactRequest(
            user_id=current_user.id,
            name=name,
            email=email,
            company=company if company else None,
            message=message,
            source='artifact_panel',
            selected_experts=selected_experts if selected_experts else None  # Store expert selections
        )
        db.session.add(contact_request)
        db.session.commit()

        logger.info(f"Expert contact request saved: ID {contact_request.id} from {name} ({email})")

        # TODO: In production, implement:
        # 1. Send notification email to sales team
        # 2. Send confirmation email to user

        return jsonify({
            'success': True,
            'message': 'Thank you for your request! Our experts will reach out within 24-48 hours.'
        }), 200

    except Exception as e:
        logger.error(f"Error processing expert contact form: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again.'
        }), 500


@chat_bp.route('/api/approval_response', methods=['POST'])
@login_required
def approval_response():
    """
    Handle user approval response for expert contact.

    This is called when user clicks Yes/No on the expert contact approval UI.

    Request JSON:
        {
            "approved": bool,
            "conversation_id": str,
            "context": str  # e.g., "expert_contact"
        }

    Returns:
        JSON: Response message and optional redirect flag
    """
    try:
        # Log incoming request details for debugging
        logger.info(f"Approval response endpoint called")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Request data: {request.data}")

        data = request.get_json(force=True)  # force=True to parse even without correct Content-Type

        if not data:
            logger.error("No JSON data in request body")
            return jsonify({'error': 'No data provided'}), 400

        approved = data.get('approved', False)
        conversation_id = data.get('conversation_id')
        context = data.get('context', '')

        logger.info(f"Approval response received: approved={approved}, conversation_id={conversation_id}, context={context}")

        # Based on the longer_market_agent_flow.py logic:
        # If user approves → "Let's fill the contact form"
        # If user rejects → "Can I help you with other queries then?"

        if approved:
            response_message = "Excellent! Let me open the contact form for you. Please fill in your details and our experts will reach out to you within 24-48 hours with personalized insights.\n\n**Opening contact form...**"
            redirect_to_contact = True
        else:
            response_message = "No problem! Can I help you with other queries then?"
            redirect_to_contact = False

        # Save the approval response to conversation history
        if conversation_id:
            try:
                from app.services.conversation_service import ConversationService
                conv_service = ConversationService()

                # Save user's approval decision as a system message
                approval_text = "Yes, I want to contact an expert" if approved else "No, thanks"
                conv_service.add_message(
                    conversation_id=conversation_id,
                    content=approval_text,
                    sender='user',
                    agent_type='system'
                )

                # Save bot's response
                conv_service.add_message(
                    conversation_id=conversation_id,
                    content=response_message,
                    sender='bot',
                    agent_type='market'
                )

                logger.info(f"Saved approval response to conversation {conversation_id}")
            except Exception as e:
                logger.error(f"Failed to save approval response to conversation: {e}")
                # Continue anyway, don't fail the request

        return jsonify({
            'success': True,
            'message': response_message,
            'redirect_to_contact': redirect_to_contact
        })

    except Exception as e:
        logger.error(f"Error handling approval response: {e}", exc_info=True)
        return jsonify({'error': f'Failed to process approval: {str(e)}'}), 500
