from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext as _


# Create your models here.
class UserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_('Users must have an email address'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
    
class Customer(models.Model):
    user            = models.ForeignKey(User, on_delete=models.CASCADE)
    name            = models.CharField(blank=False, null=False, max_length=250)
    gender          = models.CharField(blank=False, null=False, max_length=50)

# A language can be associated to many staffs, and a staff can have many languages
class Language(models.Model):
    lang            = models.CharField(blank=False, null=False, max_length=100)

# A schedule can be associated to many staff, and a staff can have many schedule
# A schedule has many slots
class Schedule(models.Model):
    date            = models.DateField(blank=False, null=False)

class Slot(models.Model):
    schedule        = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    time            = models.TimeField(blank=False, null=False)
    is_available    = models.BooleanField(blank=False, null=False, default=True)
    booked_by       = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True)

class Staff(models.Model):
    user            = models.ForeignKey(User, on_delete=models.CASCADE)
    staff_no        = models.CharField(blank=False, null=False, max_length=30)
    role            = models.CharField(blank=False, null=False, max_length=50)
    name            = models.CharField(blank=False, null=False, max_length=250)
    gender          = models.CharField(blank=False, null=False, max_length=50)

# A staff can have many specializations
class Specialization(models.Model):
    title           = models.CharField(blank=False, null=False, max_length=100)
    staff           = models.ForeignKey(Staff, on_delete=models.CASCADE)

# A staff can have many certifications
class Certification(models.Model):
    title           = models.CharField(blank=False, null=False, max_length=100)
    staff           = models.ForeignKey(Staff, on_delete=models.CASCADE)

# Mapping tables for language and schedule
class StaffLanguageMapping(models.Model):
    staff           = models.ForeignKey(Staff, on_delete=models.CASCADE)
    language        = models.ForeignKey(Language, on_delete=models.CASCADE)

class StaffScheduleMapping(models.Model):
    staff           = models.ForeignKey(Staff, on_delete=models.CASCADE)
    schedule        = models.ForeignKey(Schedule, on_delete=models.CASCADE)

# Pets with no customer would be displayed in adopt-a-pet
class Pet(models.Model):
    customer        = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True)
    animal          = models.CharField(blank=False, null=False, max_length=250)
    name            = models.CharField(blank=False, null=False, max_length=250)
    gender          = models.CharField(blank=False, null=False, max_length=50)
    species         = models.CharField(blank=False, null=False, max_length=250)
    colour          = models.CharField(blank=False, null=False, max_length=100)
    description     = models.TextField(blank=False, null=False)

# If appointment is booked but is not attended it should be cancelled
# If past the appointment date and time would be displayed as history
class Appointment(models.Model):
    customer        = models.ForeignKey(Customer, on_delete=models.CASCADE)
    staff           = models.ForeignKey(Staff, on_delete=models.CASCADE)
    slot            = models.ForeignKey(Slot, on_delete=models.CASCADE)
    description     = models.TextField(blank=True, null=True)