from django.urls import path
from . import views
from . import chatbot_views

urlpatterns = [

    path("admin/profile/", views.admin_profile, name="admin_profile"),
    path("admin/profile/edit/", views.edit_profile, name="admin_edit_profile"),
    path("admin/profile/change-password/", views.change_password, name="admin_change_password"),
    path("admin/profile/upload-photo/", views.upload_profile_photo, name="admin_upload_profile_photo"),
    path("buyer/profile/", views.buyer_profile, name="buyer_profile"),
    path("buyer/profile/edit/", views.edit_profile, name="buyer_edit_profile"),
    path("buyer/profile/change-password/", views.change_password, name="buyer_change_password"),
    path("buyer/profile/upload-photo/", views.upload_profile_photo, name="buyer_upload_profile_photo"),
    path("profile/", views.profile_view, name="profile"),
    path('properties/html/', views.properties_html, name="properties_html"),
    path("property_images/html/", views.property_images_html, name="property_images_html"),

    path("bookings/", views.bookings_html, name="bookings"),
    path("bookings/update-status/<int:booking_id>/", views.update_booking_status, name="update_booking_status"),
    path("transactions/html/", views.transactions_html, name="transactions_html"),
    path("logs/", views.logs_html, name="logs"),
    path("price_data_model/html/", views.price_data_model_html, name="price_data_model_html"),

    # Login & Dashboard
    path('login/', views.login_view, name="login"),
    path('dashboard/', views.dashboard_view, name="dashboard"),
    path('logout/', views.logout_view, name="logout"),

    # Users
    path("users/html/", views.users_html, name="users_html"),
    path("users/delete/<int:user_id>/", views.delete_user, name="delete_user"),
    path("users/edit/<int:user_id>/", views.edit_user, name="edit_user"),
    path("users/block/<int:user_id>/", views.block_user, name="block_user"),
    path("signup/", views.signup_view, name="signup"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),

    # Seller dashboards
    path('buyer-home/', views.buyer_dashboard_view, name="buyer_dashboard"),


    path("seller/properties/", views.seller_properties, name="seller_properties"),
    path("seller/add-property/", views.add_property, name="add_property"),
    path("admin/add-property/", views.admin_add_property, name="admin_add_property"),
    path("seller/property/update/<int:property_id>/", views.update_property, name="update_property"),
    path("seller/bookings/", views.seller_bookings, name="seller_bookings"),
    path("seller/transactions/", views.seller_transactions, name="seller_transactions"),
    path("seller/logs/", views.seller_logs, name="seller_logs"),
    path("seller/profile/", views.seller_profile, name="seller_profile"),
    path("seller/profile/edit/", views.edit_profile, name="seller_edit_profile"),
    path("seller/profile/change-password/", views.change_password, name="seller_change_password"),
    path("seller/profile/upload-photo/", views.upload_profile_photo, name="upload_profile_photo"),


    #buyer dashboards
    path('seller-home/', views.seller_dashboard_view, name="seller_dashboard"),
    path("buyer/properties/", views.buyer_properties_view, name="buyer_properties"),

    # Admin property update with image management
    path("admin/property/update/", views.update_property_admin, name="update_property_admin"),

    # Buyer Dashboard API Endpoints
    path("api/buyer/profile/", views.buyer_profile_api, name="buyer_profile_api"),
    path("api/buyer/quick-search/", views.buyer_quick_search_api, name="buyer_quick_search_api"),
    path("api/buyer/saved-properties/", views.buyer_saved_properties_api, name="buyer_saved_properties_api"),
    path("api/buyer/saved-properties/<int:saved_id>/notes/", views.update_saved_property_notes, name="update_saved_property_notes"),
    path("api/buyer/saved-properties/<int:saved_id>/remove/", views.remove_saved_property, name="remove_saved_property"),
    path("api/buyer/bookings/create/", views.create_booking_api, name="create_booking_api"),
    path("api/buyer/transactions/", views.buyer_transaction_history_api, name="buyer_transaction_history_api"),
    path("api/buyer/payment-history/", views.buyer_payment_history_api, name="buyer_payment_history_api"),
    path("api/buyer/support-tickets/", views.buyer_support_tickets_api, name="buyer_support_tickets_api"),
    path("api/buyer/reviews/", views.buyer_reviews_api, name="buyer_reviews_api"),
    path("api/buyer/reviewable-properties/", views.buyer_reviewable_properties_api, name="buyer_reviewable_properties_api"),
    path("api/buyer/market-insights/", views.buyer_market_insights_api, name="buyer_market_insights_api"),
    
    # Property Images API
    path("api/property-images/<int:property_id>/", views.get_property_images_api, name="get_property_images_api"),
    path("api/property-images/delete/<int:image_id>/", views.delete_property_image_api, name="delete_property_image_api"),
    path("api/property-images/upload/<int:property_id>/", views.upload_property_images_api, name="upload_property_images_api"),
    
    # Property Update API
    path("seller/property/update/<int:property_id>/", views.update_property_api, name="update_property_api"),
    
    # Unified Notification APIs
    path("api/notifications/", views.get_notifications_api, name="get_notifications_api"),
    path("api/notifications/<int:notification_id>/mark-read/", views.mark_notification_read, name="mark_notification_read"),
    path("api/notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    
    # Dashboard Search API
    path("api/dashboard/search/", views.dashboard_search_api, name="dashboard_search_api"),

    # Admin Support Tickets
    path("admin/support-tickets/", views.admin_support_tickets, name="admin_support_tickets"),
    path("api/admin/tickets/solve/", views.admin_solve_ticket_api, name="admin_solve_ticket_api"),
    path("api/admin/tickets/update-status/", views.admin_update_ticket_status_api, name="admin_update_ticket_status_api"),
    
    # Activity Logs Bulk Delete
    path("api/logs/bulk-delete/", views.bulk_delete_logs_api, name="bulk_delete_logs_api"),

    # AI Chatbot Endpoints
    path("api/chatbot/message/", chatbot_views.chatbot_message_api, name="chatbot_message_api"),
    path("api/chatbot/history/", chatbot_views.chatbot_history_api, name="chatbot_history_api"),
    path("api/chatbot/feedback/", chatbot_views.chatbot_feedback_api, name="chatbot_feedback_api"),
    path("api/chatbot/clear/", chatbot_views.chatbot_clear_history_api, name="chatbot_clear_history_api"),
    path("api/chatbot/property-summary/", chatbot_views.chatbot_property_summary_api, name="chatbot_property_summary_api"),
    path("admin/chatbot-analytics/", chatbot_views.admin_chatbot_analytics, name="admin_chatbot_analytics"),
  
]


