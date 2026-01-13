from django.contrib import admin
from .models import EstateUser, Property, PropertyImage, Booking, Transaction, Log, PriceDataModel

admin.site.register(EstateUser)
admin.site.register(Property)
admin.site.register(PropertyImage)
admin.site.register(Booking)
admin.site.register(Transaction)
admin.site.register(Log)
admin.site.register(PriceDataModel)