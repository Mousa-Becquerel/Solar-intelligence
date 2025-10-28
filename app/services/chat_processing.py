"""
Chat processing service - handles agent interactions and streaming.

This module provides the core chat processing logic that was previously
in app.py, now refactored to work with the blueprint architecture.
"""

import json
import logging
import asyncio
from flask import Response, jsonify, current_app
from models import db, Conversation, Message
from typing import Optional

logger = logging.getLogger(__name__)

# Global agent instances (initialized on first use)
# We lazy-load to avoid import errors at module load time
_price_agent = None
_news_agent = None
_leo_om_agent = None
_digitalization_agent = None
_market_intelligence_agent = None


def get_price_agent():
    """Get or create the module prices agent instance."""
    global _price_agent
    if _price_agent is None:
        try:
            from module_prices_agent import ModulePricesAgent, ModulePricesConfig
            config = ModulePricesConfig(verbose=False)
            _price_agent = ModulePricesAgent(config)
            logger.info("✅ Module Prices Agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Module Prices Agent: {e}", exc_info=True)
            raise
    return _price_agent


def get_news_agent_instance():
    """Get or create the news agent instance."""
    global _news_agent
    if _news_agent is None:
        try:
            from news_agent import get_news_agent
            _news_agent = get_news_agent()
            logger.info("✅ News Agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize News Agent: {e}", exc_info=True)
            raise
    return _news_agent


def get_leo_om_agent_instance():
    """Get or create the Leo O&M agent instance."""
    global _leo_om_agent
    if _leo_om_agent is None:
        try:
            from leo_om_agent import get_leo_om_agent
            _leo_om_agent = get_leo_om_agent()
            logger.info("✅ Leo O&M Agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Leo O&M Agent: {e}", exc_info=True)
            raise
    return _leo_om_agent


def get_digitalization_agent_instance():
    """Get or create the digitalization agent instance."""
    global _digitalization_agent
    if _digitalization_agent is None:
        try:
            from digitalization_trend_agent import get_digitalization_agent
            _digitalization_agent = get_digitalization_agent()
            logger.info("✅ Digitalization Agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Digitalization Agent: {e}", exc_info=True)
            raise
    return _digitalization_agent


def get_market_intelligence_agent_instance():
    """Get or create the market intelligence agent instance."""
    global _market_intelligence_agent
    if _market_intelligence_agent is None:
        try:
            from market_intelligence_agent import get_market_intelligence_agent
            _market_intelligence_agent = get_market_intelligence_agent()
            logger.info("✅ Market Intelligence Agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Market Intelligence Agent: {e}", exc_info=True)
            raise
    return _market_intelligence_agent


def clean_nan_values(obj):
    """Clean NaN values from nested dictionaries and lists."""
    import math

    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    else:
        return obj


def process_price_agent(user_message: str, conv_id: int) -> dict:
    """
    Process a message with the price agent (non-streaming).

    Returns:
        dict with 'response' key containing response_data list
    """
    price_agent = get_price_agent()

    # Use asyncio.run() for proper event loop handling
    result = asyncio.run(price_agent.analyze(user_message, conversation_id=str(conv_id)))

    if result["success"]:
        analysis_output = result["analysis"]
        logger.info(f"Module Prices Agent success")
    else:
        analysis_output = f"Error analyzing prices: {result['error']}"
        logger.error(f"Module Prices Agent error: {analysis_output}")

    # Handle structured output from the analyze method
    if result["success"]:
        output = analysis_output

        # Check if it's a PlotResult
        if hasattr(output, 'plot_type') and hasattr(output, 'url_path'):
            if output.success:
                description = getattr(output, 'description', '')
                response_data = [{
                    'type': 'chart',
                    'value': description,
                    'artifact': output.url_path,
                    'comment': None
                }]
            else:
                response_data = [{
                    'type': 'string',
                    'value': f"Error generating plot: {output.error_message}",
                    'comment': None
                }]

        # Check if it's a DataAnalysisResult
        elif hasattr(output, 'result_type') and hasattr(output, 'content'):
            logger.info(f"DataAnalysisResult detected - result_type: {output.result_type}")

            if output.result_type == "dataframe" and output.dataframe_data:
                response_data = [{
                    'type': 'table',
                    'value': output.content,
                    'table_data': output.dataframe_data,
                    'full_data': output.dataframe_data,
                    'comment': None
                }]
            else:
                response_data = [{
                    'type': 'string',
                    'value': output.content,
                    'comment': None
                }]

        # Check if it's a MultiResult (multiple plots/data)
        elif hasattr(output, 'primary_result_type') and hasattr(output, 'plots'):
            response_data = []

            # Add meaningful data results (only tables)
            for data_result in output.data_results:
                if data_result.result_type == "dataframe" and data_result.dataframe_data:
                    response_data.append({
                        'type': 'table',
                        'value': data_result.content,
                        'table_data': data_result.dataframe_data,
                        'full_data': data_result.dataframe_data,
                        'comment': None
                    })

            # Add all plots
            for plot in output.plots:
                if plot.success:
                    description = output.summary if output.summary else (plot.description or plot.title)
                    response_data.append({
                        'type': 'chart',
                        'value': description,
                        'artifact': plot.url_path,
                        'comment': None
                    })

            # If no meaningful results, show the summary as text
            if not response_data and output.summary:
                response_data = [{
                    'type': 'string',
                    'value': output.summary,
                    'comment': None
                }]

        # Check if it's a PlotDataResult (D3/JSON plot data)
        elif hasattr(output, 'plot_type') and hasattr(output, 'data') and isinstance(output.data, list):
            if output.success:
                response_data = [{
                    'type': 'interactive_chart',
                    'value': output.title,
                    'plot_data': {
                        'plot_type': output.plot_type,
                        'title': output.title,
                        'x_axis_label': output.x_axis_label,
                        'y_axis_label': output.y_axis_label,
                        'unit': output.unit,
                        'data': output.data,
                        'series_info': output.series_info
                    },
                    'comment': None
                }]
            else:
                response_data = [{
                    'type': 'string',
                    'value': f"Error generating interactive chart: {output.error_message}",
                    'comment': None
                }]

        # Check if output is a string
        elif isinstance(output, str):
            response_data = [{
                'type': 'string',
                'value': output,
                'comment': None
            }]

        # Fallback
        else:
            response_data = [{
                'type': 'string',
                'value': str(output),
                'comment': None
            }]

    # Handle error case
    else:
        response_data = [{
            'type': 'string',
            'value': analysis_output,
            'comment': None
        }]

    # Store bot response
    try:
        for resp in response_data:
            cleaned_resp = clean_nan_values(resp)
            bot_msg = Message(conversation_id=conv_id, sender='bot', content=json.dumps(cleaned_resp))
            db.session.add(bot_msg)
        db.session.commit()
    except Exception as e:
        logger.error(f"Database error storing bot messages: {e}")
        db.session.rollback()

    return {'response': response_data}


def process_news_agent_stream(user_message: str, conv_id: int, app):
    """
    Process a message with the news agent (streaming).

    Returns:
        Flask Response with SSE stream
    """
    news_agent = get_news_agent_instance()

    def generate_streaming_response():
        """Generator function for Server-Sent Events streaming"""

        async def stream_agent():
            try:
                full_response = ""

                # Stream text chunks as they arrive
                async for chunk in news_agent.analyze_stream(user_message, conversation_id=str(conv_id)):
                    full_response += chunk
                    # Send chunk as SSE event
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

                # Save the complete response to database BEFORE sending done event
                try:
                    with app.app_context():
                        try:
                            bot_msg = Message(
                                conversation_id=conv_id,
                                sender='bot',
                                content=json.dumps({
                                    'type': 'string',
                                    'value': full_response,
                                    'comment': None
                                })
                            )
                            db.session.add(bot_msg)
                            db.session.commit()
                            logger.info(f"News agent message saved: {len(full_response)} chars")
                        except Exception as db_error:
                            logger.error(f"Error saving news agent message: {db_error}")
                            db.session.rollback()
                            raise
                        finally:
                            db.session.close()
                except Exception as outer_error:
                    logger.error(f"Failed to save message: {outer_error}")

                # Send completion event
                yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"

                logger.info(f"News agent streaming completed: {len(full_response)} chars")

            except Exception as e:
                error_msg = f"Streaming error: {str(e)}"
                logger.error(error_msg)
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

        # Run the async generator
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            async_gen = stream_agent()
            while True:
                try:
                    chunk = loop.run_until_complete(async_gen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break
        finally:
            asyncio.set_event_loop(None)
            try:
                loop.close()
            except Exception as e:
                logger.error(f"Error closing event loop: {e}")

    return Response(
        generate_streaming_response(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
            'Content-Type': 'text/event-stream; charset=utf-8',
            'X-Content-Type-Options': 'nosniff'
        }
    )


def process_leo_om_agent(user_message: str, conv_id: int) -> dict:
    """
    Process a message with the Leo O&M agent (non-streaming).

    Returns:
        dict with 'response' key containing response_data list
    """
    leo_om_agent = get_leo_om_agent_instance()

    # Use asyncio.run() for proper event loop handling
    result = asyncio.run(leo_om_agent.analyze(user_message, conversation_id=str(conv_id)))

    if result["success"]:
        analysis_output = result["analysis"]
        logger.info(f"Leo O&M Agent success")
    else:
        analysis_output = f"Error analyzing O&M query: {result['error']}"
        logger.error(f"Leo O&M Agent error: {analysis_output}")

    # Simple string response
    response_data = [{
        'type': 'string',
        'value': analysis_output,
        'comment': None
    }]

    # Store bot response
    try:
        for resp in response_data:
            bot_msg = Message(conversation_id=conv_id, sender='bot', content=json.dumps(resp))
            db.session.add(bot_msg)
        db.session.commit()
    except Exception as e:
        logger.error(f"Database error storing bot messages: {e}")
        db.session.rollback()

    return {'response': response_data}


def process_digitalization_agent_stream(user_message: str, conv_id: int, app):
    """
    Process a message with the digitalization agent (streaming).

    Returns:
        Flask Response with SSE stream
    """
    digitalization_agent = get_digitalization_agent_instance()

    def generate_streaming_response():
        """Generator function for Server-Sent Events streaming"""

        async def stream_agent():
            try:
                full_response = ""

                # Stream text chunks as they arrive
                async for chunk in digitalization_agent.analyze_stream(user_message, conversation_id=str(conv_id)):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

                # Save the complete response to database
                try:
                    with app.app_context():
                        try:
                            bot_msg = Message(
                                conversation_id=conv_id,
                                sender='bot',
                                content=json.dumps({
                                    'type': 'string',
                                    'value': full_response,
                                    'comment': None
                                })
                            )
                            db.session.add(bot_msg)
                            db.session.commit()
                            logger.info(f"Digitalization agent message saved: {len(full_response)} chars")
                        except Exception as db_error:
                            logger.error(f"Error saving digitalization agent message: {db_error}")
                            db.session.rollback()
                            raise
                        finally:
                            db.session.close()
                except Exception as outer_error:
                    logger.error(f"Failed to save message: {outer_error}")

                # Send completion event
                yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"

            except Exception as e:
                error_msg = f"Streaming error: {str(e)}"
                logger.error(error_msg)
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

        # Run async generator
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            async_gen = stream_agent()
            while True:
                try:
                    chunk = loop.run_until_complete(async_gen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break
        finally:
            asyncio.set_event_loop(None)
            try:
                loop.close()
            except Exception as e:
                logger.error(f"Error closing event loop: {e}")

    return Response(
        generate_streaming_response(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
            'Content-Type': 'text/event-stream; charset=utf-8',
            'X-Content-Type-Options': 'nosniff'
        }
    )


def process_market_intelligence_agent_stream(user_message: str, conv_id: int, app):
    """
    Process a message with the market intelligence agent (streaming).

    Returns:
        Flask Response with SSE stream
    """
    market_intelligence_agent = get_market_intelligence_agent_instance()

    def generate_streaming_response():
        """Generator function for Server-Sent Events streaming"""

        async def stream_agent():
            try:
                full_response = ""
                plot_data = None
                response_type = "text"

                if not market_intelligence_agent:
                    error_msg = "Market Intelligence agent not available"
                    yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                    return

                # Send initial processing message
                yield f"data: {json.dumps({'type': 'processing', 'message': 'Analyzing your query...'})}\n\n"

                # Stream response
                async for chunk in market_intelligence_agent.analyze_stream(user_message, conversation_id=str(conv_id)):
                    # Check if chunk is JSON (plot data)
                    try:
                        response_json = json.loads(chunk)
                        if isinstance(response_json, dict):
                            event_type = response_json.get('type')

                            # Handle new streaming format
                            if event_type == 'plot':
                                response_type = "plot"
                                plot_data = response_json['content']
                                full_response = f"Generated plot: {plot_data.get('title', 'Untitled')}"
                                logger.info(f"Plot generated: {plot_data.get('plot_type')} - {plot_data.get('title')}")
                                yield f"data: {json.dumps({'type': 'plot', 'content': plot_data})}\n\n"

                            # Legacy format - direct plot JSON
                            elif 'plot_type' in response_json:
                                response_type = "plot"
                                plot_data = response_json
                                full_response = f"Generated plot: {plot_data.get('title', 'Untitled')}"
                                logger.info(f"Plot generated (legacy): {plot_data.get('plot_type')}")
                                yield f"data: {json.dumps({'type': 'plot', 'content': plot_data})}\n\n"

                            else:
                                # JSON but not a plot
                                full_response += str(response_json)
                                yield f"data: {json.dumps({'type': 'chunk', 'content': str(response_json)})}\n\n"
                        else:
                            # JSON but not a dict
                            full_response += str(chunk)
                            yield f"data: {json.dumps({'type': 'chunk', 'content': str(chunk)})}\n\n"

                    except (json.JSONDecodeError, ValueError):
                        # It's a text chunk
                        if chunk:
                            full_response += chunk
                            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

                # Save the complete response to database
                try:
                    with app.app_context():
                        try:
                            content_to_save = {
                                'type': 'plot' if response_type == "plot" else 'string',
                                'value': plot_data if response_type == "plot" else full_response
                            }

                            bot_msg = Message(
                                conversation_id=conv_id,
                                sender='bot',
                                content=json.dumps(content_to_save)
                            )
                            db.session.add(bot_msg)
                            db.session.commit()
                            logger.info(f"Market Intelligence message saved: type={response_type}")
                        except Exception as db_error:
                            logger.error(f"Error saving market intelligence message: {db_error}")
                            db.session.rollback()
                            raise
                        finally:
                            db.session.close()
                except Exception as outer_error:
                    logger.error(f"Failed to save message: {outer_error}")

                # Send completion event
                yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"

            except Exception as e:
                error_msg = f"Streaming error: {str(e)}"
                logger.error(error_msg)
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

        # Run async generator
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            async_gen = stream_agent()
            while True:
                try:
                    chunk = loop.run_until_complete(async_gen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break
        finally:
            asyncio.set_event_loop(None)
            try:
                loop.close()
            except Exception as e:
                logger.error(f"Error closing event loop: {e}")

    return Response(
        generate_streaming_response(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
            'Content-Type': 'text/event-stream; charset=utf-8',
            'X-Content-Type-Options': 'nosniff'
        }
    )


def process_chat_request(request_obj, current_user):
    """
    Process a chat request with agent interaction.

    This is the main entry point for chat processing, extracted from app.py
    and refactored to work with the blueprint architecture.

    Args:
        request_obj: Flask request object
        current_user: Current authenticated user

    Returns:
        Response: Streaming response or JSON error
    """
    try:
        data = request_obj.json
        user_message = data.get('message', '')

        # Input validation
        if not user_message or not user_message.strip():
            return jsonify({'error': 'Empty message'}), 400

        # Validate message length
        MAX_MESSAGE_LENGTH = 5000
        if len(user_message) > MAX_MESSAGE_LENGTH:
            return jsonify({
                'error': f'Message too long. Maximum length is {MAX_MESSAGE_LENGTH} characters.'
            }), 400

        conv_id = data.get('conversation_id')
        agent_type = data.get('agent_type', 'market')

        if not conv_id:
            return jsonify({'error': 'conversation_id required'}), 400

        # Get conversation and validate user access
        conversation = db.session.get(Conversation, conv_id)
        if not conversation or conversation.user_id != current_user.id:
            return jsonify({'error': 'Conversation not found or access denied'}), 404

        # Update conversation agent type if changed
        if conversation.agent_type != agent_type:
            conversation.agent_type = agent_type
            db.session.commit()

        # Check query limits
        if not current_user.can_make_query():
            queries_used = current_user.monthly_query_count
            query_limit = current_user.get_query_limit()
            plan_type = current_user.plan_type
            return jsonify({
                'error': f'Query limit reached. You have used {queries_used}/{query_limit} queries this month.',
                'plan_type': plan_type,
                'queries_used': queries_used,
                'query_limit': query_limit if query_limit != float('inf') else 'unlimited',
                'upgrade_required': plan_type == 'free'
            }), 429

        # Increment query count
        try:
            current_user.increment_query_count()
            db.session.commit()
            logger.info(f"Query count incremented for user {current_user.id}")
        except Exception as e:
            logger.error(f"Error incrementing query count: {e}")
            db.session.rollback()
            return jsonify({'error': 'Failed to track query usage'}), 500

        # Store user message
        try:
            user_msg = Message(
                conversation_id=conv_id,
                sender='user',
                content=json.dumps({
                    "type": "string",
                    "value": user_message,
                    "comment": None
                })
            )
            db.session.add(user_msg)
            db.session.commit()
        except Exception as e:
            logger.error(f"Database error storing user message: {e}")
            db.session.rollback()
            return jsonify({'error': 'Database error storing message'}), 500

        # Process with appropriate agent
        try:
            if agent_type == "price":
                result = process_price_agent(user_message, conv_id)
                return jsonify(result)

            elif agent_type == "news":
                return process_news_agent_stream(user_message, conv_id, current_app._get_current_object())

            elif agent_type == "om":
                result = process_leo_om_agent(user_message, conv_id)
                return jsonify(result)

            elif agent_type == "digitalization":
                return process_digitalization_agent_stream(user_message, conv_id, current_app._get_current_object())

            elif agent_type == "market":
                return process_market_intelligence_agent_stream(user_message, conv_id, current_app._get_current_object())

            else:
                return jsonify({'error': f'Unknown agent type: {agent_type}'}), 400

        except Exception as agent_error:
            logger.error(f"Agent processing error: {agent_error}", exc_info=True)
            return jsonify({'error': f'Agent processing failed: {str(agent_error)}'}), 500

    except Exception as e:
        logger.error(f"Chat processing error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to process chat request', 'details': str(e)}), 500
