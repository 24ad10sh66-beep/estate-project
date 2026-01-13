from django.db import models


# ---------------------------
# User Model
# ---------------------------
class EstateUser(models.Model):
    user_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    password_hash = models.CharField(max_length=100)
    role = models.CharField(max_length=20)
    phone = models.CharField(max_length=15, null=True, blank=True)
    email = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    profile_photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "users"


# ---------------------------
# Property Model
# ---------------------------
class Property(models.Model):
    # Property Status Choices (enforced at model level)
    STATUS_AVAILABLE = "Available"
    STATUS_SOLD = "Sold"
    STATUS_PENDING = "Pending"

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_SOLD, "Sold"),
        (STATUS_PENDING, "Pending"),
    ]

    property_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        EstateUser, on_delete=models.CASCADE, related_name="properties", null=True
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    location = models.CharField(max_length=100)
    city = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    price = models.FloatField()
    area_sqft = models.FloatField(null=True, blank=True)
    bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.IntegerField(null=True, blank=True)
    property_type = models.CharField(max_length=50, default="Residential")
    amenities = models.CharField(max_length=255, null=True, blank=True)  # comma separated
    contact = models.CharField(max_length=20, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=STATUS_AVAILABLE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "properties"


# ---------------------------
# Property Image Model
# ---------------------------
class PropertyImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="images", null=True
    )
    image_url = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Image {self.image_id} for {self.property.title}"

    class Meta:
        db_table = "property_images"


# ---------------------------
# Booking Model
# ---------------------------
class Booking(models.Model):
    booking_id = models.AutoField(primary_key=True)
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="bookings", null=True
    )
    user = models.ForeignKey(
        EstateUser, on_delete=models.CASCADE, related_name="bookings", null=True
    )
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="pending")

    def __str__(self):
        return f"Booking {self.booking_id} - {self.user.name} on {self.property.title}"

    class Meta:
        db_table = "bookings"


# ---------------------------
# Transactions Model
# ---------------------------
class Transaction(models.Model):
    txn_id = models.AutoField(primary_key=True)
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="transactions", null=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_status = models.CharField(max_length=20)  # pending/success/failed/completed
    payment_method = models.CharField(
        max_length=50, null=True, blank=True
    )  # upi/credit_card/debit_card/net_banking
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Txn {self.txn_id} - {self.payment_status}"

    class Meta:
        db_table = "transactions"


# ---------------------------
# Logs Model
# ---------------------------
class Log(models.Model):
    log_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(EstateUser, on_delete=models.CASCADE, related_name="logs", null=True)
    action = models.CharField(max_length=500)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - {self.action}"

    class Meta:
        db_table = "logs"


# ---------------------------
# Price Data Model
# ---------------------------
class PriceDataModel(models.Model):
    data_id = models.AutoField(primary_key=True)
    location = models.CharField(max_length=100)
    area_sqft = models.FloatField()
    bedrooms = models.IntegerField()
    bathrooms = models.IntegerField()
    property_type = models.CharField(max_length=50)
    actual_price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.location} - {self.property_type} ({self.area_sqft} sqft)"

    class Meta:
        db_table = "price_data_model"


# ---------------------------
# Saved Properties Model
# ---------------------------
class SavedProperty(models.Model):
    saved_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        EstateUser, on_delete=models.CASCADE, related_name="saved_properties", null=True
    )
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="saved_by", null=True
    )
    saved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)  # Personal notes about the property

    def __str__(self):
        return f"{self.user.name} saved {self.property.title}"

    class Meta:
        db_table = "saved_properties"
        unique_together = ("user", "property")  # Prevent duplicate saves


# ---------------------------
# Payment History Model
# ---------------------------
class PaymentHistory(models.Model):
    payment_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        EstateUser, on_delete=models.CASCADE, related_name="payment_history", null=True
    )
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="payments", null=True
    )
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="payment_details", null=True, blank=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_type = models.CharField(
        max_length=50
    )  # booking_fee, token_amount, full_payment, emi, etc.
    payment_method = models.CharField(
        max_length=50, default="online"
    )  # online, cash, cheque, bank_transfer
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, default="pending"
    )  # pending, success, failed, refunded
    payment_reference = models.CharField(
        max_length=100, null=True, blank=True
    )  # transaction reference
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.name} - ₹{self.amount} for {self.property.title}"

    class Meta:
        db_table = "payment_history"


# ---------------------------
# Support Tickets Model
# ---------------------------
class SupportTicket(models.Model):
    ticket_id = models.AutoField(primary_key=True)
    token_id = models.CharField(
        max_length=50, unique=True, null=True, blank=True
    )  # Format: SUP-YYYYMMDD-XXXX
    user = models.ForeignKey(
        EstateUser, on_delete=models.CASCADE, related_name="support_tickets", null=True
    )
    subject = models.CharField(max_length=200)
    category = models.CharField(
        max_length=50, default="general"
    )  # general, payment, property, technical
    priority = models.CharField(max_length=20, default="medium")  # low, medium, high, urgent
    status = models.CharField(max_length=20, default="open")  # open, in_progress, resolved, closed
    description = models.TextField()
    assigned_to = models.ForeignKey(
        EstateUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Ticket #{self.ticket_id} - {self.token_id or 'No Token'} - {self.subject}"

    class Meta:
        db_table = "support_tickets"


# ---------------------------
# Support Ticket Responses Model
# ---------------------------
class TicketResponse(models.Model):
    response_id = models.AutoField(primary_key=True)
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="responses")
    user = models.ForeignKey(
        EstateUser, on_delete=models.CASCADE, related_name="ticket_responses", null=True
    )
    message = models.TextField()
    is_staff_response = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response to Ticket #{self.ticket.ticket_id}"

    class Meta:
        db_table = "ticket_responses"


# ---------------------------
# Property Reviews Model
# ---------------------------
class PropertyReview(models.Model):
    review_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        EstateUser, on_delete=models.CASCADE, related_name="reviews", null=True
    )
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="reviews", null=True
    )
    rating = models.IntegerField(default=5)  # 1-5 star rating
    title = models.CharField(max_length=200, null=True, blank=True)
    review_text = models.TextField()
    pros = models.TextField(null=True, blank=True)  # What user liked
    cons = models.TextField(null=True, blank=True)  # What user didn't like
    would_recommend = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)  # Verified purchase/booking
    is_approved = models.BooleanField(default=True)  # Admin approved
    helpful_votes = models.IntegerField(default=0)  # Other users found it helpful
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.name} reviewed {self.property.title} - {self.rating}★"

    class Meta:
        db_table = "property_reviews"
        unique_together = ("user", "property")  # One review per user per property


# ---------------------------
# Market Insights Model
# ---------------------------
class MarketInsight(models.Model):
    insight_id = models.AutoField(primary_key=True)
    location = models.CharField(max_length=100)
    property_type = models.CharField(max_length=50)
    average_price = models.DecimalField(max_digits=12, decimal_places=2)
    price_change_percent = models.FloatField(default=0.0)  # % change from last period
    total_listings = models.IntegerField(default=0)
    sold_count = models.IntegerField(default=0)
    days_on_market = models.IntegerField(default=0)  # Average days to sell
    demand_score = models.FloatField(default=0.0)  # 0-100 score
    period_start = models.DateField()
    period_end = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.location} - {self.property_type} Market Data"

    class Meta:
        db_table = "market_insights"


# ---------------------------
# Seller Notifications Model
# ---------------------------
class SellerNotification(models.Model):
    notification_id = models.AutoField(primary_key=True)
    seller = models.ForeignKey(
        EstateUser, on_delete=models.CASCADE, related_name="seller_notifications", null=True
    )
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="notifications", null=True
    )
    booking = models.ForeignKey(
        "Booking", on_delete=models.CASCADE, related_name="notifications", null=True
    )
    notification_type = models.CharField(
        max_length=50, default="booking_received"
    )  # booking_received, payment_received, booking_cancelled
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Notification #{self.notification_id} - {self.title}"

    class Meta:
        db_table = "seller_notifications"
        ordering = ["-created_at"]


# ---------------------------
# Buyer Notifications Model
# ---------------------------
class BuyerNotification(models.Model):
    notification_id = models.AutoField(primary_key=True)
    buyer = models.ForeignKey(
        EstateUser, on_delete=models.CASCADE, related_name="buyer_notifications", null=True
    )
    support_ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="buyer_notifications",
        null=True,
        blank=True,
    )
    notification_type = models.CharField(
        max_length=50, default="ticket_resolved"
    )  # ticket_resolved, ticket_updated, system_message
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Notification #{self.notification_id} - {self.title}"

    class Meta:
        db_table = "buyer_notifications"
        ordering = ["-created_at"]


# ---------------------------
# Chatbot Conversation Model
# ---------------------------
class ChatConversation(models.Model):
    conversation_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        EstateUser,
        on_delete=models.CASCADE,
        related_name="chat_conversations",
        null=True,
        blank=True,
    )
    session_id = models.CharField(max_length=100, unique=True)  # For anonymous users
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    user_role = models.CharField(max_length=20, null=True, blank=True)  # buyer/seller/admin

    def __str__(self):
        return (
            f"Conversation #{self.conversation_id} - {self.user.name if self.user else 'Anonymous'}"
        )

    class Meta:
        db_table = "chat_conversations"
        ordering = ["-last_activity"]


# ---------------------------
# Chatbot Message Model
# ---------------------------
class ChatMessage(models.Model):
    message_id = models.AutoField(primary_key=True)
    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender_type = models.CharField(max_length=10)  # 'user' or 'bot'
    message_text = models.TextField()
    message_metadata = models.JSONField(
        null=True, blank=True
    )  # For storing context, properties, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    is_helpful = models.BooleanField(null=True, blank=True)  # User feedback

    def __str__(self):
        return f"Message #{self.message_id} - {self.sender_type}"

    class Meta:
        db_table = "chat_messages"
        ordering = ["created_at"]
