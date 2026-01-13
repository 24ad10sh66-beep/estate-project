"""
Simple Price Prediction for Chatbot
Add this to backend/chatbot_service.py
"""

from django.db.models import Avg, Min, Max, Count
from backend.models import PriceDataModel

def predict_property_price_simple(location, bedrooms, area_sqft, property_type):
    """
    Simple price prediction using PriceDataModel
    No ML required - just statistical analysis
    """
    
    # Find similar properties (±20% area tolerance)
    similar = PriceDataModel.objects.filter(
        location__icontains=location,
        property_type__iexact=property_type,
        bedrooms=bedrooms,
        area_sqft__range=(area_sqft * 0.8, area_sqft * 1.2)
    )
    
    if similar.exists():
        stats = similar.aggregate(
            avg_price=Avg('actual_price'),
            min_price=Min('actual_price'),
            max_price=Max('actual_price'),
            count=Count('data_id')
        )
        
        predicted_price = stats['avg_price']
        price_per_sqft = predicted_price / area_sqft
        confidence = min(stats['count'] * 5, 95)  # More samples = higher confidence
        
        return {
            'success': True,
            'predicted_price': round(predicted_price, 2),
            'price_range': {
                'min': round(stats['min_price'], 2),
                'max': round(stats['max_price'], 2)
            },
            'price_per_sqft': round(price_per_sqft, 2),
            'confidence': confidence,
            'based_on': f"{stats['count']} similar properties",
            'message': f"Based on {stats['count']} similar {property_type}s in {location}, "
                      f"predicted price is ₹{predicted_price/100000:.2f} lakhs. "
                      f"Range: ₹{stats['min_price']/100000:.2f}L - ₹{stats['max_price']/100000:.2f}L. "
                      f"Confidence: {confidence}%."
        }
    else:
        # Fallback: Get general area average
        fallback = PriceDataModel.objects.filter(
            location__icontains=location
        ).aggregate(avg_price=Avg('actual_price'))
        
        if fallback['avg_price']:
            return {
                'success': True,
                'predicted_price': fallback['avg_price'],
                'confidence': 30,
                'message': f"Limited data for exact match. General average in {location}: "
                          f"₹{fallback['avg_price']/100000:.2f} lakhs. "
                          f"More data needed for accurate prediction."
            }
        else:
            return {
                'success': False,
                'message': "Sorry, no market data available for this location yet."
            }


# HOW TO USE IN CHATBOT:
# =====================

# 1. In chatbot_service.py, add above function

# 2. Update generate_response() to detect price queries:
# NOTE: Add this code inside your ChatbotService class in backend/chatbot_service.py

# def generate_response(self, user_message, user_id=None):
#     # ... existing code ...
#     
#     # Check if user asking about price
#     if any(word in user_message.lower() for word in ['price', 'cost', 'budget', 'predict']):
#         # Extract details from message
#         filters = self.extract_search_filters(user_message)
#         
#         if filters.get('location') and filters.get('bedrooms'):
#             # Call prediction
#             prediction = predict_property_price_simple(
#                 location=filters['location'],
#                 bedrooms=filters['bedrooms'],
#                 area_sqft=filters.get('area_sqft', 1200),  # Default 1200 sqft
#                 property_type=filters.get('property_type', 'Apartment')
#             )
#             
#             if prediction['success']:
#                 # Add prediction to AI response
#                 full_prompt += f"\n\nMarket Data: {prediction['message']}"


# 3. Update system prompt to mention price prediction:
# NOTE: Add this to your ChatbotService class __init__ method

# EXAMPLE_SYSTEM_PROMPT = """You are an intelligent real estate assistant with AI-powered insights.
# 
# Key capabilities:
# - Search properties by location, price, type
# - **NEW: Predict property prices using market data**
# - Provide market insights and trends
# - Help with bookings
# 
# When user asks about prices:
# - Use the market data provided to give accurate price predictions
# - Always mention confidence level
# - Explain price ranges
# - Compare with market averages
# 
# Example queries:
# "What should be the price of 3BHK in Mumbai?"
# "Is ₹85 lakhs good for 1500 sqft apartment in Pune?"
# "Show me average prices in Bangalore"
# """


# EXAMPLE CONVERSATION:
# ====================

# User: "What should be price of 3BHK apartment in Mumbai, 1500 sqft?"
# 
# System extracts:
# - location: Mumbai
# - bedrooms: 3
# - area_sqft: 1500
# - property_type: Apartment
#
# Calls: predict_property_price_simple(Mumbai, 3, 1500, Apartment)
#
# Returns: "Based on 25 similar Apartments in Mumbai, predicted price is ₹85.5 lakhs. 
#           Range: ₹75L-₹95L. Confidence: 85%."
#
# Chatbot responds with full context + market data


# TO POPULATE DATA (Run once):
# ============================

def populate_price_data_from_properties():
    """Copy existing properties to PriceDataModel for training"""
    from backend.models import Property, PriceDataModel
    
    properties = Property.objects.all()
    count = 0
    
    for prop in properties:
        # Check if already exists
        exists = PriceDataModel.objects.filter(
            location=prop.location,
            area_sqft=prop.area_sqft,
            bedrooms=prop.bedrooms,
            actual_price=prop.price
        ).exists()
        
        if not exists:
            PriceDataModel.objects.create(
                location=prop.location,
                area_sqft=prop.area_sqft,
                bedrooms=prop.bedrooms,
                bathrooms=prop.bathrooms,
                property_type=prop.property_type,
                actual_price=prop.price
            )
            count += 1
    
    print(f"✅ Populated {count} entries into PriceDataModel")
    return count

# Run: python manage.py shell
# >>> from backend.chatbot_service import populate_price_data_from_properties
# >>> populate_price_data_from_properties()
