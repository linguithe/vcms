from django.contrib import admin
from .models import *

# Register your models here.
for model in [
    AppointmentType,
]:
    admin.site.register(model)