import hashlib
import json
from cryptography.fernet import Fernet
from datetime import datetime
from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext as _


# Create your models here.
class UserManager(BaseUserManager):
    def create_user(self, email, password, role, **extra_fields):
        if not email:
            raise ValueError(_('Users must have an email address'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.role = role
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
    class Meta:
        db_table = 'User'

    class Role(models.TextChoices):
        C = 'Customer'
        S = 'Staff'

    username = None
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        max_length=50, 
        blank=False, 
        null=False, 
        choices=Role.choices, default=Role.C
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['role']

    objects = UserManager()

    def __str__(self):
        return self.email
    
class Customer(models.Model):
    class Meta:
        db_table = 'Customer'

    user                = models.ForeignKey(User, on_delete=models.CASCADE)
    name                = models.CharField(blank=False, null=False, max_length=250)
    gender              = models.CharField(blank=False, null=False, max_length=50)
    dob                 = models.CharField(blank=False, null=False, max_length=100)
    phone               = models.CharField(blank=False, null=False, max_length=100, unique=True)
    address             = models.TextField(blank=False, null=False)
    is_approved         = models.BooleanField(blank=False, null=False, default=False)

# A schedule can be associated to many staff, and a staff can have many schedule
# A schedule has many slots
class Schedule(models.Model):
    class Meta:
        db_table = 'Schedule'

    date                = models.CharField(blank=False, null=False, max_length=50)

class Slot(models.Model):
    class Meta:
        db_table = 'Slot'

    start_time          = models.CharField(blank=False, null=False, max_length=50)
    end_time            = models.CharField(blank=False, null=False, max_length=50)
    is_available        = models.BooleanField(blank=False, null=False, default=True)
    booked_by           = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True)
    type                = models.CharField(blank=False, null=False, max_length=100) # value from AppointmentType

class Staff(models.Model):
    class Meta:
        db_table = 'Staff'

    class Role(models.TextChoices):
        D = 'Doctor'
        G = 'Groomer'
        A = 'Admin'

    user                = models.ForeignKey(User, on_delete=models.CASCADE)
    staff_no            = models.CharField(blank=False, null=False, max_length=30)
    name                = models.CharField(blank=False, null=False, max_length=250)
    gender              = models.CharField(blank=False, null=False, max_length=50)
    is_active           = models.BooleanField(blank=False, null=False, default=True)
    role                = models.CharField(
                            max_length=50, 
                            blank=False, 
                            null=False, 
                            choices=Role.choices, default=Role.D
                        )

class FirstPassword(models.Model):
    class Meta:
        db_table = 'FirstPassword'

    staff               = models.ForeignKey(Staff, on_delete=models.CASCADE)
    password            = models.CharField(blank=False, null=False, max_length=250)

# Mapping table for schedule to slot
class ScheduleSlotMapping(models.Model):
    class Meta:
        db_table = 'ScheduleSlotMapping'

    schedule            = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    slot                = models.ForeignKey(Slot, on_delete=models.CASCADE)

class StaffScheduleSlotMapping(models.Model):
    class Meta:
        db_table = 'StaffScheduleSlotMapping'

    staff               = models.ForeignKey(Staff, on_delete=models.CASCADE)
    ssm                 = models.ForeignKey(ScheduleSlotMapping, on_delete=models.CASCADE)

# Pets with no customer would be displayed in adopt-a-pet
class Pet(models.Model):
    class Meta:
        db_table = 'Pet'

    customer            = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True)
    animal              = models.CharField(blank=False, null=False, max_length=250)
    name                = models.CharField(blank=False, null=False, max_length=250)
    gender              = models.CharField(blank=False, null=False, max_length=50)
    species             = models.CharField(blank=False, null=False, max_length=250)
    description         = models.TextField(blank=False, null=False)

class PetImage(models.Model):
    class Meta:
        db_table = 'PetImage'

    pet                 = models.ForeignKey(Pet, on_delete=models.CASCADE)
    image               = models.ImageField(blank=True, null=True)

# If appointment is booked but is not attended it should be cancelled
# If past the appointment date and time would be displayed as history
class Appointment(models.Model):
    class Meta:
        db_table = 'Appointment'

    customer            = models.ForeignKey(Customer, on_delete=models.CASCADE)
    pet                 = models.ForeignKey(Pet, on_delete=models.CASCADE)
    sssm                = models.ForeignKey(StaffScheduleSlotMapping, on_delete=models.CASCADE)
    type                = models.CharField(blank=False, null=False, max_length=100)
    description         = models.TextField(blank=True, null=True)
    is_completed        = models.BooleanField(blank=False, null=False, default=False)

# Store appointment change requests
class AppointmentChangeRequest(models.Model):
    class Meta:
        db_table = 'AppointmentChangeRequest'

    by                  = models.ForeignKey(User, on_delete=models.CASCADE)
    appointment         = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    type                = models.CharField(blank=False, null=False, max_length=100)
    description         = models.TextField(blank=True, null=True)
    date                = models.CharField(blank=False, null=False, max_length=50)
    start_time          = models.CharField(blank=False, null=False, max_length=50)
    end_time            = models.CharField(blank=False, null=False, max_length=50)
    is_approved         = models.BooleanField(blank=False, null=False, default=False)
    is_rejected         = models.BooleanField(blank=False, null=False, default=False)
    cancellation        = models.BooleanField(blank=False, null=False, default=False)
    request_datetime    = models.DateTimeField(blank=False, null=False, auto_now_add=True)

# To store appointment types
class AppointmentType(models.Model):
    class Meta:
        db_table = 'AppointmentType'

    type                = models.CharField(blank=False, null=False, max_length=100)

# Email queue for scheduler
class EmailQueue(models.Model):
    class Meta:
        db_table = 'EmailQueue'

    to                  = models.CharField(blank=False, null=False, max_length=250)
    content             = models.TextField(blank=True, null=True)
    module              = models.CharField(blank=False, null=False, max_length=250)
    is_sent             = models.BooleanField(blank=False, null=False, default=False)
    sent_at             = models.DateTimeField(blank=True, null=True)
    request_datetime    = models.DateTimeField(blank=False, null=False, auto_now_add=True)
    send_datetime       = models.DateTimeField(blank=True, null=True)
    retry_count         = models.IntegerField(blank=False, null=False, default=0)
    void                = models.BooleanField(blank=False, null=False, default=False)

# Notifications
class Notification(models.Model):
    class Meta:
        db_table = 'Notification'

    user               = models.ForeignKey(User, on_delete=models.CASCADE)
    module             = models.CharField(blank=False, null=False, max_length=250)
    title              = models.CharField(blank=False, null=False, max_length=250)
    content            = models.TextField(blank=False, null=False)
    data               = models.JSONField(blank=True, null=True)
    is_read            = models.BooleanField(blank=False, null=False, default=False)
    created_datetime   = models.DateTimeField(blank=False, null=False, auto_now_add=True)

# Medical history block
class MedicalHistory(models.Model):
    class Meta:
        db_table = 'MedicalHistory'

    index              = models.IntegerField(blank=False, null=False)
    timestamp          = models.CharField(blank=False, null=False, max_length=250)
    previous_hash      = models.CharField(blank=False, null=False, max_length=250)
    data               = models.TextField(blank=False, null=False)
    hash               = models.CharField(blank=False, null=False, max_length=250)

    @staticmethod
    def encrypt(data):
        try:
            with open('vcms/encryption_key.txt', 'rb') as file:
                key = file.read()
        except FileNotFoundError:
            # If not, generate a new key and save it in the file
            key = Fernet.generate_key()
            with open('vcms/encryption_key.txt', 'wb') as file:
                file.write(key)

        cipher_suite = Fernet(key)

        if isinstance(data, str):
            data_str = data
        else:
            data_str = json.dumps(data)
        encrypted_data = cipher_suite.encrypt(data_str.encode())
        decrypted_data = encrypted_data.decode()
        return decrypted_data


    @classmethod
    def genesis(cls):
        index = 0
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        previous_hash = '0'
        data = MedicalHistory.encrypt(data={'gen': 'Genesis Block'})
        genesis_block = cls(
            index=0, 
            timestamp=timestamp, 
            previous_hash='0', 
            data=data,
            hash = hashlib.sha256(
                f'{index}{timestamp}{previous_hash}{data}'.encode()
            ).hexdigest()
        )
        super(MedicalHistory, genesis_block).save()

    def save(self, *args, **kwargs):
        if not MedicalHistory.objects.exists() and self.index != 0:
            self.genesis()

        if not self.pk and MedicalHistory.objects.exists():
            self.index = MedicalHistory.objects.latest('index').index + 1

        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.index == 0:
            self.previous_hash = '0'
        else:
            self.previous_hash = MedicalHistory.objects.get(index=self.index-1).hash

        self.data = MedicalHistory.encrypt(data=self.data)

        self.hash = hashlib.sha256(
            f'{self.index}{self.timestamp}{self.previous_hash}{self.data}'.encode()
        ).hexdigest()

        super().save(*args, **kwargs)