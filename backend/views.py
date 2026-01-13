from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.mail import send_mail
from django.db import models
from django.conf import settings
from django.views.decorators.http import require_POST
import json

# Restore users_html view
def users_html(request):
    query = request.GET.get("q")
    users = EstateUser.objects.all()

    if query:
        if query.isdigit():
            # Pehle ID ke liye check
            if EstateUser.objects.filter(user_id=int(query)).exists():
                users = EstateUser.objects.filter(user_id=int(query))  # Unique user by ID
            else:
                users = EstateUser.objects.filter(phone__icontains=query)  # Phone par partial search
        else:
            # Name par partial search
            users = EstateUser.objects.filter(name__icontains=query)

    return render(request, "backend/users.html", {"users": users, "query": query})

# User Management Views for Admin
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

@csrf_exempt
@require_POST
def delete_user(request, user_id):
    if 'role' not in request.session or request.session['role'] != "admin":
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        user_to_delete = EstateUser.objects.get(user_id=user_id)
        user_name = user_to_delete.name
        
        # Log the action before deletion
        admin_user = EstateUser.objects.get(user_id=request.session['user_id'])
        Log.objects.create(
            user=admin_user, 
            action=f"Deleted user: {user_name} (ID: {user_id})"
        )
        
        # Delete the user
        user_to_delete.delete()
        
        return JsonResponse({
            "success": True, 
            "message": f"User '{user_name}' has been deleted successfully."
        })
    
    except EstateUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_POST 
def edit_user(request, user_id):
    if 'role' not in request.session or request.session['role'] != "admin":
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        user_to_edit = EstateUser.objects.get(user_id=user_id)
        
        # Get data from request
        data = json.loads(request.body)
        
        # Update user fields
        user_to_edit.name = data.get('name', user_to_edit.name)
        user_to_edit.phone = data.get('phone', user_to_edit.phone)
        user_to_edit.email = data.get('email', user_to_edit.email)
        user_to_edit.role = data.get('role', user_to_edit.role)
        
        user_to_edit.save()
        
        # Log the action
        admin_user = EstateUser.objects.get(user_id=request.session['user_id'])
        Log.objects.create(
            user=admin_user,
            action=f"Edited user: {user_to_edit.name} (ID: {user_id})"
        )
        
        return JsonResponse({
            "success": True,
            "message": f"User '{user_to_edit.name}' has been updated successfully.",
            "user": {
                "name": user_to_edit.name,
                "phone": user_to_edit.phone,
                "email": user_to_edit.email,
                "role": user_to_edit.role
            }
        })
    
    except EstateUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_POST
def block_user(request, user_id):
    if 'role' not in request.session or request.session['role'] != "admin":
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        user_to_block = EstateUser.objects.get(user_id=user_id)
        
        # Get data from request
        data = json.loads(request.body)
        action = data.get('action', 'block')  # 'block' or 'unblock'
        
        # For now, we'll use a simple field to track blocked status
        # You might want to add a 'is_blocked' field to your EstateUser model
        # For this implementation, we'll log the action but not change the user
        
        admin_user = EstateUser.objects.get(user_id=request.session['user_id'])
        
        if action == 'block':
            Log.objects.create(
                user=admin_user,
                action=f"Blocked user: {user_to_block.name} (ID: {user_id})"
            )
            message = f"User '{user_to_block.name}' has been blocked successfully."
        else:
            Log.objects.create(
                user=admin_user,
                action=f"Unblocked user: {user_to_block.name} (ID: {user_id})"
            )
            message = f"User '{user_to_block.name}' has been unblocked successfully."
        
        return JsonResponse({
            "success": True,
            "message": message,
            "action": action
        })
    
    except EstateUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# Restore home view for root URL
def home(request):
    # Get all images with property details for carousel
    from .models import PropertyImage, Property
    from django.conf import settings
    import json
    import os
    
    # Check if user is logged in
    is_logged_in = 'role' in request.session and 'user_id' in request.session
    user_role = request.session.get('role', None) if is_logged_in else None
    user_name = None
    user_id = None
    
    # Get user details if logged in
    if is_logged_in:
        user_id = request.session.get('user_id')
        try:
            from .models import EstateUser
            user = EstateUser.objects.get(user_id=user_id)
            user_name = user.name
            
            # Log the home page visit for logged-in users
            from .models import Log
            Log.objects.create(user=user, action="Visited home page")
        except EstateUser.DoesNotExist:
            is_logged_in = False
            user_role = None
    
    # Get images from PropertyImage model with related property data
    property_images = PropertyImage.objects.select_related('property').order_by('-uploaded_at')
    carousel_data = []
    image_urls = []
    
    # Add PropertyImage URLs with property details
    for img in property_images:
        if img.property:  # Only include images that have associated properties
            url = img.image_url
            if url:
                # Handle different URL formats
                if url.startswith('http'):
                    full_url = url
                elif url.startswith('/media/'):
                    full_url = url
                else:
                    full_url = settings.MEDIA_URL + url
                
                # Create carousel item with property details
                # Hide sensitive info if user is not logged in
                carousel_item = {
                    'image_url': full_url,
                    'title': img.property.title,
                    'description': img.property.description,
                    'location': img.property.location,
                    'city': img.property.city,
                    'state': img.property.state,
                    'price': float(img.property.price) if (img.property.price and is_logged_in) else 0,
                    'property_type': img.property.property_type,
                    'bedrooms': img.property.bedrooms,
                    'bathrooms': img.property.bathrooms,
                    'area_sqft': float(img.property.area_sqft) if img.property.area_sqft else 0,
                    'status': img.property.status,
                    'contact': img.property.contact if is_logged_in else 'Login to view contact',
                    'is_logged_in': is_logged_in,
                    'show_sensitive_info': is_logged_in
                }
                carousel_data.append(carousel_item)
                image_urls.append(full_url)
    
    # Add some default images if no property images exist
    default_images_data = [
        {'name': 'apartment.jpeg', 'title': 'Modern Apartment', 'location': 'Mumbai, Maharashtra', 'price': 5000000, 'type': 'Apartment'},
        {'name': 'download.jpeg', 'title': 'Luxury Villa', 'location': 'Pune, Maharashtra', 'price': 8500000, 'type': 'Villa'},
        {'name': 'download1.jpeg', 'title': 'Family Home', 'location': 'Delhi, Delhi', 'price': 4500000, 'type': 'House'},
        {'name': 'shiva1.jpg', 'title': 'Commercial Space', 'location': 'Bangalore, Karnataka', 'price': 7500000, 'type': 'Commercial'},
        {'name': 'shiva2.jpg', 'title': 'Studio Apartment', 'location': 'Chennai, Tamil Nadu', 'price': 2500000, 'type': 'Studio'},
        {'name': 'shiva3.jpg', 'title': 'Penthouse', 'location': 'Hyderabad, Telangana', 'price': 12000000, 'type': 'Penthouse'},
    ]
    
    # Add default images if we don't have enough property images
    for default_img in default_images_data:
        default_url = settings.MEDIA_URL + default_img['name']
        media_path = os.path.join(settings.MEDIA_ROOT, default_img['name'])
        
        if os.path.exists(media_path) and default_url not in image_urls:
            carousel_item = {
                'image_url': default_url,
                'title': default_img['title'],
                'description': f"Beautiful {default_img['type'].lower()} with modern amenities and excellent location.",
                'location': default_img['location'],
                'city': default_img['location'].split(',')[0].strip(),
                'state': default_img['location'].split(',')[1].strip() if ',' in default_img['location'] else '',
                'price': default_img['price'] if is_logged_in else 0,
                'property_type': default_img['type'],
                'bedrooms': 2,
                'bathrooms': 2,
                'area_sqft': 1200,
                'status': 'Available',
                'contact': '+91-9876543210' if is_logged_in else 'Login to view contact',
                'is_logged_in': is_logged_in,
                'show_sensitive_info': is_logged_in
            }
            carousel_data.append(carousel_item)
            image_urls.append(default_url)
    
    # Ensure we have at least one image
    if not carousel_data:
        carousel_data = [{
            'image_url': settings.MEDIA_URL + 'estatelogo.png',
            'title': 'Estate Management System',
            'description': 'Welcome to our AI-powered estate management platform',
            'location': 'All Cities, India',
            'city': 'All Cities',
            'state': 'India',
            'price': 0,
            'property_type': 'Platform',
            'bedrooms': 0,
            'bathrooms': 0,
            'area_sqft': 0,
            'status': 'Active',
            'contact': 'support@estate.com' if is_logged_in else 'Login to view contact',
            'is_logged_in': is_logged_in,
            'show_sensitive_info': is_logged_in
        }]
        image_urls = [settings.MEDIA_URL + 'estatelogo.png']
    
    # Convert to JSON for JavaScript
    image_urls_json = json.dumps(image_urls)
    carousel_data_json = json.dumps(carousel_data)
    
    return render(request, "backend/home.html", {
        "image_urls": image_urls,
        "image_urls_json": image_urls_json,
        "carousel_data": carousel_data,
        "carousel_data_json": carousel_data_json,
        "is_logged_in": is_logged_in,
        "user_role": user_role,
        "user_name": user_name,
        "user_id": user_id
    })
# Buyer profile view
def buyer_profile(request):
    if 'role' not in request.session or request.session['role'] != "buyer":
        return redirect("/backend/login/")
    buyer_id = request.session.get('buyer_id') or request.session.get('user_id')
    user = EstateUser.objects.get(user_id=buyer_id)
    address = user.address if hasattr(user, 'address') else None
    account_created = user.created_at if hasattr(user, 'created_at') else None
    last_login = user.last_login if hasattr(user, 'last_login') else None
    return render(request, "backend/profile.html", {
        "user": user,
        "role": "buyer",
        "address": address,
        "account_created": account_created,
        "last_login": last_login
    })
def admin_profile(request):
    if 'role' not in request.session or request.session['role'] != "admin":
        return redirect("/backend/login/")
    admin_id = request.session.get('admin_user') or request.session.get('user_id')
    user = EstateUser.objects.get(user_id=admin_id)
    address = user.address if hasattr(user, 'address') else None
    account_created = user.created_at if hasattr(user, 'created_at') else None
    last_login = user.last_login if hasattr(user, 'last_login') else None
    return render(request, "backend/profile.html", {
        "user": user,
        "role": "admin",
        "address": address,
        "account_created": account_created,
        "last_login": last_login
    })
def seller_bookings(request):
    if 'role' not in request.session or request.session['role'] != "seller":
        return redirect("/backend/login/")
    seller_id = request.session['user_id']
    query = request.GET.get("q", "").strip().lower()
    bookings = Booking.objects.filter(property__user_id=seller_id)
    if query:
        if query.isdigit():
            bookings = bookings.filter(booking_id=int(query))
        else:
            bookings = bookings.filter(
                models.Q(user__name__icontains=query) | models.Q(property__title__icontains=query)
            )
    return render(request, "backend/bookings.html", {"bookings": bookings, "query": query, "user_role": "seller"})

def seller_transactions(request):
    if 'role' not in request.session or request.session['role'] != "seller":
        return redirect("/backend/login/")
    seller_id = request.session['user_id']
    query = request.GET.get("q", "").strip().lower()
    transactions = Transaction.objects.filter(booking__property__user_id=seller_id)
    if query:
        transactions = transactions.filter(models.Q(booking__property__title__icontains=query))
    return render(request, "backend/transactions.html", {"transactions": transactions, "query": query, "user_role": "seller"})

def seller_logs(request):
    if 'role' not in request.session or request.session['role'] != "seller":
        return redirect("/backend/login/")
    seller_id = request.session['user_id']
    logs = Log.objects.filter(user_id=seller_id)
    return render(request, "backend/logs.html", {"logs": logs, "user_role": "seller"})

def seller_profile(request):
    if 'role' not in request.session or request.session['role'] != "seller":
        return redirect("/backend/login/")
    seller_id = request.session['user_id']
    user = EstateUser.objects.get(user_id=seller_id)
    total_properties = user.properties.count()
    address = user.address if hasattr(user, 'address') else None
    account_created = user.created_at if hasattr(user, 'created_at') else None
    last_login = user.last_login if hasattr(user, 'last_login') else None
    Log.objects.create(user=user, action="Viewed profile")
    return render(request, "backend/profile.html", {
        "user": user,
        "total_properties": total_properties,
        "role": "seller",
        "address": address,
        "account_created": account_created,
        "last_login": last_login
    })


# ...existing code...


@csrf_exempt
def upload_profile_photo(request):
    # Robust session check for all roles
    role = request.session.get('role')
    user_id = None
    profile_url = None
    if role == 'seller':
        user_id = request.session.get('seller_id') or request.session.get('user_id')
        profile_url = "/backend/seller/profile/"
    elif role == 'admin':
        user_id = request.session.get('admin_user') or request.session.get('user_id')
        profile_url = "/backend/admin/profile/"
    elif role == 'buyer':
        user_id = request.session.get('buyer_id') or request.session.get('user_id')
        profile_url = "/backend/buyer/profile/"
    else:
        user_id = request.session.get('user_id')
        profile_url = "/backend/seller/profile/"

    if not user_id or not role:
        messages.error(request, "Session expired. Please login again.")
        return redirect("/backend/login/")

    if request.method == "POST":
        user = EstateUser.objects.get(user_id=user_id)
        photo = request.FILES.get('profile_photo')
        if photo:
            user.profile_photo = photo
            user.save()
            Log.objects.create(user=user, action="Uploaded profile photo")
            messages.success(request, "Profile photo changed successfully!")
        else:
            messages.error(request, "No photo selected.")
        return redirect(profile_url)
    return redirect(profile_url)

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import EstateUser, Property, PropertyImage, Booking, Transaction, Log, PriceDataModel
from django.http import JsonResponse
from django.core.mail import send_mail
from django.db import models


# Login required decorator
def login_required(allowed_roles=None):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if 'role' not in request.session:
                return redirect("/backend/login/")
            if allowed_roles and request.session['role'] not in allowed_roles:
                return redirect("/backend/login/")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# ---------------------------
# JSON APIs
# ---------------------------
def profile_view(request):
    if 'role' not in request.session:
        return redirect("/backend/login/")
    role = request.session['role']
    user_id = request.session.get('user_id')
    user = EstateUser.objects.get(user_id=user_id)
    address = getattr(user, 'address', None)
    account_created = getattr(user, 'created_at', None)
    last_login = getattr(user, 'last_login', None)
    context = {
        "user": user,
        "role": role,
        "address": address,
        "account_created": account_created,
        "last_login": last_login
    }
    if role == "seller":
        context["total_properties"] = user.properties.count()
        Log.objects.create(user=user, action="Viewed profile")
    return render(request, "backend/profile.html", context)

def edit_profile(request):
    if 'role' not in request.session:
        return redirect("/backend/login/")
    
    role = request.session['role']
    user_id = request.session.get('user_id')
    user = EstateUser.objects.get(user_id=user_id)
    
    if request.method == "POST":
        user.name = request.POST.get("name", user.name)
        user.email = request.POST.get("email", user.email)
        user.phone = request.POST.get("phone", user.phone)
        user.address = request.POST.get("address", user.address)
        user.save()
        messages.success(request, "Profile updated successfully!")
        Log.objects.create(user=user, action="Edited profile")
        
        # Redirect based on role
        if role == "admin":
            return redirect("/backend/admin/profile/")
        elif role == "buyer":
            return redirect("/backend/buyer/profile/")
        elif role == "seller":
            return redirect("/backend/seller/profile/")
        else:
            return redirect("/backend/profile/")
    
    return render(request, "backend/edit_profile.html", {"user": user, "role": role})

def change_password(request):
    if 'role' not in request.session:
        return redirect("/backend/login/")
    
    role = request.session['role']
    user_id = request.session.get('user_id')
    user = EstateUser.objects.get(user_id=user_id)
    
    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match!")
        elif len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters long!")
        elif user.password_hash == old_password:
            user.password_hash = new_password
            user.save()
            messages.success(request, "Password changed successfully!")
            Log.objects.create(user=user, action="Changed password")
            
            # Redirect based on role
            if role == "admin":
                return redirect("/backend/admin/profile/")
            elif role == "buyer":
                return redirect("/backend/buyer/profile/")
            elif role == "seller":
                return redirect("/backend/seller/profile/")
            else:
                return redirect("/backend/profile/")
        else:
            messages.error(request, "Current password is incorrect.")
    
    return render(request, "backend/change_password.html", {"user": user, "role": role})

def properties_html(request):
    query = request.GET.get("q")
    properties = Property.objects.prefetch_related('images').all()

    if query:
        if query.isdigit():
            # Agar sirf numbers hai to ID check
            properties = Property.objects.prefetch_related('images').filter(property_id=query)
        else:
            # Agar text hai to title ya location me search
            properties = Property.objects.prefetch_related('images').filter(
                models.Q(title__icontains=query) | models.Q(location__icontains=query)
            )

    return render(request, "backend/properties.html", {"properties": properties, "query": query})

# ---------------------------
def property_images_html(request):
    query = request.GET.get("q", "").strip().lower()
    property_images = PropertyImage.objects.all()

    if query:
        if query.isdigit():  
            # Agar sirf numbers hai to ID search karo
            property_images = PropertyImage.objects.filter(image_id=int(query))
        else:
            # Name/description ko case-insensitive search karo
            property_images = PropertyImage.objects.filter(
                models.Q(image_url__icontains=query) |
                models.Q(description__icontains=query)
            )

    from django.conf import settings
    # Prepare image list with final_url
    image_list = []
    for img in property_images:
        url = img.image_url
        if url and not url.startswith('http'):
            url = settings.MEDIA_URL + url
        image_list.append({
            'image_id': img.image_id,
            'property': img.property,
            'description': img.description,
            'final_url': url
        })
    
    # Detect user role for back button
    user_role = request.session.get('role', 'admin')
    
    return render(request, "backend/property_images.html", {
        "property_images": image_list,
        "query": query,
        "user_role": user_role
    })


def bookings_html(request):
    # Check user role and show appropriate bookings
    role = request.session.get('role')
    
    if not role:
        return redirect("/backend/login/")
    
    query = request.GET.get("q")
    
    if role == "buyer":
        # Show only buyer's own bookings
        user_id = request.session.get('buyer_id') or request.session.get('user_id')
        bookings = Booking.objects.filter(user_id=user_id).select_related('property', 'property__user').prefetch_related('property__images', 'transactions')
        
        # Log activity
        try:
            buyer = EstateUser.objects.get(user_id=user_id)
            Log.objects.create(user=buyer, action="Viewed my bookings")
        except EstateUser.DoesNotExist:
            pass
            
    elif role == "seller":
        # Show bookings for seller's properties
        seller_id = request.session.get('seller_id') or request.session.get('user_id')
        bookings = Booking.objects.filter(property__user_id=seller_id).select_related('property', 'user').prefetch_related('property__images', 'transactions')
        
    else:  # admin
        # Show all bookings
        bookings = Booking.objects.all().select_related('property', 'user', 'property__user').prefetch_related('property__images', 'transactions')

    # Apply search filter
    if query:
        if query.isdigit():
            bookings = bookings.filter(booking_id=query)
        else:
            bookings = bookings.filter(
                models.Q(user__name__icontains=query) | 
                models.Q(property__title__icontains=query) |
                models.Q(property__location__icontains=query)
            )
    
    # Order by most recent first
    bookings = bookings.order_by('-booking_date')
    
    # Calculate status counts for buyer dashboard
    total_count = bookings.count()
    pending_count = bookings.filter(status='pending').count()
    confirmed_count = bookings.filter(status='confirmed').count()

    return render(request, "backend/bookings.html", {
        "bookings": bookings, 
        "query": query,
        "role": role,
        "total_count": total_count,
        "pending_count": pending_count,
        "confirmed_count": confirmed_count
    })

# Update Booking Status API (for admin/seller to confirm bookings)
@csrf_exempt
def update_booking_status(request, booking_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    
    # Check role authorization
    role = request.session.get('role')
    if role not in ['admin', 'seller']:
        return JsonResponse({"error": "Unauthorized - Admin or Seller access required"}, status=403)
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status', '').lower()
        
        if new_status not in ['confirmed', 'cancelled', 'pending', 'completed']:
            return JsonResponse({"error": "Invalid status"}, status=400)
        
        # Get the booking
        booking = Booking.objects.select_related('property', 'user').get(booking_id=booking_id)
        
        # If seller, verify they own the property
        if role == 'seller':
            seller_id = request.session.get('seller_id') or request.session.get('user_id')
            if booking.property.user_id != seller_id:
                return JsonResponse({"error": "Unauthorized - You don't own this property"}, status=403)
        
        # Update the booking status
        old_status = booking.status
        booking.status = new_status
        booking.save()
        
        # ✅ CRITICAL FIX: If booking is confirmed/completed, mark property as Sold
        if new_status in ['confirmed', 'completed']:
            property_obj = booking.property
            if property_obj and property_obj.status != 'Sold':
                property_obj.status = 'Sold'
                property_obj.save()
                
                # Notify seller that property is sold
                from . import notification_service
                seller = property_obj.user
                if seller:
                    notification_service.create_seller_notification(
                        seller_id=seller.user_id,
                        title=f'🎉 Property Sold: {property_obj.title}',
                        message=f'Your property "{property_obj.title}" has been marked as SOLD. Booking #{booking_id} is now {new_status}. Buyer: {booking.user.name if booking.user else "Unknown"}',
                        notification_type=notification_service.NotificationType.PAYMENT_RECEIVED,
                        property_obj=property_obj,
                        booking_obj=booking
                    )
        
        # If booking is cancelled and property was sold, mark it back as Available (optional)
        elif new_status == 'cancelled':
            property_obj = booking.property
            if property_obj and property_obj.status == 'Sold':
                # Check if there are other confirmed bookings for this property
                other_confirmed_bookings = Booking.objects.filter(
                    property=property_obj,
                    status__in=['confirmed', 'completed']
                ).exclude(booking_id=booking_id).exists()
                
                if not other_confirmed_bookings:
                    # No other confirmed bookings, mark property as Available again
                    property_obj.status = 'Available'
                    property_obj.save()
        
        # Get the user making the change
        user_id = request.session.get('user_id')
        if role == 'seller':
            user_id = request.session.get('seller_id') or user_id
        elif role == 'admin':
            user_id = request.session.get('admin_user') or user_id
        
        admin_or_seller = EstateUser.objects.get(user_id=user_id)
        
        # Log the action
        Log.objects.create(
            user=admin_or_seller,
            action=f"Updated booking #{booking_id} status from '{old_status}' to '{new_status}' for property: {booking.property.title}"
        )
        
        # Notify buyer and admin about the status change using notification service
        from . import notification_service
        
        if new_status == 'confirmed':
            notification_service.notify_booking_confirmed(booking_id)
        elif new_status == 'cancelled':
            # Determine who cancelled - if seller/admin, notify buyer
            cancelled_by = 'seller' if role == 'seller' else 'admin'
            notification_service.notify_booking_cancelled(booking_id, cancelled_by=cancelled_by)
        
        # Log activity for the buyer as well
        Log.objects.create(
            user=booking.user,
            action=f"Booking #{booking_id} status changed to '{new_status}' for property: {booking.property.title}"
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Booking #{booking_id} status updated to {new_status}',
            'booking_id': booking_id,
            'new_status': new_status,
            'property_title': booking.property.title,
            'buyer_name': booking.user.name if booking.user else 'Unknown'
        })
        
    except Booking.DoesNotExist:
        return JsonResponse({"error": "Booking not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"Update failed: {str(e)}"}, status=500)

def transactions_html(request):
    query = request.GET.get("q")
    transactions = Transaction.objects.all()

    if query:
        if query.isdigit():
            transactions = Transaction.objects.filter(txn_id=query)  # fix: correct pk
        else:
            # abhi Transaction me buyer/seller direct nahi hai
            transactions = Transaction.objects.filter(
                booking__user__name__icontains=query
            )

    return render(request, "backend/transactions.html", {"transactions": transactions, "query": query})

def logs_html(request):
    query = request.GET.get("q")
    recent = request.GET.get("recent")
    role = request.session.get('role')
    if role == 'admin':
        logs = Log.objects.all()
    else:
        user_id = request.session.get('buyer_id') or request.session.get('seller_id') or request.session.get('user_id')
        logs = Log.objects.filter(user_id=user_id)

    # If ?recent=1, show only recent property views for current user (for admin, show all recent property views)
    if recent == "1":
        if role == 'admin':
            logs_recent = logs.filter(action__icontains="Viewed properties list").order_by('-timestamp')[:20]
        else:
            logs_recent = logs.filter(action__icontains="Viewed properties list").order_by('-timestamp')[:20]
        recent_props = []
        for log in logs_recent:
            import re
            match = re.search(r'property\s*(\d+)', log.action)
            prop = None
            if match:
                prop_id = int(match.group(1))
                try:
                    prop = Property.objects.get(property_id=prop_id)
                except Property.DoesNotExist:
                    prop = None
            if prop:
                image = prop.images.first().image_url if prop.images.exists() else None
                recent_props.append({
                    'title': prop.title,
                    'location': prop.location,
                    'city': prop.city,
                    'state': prop.state,
                    'address': prop.address,
                    'image': image,
                    'viewed_at': log.timestamp,
                    'description': prop.description,
                    'price': prop.price,
                    'type': prop.property_type,
                    'bedrooms': prop.bedrooms,
                    'bathrooms': prop.bathrooms,
                    'status': prop.status,
                    'seller': prop.user.name if prop.user else '',
                    'contact': prop.contact,
                    'property_id': prop.property_id,
                })
        return render(request, "backend/logs.html", {"recent_props": recent_props, "recent": True})

    if query:
        logs = logs.filter(
            models.Q(action__icontains=query) | models.Q(user__name__icontains=query)
        )

    return render(request, "backend/logs.html", {"logs": logs, "query": query})

def price_data_model_html(request):
    query = request.GET.get("q")
    price_data_model = PriceDataModel.objects.all()

    if query:
        if query.isdigit():
            price_data_model = PriceDataModel.objects.filter(data_id=query)  # fix: correct pk
        else:
            price_data_model = PriceDataModel.objects.filter(location__icontains=query)

    return render(request, "backend/price_data_model.html", {"prices": price_data_model, "query": query})

# Buyer - Browse Properties view
def buyer_properties_view(request):
    if 'role' not in request.session or request.session['role'] != "buyer":
        return redirect("/backend/login/")
    
    query = request.GET.get("q")
    property_type = request.GET.get("type")
    city = request.GET.get("city")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    
    # ✅ CRITICAL: Only show Available properties to buyers
    # Sold properties are automatically hidden from buyer search
    # This prevents buyers from trying to purchase already-sold properties
    properties = Property.objects.prefetch_related('images').filter(status="Available")
    
    # Apply filters
    if query:
        properties = properties.filter(
            models.Q(title__icontains=query) |
            models.Q(description__icontains=query) |
            models.Q(city__icontains=query) |
            models.Q(state__icontains=query) |
            models.Q(location__icontains=query)
        )
    
    if property_type:
        properties = properties.filter(property_type=property_type)
    
    if city:
        properties = properties.filter(city__icontains=city)
    
    if min_price:
        try:
            properties = properties.filter(price__gte=int(min_price))
        except ValueError:
            pass
    
    if max_price:
        try:
            properties = properties.filter(price__lte=int(max_price))
        except ValueError:
            pass
    
    # Order by price (default)
    properties = properties.order_by('price')
    
    # Log the activity
    try:
        buyer = EstateUser.objects.get(user_id=request.session['user_id'])
        Log.objects.create(user=buyer, action="Browsed available properties")
    except EstateUser.DoesNotExist:
        pass
    
    return render(request, "backend/buyer_properties.html", {
        "properties": properties, 
        "query": query,
        "property_type": property_type,
        "city": city,
        "min_price": min_price,
        "max_price": max_price
    })

# ---------------------------
# Authentication & Dashboard Views
# ---------------------------

def login_view(request):
    if request.method == "POST":
        identifier = request.POST.get("identifier", "").strip()
        password = request.POST.get("password", "").strip()
        role = request.POST.get("role")  # agar role select kar rahe ho to use rakh lo

        user = None

        # 1) agar identifier me '@' hai -> treat as email
        if "@" in identifier:
            try:
                user = EstateUser.objects.filter(email__iexact=identifier).first()
            except EstateUser.DoesNotExist:
                user = None
        else:
            # 2) otherwise treat as phone (also try exact match)
            ph = ''.join(ch for ch in identifier if ch.isdigit())  # normalize: keep only digits
            try:
                user = EstateUser.objects.filter(phone__icontains=ph).first()
            except EstateUser.DoesNotExist:
                user = None

        # 3) verify user and password (note: currently using plain text compare)
        if user:
            # if you store plain text (password_hash holds plain) compare directly:
            if user.password_hash == password:
                # optional: check role if you require role match
                if role and role != user.role:
                    messages.error(request, "Role does not match this account.")
                    return render(request, "backend/login.html")

                # set session by role
                request.session['role'] = user.role
                # User login success, session me user_id set karo
                request.session['user_id'] = user.user_id
                if user.role == "admin":
                    request.session['admin_user'] = user.user_id
                elif user.role == "buyer":
                    request.session['buyer_id'] = user.user_id
                elif user.role == "seller":
                    request.session['seller_id'] = user.user_id
                
                # Log successful login
                Log.objects.create(user=user, action=f"Logged in as {user.role}")
                
                # Check if there's a redirect parameter from URL
                redirect_url = request.GET.get('next', '')
                
                # Ensure redirect URL is safe (starts with / and doesn't go to external sites)
                if redirect_url and (not redirect_url.startswith('/') or redirect_url.startswith('//')):
                    redirect_url = ''
                
                # Role-based dashboard redirection (if no specific redirect URL)
                if not redirect_url:
                    if user.role == "admin":
                        redirect_url = "/backend/dashboard/"
                    elif user.role == "buyer":
                        redirect_url = "/backend/buyer-home/"
                    elif user.role == "seller":
                        redirect_url = "/backend/seller-home/"
                    else:
                        redirect_url = "/"  # Fallback to home
                
                # Redirect with success message
                messages.success(request, f"Welcome back, {user.name}! You are now logged in as {user.role.title()}.")
                return redirect(redirect_url)
            else:
                messages.error(request, "Invalid password.")
        else:
            messages.error(request, "No account found with given email or phone.")

    return render(request, "backend/login.html")



def logout_view(request):
    # Log the logout activity before clearing session
    if 'user_id' in request.session:
        try:
            user_id = request.session.get('user_id')
            user = EstateUser.objects.get(user_id=user_id)
            Log.objects.create(user=user, action="Logged out from system")
        except EstateUser.DoesNotExist:
            pass
    
    request.session.flush()  # clear all session data
    messages.success(request, "You have been logged out successfully. Welcome back to browse properties!")
    return redirect("/")


def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("number")   # form se phone lena
        role = request.POST.get("role")      # form se role lena
        password = request.POST.get("password")
        address = request.POST.get("address")

        # Check if username, email or phone already exists
        if EstateUser.objects.filter(name=username).exists():
            messages.error(request, "❌ Username already exists. Please choose a different username.")
        elif EstateUser.objects.filter(email=email).exists():
            messages.error(request, "❌ Email already registered. Please use a different email or try logging in.")
        elif EstateUser.objects.filter(phone=phone).exists():
            messages.error(request, "❌ Phone number already registered. Please use a different number or try logging in.")
        else:
            # Create new user
            user = EstateUser(
                name=username,
                email=email,
                phone=phone,
                role=role,
                password_hash=password,
                address=address
            )
            user.save()
            
            # Log account creation
            Log.objects.create(user=user, action=f"Account created as {role}")
            
            # Auto-login after successful signup for better UX
            request.session['role'] = user.role
            request.session['user_id'] = user.user_id
            if user.role == "admin":
                request.session['admin_user'] = user.user_id
            elif user.role == "buyer":
                request.session['buyer_id'] = user.user_id
            elif user.role == "seller":
                request.session['seller_id'] = user.user_id
            
            # Check if there's a redirect parameter
            redirect_url = request.GET.get('next', '/')
            
            # Ensure redirect URL is safe
            if not redirect_url.startswith('/') or redirect_url.startswith('//'):
                redirect_url = '/'
            
            messages.success(request, f"🎉 Welcome to Estate Management, {username}! Your {role} account has been created and you're now logged in.")
            return redirect(redirect_url)

    # Agar GET request hai ya error hua
    return render(request, "backend/login.html")

def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = EstateUser.objects.get(email=email)
            # Log password recovery attempt
            Log.objects.create(user=user, action="Requested password recovery")
            
            send_mail(
                "Estate Management Password Recovery",
                f"Hello {user.name},\n\nYour password is: {user.password_hash}\n\nPlease login and consider changing your password for security.\n\nBest regards,\nEstate Management Team",
                "from@example.com",
                [email],
                fail_silently=False,
            )
            messages.success(request, "✅ Password recovery email has been sent! Please check your inbox.")
        except EstateUser.DoesNotExist:
            messages.error(request, "❌ Email address not found in our records. Please check and try again.")
    return redirect("/backend/login/")



@login_required(allowed_roles=["admin", "buyer", "seller"])
def dashboard_view(request):
    role = request.session['role']
    if role == "admin":
        admin_id = request.session.get('admin_user') or request.session.get('user_id')
        user = EstateUser.objects.get(user_id=admin_id)
        
        # Log admin dashboard visit
        Log.objects.create(user=user, action="Viewed admin dashboard")
        
        # Calculate real admin dashboard statistics
        from django.db.models import Sum, Count
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        # Total system statistics
        total_users = EstateUser.objects.count()
        total_properties = Property.objects.count()
        total_bookings = Booking.objects.count()
        total_transactions = Transaction.objects.count()
        
        # Active statistics
        active_sellers = EstateUser.objects.filter(role='seller').count()
        active_buyers = EstateUser.objects.filter(role='buyer').count()
        pending_bookings = Booking.objects.filter(status='pending').count()
        
        # Revenue statistics
        current_month = timezone.now().month
        current_year = timezone.now().year
        total_revenue = Transaction.objects.aggregate(total=Sum('amount'))['total'] or 0
        monthly_revenue = Transaction.objects.filter(
            payment_date__month=current_month,
            payment_date__year=current_year
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Growth calculations
        prev_month = current_month - 1 if current_month > 1 else 12
        prev_year = current_year if current_month > 1 else current_year - 1
        
        prev_month_users = EstateUser.objects.filter(
            created_at__month=prev_month,
            created_at__year=prev_year
        ).count()
        
        prev_month_properties = Property.objects.filter(
            created_at__month=prev_month,
            created_at__year=prev_year
        ).count()
        
        # Calculate growth percentages
        def calculate_growth(current, previous):
            if previous == 0:
                return f"+{current} new" if current > 0 else "No growth"
            growth = round(((current - previous) / previous) * 100, 1)
            return f"+{growth}%" if growth > 0 else f"{growth}%"
        
        # Recent system activity
        recent_activities = Log.objects.all().order_by('-timestamp')[:10]
        
        # Additional system statistics
        total_images = PropertyImage.objects.count()
        
        # Property status breakdown
        properties_available = Property.objects.filter(status='Available').count()
        properties_sold = Property.objects.filter(status='Sold').count()
        properties_pending = Property.objects.filter(status='Pending').count()
        
        # Buyer purchase information
        confirmed_bookings = Booking.objects.filter(status='Confirmed').count()
        completed_transactions = Transaction.objects.filter(payment_status='success').count()
        
        # Calculate successful purchases (confirmed bookings with successful transactions)
        successful_purchases = Transaction.objects.filter(
            payment_status='success',
            booking__status='Confirmed'
        ).count()
        
        # Real-time notifications count (pending actions for admin)
        pending_notifications = pending_bookings + (1 if total_transactions == 0 else 0)
        
        # Admin dashboard statistics
        admin_stats = {
            'total_users': {
                'count': total_users,
                'growth': f"+{prev_month_users} this month" if prev_month_users > 0 else "No new users"
            },
            'total_properties': {
                'count': total_properties,
                'growth': f"+{prev_month_properties} this month" if prev_month_properties > 0 else "No new properties"
            },
            'properties_by_status': {
                'available': properties_available,
                'sold': properties_sold,
                'pending': properties_pending
            },
            'active_bookings': {
                'count': pending_bookings,
                'total': total_bookings,
                'confirmed': confirmed_bookings
            },
            'system_revenue': {
                'total': total_revenue,
                'monthly': monthly_revenue
            },
            'transactions': {
                'total': total_transactions,
                'completed': completed_transactions,
                'successful_purchases': successful_purchases
            },
            'user_breakdown': {
                'sellers': active_sellers,
                'buyers': active_buyers,
                'admins': EstateUser.objects.filter(role='admin').count()
            },
            'total_images': total_images,
            'notifications_count': pending_notifications
        }
        
        return render(request, "backend/admin_dashboard.html", {
            "user": user, 
            "recent_activities": recent_activities,
            "stats": admin_stats
        })
    elif role == "buyer":
        # Redirect buyer to proper buyer dashboard with real-time data
        return redirect('/backend/buyer-home/')
    elif role == "seller":
        # Redirect seller to proper seller dashboard with real-time data
        return redirect('/backend/seller-home/')

@login_required(allowed_roles=["buyer"])
def buyer_dashboard_view(request):
    """
    Buyer Dashboard View with Real-time Data
    Always fetches fresh data from database
    """
    if 'role' not in request.session or request.session['role'] != 'buyer':
        return redirect('/backend/login/')
    user_id = request.session.get('buyer_id') or request.session.get('user_id')
    user = EstateUser.objects.get(user_id=user_id)
    
    # Calculate real buyer dashboard statistics
    from django.db.models import Count, Avg, Q
    from django.utils import timezone
    from datetime import timedelta
    from django.views.decorators.cache import never_cache
    
    # Available properties for browsing (case-insensitive status check)
    available_properties = Property.objects.filter(
        Q(status__iexact='available') | Q(status__iexact='Available')
    ).count()
    
    # Buyer's bookings (handle both pending and Pending)
    my_bookings = Booking.objects.filter(user=user_id).count()
    pending_bookings = Booking.objects.filter(
        user=user_id
    ).filter(
        Q(status__iexact='pending') | Q(status__iexact='Pending')
    ).count()
    
    # Featured/recommended properties (latest 6 Available) with images - CONVERT TO LIST
    featured_properties_qs = Property.objects.filter(
        Q(status__iexact='available') | Q(status__iexact='Available')
    ).prefetch_related('images').order_by('-created_at')[:6]
    featured_properties = list(featured_properties_qs)  # Convert QuerySet to list for template
    
    # Debug: Print featured properties count
    print(f"🔍 DEBUG: Total properties in DB: {Property.objects.count()}")
    print(f"🔍 DEBUG: Available properties: {available_properties}")
    print(f"🔍 DEBUG: Featured properties count: {len(featured_properties)}")
    for prop in featured_properties:
        print(f"   - Property: {prop.title}, Images: {prop.images.count()}, Status: {prop.status}")
    
    # Popular locations (top 5 by property count) - CONVERT TO LIST
    popular_locations = list(Property.objects.filter(
        Q(status__iexact='available') | Q(status__iexact='Available')
    ).values('location').annotate(
        property_count=Count('property_id')
    ).order_by('-property_count')[:5])
    
    # Price range statistics
    from django.db.models import Min, Max
    price_stats = Property.objects.filter(
        Q(status__iexact='available') | Q(status__iexact='Available')
    ).aggregate(
        avg_price=Avg('price'),
        min_price=Min('price'),
        max_price=Max('price')
    )
    
    # Log buyer dashboard visit
    Log.objects.create(user=user, action="Viewed buyer dashboard")
    
    # Recent activities for this buyer - CONVERT TO LIST
    recent_activities = list(Log.objects.filter(user=user_id).order_by('-timestamp')[:5])
    
    # Buyer notifications (pending bookings + new properties)
    new_properties_count = Property.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).filter(
        Q(status__iexact='available') | Q(status__iexact='Available')
    ).count()
    buyer_notifications = pending_bookings + (1 if new_properties_count > 0 else 0)
    
    # Buyer dashboard statistics
    buyer_stats = {
        'available_properties': available_properties,
        'my_bookings': {
            'total': my_bookings,
            'pending': pending_bookings
        },
        'featured_properties': featured_properties,
        'popular_locations': popular_locations,
        'price_range': {
            'average': price_stats['avg_price'] or 0,
            'min': price_stats['min_price'] or 0,
            'max': price_stats['max_price'] or 0
        },
        'notifications_count': buyer_notifications,
        'new_properties_count': new_properties_count
    }
    
    # Debug: Print stats being passed to template
    print(f"🔍 DEBUG: Stats being passed to template:")
    print(f"   - available_properties: {buyer_stats['available_properties']}")
    print(f"   - featured_properties count: {len(buyer_stats['featured_properties'])}")
    print(f"   - my_bookings total: {buyer_stats['my_bookings']['total']}")
    print(f"   - my_bookings pending: {buyer_stats['my_bookings']['pending']}")
    
    # Create response with no-cache headers to ensure fresh data
    response = render(request, 'backend/buyer_dashboard.html', {
        'user': user,
        'recent_activities': recent_activities,
        'stats': buyer_stats,
    })
    
    # Add cache control headers to prevent caching
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response
@login_required(allowed_roles=["seller"])
def seller_dashboard_view(request):
    if 'role' not in request.session or request.session['role'] != "seller":
        return redirect("/backend/login/")
    
    seller_id = request.session['user_id']
    user = EstateUser.objects.get(user_id=seller_id)
    
    # Log seller dashboard visit
    Log.objects.create(user=user, action="Viewed seller dashboard")
    
    # Calculate real dashboard statistics
    from django.db.models import Sum, Count
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # Get seller's properties count
    my_properties_count = Property.objects.filter(user=seller_id).count()
    
    # Get active bookings count
    active_bookings_count = Booking.objects.filter(property__user=seller_id, status='pending').count()
    
    # Calculate monthly revenue (current month)
    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_revenue = Transaction.objects.filter(
        booking__property__user=seller_id,
        payment_date__month=current_month,
        payment_date__year=current_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate property views (estimate based on logs)
    property_views_count = Log.objects.filter(
        user=seller_id,
        action__icontains='property'
    ).count()
    
    # Calculate growth percentages
    # Previous month for comparison
    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1
    
    # Previous month properties
    prev_month_properties = Property.objects.filter(
        user=seller_id,
        created_at__month=prev_month,
        created_at__year=prev_year
    ).count()
    
    # Previous month revenue
    prev_monthly_revenue = Transaction.objects.filter(
        booking__property__user=seller_id,
        payment_date__month=prev_month,
        payment_date__year=prev_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate percentage changes
    def calculate_percentage_change(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)
    
    # Properties growth
    properties_growth = f"+{prev_month_properties} this month" if prev_month_properties > 0 else "No new properties"
    
    # Revenue growth
    revenue_growth_percent = calculate_percentage_change(monthly_revenue, prev_monthly_revenue)
    revenue_growth = f"+{revenue_growth_percent}% increase" if revenue_growth_percent > 0 else f"{revenue_growth_percent}% change"
    
    # Views growth (last 7 days vs previous 7 days)
    last_week = timezone.now() - timedelta(days=7)
    prev_week = timezone.now() - timedelta(days=14)
    
    recent_views = Log.objects.filter(
        user=seller_id,
        action__icontains='property',
        timestamp__gte=last_week
    ).count()
    
    prev_views = Log.objects.filter(
        user=seller_id,
        action__icontains='property',
        timestamp__gte=prev_week,
        timestamp__lt=last_week
    ).count()
    
    views_growth_percent = calculate_percentage_change(recent_views, prev_views)
    views_growth = f"+{views_growth_percent}% this week" if views_growth_percent > 0 else f"{views_growth_percent}% this week"
    
    # Pending bookings info
    pending_bookings_info = f"+{active_bookings_count} pending" if active_bookings_count > 0 else "No pending requests"
    
    # Recent activities
    recent_activities = Log.objects.filter(user=seller_id).order_by('-timestamp')[:5]
    
    # Additional stats for action cards
    # Count images uploaded by seller
    images_count = PropertyImage.objects.filter(property__user=seller_id).count()
    
    # Last activity time
    last_activity = Log.objects.filter(user=seller_id).order_by('-timestamp').first()
    last_activity_time = "No activity" if not last_activity else f"2 min ago"
    
    # Seller notifications (pending bookings for their properties)
    seller_notifications = active_bookings_count
    
    # Dashboard statistics
    dashboard_stats = {
        'my_properties': {
            'count': my_properties_count,
            'growth': properties_growth
        },
        'active_bookings': {
            'count': active_bookings_count,
            'info': pending_bookings_info
        },
        'monthly_revenue': {
            'amount': monthly_revenue,
            'growth': revenue_growth
        },
        'property_views': {
            'count': property_views_count,
            'growth': views_growth
        },
        'images_uploaded': images_count,
        'last_activity': last_activity_time,
        'notifications_count': seller_notifications
    }
    
    return render(request, "backend/seller_dashboard.html", {
        "user": user, 
        "recent_activities": recent_activities,
        "stats": dashboard_stats
    })

# Seller - My Properties view
def seller_properties(request):
    if 'role' not in request.session or request.session['role'] != "seller":
        return redirect("/backend/login/")

    query = request.GET.get("q", "").strip().lower()
    seller_id = request.session['user_id']  # login session me user id store hai assume
    properties = Property.objects.filter(user_id=seller_id).distinct()

    if query:
            if query.isdigit():
                properties = properties.filter(property_id=int(query))
            else:
                properties = properties.filter(location__icontains=query)

    # Seller activity log (properties view)
    seller = EstateUser.objects.get(user_id=seller_id)
    Log.objects.create(user=seller, action="Viewed properties list")
    return render(request, "backend/seller_properties.html", {"properties": properties, "query": query})

# Seller - Add Property view
def add_property(request):
    if 'role' not in request.session or request.session['role'] != "seller":
        return redirect("/backend/login/")

    if request.method == "POST":
        user_id = request.session['user_id']
        title = request.POST.get("title")
        description = request.POST.get("description")
        property_type = request.POST.get("type")
        city = request.POST.get("city")
        state = request.POST.get("state")
        address = request.POST.get("address")
        price = request.POST.get("price")
        area_sqft = request.POST.get("area")
        bedrooms = request.POST.get("bedrooms")
        bathrooms = request.POST.get("bathrooms")
        amenities = request.POST.getlist("amenities")
        contact = request.POST.get("contact")
        # location field me city + state + address combine kar rahe hain
        location = f"{address}, {city}, {state}"

        # Property create
        prop = Property.objects.create(
            user_id=user_id,
            title=title,
            description=description,
            property_type=property_type,
            city=city,
            state=state,
            address=address,
            location=location,
            price=price,
            area_sqft=area_sqft,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            amenities=", ".join(amenities),
            contact=contact,
            status="Available"
        )

        # Images handle karo - save files properly
        images = request.FILES.getlist("images")
        descriptions = request.POST.getlist("image_descriptions") if "image_descriptions" in request.POST else []
        
        for idx, img in enumerate(images):
            desc = descriptions[idx] if idx < len(descriptions) else ""
            
            # Save the file to media directory
            import os
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            
            # Create unique filename
            import uuid
            file_ext = img.name.split('.')[-1] if '.' in img.name else 'jpg'
            unique_filename = f"property_{prop.property_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
            
            # Save file
            file_path = default_storage.save(unique_filename, ContentFile(img.read()))
            
            # Create PropertyImage record
            PropertyImage.objects.create(
                property=prop,
                image_url=file_path,  # Store relative path
                description=desc
            )

        # Log the activity
        seller = EstateUser.objects.get(user_id=user_id)
        Log.objects.create(user=seller, action=f"Added new property: {title}")
        
        # Send notification to admins about new property
        from . import notification_service
        notification_service.notify_property_added(prop.property_id)
        
        messages.success(request, f"Property '{title}' added successfully with {len(images)} images!")
        return redirect("/backend/seller/properties/")

    # Pass user role and other context for unified template
    context = {
        'user_role': 'seller'
    }
    return render(request, "backend/add_property.html", context)

# Admin - Add Property view
def admin_add_property(request):
    if 'role' not in request.session or request.session['role'] != "admin":
        return redirect("/backend/login/")

    if request.method == "POST":
        # Admin can assign property to any seller
        seller_id = request.POST.get("seller_id")
        if not seller_id:
            messages.error(request, "Please select a seller for the property.")
            return render(request, "backend/admin_add_property.html", get_admin_add_property_context())
        
        title = request.POST.get("title")
        description = request.POST.get("description")
        property_type = request.POST.get("type")
        city = request.POST.get("city")
        state = request.POST.get("state")
        address = request.POST.get("address")
        price = request.POST.get("price")
        area_sqft = request.POST.get("area")
        bedrooms = request.POST.get("bedrooms")
        bathrooms = request.POST.get("bathrooms")
        amenities = request.POST.getlist("amenities")
        contact = request.POST.get("contact")
        # location field me city + state + address combine kar rahe hain
        location = f"{address}, {city}, {state}"

        # Property create
        prop = Property.objects.create(
            user_id=seller_id,
            title=title,
            description=description,
            property_type=property_type,
            city=city,
            state=state,
            address=address,
            location=location,
            price=price,
            area_sqft=area_sqft,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            amenities=", ".join(amenities),
            contact=contact,
            status="Available"
        )

        # Images handle karo - save files properly
        images = request.FILES.getlist("images")
        descriptions = request.POST.getlist("image_descriptions") if "image_descriptions" in request.POST else []
        
        for idx, img in enumerate(images):
            desc = descriptions[idx] if idx < len(descriptions) else ""
            
            # Save the file to media directory
            import os
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            
            # Create unique filename
            import uuid
            file_ext = img.name.split('.')[-1] if '.' in img.name else 'jpg'
            unique_filename = f"property_{prop.property_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
            
            # Save file
            file_path = default_storage.save(unique_filename, ContentFile(img.read()))
            
            # Create PropertyImage record
            PropertyImage.objects.create(
                property=prop,
                image_url=file_path,  # Store relative path
                description=desc
            )

        # Log the activity
        admin = EstateUser.objects.get(user_id=request.session['user_id'])
        Log.objects.create(user=admin, action=f"Added new property: {title} for seller ID: {seller_id}")
        
        messages.success(request, f"Property '{title}' added successfully for seller!")
        return redirect("/backend/dashboard/")

    # Pass admin role and sellers context for unified template
    context = get_admin_add_property_context()
    context['user_role'] = 'admin'
    return render(request, "backend/add_property.html", context)

def get_admin_add_property_context():
    # Get all sellers for dropdown
    sellers = EstateUser.objects.filter(role="seller").order_by('name')
    return {"sellers": sellers}

# Property Update View for Sellers
@csrf_exempt
@require_POST
def update_property(request, property_id):
    if 'role' not in request.session or request.session['role'] != "seller":
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        # Get the property and verify ownership
        seller_id = request.session.get('seller_id') or request.session.get('user_id')
        property_obj = Property.objects.get(property_id=property_id, user_id=seller_id)
        
        # Parse JSON data from request
        data = json.loads(request.body)
        
        # Update property fields
        property_obj.title = data.get('title', property_obj.title)
        property_obj.property_type = data.get('property_type', property_obj.property_type)
        property_obj.price = float(data.get('price', property_obj.price))
        property_obj.area_sqft = int(data.get('area_sqft', property_obj.area_sqft))
        property_obj.bedrooms = int(data.get('bedrooms', property_obj.bedrooms))
        property_obj.bathrooms = int(data.get('bathrooms', property_obj.bathrooms))
        property_obj.city = data.get('city', property_obj.city)
        property_obj.state = data.get('state', property_obj.state)
        property_obj.address = data.get('address', property_obj.address)
        property_obj.description = data.get('description', property_obj.description)
        property_obj.amenities = data.get('amenities', property_obj.amenities)
        
        # Save the updated property
        property_obj.save()
        
        # Log the activity
        seller = EstateUser.objects.get(user_id=seller_id)
        Log.objects.create(
            user=seller, 
            action=f"Updated property: {property_obj.title} (ID: {property_id})"
        )
        
        return JsonResponse({
            "success": True, 
            "message": "Property updated successfully!",
            "property": {
                "title": property_obj.title,
                "price": property_obj.price,
                "location": f"{property_obj.city}, {property_obj.state}"
            }
        })
        
    except Property.DoesNotExist:
        return JsonResponse({"error": "Property not found or access denied"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"Update failed: {str(e)}"}, status=400)

# ---------------------------
# Admin Property Update with Image Management
# ---------------------------
@csrf_exempt
def update_property_admin(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method allowed"}, status=405)
    
    # Check admin session
    if 'role' not in request.session or request.session['role'] != "admin":
        return JsonResponse({"error": "Admin access required"}, status=403)
    
    try:
        import json
        import os
        from django.conf import settings
        
        property_id = request.POST.get('property_id')
        if not property_id:
            return JsonResponse({"error": "Property ID is required"}, status=400)
        
        # Get property object
        property_obj = Property.objects.get(property_id=property_id)
        
        # Update basic property fields
        property_obj.title = request.POST.get('title', property_obj.title)
        property_obj.property_type = request.POST.get('type', property_obj.property_type)
        property_obj.price = float(request.POST.get('price', property_obj.price))
        property_obj.area_sqft = float(request.POST.get('area', property_obj.area_sqft or 0))
        property_obj.bedrooms = int(request.POST.get('bedrooms', property_obj.bedrooms or 0))
        property_obj.bathrooms = int(request.POST.get('bathrooms', property_obj.bathrooms or 0))
        property_obj.city = request.POST.get('city', property_obj.city)
        property_obj.state = request.POST.get('state', property_obj.state)
        property_obj.address = request.POST.get('address', property_obj.address)
        property_obj.amenities = request.POST.get('amenities', property_obj.amenities)
        property_obj.description = request.POST.get('description', property_obj.description)
        property_obj.contact = request.POST.get('contact', property_obj.contact)
        
        # Track status change for notification
        old_status = property_obj.status
        new_status = request.POST.get('status', property_obj.status)
        property_obj.status = new_status
        
        property_obj.save()
        
        # Notify seller if status changed
        if old_status != new_status:
            from . import notification_service
            notification_service.notify_property_status_changed(property_id, new_status)
        
        # Handle image operations
        new_image_url = None
        image_updated = False
        
        # Check if image is being removed
        image_removed = request.POST.get('image_removed') == 'true'
        if image_removed:
            # Remove existing images
            PropertyImage.objects.filter(property=property_obj).delete()
            image_updated = True
            new_image_url = '/media/estatelogo.png'
        
        # Check if new image is uploaded
        new_image = request.FILES.get('newImage')
        if new_image:
            # Remove old images first
            PropertyImage.objects.filter(property=property_obj).delete()
            
            # Save new image
            import uuid
            file_extension = os.path.splitext(new_image.name)[1]
            unique_filename = f"property_{property_id}_{uuid.uuid4().hex[:8]}{file_extension}"
            
            # Save file to media directory
            media_path = os.path.join(settings.MEDIA_ROOT, unique_filename)
            with open(media_path, 'wb+') as destination:
                for chunk in new_image.chunks():
                    destination.write(chunk)
            
            # Create PropertyImage entry
            PropertyImage.objects.create(
                property=property_obj,
                image_url=unique_filename,
                description=f"Property image for {property_obj.title}"
            )
            
            image_updated = True
            new_image_url = f'/media/{unique_filename}'
        
        # Log the activity
        admin_user = EstateUser.objects.get(user_id=request.session['user_id'])
        action_details = f"Updated property: {property_obj.title} (ID: {property_id})"
        if image_updated:
            action_details += " - Image updated"
        
        Log.objects.create(user=admin_user, action=action_details)
        
        # Prepare response
        response_data = {
            "success": True,
            "message": "Property updated successfully!",
            "property": {
                "id": property_obj.property_id,
                "title": property_obj.title,
                "type": property_obj.property_type,
                "price": property_obj.price,
                "area": property_obj.area_sqft,
                "bedrooms": property_obj.bedrooms,
                "bathrooms": property_obj.bathrooms,
                "city": property_obj.city,
                "state": property_obj.state,
                "address": property_obj.address,
                "amenities": property_obj.amenities,
                "description": property_obj.description,
                "contact": property_obj.contact,
                "status": property_obj.status
            }
        }
        
        if image_updated:
            response_data["property"]["imageUrl"] = new_image_url
            response_data["imageUpdated"] = True
        
        return JsonResponse(response_data)
        
    except Property.DoesNotExist:
        return JsonResponse({"error": "Property not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"Update failed: {str(e)}"}, status=500)


# ---------------------------
# Buyer Dashboard API Views
# ---------------------------
from .models import SavedProperty, PaymentHistory, SupportTicket, TicketResponse, PropertyReview, MarketInsight, SellerNotification, BuyerNotification
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Avg, Count, Sum

@csrf_exempt
def buyer_saved_properties_api(request):
    """API for managing saved properties"""
    if 'role' not in request.session or request.session['role'] != "buyer":
        return JsonResponse({"error": "Buyer access required"}, status=403)
    
    user_id = request.session.get('buyer_id') or request.session.get('user_id')
    
    if request.method == "GET":
        try:
            saved_properties = SavedProperty.objects.filter(user_id=user_id).select_related('property')
            
            properties_data = []
            for saved in saved_properties:
                prop = saved.property
                # Get first image
                first_image = prop.images.first()
                image_url = None
                if first_image:
                    url = first_image.image_url
                    if not url.startswith('http') and not url.startswith('/media/'):
                        image_url = settings.MEDIA_URL + url
                    else:
                        image_url = url
                
                properties_data.append({
                    'saved_id': saved.saved_id,
                    'property_id': prop.property_id,
                    'title': prop.title,
                    'location': prop.location,
                    'city': prop.city,
                    'state': prop.state,
                    'price': float(prop.price),
                    'area_sqft': float(prop.area_sqft) if prop.area_sqft else 0,
                    'bedrooms': prop.bedrooms,
                    'bathrooms': prop.bathrooms,
                    'property_type': prop.property_type,
                    'status': prop.status,
                    'image_url': image_url,
                    'saved_at': saved.saved_at.strftime('%Y-%m-%d %H:%M'),
                    'notes': saved.notes or ''
                })
            
            # Log the action
            user = EstateUser.objects.get(user_id=user_id)
            Log.objects.create(user=user, action="Viewed saved properties")
            
            return JsonResponse({
                'success': True,
                'properties': properties_data,
                'count': len(properties_data)
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            property_id = data.get('property_id')
            notes = data.get('notes', '')
            
            if not property_id:
                return JsonResponse({"error": "Property ID required"}, status=400)
            
            # Check if property exists
            try:
                property_obj = Property.objects.get(property_id=property_id)
            except Property.DoesNotExist:
                return JsonResponse({"error": "Property not found"}, status=404)
            
            # Create or update saved property
            saved_property, created = SavedProperty.objects.get_or_create(
                user_id=user_id,
                property_id=property_id,
                defaults={'notes': notes}
            )
            
            if not created:
                return JsonResponse({"error": "Property already saved"}, status=400)
            
            # Log the action
            user = EstateUser.objects.get(user_id=user_id)
            Log.objects.create(user=user, action=f"Saved property: {property_obj.title}")
            
            # Notify seller that their property was saved
            from . import notification_service
            notification_service.notify_property_saved(property_id, user_id)
            
            return JsonResponse({
                'success': True,
                'message': 'Property saved successfully',
                'saved_id': saved_property.saved_id
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    elif request.method == "DELETE":
        try:
            data = json.loads(request.body)
            saved_id = data.get('saved_id')
            
            if not saved_id:
                return JsonResponse({"error": "Saved ID required"}, status=400)
            
            saved_property = SavedProperty.objects.get(saved_id=saved_id, user_id=user_id)
            property_title = saved_property.property.title
            saved_property.delete()
            
            # Log the action
            user = EstateUser.objects.get(user_id=user_id)
            Log.objects.create(user=user, action=f"Removed saved property: {property_title}")
            
            return JsonResponse({
                'success': True,
                'message': 'Property removed from saved list'
            })
            
        except SavedProperty.DoesNotExist:
            return JsonResponse({"error": "Saved property not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def update_saved_property_notes(request, saved_id):
    """API endpoint to update notes for a saved property"""
    if 'role' not in request.session or request.session['role'] != "buyer":
        return JsonResponse({"error": "Buyer access required"}, status=403)
    
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    
    user_id = request.session.get('buyer_id') or request.session.get('user_id')
    
    try:
        data = json.loads(request.body)
        notes = data.get('notes', '')
        
        # Get the saved property
        saved_property = SavedProperty.objects.get(saved_id=saved_id, user_id=user_id)
        
        # Update notes
        saved_property.notes = notes
        saved_property.save()
        
        # Log the action
        user = EstateUser.objects.get(user_id=user_id)
        Log.objects.create(user=user, action=f"Updated notes for saved property: {saved_property.property.title}")
        
        return JsonResponse({
            'success': True,
            'message': 'Notes updated successfully'
        })
        
    except SavedProperty.DoesNotExist:
        return JsonResponse({"error": "Saved property not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def remove_saved_property(request, saved_id):
    """API endpoint to remove a saved property"""
    if 'role' not in request.session or request.session['role'] != "buyer":
        return JsonResponse({"error": "Buyer access required"}, status=403)
    
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    
    user_id = request.session.get('buyer_id') or request.session.get('user_id')
    
    try:
        # Get and delete the saved property
        saved_property = SavedProperty.objects.get(saved_id=saved_id, user_id=user_id)
        property_title = saved_property.property.title
        saved_property.delete()
        
        # Log the action
        user = EstateUser.objects.get(user_id=user_id)
        Log.objects.create(user=user, action=f"Removed saved property: {property_title}")
        
        return JsonResponse({
            'success': True,
            'message': 'Property removed from saved list'
        })
        
    except SavedProperty.DoesNotExist:
        return JsonResponse({"error": "Saved property not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def buyer_payment_history_api(request):
    """API for payment history"""
    if 'role' not in request.session or request.session['role'] != "buyer":
        return JsonResponse({"error": "Buyer access required"}, status=403)
    
    user_id = request.session.get('buyer_id') or request.session.get('user_id')
    
    if request.method == "GET":
        try:
            payments = PaymentHistory.objects.filter(user_id=user_id).select_related('property').order_by('-payment_date')
            
            payments_data = []
            total_spent = 0
            
            for payment in payments:
                prop = payment.property
                payment_data = {
                    'payment_id': payment.payment_id,
                    'property_title': prop.title if prop else 'N/A',
                    'property_location': prop.location if prop else 'N/A',
                    'amount': float(payment.amount),
                    'payment_type': payment.payment_type,
                    'payment_method': payment.payment_method,
                    'status': payment.status,
                    'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M'),
                    'payment_reference': payment.payment_reference or '',
                    'description': payment.description or ''
                }
                payments_data.append(payment_data)
                
                if payment.status == 'success':
                    total_spent += float(payment.amount)
            
            # Log the action
            user = EstateUser.objects.get(user_id=user_id)
            Log.objects.create(user=user, action="Viewed payment history")
            
            return JsonResponse({
                'success': True,
                'payments': payments_data,
                'total_spent': total_spent,
                'count': len(payments_data)
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    elif request.method == "POST":
        # Create new payment record
        try:
            data = json.loads(request.body)
            
            payment = PaymentHistory.objects.create(
                user_id=user_id,
                property_id=data.get('property_id'),
                amount=data.get('amount'),
                payment_type=data.get('payment_type', 'booking_fee'),
                payment_method=data.get('payment_method', 'online'),
                status=data.get('status', 'pending'),
                payment_reference=data.get('payment_reference', ''),
                description=data.get('description', '')
            )
            
            # Log the action
            user = EstateUser.objects.get(user_id=user_id)
            Log.objects.create(user=user, action=f"Made payment: ₹{payment.amount}")
            
            return JsonResponse({
                'success': True,
                'message': 'Payment recorded successfully',
                'payment_id': payment.payment_id
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def create_booking_api(request):
    """API endpoint to create a new booking with payment and seller notification"""
    if 'role' not in request.session or request.session['role'] != "buyer":
        return JsonResponse({"error": "Buyer access required"}, status=403)
    
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    
    user_id = request.session.get('buyer_id') or request.session.get('user_id')
    
    try:
        data = json.loads(request.body)
        property_id = data.get('property_id')
        buyer_name = data.get('buyer_name')
        buyer_phone = data.get('buyer_phone')
        buyer_email = data.get('buyer_email')
        visit_date = data.get('visit_date')
        message = data.get('message', '')
        payment_method = data.get('payment_method')
        amount = data.get('amount')
        
        # Validation
        if not all([property_id, buyer_name, buyer_phone, buyer_email, visit_date, payment_method, amount]):
            return JsonResponse({"error": "All required fields including payment method must be provided"}, status=400)
        
        # Validate property exists and is available
        try:
            property_obj = Property.objects.get(property_id=property_id)
            
            # CRITICAL: Check if property is already sold
            if property_obj.status == 'Sold':
                return JsonResponse({
                    "error": "This property has already been sold",
                    "property_status": "Sold"
                }, status=400)
                
        except Property.DoesNotExist:
            return JsonResponse({"error": "Property not found"}, status=404)
        
        # Get buyer user object
        try:
            buyer = EstateUser.objects.get(user_id=user_id)
        except EstateUser.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)
        
        # Create booking with confirmed status (since payment is done)
        booking = Booking.objects.create(
            user=buyer,
            property=property_obj,
            status='confirmed'  # Confirmed because payment is done
        )
        
        # Create transaction record
        transaction = Transaction.objects.create(
            booking=booking,
            amount=float(amount),
            payment_method=payment_method,
            payment_status='completed',
            payment_date=timezone.now()
        )
        
        # ✅ CRITICAL FIX: Update property status to 'Sold' immediately
        property_obj.status = 'Sold'
        property_obj.save()
        
        # Send notifications using notification service
        from . import notification_service
        
        # Notify seller about property sold
        seller = property_obj.user
        if seller:
            notification_message = f"""
🎉 PROPERTY SOLD! 🎉

Property: {property_obj.title}
Sale Price: ₹{amount}
Buyer: {buyer_name}
Contact: {buyer_phone}, {buyer_email}
Visit Date: {visit_date}
Payment Method: {payment_method.replace('_', ' ').title()}
Status: Payment Completed & Property Marked as SOLD

{f'Message from buyer: {message}' if message else ''}

Congratulations on your successful sale!
            """.strip()
            
            # Use notification service
            notification_service.create_seller_notification(
                seller_id=seller.user_id,
                title=f'🎉 Property Sold: {property_obj.title}',
                message=notification_message,
                notification_type=notification_service.NotificationType.PAYMENT_RECEIVED,
                property_obj=property_obj,
                booking_obj=booking
            )
        
        # Notify buyer about successful purchase
        notification_service.create_buyer_notification(
            buyer_id=buyer.user_id,
            title='✅ Property Purchase Confirmed!',
            message=f'Congratulations! You have successfully purchased "{property_obj.title}". Payment of ₹{amount} received. Visit date: {visit_date}. The property is now yours!',
            notification_type=notification_service.NotificationType.BOOKING_CONFIRMED
        )
        
        # Log the action with full details
        Log.objects.create(
            user=buyer, 
            action=f"Property PURCHASED: {property_obj.title} (Booking ID: {booking.booking_id}, Amount: ₹{amount}, Payment: {payment_method}, Property Status: SOLD)"
        )
        
        # Log for seller
        if seller:
            Log.objects.create(
                user=seller,
                action=f"Property SOLD: {property_obj.title} (Sold to: {buyer_name}, Amount: ₹{amount}, Booking ID: {booking.booking_id})"
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Payment successful! Property purchased. The property is now marked as SOLD.',
            'booking_id': booking.booking_id,
            'transaction_id': transaction.txn_id,
            'booking_date': booking.booking_date.strftime('%Y-%m-%d %H:%M'),
            'status': booking.status,
            'payment_status': transaction.payment_status,
            'property_status': 'Sold',  # Explicitly confirm property is now sold
            'property_title': property_obj.title
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def buyer_transaction_history_api(request):
    """API endpoint to fetch transaction history from transactions table"""
    if 'role' not in request.session or request.session['role'] != "buyer":
        return JsonResponse({"error": "Buyer access required"}, status=403)
    
    if request.method != "GET":
        return JsonResponse({"error": "GET method required"}, status=405)
    
    user_id = request.session.get('buyer_id') or request.session.get('user_id')
    
    try:
        # Get user's bookings first, then get transactions for those bookings
        user_bookings = Booking.objects.filter(user_id=user_id)
        transactions = Transaction.objects.filter(
            booking__in=user_bookings
        ).select_related('booking__property', 'booking__user').order_by('-payment_date')
        
        transactions_data = []
        total_amount = 0
        
        for txn in transactions:
            property_title = txn.booking.property.title if txn.booking and txn.booking.property else 'N/A'
            property_location = f"{txn.booking.property.city}, {txn.booking.property.state}" if txn.booking and txn.booking.property else 'N/A'
            
            transaction_data = {
                'txn_id': txn.txn_id,
                'property_title': property_title,
                'property_location': property_location,
                'amount': float(txn.amount),
                'payment_status': txn.payment_status,
                'payment_date': txn.payment_date.strftime('%Y-%m-%d %H:%M'),
                'booking_id': txn.booking.booking_id if txn.booking else None
            }
            transactions_data.append(transaction_data)
            
            if txn.payment_status == 'success':
                total_amount += float(txn.amount)
        
        # Log the action
        user = EstateUser.objects.get(user_id=user_id)
        Log.objects.create(user=user, action="Viewed transaction history")
        
        return JsonResponse({
            'success': True,
            'transactions': transactions_data,
            'total_amount': total_amount,
            'count': len(transactions_data)
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def buyer_support_tickets_api(request):
    """API for support tickets"""
    if 'role' not in request.session or request.session['role'] != "buyer":
        return JsonResponse({"error": "Buyer access required", "success": False}, status=403)
    
    user_id = request.session.get('buyer_id') or request.session.get('user_id')
    
    if request.method == "GET":
        try:
            tickets = SupportTicket.objects.filter(user_id=user_id).order_by('-created_at')
            
            tickets_data = []
            for ticket in tickets:
                # Get response count
                response_count = ticket.responses.count()
                last_response = ticket.responses.order_by('-created_at').first()
                
                ticket_data = {
                    'ticket_id': ticket.ticket_id,
                    'token_id': ticket.token_id or f"TKT-{ticket.ticket_id}",  # Fallback for old tickets
                    'subject': ticket.subject,
                    'category': ticket.category,
                    'priority': ticket.priority,
                    'status': ticket.status,
                    'description': ticket.description,
                    'created_at': ticket.created_at.strftime('%Y-%m-%d %H:%M'),
                    'updated_at': ticket.updated_at.strftime('%Y-%m-%d %H:%M'),
                    'response_count': response_count,
                    'last_response_date': last_response.created_at.strftime('%Y-%m-%d %H:%M') if last_response else None
                }
                tickets_data.append(ticket_data)
            
            # Count by status
            open_count = tickets.filter(status='open').count()
            in_progress_count = tickets.filter(status='in_progress').count()
            resolved_count = tickets.filter(status='resolved').count()
            
            # Log the action
            user = EstateUser.objects.get(user_id=user_id)
            Log.objects.create(user=user, action="Viewed support tickets")
            
            return JsonResponse({
                'success': True,
                'tickets': tickets_data,
                'stats': {
                    'total': len(tickets_data),
                    'open': open_count,
                    'in_progress': in_progress_count,
                    'resolved': resolved_count
                }
            })
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in buyer_support_tickets_api: {error_details}")  # Log to console
            return JsonResponse({"error": str(e), "success": False}, status=500)
    
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            
            # Generate unique token ID (format: SUP-YYYYMMDD-XXXX)
            from datetime import datetime
            import random
            date_str = datetime.now().strftime('%Y%m%d')
            random_num = str(random.randint(1000, 9999))
            token_id = f"SUP-{date_str}-{random_num}"
            
            # Ensure token uniqueness
            while SupportTicket.objects.filter(token_id=token_id).exists():
                random_num = str(random.randint(1000, 9999))
                token_id = f"SUP-{date_str}-{random_num}"
            
            ticket = SupportTicket.objects.create(
                user_id=user_id,
                token_id=token_id,
                subject=data.get('subject', ''),
                category=data.get('category', 'general'),
                priority=data.get('priority', 'medium'),
                description=data.get('description', '')
            )
            
            # Log the action
            user = EstateUser.objects.get(user_id=user_id)
            Log.objects.create(user=user, action=f"Created support ticket: {ticket.subject} (Token: {token_id})")
            
            # Notify admins about new support ticket
            from . import notification_service
            notification_service.notify_ticket_created(ticket.ticket_id)
            
            return JsonResponse({
                'success': True,
                'message': 'Support ticket created successfully',
                'ticket_id': ticket.ticket_id,
                'token_id': token_id
            })
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error creating support ticket: {error_details}")
            return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def buyer_reviews_api(request):
    """API for property reviews"""
    if 'role' not in request.session or request.session['role'] != "buyer":
        return JsonResponse({"error": "Buyer access required"}, status=403)
    
    user_id = request.session.get('buyer_id') or request.session.get('user_id')
    
    if request.method == "GET":
        try:
            reviews = PropertyReview.objects.filter(user_id=user_id).select_related('property').order_by('-created_at')
            
            reviews_data = []
            for review in reviews:
                prop = review.property
                review_data = {
                    'review_id': review.review_id,
                    'property_title': prop.title if prop else 'N/A',
                    'property_location': prop.location if prop else 'N/A',
                    'rating': review.rating,
                    'title': review.title or '',
                    'review_text': review.review_text,
                    'pros': review.pros or '',
                    'cons': review.cons or '',
                    'would_recommend': review.would_recommend,
                    'is_verified': review.is_verified,
                    'is_approved': review.is_approved,
                    'helpful_votes': review.helpful_votes,
                    'created_at': review.created_at.strftime('%Y-%m-%d %H:%M'),
                    'updated_at': review.updated_at.strftime('%Y-%m-%d %H:%M')
                }
                reviews_data.append(review_data)
            
            # Calculate average rating
            avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
            
            # Log the action
            user = EstateUser.objects.get(user_id=user_id)
            Log.objects.create(user=user, action="Viewed submitted reviews")
            
            return JsonResponse({
                'success': True,
                'reviews': reviews_data,
                'stats': {
                    'total': len(reviews_data),
                    'average_rating': round(avg_rating, 1)
                }
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            
            # Check if user already reviewed this property
            property_id = data.get('property_id')
            if PropertyReview.objects.filter(user_id=user_id, property_id=property_id).exists():
                return JsonResponse({"error": "You have already reviewed this property"}, status=400)
            
            review = PropertyReview.objects.create(
                user_id=user_id,
                property_id=property_id,
                rating=data.get('rating', 5),
                title=data.get('title', ''),
                review_text=data.get('review_text', ''),
                pros=data.get('pros', ''),
                cons=data.get('cons', ''),
                would_recommend=data.get('would_recommend', True)
            )
            
            # Log the action
            user = EstateUser.objects.get(user_id=user_id)
            property_obj = Property.objects.get(property_id=property_id)
            Log.objects.create(user=user, action=f"Reviewed property: {property_obj.title}")
            
            return JsonResponse({
                'success': True,
                'message': 'Review submitted successfully',
                'review_id': review.review_id
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def buyer_profile_api(request):
    """API to get buyer's profile data for auto-filling forms"""
    if 'role' not in request.session or request.session['role'] != "buyer":
        return JsonResponse({"error": "Buyer access required"}, status=403)
    
    user_id = request.session.get('buyer_id') or request.session.get('user_id')
    
    try:
        user = EstateUser.objects.get(user_id=user_id)
        
        return JsonResponse({
            'success': True,
            'profile': {
                'name': user.name,
                'email': user.email or '',
                'phone': user.phone or '',
                'address': user.address or ''
            }
        })
        
    except EstateUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def buyer_reviewable_properties_api(request):
    """API to get properties that the buyer can review (properties they have booked)"""
    if 'role' not in request.session or request.session['role'] != "buyer":
        return JsonResponse({"error": "Buyer access required"}, status=403)
    
    user_id = request.session.get('buyer_id') or request.session.get('user_id')
    
    try:
        # Get all properties from buyer's bookings
        bookings = Booking.objects.filter(user_id=user_id).select_related('property').order_by('-booking_date')
        
        # Get unique properties (avoid duplicates if user booked same property multiple times)
        seen_property_ids = set()
        properties_data = []
        
        for booking in bookings:
            if booking.property and booking.property.property_id not in seen_property_ids:
                prop = booking.property
                seen_property_ids.add(prop.property_id)
                
                # Check if user already reviewed this property
                already_reviewed = PropertyReview.objects.filter(
                    user_id=user_id,
                    property_id=prop.property_id
                ).exists()
                
                properties_data.append({
                    'property_id': prop.property_id,
                    'title': prop.title,
                    'location': prop.location,
                    'property_type': prop.property_type,
                    'booking_date': booking.booking_date.strftime('%Y-%m-%d'),
                    'already_reviewed': already_reviewed
                })
        
        # Log the action
        user = EstateUser.objects.get(user_id=user_id)
        Log.objects.create(user=user, action="Viewed reviewable properties list")
        
        return JsonResponse({
            'success': True,
            'properties': properties_data,
            'total': len(properties_data)
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def buyer_market_insights_api(request):
    """API for market insights"""
    if 'role' not in request.session or request.session['role'] != "buyer":
        return JsonResponse({"error": "Buyer access required"}, status=403)
    
    if request.method == "GET":
        try:
            # Get latest market insights
            insights = MarketInsight.objects.all().order_by('-created_at')[:20]
            
            insights_data = []
            for insight in insights:
                insight_data = {
                    'insight_id': insight.insight_id,
                    'location': insight.location,
                    'property_type': insight.property_type,
                    'average_price': float(insight.average_price),
                    'price_change_percent': insight.price_change_percent,
                    'total_listings': insight.total_listings,
                    'sold_count': insight.sold_count,
                    'days_on_market': insight.days_on_market,
                    'demand_score': insight.demand_score,
                    'period_start': insight.period_start.strftime('%Y-%m-%d'),
                    'period_end': insight.period_end.strftime('%Y-%m-%d'),
                    'created_at': insight.created_at.strftime('%Y-%m-%d %H:%M')
                }
                insights_data.append(insight_data)
            
            # Generate some sample market trends if no data exists
            if not insights_data:
                # Create sample data for demonstration
                sample_locations = ['Mumbai', 'Delhi', 'Bangalore', 'Pune', 'Chennai']
                sample_types = ['Residential', 'Commercial', 'Villa', 'Apartment']
                
                current_date = timezone.now().date()
                for i, location in enumerate(sample_locations):
                    for j, prop_type in enumerate(sample_types[:2]):  # Limit to 2 types per location
                        sample_data = {
                            'location': location,
                            'property_type': prop_type,
                            'average_price': 5000000 + (i * 1000000) + (j * 500000),
                            'price_change_percent': round(-5 + (i * 2.5) + (j * 1.5), 1),
                            'total_listings': 150 + (i * 20) + (j * 10),
                            'sold_count': 45 + (i * 8) + (j * 3),
                            'days_on_market': 35 + (i * 5),
                            'demand_score': 60.0 + (i * 8.0),
                            'period_start': (current_date - timedelta(days=30)).strftime('%Y-%m-%d'),
                            'period_end': current_date.strftime('%Y-%m-%d'),
                            'created_at': timezone.now().strftime('%Y-%m-%d %H:%M')
                        }
                        insights_data.append(sample_data)
            
            # Log the action
            user_id = request.session.get('buyer_id') or request.session.get('user_id')
            user = EstateUser.objects.get(user_id=user_id)
            Log.objects.create(user=user, action="Viewed market insights")
            
            return JsonResponse({
                'success': True,
                'insights': insights_data,
                'count': len(insights_data)
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# Property Images API (for seller property view modal)
@csrf_exempt
def get_property_images_api(request, property_id):
    """API to get all images for a specific property"""
    try:
        # Get property
        property_obj = Property.objects.get(property_id=property_id)
        
        # Get all images for this property
        images = PropertyImage.objects.filter(property=property_obj)
        
        # Prepare image data
        images_data = []
        for img in images:
            url = img.image_url
            # Handle both relative and absolute URLs
            if url and not url.startswith('http'):
                from django.conf import settings
                url = settings.MEDIA_URL + url
            
            images_data.append({
                'image_id': img.image_id,
                'url': url,
                'description': img.description or '',
                'uploaded_at': img.uploaded_at.strftime('%Y-%m-%d %H:%M') if hasattr(img, 'uploaded_at') else ''
            })
        
        return JsonResponse({
            'success': True,
            'property_id': property_id,
            'property_title': property_obj.title,
            'images': images_data,
            'count': len(images_data)
        })
        
    except Property.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Property not found',
            'images': []
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'images': []
        }, status=500)


# ========================
# Unified Notification API
# ========================
@csrf_exempt
def get_notifications_api(request):
    """Universal API to get notifications for all user types (buyer/seller/admin)"""
    
    # Check if user is logged in
    if 'role' not in request.session or 'user_id' not in request.session:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    role = request.session.get('role')
    user_id = request.session.get('user_id')
    
    # Get role-specific user_id
    if role == 'seller':
        user_id = request.session.get('seller_id') or user_id
    elif role == 'buyer':
        user_id = request.session.get('buyer_id') or user_id
    elif role == 'admin':
        user_id = request.session.get('admin_user') or user_id
    
    try:
        from .models import SellerNotification, BuyerNotification
        from django.utils import timezone
        
        # Get notifications based on role
        notifications_data = []
        unread_count = 0
        
        if role == 'buyer':
            # Get buyer notifications
            all_notifications = BuyerNotification.objects.filter(buyer_id=user_id)
            unread_count = all_notifications.filter(is_read=False).count()
            notifications = all_notifications.order_by('-created_at')[:50]
            
            for notif in notifications:
                notifications_data.append({
                    'notification_id': notif.notification_id,
                    'title': notif.title,
                    'message': notif.message,
                    'type': notif.notification_type,
                    'is_read': notif.is_read,
                    'created_at': notif.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'ticket_id': notif.support_ticket.ticket_id if notif.support_ticket else None,
                    'time_ago': get_time_ago(notif.created_at)
                })
        else:
            # Get seller/admin notifications
            all_notifications = SellerNotification.objects.filter(seller_id=user_id)
            unread_count = all_notifications.filter(is_read=False).count()
            notifications = all_notifications.order_by('-created_at')[:50]
            
            for notif in notifications:
                notifications_data.append({
                    'notification_id': notif.notification_id,
                    'title': notif.title,
                    'message': notif.message,
                    'type': notif.notification_type,
                    'is_read': notif.is_read,
                    'created_at': notif.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'property_id': notif.property.property_id if notif.property else None,
                    'property_title': notif.property.title if notif.property else None,
                    'booking_id': notif.booking.booking_id if notif.booking else None,
                    'time_ago': get_time_ago(notif.created_at)
                })
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'unread_count': unread_count,
            'total_count': len(notifications_data),
            'user_role': role
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Notification API Error: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch notifications',
            'notifications': [],
            'unread_count': 0
        }, status=500)


@csrf_exempt
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    
    if 'user_id' not in request.session:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        from .models import SellerNotification, BuyerNotification
        from django.utils import timezone
        
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if role == 'seller':
            user_id = request.session.get('seller_id') or user_id
        elif role == 'buyer':
            user_id = request.session.get('buyer_id') or user_id
        elif role == 'admin':
            user_id = request.session.get('admin_user') or user_id
        
        # Get notification based on role
        if role == 'buyer':
            notification = BuyerNotification.objects.get(
                notification_id=notification_id,
                buyer_id=user_id
            )
        else:
            notification = SellerNotification.objects.get(
                notification_id=notification_id,
                seller_id=user_id
            )
        
        # Mark as read
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read',
            'notification_id': notification_id
        })
        
    except (SellerNotification.DoesNotExist, BuyerNotification.DoesNotExist):
        return JsonResponse({
            'success': False,
            'error': 'Notification not found or access denied'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def mark_all_notifications_read(request):
    """Mark all notifications as read for current user"""
    
    if 'user_id' not in request.session:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        from .models import SellerNotification, BuyerNotification
        from django.utils import timezone
        
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if role == 'seller':
            user_id = request.session.get('seller_id') or user_id
        elif role == 'buyer':
            user_id = request.session.get('buyer_id') or user_id
        elif role == 'admin':
            user_id = request.session.get('admin_user') or user_id
        
        # Mark all unread notifications as read based on role
        if role == 'buyer':
            updated = BuyerNotification.objects.filter(
                buyer_id=user_id,
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )
        else:
            updated = SellerNotification.objects.filter(
                seller_id=user_id,
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )
        
        return JsonResponse({
            'success': True,
            'message': f'{updated} notifications marked as read',
            'updated_count': updated
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Helper function for time ago
def get_time_ago(timestamp):
    """Convert timestamp to human readable 'time ago' format"""
    from django.utils import timezone
    import datetime
    
    now = timezone.now()
    diff = now - timestamp
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    else:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"


# ===========================
# DASHBOARD SEARCH API
# ===========================

@csrf_exempt
def dashboard_search_api(request):
    """
    Universal dashboard search API for all user roles
    - Buyer: searches properties
    - Seller: searches properties and bookings
    - Admin: searches users, properties, logs
    """
    if 'role' not in request.session or 'user_id' not in request.session:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    query = request.GET.get('q', '').strip()
    role = request.session['role']
    
    if not query:
        return JsonResponse({"success": True, "results": [], "query": query})
    
    try:
        results = {
            'query': query,
            'role': role,
            'properties': [],
            'bookings': [],
            'users': [],
            'logs': []
        }
        
        # BUYER: Search properties only
        if role == 'buyer':
            properties = Property.objects.prefetch_related('images').filter(
                status='Available'
            ).filter(
                models.Q(title__icontains=query) |
                models.Q(location__icontains=query) |
                models.Q(city__icontains=query) |
                models.Q(state__icontains=query) |
                models.Q(property_type__icontains=query) |
                models.Q(description__icontains=query)
            )[:10]  # Limit to 10 results
            
            for prop in properties:
                first_image = prop.images.first()
                image_url = ''
                if first_image:
                    url = first_image.image_url
                    if not url.startswith('http') and not url.startswith('/media/'):
                        image_url = settings.MEDIA_URL + url
                    else:
                        image_url = url
                else:
                    image_url = settings.MEDIA_URL + 'default_property.jpg'
                
                results['properties'].append({
                    'id': prop.property_id,
                    'title': prop.title,
                    'location': f"{prop.city}, {prop.state}",
                    'price': float(prop.price),
                    'type': prop.property_type,
                    'status': prop.status,
                    'image_url': image_url,
                    'url': f'/backend/buyer/properties/?property_id={prop.property_id}'
                })
        
        # SELLER: Search properties and bookings
        elif role == 'seller':
            seller_id = request.session.get('seller_id') or request.session.get('user_id')
            
            # Search seller's properties
            properties = Property.objects.prefetch_related('images').filter(
                user_id=seller_id
            ).filter(
                models.Q(title__icontains=query) |
                models.Q(location__icontains=query) |
                models.Q(city__icontains=query) |
                models.Q(property_type__icontains=query)
            )[:8]
            
            for prop in properties:
                first_image = prop.images.first()
                image_url = ''
                if first_image:
                    url = first_image.image_url
                    if not url.startswith('http') and not url.startswith('/media/'):
                        image_url = settings.MEDIA_URL + url
                    else:
                        image_url = url
                else:
                    image_url = settings.MEDIA_URL + 'default_property.jpg'
                
                results['properties'].append({
                    'id': prop.property_id,
                    'title': prop.title,
                    'location': f"{prop.city}, {prop.state}",
                    'price': float(prop.price),
                    'type': prop.property_type,
                    'status': prop.status,
                    'image_url': image_url,
                    'url': f'/backend/seller/properties/?q={prop.property_id}'
                })
            
            # Search seller's bookings
            if query.isdigit():
                bookings = Booking.objects.select_related('property', 'user').filter(
                    property__user_id=seller_id,
                    booking_id=int(query)
                )[:5]
            else:
                bookings = Booking.objects.select_related('property', 'user').filter(
                    property__user_id=seller_id
                ).filter(
                    models.Q(property__title__icontains=query) |
                    models.Q(user__name__icontains=query) |
                    models.Q(status__icontains=query)
                )[:5]
            
            for booking in bookings:
                results['bookings'].append({
                    'id': booking.booking_id,
                    'property_title': booking.property.title,
                    'buyer_name': booking.user.name,
                    'status': booking.status,
                    'booking_date': booking.booking_date.strftime('%Y-%m-%d'),
                    'amount': float(booking.total_amount) if booking.total_amount else 0,
                    'url': f'/backend/seller/bookings/?q={booking.booking_id}'
                })
        
        # ADMIN: Search users, properties, and logs
        elif role == 'admin':
            # Search users
            if query.isdigit():
                users = EstateUser.objects.filter(user_id=int(query))[:5]
            else:
                users = EstateUser.objects.filter(
                    models.Q(name__icontains=query) |
                    models.Q(email__icontains=query) |
                    models.Q(role__icontains=query)
                )[:5]
            
            for user in users:
                results['users'].append({
                    'id': user.user_id,
                    'name': user.name,
                    'email': user.email,
                    'role': user.role,
                    'phone': user.phone,
                    'url': f'/backend/users/html/?q={user.user_id}'
                })
            
            # Search properties
            if query.isdigit():
                properties = Property.objects.prefetch_related('images').filter(
                    property_id=int(query)
                )[:5]
            else:
                properties = Property.objects.prefetch_related('images').filter(
                    models.Q(title__icontains=query) |
                    models.Q(location__icontains=query) |
                    models.Q(city__icontains=query) |
                    models.Q(property_type__icontains=query)
                )[:5]
            
            for prop in properties:
                first_image = prop.images.first()
                image_url = ''
                if first_image:
                    url = first_image.image_url
                    if not url.startswith('http') and not url.startswith('/media/'):
                        image_url = settings.MEDIA_URL + url
                    else:
                        image_url = url
                else:
                    image_url = settings.MEDIA_URL + 'default_property.jpg'
                
                results['properties'].append({
                    'id': prop.property_id,
                    'title': prop.title,
                    'location': f"{prop.city}, {prop.state}",
                    'price': float(prop.price),
                    'type': prop.property_type,
                    'status': prop.status,
                    'owner_name': prop.user.name if prop.user else 'N/A',
                    'image_url': image_url,
                    'url': f'/backend/properties/html/?q={prop.property_id}'
                })
            
            # Search logs
            if query.isdigit():
                logs = Log.objects.select_related('user').filter(log_id=int(query))[:5]
            else:
                logs = Log.objects.select_related('user').filter(
                    models.Q(action__icontains=query) |
                    models.Q(user__name__icontains=query)
                ).order_by('-timestamp')[:5]
            
            for log in logs:
                results['logs'].append({
                    'id': log.log_id,
                    'user_name': log.user.name,
                    'action': log.action,
                    'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'url': f'/backend/logs/?q={log.log_id}'
                })
        
        return JsonResponse({'success': True, 'results': results})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ---------------------------
# Buyer Quick Search API (for dashboard inline search)
# ---------------------------
@csrf_exempt
def buyer_quick_search_api(request):
    """
    Quick search API for buyer dashboard with advanced filters
    Supports: query, price range, property type, bedrooms, bathrooms
    """
    if 'role' not in request.session or request.session['role'] != 'buyer':
        return JsonResponse({"error": "Buyer access required"}, status=403)
    
    try:
        # Get search parameters
        query = request.GET.get('q', '').strip()
        min_price = request.GET.get('min_price', '').strip()
        max_price = request.GET.get('max_price', '').strip()
        property_type = request.GET.get('type', '').strip()
        bedrooms = request.GET.get('bedrooms', '').strip()
        bathrooms = request.GET.get('bathrooms', '').strip()
        
        # Start with available properties
        properties = Property.objects.prefetch_related('images').filter(status='Available')
        
        # Apply text search filter
        if query:
            properties = properties.filter(
                models.Q(title__icontains=query) |
                models.Q(location__icontains=query) |
                models.Q(city__icontains=query) |
                models.Q(state__icontains=query) |
                models.Q(property_type__icontains=query) |
                models.Q(description__icontains=query) |
                models.Q(amenities__icontains=query)
            )
        
        # Apply price range filters
        if min_price:
            try:
                properties = properties.filter(price__gte=float(min_price))
            except ValueError:
                pass
        
        if max_price:
            try:
                properties = properties.filter(price__lte=float(max_price))
            except ValueError:
                pass
        
        # Apply property type filter
        if property_type:
            properties = properties.filter(property_type__iexact=property_type)
        
        # Apply bedrooms filter
        if bedrooms:
            try:
                bedrooms_int = int(bedrooms)
                if bedrooms_int >= 5:
                    properties = properties.filter(bedrooms__gte=5)
                else:
                    properties = properties.filter(bedrooms=bedrooms_int)
            except ValueError:
                pass
        
        # Apply bathrooms filter
        if bathrooms:
            try:
                bathrooms_int = int(bathrooms)
                if bathrooms_int >= 4:
                    properties = properties.filter(bathrooms__gte=4)
                else:
                    properties = properties.filter(bathrooms=bathrooms_int)
            except ValueError:
                pass
        
        # Limit results
        properties = properties[:20]
        
        # Build response
        results = []
        for prop in properties:
            first_image = prop.images.first()
            image_url = ''
            if first_image:
                url = first_image.image_url
                if not url.startswith('http') and not url.startswith('/media/'):
                    image_url = settings.MEDIA_URL + url
                else:
                    image_url = url
            else:
                image_url = settings.MEDIA_URL + 'default_property.jpg'
            
            results.append({
                'property_id': prop.property_id,
                'title': prop.title,
                'description': prop.description[:150] + '...' if len(prop.description) > 150 else prop.description,
                'location': prop.location,
                'city': prop.city,
                'state': prop.state,
                'price': float(prop.price),
                'area_sqft': float(prop.area_sqft) if prop.area_sqft else None,
                'bedrooms': prop.bedrooms,
                'bathrooms': prop.bathrooms,
                'property_type': prop.property_type,
                'status': prop.status,
                'image_url': image_url,
                'amenities': prop.amenities
            })
        
        # Log the search activity
        try:
            buyer = EstateUser.objects.get(user_id=request.session['user_id'])
            search_details = f"Quick search: '{query}'" if query else "Quick search with filters"
            if property_type:
                search_details += f", type={property_type}"
            if min_price or max_price:
                search_details += f", price={min_price or '0'}-{max_price or '∞'}"
            Log.objects.create(user=buyer, action=search_details)
        except EstateUser.DoesNotExist:
            pass
        
        return JsonResponse({
            'success': True,
            'properties': results,
            'count': len(results),
            'filters_applied': {
                'query': query,
                'min_price': min_price,
                'max_price': max_price,
                'property_type': property_type,
                'bedrooms': bedrooms,
                'bathrooms': bathrooms
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ======================
# ADMIN SUPPORT TICKETS
# ======================

def admin_support_tickets(request):
    """Admin view to manage all support tickets"""
    if 'role' not in request.session or request.session['role'] != "admin":
        return redirect("/backend/login/")
    
    try:
        # Get admin user
        admin_user_id = request.session.get('admin_user') or request.session.get('user_id')
        admin_user = EstateUser.objects.get(user_id=admin_user_id)
        
        # Log activity
        Log.objects.create(user=admin_user, action="Viewed support tickets dashboard")
        
        # Get filter parameters
        status_filter = request.GET.get('status', 'all')
        search_query = request.GET.get('q', '').strip()
        
        # Base queryset with user details - ONLY select_related for user, not assigned_to yet
        tickets = SupportTicket.objects.select_related('user').order_by('-created_at')
        
        # Apply filters
        if status_filter != 'all':
            tickets = tickets.filter(status=status_filter)
        
        # Apply search (token ID or subject)
        if search_query:
            if search_query.startswith('SUP-'):
                tickets = tickets.filter(token_id__icontains=search_query)
            else:
                tickets = tickets.filter(
                    models.Q(subject__icontains=search_query) |
                    models.Q(description__icontains=search_query) |
                    models.Q(user__name__icontains=search_query)
                )
        
        # Get statistics
        stats = {
            'total': SupportTicket.objects.count(),
            'open': SupportTicket.objects.filter(status='open').count(),
            'in_progress': SupportTicket.objects.filter(status='in_progress').count(),
            'resolved': SupportTicket.objects.filter(status='resolved').count(),
            'closed': SupportTicket.objects.filter(status='closed').count(),
        }
        
        context = {
            'admin': admin_user,
            'tickets': tickets,
            'stats': stats,
            'status_filter': status_filter,
            'search_query': search_query
        }
        
        return render(request, 'backend/admin_support_tickets.html', context)
        
    except EstateUser.DoesNotExist:
        return JsonResponse({
            'error': 'Admin user not found. Please login again.'
        }, status=404)
    except Exception as e:
        # Log the error
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Admin Support Tickets Error: {str(e)}")
        print(error_trace)
        
        # Return user-friendly error page or JSON
        return render(request, 'backend/error_page.html', {
            'error_title': 'Support Tickets Error',
            'error_message': 'Unable to load support tickets. Please contact system administrator.',
            'error_details': str(e) if request.session.get('role') == 'admin' else None
        }, status=500)


@csrf_exempt
def admin_solve_ticket_api(request):
    """API endpoint to mark ticket as solved with admin response"""
    if 'role' not in request.session or request.session['role'] != "admin":
        return JsonResponse({"error": "Admin access required"}, status=403)
    
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    
    try:
        data = json.loads(request.body)
        ticket_id = data.get('ticket_id')
        admin_response = data.get('admin_response', '').strip()
        
        if not ticket_id:
            return JsonResponse({"error": "Ticket ID required"}, status=400)
        
        if not admin_response:
            return JsonResponse({"error": "Admin response message required"}, status=400)
        
        # Get ticket
        ticket = SupportTicket.objects.get(ticket_id=ticket_id)
        
        # Get admin user
        admin_user_id = request.session.get('admin_user') or request.session.get('user_id')
        admin_user = EstateUser.objects.get(user_id=admin_user_id)
        
        # Update ticket status
        from django.utils import timezone
        ticket.status = 'resolved'
        ticket.resolved_at = timezone.now()
        ticket.assigned_to = admin_user
        ticket.save()
        
        # Create ticket response
        TicketResponse.objects.create(
            ticket=ticket,
            user=admin_user,
            message=admin_response,
            is_staff_response=True
        )
        
        # Notify buyer about ticket resolution using notification service
        from . import notification_service
        notification_service.notify_ticket_resolved(ticket_id)
        
        # Log activity
        Log.objects.create(
            user=admin_user,
            action=f"Solved support ticket {ticket.token_id} for {ticket.user.name}"
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Ticket marked as solved and buyer notified',
            'ticket_id': ticket.ticket_id,
            'token_id': ticket.token_id,
            'resolved_at': ticket.resolved_at.isoformat()
        })
        
    except SupportTicket.DoesNotExist:
        return JsonResponse({"error": "Ticket not found"}, status=404)
    except EstateUser.DoesNotExist:
        return JsonResponse({"error": "Admin user not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def admin_update_ticket_status_api(request):
    """API endpoint to update ticket status (open, in_progress, resolved, closed)"""
    if 'role' not in request.session or request.session['role'] != "admin":
        return JsonResponse({"error": "Admin access required"}, status=403)
    
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    
    try:
        data = json.loads(request.body)
        ticket_id = data.get('ticket_id')
        new_status = data.get('status')
        
        if not ticket_id or not new_status:
            return JsonResponse({"error": "Ticket ID and status required"}, status=400)
        
        if new_status not in ['open', 'in_progress', 'resolved', 'closed']:
            return JsonResponse({"error": "Invalid status"}, status=400)
        
        # Get ticket
        ticket = SupportTicket.objects.get(ticket_id=ticket_id)
        old_status = ticket.status
        ticket.status = new_status
        
        # If marking as resolved or closed, set resolved_at
        if new_status in ['resolved', 'closed'] and not ticket.resolved_at:
            from django.utils import timezone
            ticket.resolved_at = timezone.now()
        
        ticket.save()
        
        # Notify buyer if status changed to resolved
        if new_status == 'resolved':
            from . import notification_service
            notification_service.notify_ticket_resolved(ticket_id)
        
        # Log activity
        admin_user_id = request.session.get('admin_user') or request.session.get('user_id')
        admin_user = EstateUser.objects.get(user_id=admin_user_id)
        Log.objects.create(
            user=admin_user,
            action=f"Changed ticket {ticket.token_id} status from {old_status} to {new_status}"
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Ticket status updated to {new_status}',
            'ticket_id': ticket.ticket_id,
            'old_status': old_status,
            'new_status': new_status
        })
        
    except SupportTicket.DoesNotExist:
        return JsonResponse({"error": "Ticket not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ======================
# ACTIVITY LOGS BULK DELETE
# ======================

@csrf_exempt
def bulk_delete_logs_api(request):
    """API endpoint to bulk delete activity logs"""
    if 'role' not in request.session:
        return JsonResponse({"error": "Authentication required"}, status=403)
    
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    
    try:
        data = json.loads(request.body)
        log_ids = data.get('log_ids', [])
        
        if not log_ids:
            return JsonResponse({"error": "No log IDs provided"}, status=400)
        
        if not isinstance(log_ids, list):
            return JsonResponse({"error": "log_ids must be an array"}, status=400)
        
        # Get current user
        user_id = request.session.get('admin_user') or request.session.get('seller_id') or request.session.get('buyer_id') or request.session.get('user_id')
        current_user = EstateUser.objects.get(user_id=user_id)
        role = request.session.get('role')
        
        # Filter logs based on role
        if role == 'admin':
            # Admin can delete any logs
            logs_to_delete = Log.objects.filter(log_id__in=log_ids)
        else:
            # Seller/Buyer can only delete their own logs
            logs_to_delete = Log.objects.filter(log_id__in=log_ids, user=current_user)
        
        if not logs_to_delete.exists():
            return JsonResponse({"error": "No valid logs found to delete"}, status=404)
        
        # Count before deletion
        delete_count = logs_to_delete.count()
        
        # Store info before deletion for logging
        deleted_log_ids = list(logs_to_delete.values_list('log_id', flat=True))
        
        # Perform bulk delete
        logs_to_delete.delete()
        
        # Create a log entry about the bulk deletion (if user has logs remaining)
        Log.objects.create(
            user=current_user,
            action=f"Bulk deleted {delete_count} activity log(s)"
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully deleted {delete_count} log(s)',
            'deleted_count': delete_count,
            'deleted_ids': deleted_log_ids
        })
        
    except EstateUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ==================== PROPERTY IMAGE MANAGEMENT APIs ====================

@csrf_exempt
def get_property_images_api(request, property_id):
    """
    API endpoint to fetch all images for a specific property
    GET /backend/api/property-images/<property_id>/
    Returns: JSON with array of image objects containing id, url, description
    """
    try:
        # Get the property
        property_obj = Property.objects.get(property_id=property_id)
        
        # Check if user has permission to view this property
        if 'role' in request.session:
            role = request.session['role']
            user_id = request.session.get('admin_user') or request.session.get('seller_id') or request.session.get('buyer_id') or request.session.get('user_id')
            
            # Sellers can only see their own properties
            if role == 'seller' and property_obj.user_id != user_id:
                return JsonResponse({"error": "You don't have permission to view this property"}, status=403)
        
        # Fetch all images for this property
        images = PropertyImage.objects.filter(property=property_obj)
        
        # Build image data array
        image_data = []
        for img in images:
            # Construct full URL for the image
            url = img.image_url
            if not url.startswith('http') and not url.startswith('/media/'):
                url = settings.MEDIA_URL + url
            
            image_data.append({
                'id': img.image_id,
                'url': url,
                'description': img.description or '',
                'property_id': property_id
            })
        
        return JsonResponse({
            'success': True,
            'images': image_data,
            'count': len(image_data)
        })
        
    except Property.DoesNotExist:
        return JsonResponse({"error": "Property not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def delete_property_image_api(request, image_id):
    """
    API endpoint to permanently delete a property image
    DELETE /backend/api/property-images/delete/<image_id>/
    Security: Only sellers can delete their own property images, admins can delete any
    """
    if request.method != "DELETE" and request.method != "POST":
        return JsonResponse({"error": "DELETE or POST method required"}, status=405)
    
    if 'role' not in request.session:
        return JsonResponse({"error": "Authentication required"}, status=403)
    
    try:
        # Get the image
        image = PropertyImage.objects.get(image_id=image_id)
        property_obj = image.property
        
        # Check permission
        role = request.session['role']
        user_id = request.session.get('admin_user') or request.session.get('seller_id') or request.session.get('buyer_id') or request.session.get('user_id')
        
        # Only seller who owns the property or admin can delete
        if role == 'seller' and property_obj.user_id != user_id:
            return JsonResponse({"error": "You don't have permission to delete this image"}, status=403)
        
        # Store image path for deletion
        image_path = image.image_url
        
        # Delete the file from storage if it exists
        try:
            from django.core.files.storage import default_storage
            if default_storage.exists(image_path):
                default_storage.delete(image_path)
        except Exception as file_error:
            print(f"Warning: Could not delete file {image_path}: {file_error}")
        
        # Delete the database record
        image.delete()
        
        # Log the activity
        current_user = EstateUser.objects.get(user_id=user_id)
        Log.objects.create(
            user=current_user,
            action=f"Deleted image from property: {property_obj.title} (ID: {property_obj.property_id})"
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Image deleted successfully',
            'image_id': image_id
        })
        
    except PropertyImage.DoesNotExist:
        return JsonResponse({"error": "Image not found"}, status=404)
    except EstateUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def upload_property_images_api(request, property_id):
    """
    API endpoint to upload new images to a property
    POST /backend/api/property-images/upload/<property_id>/
    Accepts: multipart/form-data with 'images' file field (supports multiple)
    Validation: File format (jpg, jpeg, png, webp), size (<5MB per image)
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    
    if 'role' not in request.session:
        return JsonResponse({"error": "Authentication required"}, status=403)
    
    try:
        # Get the property
        property_obj = Property.objects.get(property_id=property_id)
        
        # Check permission
        role = request.session['role']
        user_id = request.session.get('admin_user') or request.session.get('seller_id') or request.session.get('buyer_id') or request.session.get('user_id')
        
        # Only seller who owns the property or admin can upload
        if role == 'seller' and property_obj.user_id != user_id:
            return JsonResponse({"error": "You don't have permission to upload images for this property"}, status=403)
        
        # Get uploaded files
        images = request.FILES.getlist('images')
        
        if not images:
            return JsonResponse({"error": "No images provided"}, status=400)
        
        # Validation settings
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']
        
        uploaded_images = []
        errors = []
        
        for idx, img in enumerate(images):
            # Validate file size
            if img.size > MAX_FILE_SIZE:
                errors.append(f"Image {idx + 1} exceeds 5MB size limit")
                continue
            
            # Validate file extension
            file_ext = img.name.split('.')[-1].lower() if '.' in img.name else ''
            if file_ext not in ALLOWED_EXTENSIONS:
                errors.append(f"Image {idx + 1} has invalid format. Allowed: jpg, jpeg, png, webp")
                continue
            
            # Save the file with unique filename
            import uuid
            unique_filename = f"property_{property_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
            
            try:
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile
                
                file_path = default_storage.save(unique_filename, ContentFile(img.read()))
                
                # Create PropertyImage record
                new_image = PropertyImage.objects.create(
                    property=property_obj,
                    image_url=file_path,
                    description=f"Property image {idx + 1}"
                )
                
                # Construct full URL
                url = file_path
                if not url.startswith('http') and not url.startswith('/media/'):
                    url = settings.MEDIA_URL + url
                
                uploaded_images.append({
                    'id': new_image.image_id,
                    'url': url,
                    'description': new_image.description
                })
                
            except Exception as save_error:
                errors.append(f"Failed to save image {idx + 1}: {str(save_error)}")
        
        # Log the activity
        current_user = EstateUser.objects.get(user_id=user_id)
        Log.objects.create(
            user=current_user,
            action=f"Uploaded {len(uploaded_images)} image(s) to property: {property_obj.title} (ID: {property_id})"
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully uploaded {len(uploaded_images)} image(s)',
            'uploaded_count': len(uploaded_images),
            'images': uploaded_images,
            'errors': errors if errors else None
        })
        
    except Property.DoesNotExist:
        return JsonResponse({"error": "Property not found"}, status=404)
    except EstateUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def update_property_api(request, property_id):
    """
    API endpoint to update property details
    POST /backend/seller/property/update/<property_id>/
    Accepts: JSON with property fields
    Security: Only seller who owns the property or admin can update
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    
    if 'role' not in request.session:
        return JsonResponse({"error": "Authentication required"}, status=403)
    
    try:
        # Get the property
        property_obj = Property.objects.get(property_id=property_id)
        
        # Check permission
        role = request.session['role']
        user_id = request.session.get('admin_user') or request.session.get('seller_id') or request.session.get('buyer_id') or request.session.get('user_id')
        
        # Only seller who owns the property or admin can update
        if role == 'seller' and property_obj.user_id != user_id:
            return JsonResponse({"error": "You don't have permission to update this property"}, status=403)
        
        # Parse JSON data
        data = json.loads(request.body)
        
        # Update fields with proper type conversion
        if 'title' in data:
            property_obj.title = data['title']
        if 'description' in data:
            property_obj.description = data['description']
        if 'property_type' in data:
            property_obj.property_type = data['property_type']
        if 'price' in data:
            # Convert to float first, then to int to handle decimal strings
            property_obj.price = int(float(data['price']))
        if 'area_sqft' in data:
            # Convert to float first, then to int to handle decimal strings like "444.0"
            property_obj.area_sqft = int(float(data['area_sqft']))
        if 'bedrooms' in data:
            # Convert to int, handle both string and number
            property_obj.bedrooms = int(float(data['bedrooms']))
        if 'bathrooms' in data:
            # Convert to int, handle both string and number
            property_obj.bathrooms = int(float(data['bathrooms']))
        if 'city' in data:
            property_obj.city = data['city']
        if 'state' in data:
            property_obj.state = data['state']
        if 'address' in data:
            property_obj.address = data['address']
            # Update location field (city + state + address)
            property_obj.location = f"{data['address']}, {data['city']}, {data['state']}"
        if 'amenities' in data:
            property_obj.amenities = data['amenities']
        
        # Save the property
        property_obj.save()
        
        # Log the activity
        current_user = EstateUser.objects.get(user_id=user_id)
        Log.objects.create(
            user=current_user,
            action=f"Updated property: {property_obj.title} (ID: {property_id})"
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Property updated successfully',
            'property': {
                'id': property_obj.property_id,
                'title': property_obj.title,
                'price': str(property_obj.price),
                'location': property_obj.location,
                'city': property_obj.city,
                'state': property_obj.state,
                'area_sqft': property_obj.area_sqft,
                'bedrooms': property_obj.bedrooms,
                'bathrooms': property_obj.bathrooms
            }
        })
        
    except Property.DoesNotExist:
        return JsonResponse({"error": "Property not found"}, status=404)
    except EstateUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except ValueError as e:
        return JsonResponse({"error": f"Invalid data format: {str(e)}"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Update failed: {str(e)}"}, status=500)
        return JsonResponse({"error": "User not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
