"""
Chatbot Views for Estate Project
Provides API endpoints for the AI chatbot functionality
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import json


@csrf_exempt
@require_http_methods(["POST"])
def chatbot_message_api(request):
    """Handle incoming chatbot messages"""
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        
        # Simple echo response for now (can be enhanced with AI later)
        response = {
            'success': True,
            'response': f"Thank you for your message. Our chatbot is currently in development. Your message: {message}",
            'timestamp': str(data.get('timestamp', ''))
        }
        return JsonResponse(response)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def chatbot_history_api(request):
    """Get chatbot conversation history"""
    return JsonResponse({
        'success': True,
        'history': []
    })


@csrf_exempt
@require_http_methods(["POST"])
def chatbot_feedback_api(request):
    """Handle chatbot feedback"""
    try:
        data = json.loads(request.body)
        return JsonResponse({
            'success': True,
            'message': 'Feedback received successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def chatbot_clear_history_api(request):
    """Clear chatbot conversation history"""
    return JsonResponse({
        'success': True,
        'message': 'History cleared successfully'
    })


@csrf_exempt
@require_http_methods(["GET"])
def chatbot_property_summary_api(request):
    """Get property summary for chatbot"""
    return JsonResponse({
        'success': True,
        'summary': 'Property information is being prepared.'
    })


@login_required
def admin_chatbot_analytics(request):
    """Admin view for chatbot analytics"""
    context = {
        'total_conversations': 0,
        'total_messages': 0,
        'avg_messages_per_conversation': 0,
        'feedback_positive': 0,
        'feedback_negative': 0,
    }
    return render(request, 'backend/admin_chatbot_analytics.html', context)
