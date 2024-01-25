import re
from getpass import getpass
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from sequences import *
from vcmsapp.models import Staff, User, FirstPassword

class Command(BaseCommand):
    help = 'Create a new superuser and a corresponding staff object'

    def handle(self, *args, **options):
        email = input('Email: ')

        while not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            self.stdout.write(self.style.ERROR('Error: Invalid email'))
            email = input('Email: ')

        password = getpass('Password: ')
        password_confirm = getpass('Password (again): ')

        while password != password_confirm:
            self.stdout.write(self.style.ERROR('Error: Passwords do not match'))
            password = getpass('Password: ')
            password_confirm = getpass('Password (again): ')

        name = input('Name: ').strip()
        while (not re.match(r"^[a-zA-Z\s]*$", name)) or name == '':
            if not re.match(r"^[a-zA-Z\s]*$", name):
                self.stdout.write(self.style.ERROR('Error: Name can only contain alphabets and spaces'))
            elif name == '':
                self.stdout.write(self.style.ERROR('Error: Name cannot be empty'))
            name = input('Name: ').strip()

        gender = input('Gender [Male/Female]: ')
        while gender not in ['Male', 'Female']:
            self.stdout.write(self.style.ERROR('Error: Invalid gender'))
            gender = input('Gender [Male/Female]: ')

        staff_no = 'STF' + str(get_next_value('staff')).zfill(settings.ZFILL)
        role = Staff.Role.A

        user = User.objects.create_superuser(email=email, password=password, role=User.Role.S)
        user.set_password(password)

        staff = Staff(user=user, name=name, gender=gender, role=role, staff_no=staff_no)

        try:
            user.full_clean()
            staff.full_clean()
        except ValidationError as e:
            self.stdout.write(self.style.ERROR('Error: ' + str(e)))
            return

        user.save()
        staff.save()
        
        fp = FirstPassword(staff=staff, password=password)
        fp.save()

        self.stdout.write(self.style.SUCCESS('Successfully created superuser and staff object'))