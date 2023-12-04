from rest_framework import serializers
from .models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=False)

    class Meta:
        model = Customer
        fields = ('id', 'user', 'name', 'gender')

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ('id', 'lang')

class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = ('id', 'date')

class SlotSerializer(serializers.ModelSerializer):
    schedule = ScheduleSerializer(read_only=False)

    class Meta:
        model = Slot
        fields = ('id', 'schedule', 'time', 'is_available', 'booked_by')

class StaffSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=False)

    class Meta:
        model = Staff
        fields = ('id', 'user', 'staff_no', 'role', 'name', 'gender')

class SpecializationSerializer(serializers.ModelSerializer):
    staff = StaffSerializer(read_only=False)

    class Meta:
        model = Specialization
        fields = ('id', 'title', 'staff')

class CertificationSerializer(serializers.ModelSerializer):
    staff = StaffSerializer(read_only=False)

    class Meta:
        model = Certification
        fields = ('id', 'title', 'staff')

class StaffLanguageMappingSerializer(serializers.ModelSerializer):
    staff = StaffSerializer(read_only=False)
    language = LanguageSerializer(read_only=False)

    class Meta:
        model = StaffLanguageMapping
        fields = ('id', 'staff', 'language')

class StaffScheduleMappingSerializer(serializers.ModelSerializer):
    staff = StaffSerializer(read_only=False)
    schedule = ScheduleSerializer(read_only=False)

    class Meta:
        model = StaffScheduleMapping
        fields = ('id', 'staff', 'schedule')

class PetSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=False)

    class Meta:
        model = Pet
        fields = ('id', 'customer', 'animal', 'name', 'gender', 'species', 'colour', 'description')

class AppointmentSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=False)
    staff = StaffSerializer(read_only=False)
    slot = SlotSerializer(read_only=False)

    class Meta:
        model = Appointment
        fields = ('id', 'customer', 'staff', 'slot', 'description')