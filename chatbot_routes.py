from flask import Blueprint, request, jsonify, session
import logging
import os

logger = logging.getLogger(__name__)

print("[DEBUG] Importing chatbot_service")
try:
    from services.chatbot_service import chatbot_service
    print("[DEBUG] Successfully imported chatbot_service")
except Exception as e:
    print(f"[DEBUG] Error importing chatbot_service: {e}")
    raise

# Import AI agent availability
try:
    from services.job_ai_agent_service import AI_AGENT_AVAILABLE
except ImportError:
    AI_AGENT_AVAILABLE = False

# Import ADK availability
try:
    from google.adk.agents.agent import Agent
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/api/chatbot')

# Add this new endpoint to check agent server status
@chatbot_bp.route('/agent-status', methods=['GET'])
def agent_status():
    """Check agent server status"""
    try:
        import requests
        
        agent_server_url = os.environ.get('AGENT_SERVER_URL', 'http://localhost:8000')
        
        status_info = {
            'success': True,
            'agent_server': {
                'url': agent_server_url,
                'configured': bool(agent_server_url),
                'available': False,
                'status': 'unknown'
            },
            'chatbot_service': {
                'use_agent_server': chatbot_service.use_agent_server,
                'priority_order': chatbot_service.response_priority,
                'session_id': chatbot_service.session_id
            },
            'providers': {
                'gemini': chatbot_service.use_gemini_agent,
                'openai': AI_AGENT_AVAILABLE,
                'adk': ADK_AVAILABLE
            }
        }
        
        # Try to connect to agent server
        if agent_server_url:
            try:
                response = requests.get(f"{agent_server_url}/health", timeout=3)
                if response.status_code == 200:
                    status_info['agent_server']['available'] = True
                    status_info['agent_server']['status'] = 'healthy'
                    status_info['agent_server']['response'] = response.json()
                else:
                    status_info['agent_server']['status'] = f'error: {response.status_code}'
            except requests.exceptions.ConnectionError:
                status_info['agent_server']['status'] = 'connection_error'
            except requests.exceptions.Timeout:
                status_info['agent_server']['status'] = 'timeout'
            except Exception as e:
                status_info['agent_server']['status'] = f'error: {str(e)}'
        
        return jsonify(status_info)
        
    except Exception as e:
        logger.error(f"Error checking agent status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500

# Add a test endpoint
@chatbot_bp.route('/test-agent', methods=['POST'])
def test_agent():
    """Test agent server connection"""
    try:
        test_message = "Hello, this is a test message from the chatbot routes."
        user_id = session.get('user_id') or "test_user"
        
        response = chatbot_service.send_message(test_message, user_id)
        
        if response:
            return jsonify({
                'success': True,
                'message': 'Agent server test completed',
                'response': response.get('content', 'No content'),
                'source': response.get('source', 'unknown'),
                'session_id': chatbot_service.session_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No response from agent server'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in test-agent endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@chatbot_bp.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    print("[DEBUG] Chat endpoint called")
    
    # Log agent server status
    agent_server_url = os.environ.get('AGENT_SERVER_URL')
    print(f"[DEBUG] AGENT_SERVER_URL: {agent_server_url}")
    
    try:
        print("[DEBUG] Getting JSON data")
        data = request.get_json()
        
        if not data or 'message' not in data:
            print("[DEBUG] No message in request")
            return jsonify({'error': 'Message is required'}), 400
        
        message = data['message']
        print(f"[DEBUG] Original message: {message}")
        user_id = session.get('user_id')
        
        # Add user context to the message if logged in
        if user_id:
            original_message = message
            message = f"[User ID: {user_id}] {message}"
            print(f"[DEBUG] Message with user ID: {message}")
        
        print("[DEBUG] Calling chatbot_service.send_message")
        response = chatbot_service.send_message(message, user_id)
        print(f"[DEBUG] Chat route received response: {response}")
        
        if response:
            print(f"[DEBUG] Response source: {response.get('source', 'unknown')}")
            content = response.get('content', 'Sorry, I could not process your request.')
            
            # Check if content is None or empty
            if content is None or (isinstance(content, str) and not content.strip()):
                print("[DEBUG] Content is None or empty, using fallback")
                content = "I apologize, but I'm having trouble connecting to my AI services. Please try again in a moment."
            
            print(f"[DEBUG] Extracted content: {content[:100]}...")
            return jsonify({
                'success': True,
                'response': content,
                'source': response.get('source', 'unknown'),
                'session_id': chatbot_service.session_id,
                'metadata': response.get('metadata', {})
            })
        else:
            print("[DEBUG] Response is falsy, returning error")
            return jsonify({'error': 'Failed to get response from chatbot'}), 500
            
    except Exception as e:
        print(f"[DEBUG] Exception in chat endpoint: {str(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@chatbot_bp.route('/recommendations', methods=['POST'])
def get_recommendations():
    """Get job recommendations based on user profile"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'User profile data is required'}), 400
        
        user_profile = {
            'skills': data.get('skills', ''),
            'experience': data.get('experience', ''),
            'education': data.get('education', ''),
            'location': data.get('location', ''),
            'preferences': data.get('preferences', '')
        }
        
        user_id = session.get('user_id')
        recommendations = chatbot_service.get_job_recommendations(user_profile, user_id)
        
        if recommendations:
            return jsonify({
                'success': True,
                'recommendations': recommendations
            })
        else:
            return jsonify({'error': 'Failed to get recommendations'}), 500
            
    except Exception as e:
        logger.error(f"Error in recommendations endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@chatbot_bp.route('/interview-tips', methods=['POST'])
def get_interview_tips():
    """Get interview tips"""
    try:
        data = request.get_json()
        
        if not data or 'job_type' not in data:
            return jsonify({'error': 'Job type is required'}), 400
        
        job_type = data['job_type']
        experience_level = data.get('experience_level', 'entry-level')
        company = data.get('company', None)
        user_id = session.get('user_id')
        
        tips = chatbot_service.get_interview_tips(job_type, experience_level, user_id, company)
        
        if tips:
            return jsonify({
                'success': True,
                'tips': tips
            })
        else:
            return jsonify({'error': 'Failed to get interview tips'}), 500
            
    except Exception as e:
        logger.error(f"Error in interview tips endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@chatbot_bp.route('/resume-suggestions', methods=['POST'])
def get_resume_suggestions():
    """Get resume suggestions based on job description"""
    try:
        data = request.get_json()
        
        if not data or 'job_description' not in data:
            return jsonify({'error': 'Job description is required'}), 400
        
        job_description = data['job_description']
        current_resume = data.get('current_resume', None)
        user_id = session.get('user_id')
        
        suggestions = chatbot_service.get_resume_suggestions(job_description, user_id, current_resume)
        
        if suggestions:
            return jsonify({
                'success': True,
                'suggestions': suggestions
            })
        else:
            return jsonify({'error': 'Failed to get resume suggestions'}), 500
            
    except Exception as e:
        logger.error(f"Error in resume suggestions endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@chatbot_bp.route('/career-advice', methods=['POST'])
def get_career_advice():
    """Get career development advice"""
    try:
        data = request.get_json()
        
        if not data or 'current_situation' not in data or 'goals' not in data:
            return jsonify({'error': 'Current situation and goals are required'}), 400
        
        current_situation = data['current_situation']
        goals = data['goals']
        user_id = session.get('user_id')
        
        advice = chatbot_service.get_career_advice(current_situation, goals, user_id)
        
        if advice:
            return jsonify({
                'success': True,
                'advice': advice
            })
        else:
            return jsonify({'error': 'Failed to get career advice'}), 500
            
    except Exception as e:
        logger.error(f"Error in career advice endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@chatbot_bp.route('/salary-guidance', methods=['POST'])
def get_salary_guidance():
    """Get salary negotiation guidance"""
    try:
        data = request.get_json()
        
        if not data or 'role' not in data or 'experience' not in data or 'location' not in data:
            return jsonify({'error': 'Role, experience, and location are required'}), 400
        
        role = data['role']
        experience = data['experience']
        location = data['location']
        industry = data.get('industry', None)
        user_id = session.get('user_id')
        
        guidance = chatbot_service.get_salary_guidance(role, experience, location, user_id, industry)
        
        if guidance:
            return jsonify({
                'success': True,
                'guidance': guidance
            })
        else:
            return jsonify({'error': 'Failed to get salary guidance'}), 500
            
    except Exception as e:
        logger.error(f"Error in salary guidance endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@chatbot_bp.route('/session/reset', methods=['POST'])
def reset_session():
    """Reset the chatbot session"""
    try:
        user_id = session.get('user_id')
        
        # Clear user context if logged in
        if user_id:
            chatbot_service.clear_user_context(user_id)
        
        success = chatbot_service.reset_session()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Session reset successfully',
                'session_id': chatbot_service.session_id
            })
        else:
            return jsonify({'error': 'Failed to reset session'}), 500
            
    except Exception as e:
        logger.error(f"Error in session reset endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@chatbot_bp.route('/session/history', methods=['GET'])
def get_session_history():
    """Get chat session history"""
    try:
        user_id = session.get('user_id')
        
        # Get conversation summary if using AI agent
        if user_id:
            summary = chatbot_service.get_conversation_summary(user_id)
            if summary:
                return jsonify({
                    'success': True,
                    'summary': summary
                })
        
        # Fallback to ADK session history
        history = chatbot_service.get_session_history()
        
        if history:
            return jsonify({
                'success': True,
                'history': history
            })
        else:
            return jsonify({'error': 'Failed to get session history'}), 500
            
    except Exception as e:
        logger.error(f"Error in session history endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@chatbot_bp.route('/status', methods=['GET'])
def get_status():
    """Get chatbot service status"""
    try:
        return jsonify({
            'success': True,
            'status': 'active' if chatbot_service.session_id else 'inactive',
            'session_id': chatbot_service.session_id,
            'agent_name': chatbot_service.agent_name,
            'adk_url': chatbot_service.adk_base_url,
            'agent_server_url': chatbot_service.agent_server_url,
            'ai_agent_available': chatbot_service.use_ai_agent,
            'use_agent_server': chatbot_service.use_agent_server,
            'response_priority': chatbot_service.response_priority
        })
        
    except Exception as e:
        logger.error(f"Error in status endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500