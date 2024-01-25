from datetime import datetime
import json
import os
import random
import shutil
from urllib.parse import urlparse
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core import serializers
from django.db import transaction
from django.db.models import Q
from sequences import *

from .blockchain import Blockchain
from .models import *
from .utils import *

# Create your views here.
def Home(request):
    return render(request, "Home.html")

# Login and Register
def Login(request):
    if request.method == "POST":
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            if user.role == 'Customer' and not user.is_staff: # validate both role and is_staff fields
                customer = Customer.objects.get(user=user)
                if not customer.is_approved:
                    messages.error(request, "Your account has not been approved yet!")
                    return redirect('vcmsapp:login')
                return redirect('vcmsapp:customer', customer_id=customer.id)
            elif user.role == 'Staff' and user.is_staff:
                if user.is_superuser:
                    admin = Staff.objects.get(user=user)
                    return redirect('vcmsapp:admin', admin_id=admin.id)
                else:
                    staff = Staff.objects.get(user=user)
                    return redirect('vcmsapp:staff', staff_id=staff.id)
            else:
                messages.error(request, "User data error!")
                return redirect('vcmsapp:login')
        else:
            messages.error(request, "Invalid email or password!")
            return redirect('vcmsapp:login')
    return render(request, "Login.html")

def Register(request):
    if request.method == "POST":
        name        = request.POST['name']
        gender      = request.POST['gender']
        dob         = request.POST['dob'] # date type input default format = 'YYYY-MM-dd'
        phone       = request.POST['phone']
        address     = request.POST['address']
        email       = request.POST['email']
        password    = request.POST['password']

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists!")
            return redirect('vcmsapp:register')
        elif Customer.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number already exists!")
            return redirect('vcmsapp:register')

        new_user = AddEntity(
            request, User, None,
            email=email,
            password=password,
            role=User.Role.C
        )

        AddEntity(
            request, Customer, None,
            user=new_user,
            name=name,
            gender=gender,
            dob=dob,
            phone=phone,
            address=address,
            is_approved=False
        )

        messages.success(request, 'Registration successful! Please wait for email of approval which would be sent to ' + email + '.')
        return redirect('vcmsapp:login')
    return render(request, "Register.html")

def Logout(request):
    logout(request)
    return redirect('vcmsapp:login')

def previous_page(request):
    previous_page = request.session.get('previous_page', None)
    return redirect(previous_page) if previous_page else redirect('vcmsapp:logout')

@login_required
def Profile(request, staff_id=None, customer_id=None): # staff includes admin
    if not staff_id and not customer_id:
        raise ValueError("Either staff_id or customer_id must be provided!")
    if staff_id:
        staff = Staff.objects.get(id=staff_id)
    elif customer_id:
        customer = Customer.objects.get(id=customer_id)

    user = request.user

    disallowed_pages = [
        'change-password',
        'Adopt-a-Pet',
        'Profile',
    ]

    referrer = request.META.get('HTTP_REFERER', None)
    if referrer:
        parsed_url = urlparse(referrer)
        if parsed_url.path not in disallowed_pages and parsed_url.path != '/':
            request.session['previous_page'] = referrer

    context = {
        'onPage': 'Profile',
    }

    if staff_id:
        if request.method == "POST":
            newName = request.POST['name']
            newGender = request.POST['gender']
            newRole = request.POST['role']
                
            EditEntity(
                request, Staff, staff.id, None,
                name=newName,
                gender=newGender,
                role=newRole,
            )

            messages.success(request, 'Profile updated successfully!')
            return redirect('vcmsapp:profile-staff', staff_id=staff_id)
        context['staff'] = staff

    elif customer_id:
        if request.method == "POST":
            newName = request.POST['name']
            newGender = request.POST['gender']
            newDob = request.POST['dob']
            newPhone = request.POST['phone']
            newAddress = request.POST['address']

            if customer.phone != newPhone and Customer.objects.filter(phone=newPhone).exists():
                messages.error(request, "Phone number already exists!")
                return redirect('vcmsapp:profile-customer', customer_id=customer_id)

            EditEntity(
                request, Customer, customer.id, None,
                name=newName,
                gender=newGender,
                dob=newDob,
                phone=newPhone,
                address=newAddress,
            )

            messages.success(request, 'Profile updated successfully!')
            return redirect('vcmsapp:profile-customer', customer_id=customer_id)
        context['customer'] = customer
    return render(request, "Profile.html", context)

@login_required
def ChangePassword(request, staff_id=None, customer_id=None):
    if not staff_id and not customer_id:
        raise ValueError("Either staff_id or customer_id must be provided!")
    user = request.user

    if request.method == "POST":
        old_password = request.POST['password']
        new_password = request.POST['newPassword']

        if user.check_password(old_password):
            user.set_password(new_password)
            user.save()
            messages.success(request, "Password changed successfully!")
            return redirect('vcmsapp:login')
        else:
            messages.error(request, "Invalid current password!")
            return redirect('vcmsapp:change-password-staff', staff_id=staff_id) if staff_id else redirect('vcmsapp:change-password-customer', customer_id=customer_id)

    context = {
        'onPage': 'Profile',
    }

    if staff_id:
        staff = Staff.objects.get(id=staff_id)
        context['staff'] = staff
    elif customer_id:
        customer = Customer.objects.get(id=customer_id)
        context['customer'] = customer
    return render(request, "ChangePassword.html", context)

@login_required
def TerminateAccount(request, customer_id):
    to_terminate = Customer.objects.get(id=customer_id)
    if request.method == "POST":
        DeleteEntity(
            request, User, to_terminate.user.id, None
        )

        DeleteEntity(
            request, Customer, to_terminate.id, None
        )
        messages.success(request, "Account terminated successfully!")
        return redirect('vcmsapp:logout')

@login_required
def NotificationPage(request, staff_id=None, customer_id=None):
    if not staff_id and not customer_id:
        raise ValueError("Either staff_id or customer_id must be provided!")
    user = request.user

    notifications = Notification.objects.filter(user=user)
    if notifications:
        notifications = serialize_and_paginate(
            notifications, 9            
        )
    else:
        notifications = None

    context = {
        'onPage': 'Notifications',
        'pages': notifications
    }

    if staff_id:
        staff = Staff.objects.get(id=staff_id)
        context['staff'] = staff
    elif customer_id:
        customer = Customer.objects.get(id=customer_id)
        context['customer'] = customer
    return render(request, "Notification.html", context)

def NotificationRedirect(request, notification_id):
    notification = Notification.objects.get(id=notification_id)
    modules = {
        'AppointmentBooked': redirect_view_appointment_staff,
        'AppointmentMade': redirect_view_appointment_customer,
        'AppointmentEditedStaff': redirect_view_appointment_staff,
        'AppointmentEditedCustomer': redirect_view_appointment_customer,
        'AppointmentUpcoming': redirect_view_appointment_customer,
    }

    if notification:
        redirect_func = modules.get(notification.module, None)
        if redirect_func:
            return redirect_func(**notification.data)


def ClearNotification(request, staff_id=None, customer_id=None):
    if not staff_id and not customer_id:
        raise ValueError("Either staff_id or customer_id must be provided!")
    user = request.user

    if request.method == "POST":
        notifications = Notification.objects.filter(user=user)
        for notification in notifications:
            DeleteEntity(
                request, Notification, notification.id, None
            )

        if staff_id:
            staff = Staff.objects.get(id=staff_id)
            return redirect('vcmsapp:notification-staff', staff_id=staff.id)
        elif customer_id:
            customer = Customer.objects.get(id=customer_id)
            return redirect('vcmsapp:notification-customer', customer_id=customer.id)

# Staff
@login_required
def StaffPage(request, staff_id):
    user = request.user
    staff = Staff.objects.get(user=user)
    today = datetime.now().strftime("%Y-%m-%d") # change to string to use for comparison with schedule date
    appointments = Appointment.objects.filter(
        Q(
            Q(sssm__ssm__schedule__date__gt=today) | 
            Q(sssm__ssm__schedule__date=today, sssm__ssm__slot__end_time__gt=datetime.now().strftime("%H:%M"))
        ),
        sssm__staff=staff,
        is_completed=False,
    )

    paginator = None
    if appointments:
        paginator = serialize_and_paginate(
            appointments, 
            extra_fields=lambda apmt: {
                'pet': apmt.pet.name,
                'customer': apmt.customer.name,
                'date': apmt.sssm.ssm.schedule.date, 
                'start_time': apmt.sssm.ssm.slot.start_time, 
                'end_time': apmt.sssm.ssm.slot.end_time
            }
        )

    context = {
        'staff': staff,
        'onPage': 'Appointments',
        'pages': paginator
    }

    if request.method == "POST":
        search_query = request.POST['search']
        paginator = None

        # search bar would search for customer name
        if (search_query.replace(" ", "") != '') and (search_query != None):
            customers = Customer.objects.filter(name__icontains=search_query)
            matched_appointments = Appointment.objects.filter(
                customer__in=customers, 
                staff=staff, 
                is_completed=False, 
                sssm__ssm__schedule__date__gte=today
            )

            paginator = serialize_and_paginate(
                matched_appointments, 
                extra_fields=lambda ma: {
                    'pet': ma.pet.name,
                    'customer': ma.customer.name,
                    'date': ma.sssm.ssm.schedule.date, 
                    'start_time': ma.sssm.ssm.slot.start_time, 
                    'end_time': ma.sssm.ssm.slot.end_time
                }
            )

            context['query'] = search_query
            context['pages'] = paginator

        return render(request, "customer/Customer.html", context)
    
    return render(request, "staff/Staff.html", context)

@login_required
def MakeAppointmentStaff(request, staff_id):
    staff = Staff.objects.get(id=staff_id)
    types = AppointmentType.objects.all().values('type')
    customers = Customer.objects.filter(is_approved=True).values('name', 'user__email')

    types = [type['type'] for type in types]
    customers = ['{} ({})'.format(customer['user__email'], customer['name']) for customer in customers]

    if request.method == "POST":
        pet = request.POST['pet']
        type = request.POST['type']
        customer = request.POST['customer']
        date = request.POST['date']
        slot_id = request.POST['time']
        description = request.POST.get('description', None)
        is_completed = False

        slot = Slot.objects.get(id=slot_id)
        ssm = ScheduleSlotMapping.objects.get(schedule__date=date, slot__start_time=slot.start_time, slot__end_time=slot.end_time)
        sssm = StaffScheduleSlotMapping.objects.get(staff=staff, ssm=ssm)
        customer = Customer.objects.get(user__email=customer[:customer.find('(')-1])
        pet = Pet.objects.get(id=pet)

        new_appointment = AddEntity(
            request, Appointment, None,
            customer=customer,
            pet=pet,
            sssm=sssm,
            type=type,
            description=description,
            is_completed=is_completed
        )

        EditEntity(
            request, Slot, slot.id, None,
            is_available=False,
            booked_by=customer
        )

        AddEntity(
            request, Notification, None,
            user=customer.user,
            module='AppointmentMade',
            title='Appointment on ' + date + ' at ' + slot.start_time + ' for ' + pet.name,
            content='Dr. ' + staff.name + ' has made an appointment for ' + pet.name + ' on ' + date + ' at ' + slot.start_time + '. Please check your appointment page for more details.',
            data={
                'appointment_id': new_appointment.id,
                'customer_id': customer.id
            }
        )

        messages.success(request, "Appointment made successfully!")
        return redirect('vcmsapp:staff', staff_id=staff_id)

    context = {
        'staff': staff,
        'onPage': 'Appointments',
        'types': types,
        'customers': customers
    }

    # use id for value of customer select field
    return render(request, 'staff/MakeAppointment.html', context)

@login_required
def MedicalNotes(request, appointment_id):
    user = request.user
    staff = Staff.objects.get(user=user)
    appointment = Appointment.objects.get(id=appointment_id)

    if request.method == "POST":
        notes = request.POST['notes']
        prescription = request.POST['prescription']

        data = {
            'notes': notes,
            'prescription': prescription,
            'appointment_id': appointment.id
        }

        AddEntity(
            request, MedicalHistory, None,
            data=data
        )
        Blockchain.load()

        EditEntity(
            request, Appointment, appointment.id, None,
            is_completed=True
        )

        messages.success(request, "Medical notes added successfully!")
        return redirect('vcmsapp:view-appointment-staff', appointment_id=appointment_id, staff_id=staff.id)

    context = {
        'staff': staff,
        'onPage': 'Appointments',
        'appointment': appointment
    }
    return render(request, 'staff/MedicalNotes.html', context)

@login_required
def SlotPage(request, staff_id):
    staff = Staff.objects.get(id=staff_id)
    today = datetime.now().strftime("%Y-%m-%d")
    ssms = ScheduleSlotMapping.objects.filter(
        id__in=StaffScheduleSlotMapping.objects.filter(staff=staff).values('ssm')
    )
    ssms = serialize_and_paginate(
        ssms, 
        paginate=False, 
        extra_fields=lambda ssm: {
            'start': datetime.strptime(f"{ssm.schedule.date} {ssm.slot.start_time}", "%Y-%m-%d %H:%M").isoformat(),
            'end': datetime.strptime(f"{ssm.schedule.date} {ssm.slot.end_time}", "%Y-%m-%d %H:%M").isoformat(),
            'title': ssm.slot.type,
            'available': ssm.slot.is_available
        }
    )

    context = {
        'staff': staff,
        'onPage': 'Slots',
        'events': ssms
    }
    return render(request, 'staff/Slot.html', context)

@login_required
def ViewSlot(request, staff_id):
    date = request.GET.get('date', None)
    staff = Staff.objects.get(id=staff_id)
    types = AppointmentType.objects.all().values('type')
    types = [type['type'] for type in types]

    schedule = Schedule.objects.get(date=date) if Schedule.objects.filter(date=date) else AddEntity( # create schedule if not created by scheduler yet
        request, Schedule, None,
        date=date
    )

    if request.method == "POST":
        type = request.POST['type']
        start_time = request.POST['start_time']
        end_time = request.POST['end_time']

        if ScheduleSlotMapping.objects.filter(
            id__in=StaffScheduleSlotMapping.objects.filter(staff=staff).values('ssm'),
            schedule=schedule, 
            slot__start_time=start_time, 
        ).exists():
            messages.error(request, "Slot already exists!")
            return redirect('vcmsapp:slot', staff_id=staff.id)
        
        if ScheduleSlotMapping.objects.filter(
            id__in=StaffScheduleSlotMapping.objects.filter(staff=staff).values('ssm'),
            schedule=schedule, 
            slot__start_time__lte=start_time,
            slot__end_time__gte=start_time 
        ).exists():
            messages.error(request, "Slot time coincides with existing slots!")
            return redirect('vcmsapp:slot', staff_id=staff.id)
        
        new_slot = AddEntity(
            request, Slot, None,
            start_time=start_time,
            end_time=end_time,
            type=type
        )

        new_ssm = AddEntity(
            request, ScheduleSlotMapping, None,
            schedule=schedule,
            slot=new_slot,
        )

        AddEntity(
            request, StaffScheduleSlotMapping, None,
            staff=staff,
            ssm=new_ssm
        )

        messages.success(request, "Slot added successfully!")
        return redirect('vcmsapp:slot', staff_id=staff.id)

    context = {
        'staff': staff,
        'date': datetime.strptime(date, "%Y-%m-%d").strftime("%-d %b %Y"),
        'onPage': 'Slots',
        'types': types
    }
    return render(request, 'staff/AddSlot.html', context)

@login_required
def ViewEvent(request, staff_id):
    staff = Staff.objects.get(id=staff_id)
    type = request.GET.get('type', None)
    start = request.GET.get('start', None)
    end = request.GET.get('end', None)

    date = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S").strftime("%-d %b %Y")
    start_time = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S").strftime("%H:%M")
    end_time = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S").strftime("%H:%M")
    
    slot = StaffScheduleSlotMapping.objects.get(
        staff=staff, 
        ssm__schedule__date=datetime.strptime(start, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d"),
        ssm__slot__type=type,
        ssm__slot__start_time=start_time,
        ssm__slot__end_time=end_time
    ).ssm.slot if StaffScheduleSlotMapping.objects.filter(
        staff=staff, 
        ssm__schedule__date=datetime.strptime(start, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d"),
        ssm__slot__type=type,
        ssm__slot__start_time=start_time,
        ssm__slot__end_time=end_time
    ) else None

    schedule = Schedule.objects.get(date=date) if Schedule.objects.filter(date=date) else None

    types = [type['type'] for type in AppointmentType.objects.all().values('type')]

    if request.method == "POST":
        newType = request.POST['type']
        newStartTime = request.POST['start_time']
        newEndTime = request.POST['end_time']

        if ScheduleSlotMapping.objects.filter(
            id__in=StaffScheduleSlotMapping.objects.filter(staff=staff).values('ssm'),
            schedule=schedule, 
            slot__start_time=newStartTime, 
        ).exists():
            messages.error(request, "Slot already exists!")
            return redirect('vcmsapp:slot', staff_id=staff.id)
        
        if ScheduleSlotMapping.objects.filter(
            id__in=StaffScheduleSlotMapping.objects.filter(staff=staff).values('ssm'),
            schedule=schedule, 
            slot__start_time__lte=newStartTime,
            slot__end_time__gte=newStartTime 
        ).exists():
            messages.error(request, "Slot time coincides with existing slots!")
            return redirect('vcmsapp:slot', staff_id=staff.id)

        EditEntity(
            request, Slot, slot.id, " for " + newStartTime + " to " + newEndTime + " on " + date,
            start_time=newStartTime,
            end_time=newEndTime,
            type=newType
        )

        return redirect('vcmsapp:slot', staff_id=staff.id)

    context = {
        'staff': staff,
        'onPage': 'Slots',
        'date': date,
        'slot': slot,
        'types': types
    }

    return render(request, 'staff/ViewEvent.html', context)

@login_required
def RemoveSlot(request, staff_id, slot_id):
    staff = Staff.objects.get(id=staff_id)
    slot = Slot.objects.get(id=slot_id)
    if request.method == "POST":
        ssm = ScheduleSlotMapping.objects.get(slot=slot)
        sssm = StaffScheduleSlotMapping.objects.get(ssm=ssm)
        
        DeleteEntity(
            request, StaffScheduleSlotMapping, sssm.id, None
        )

        DeleteEntity(
            request, ScheduleSlotMapping, ssm.id, None
        )

        DeleteEntity(
            request, Slot, slot.id, None
        )



    messages.success(request, "Slot removed successfully!")
    return redirect('vcmsapp:slot', staff_id=staff.id)

@login_required
def ViewAppointment(request, appointment_id, staff_id=None, customer_id=None):
    if not staff_id and not customer_id:
        raise ValueError("Either staff_id or customer_id must be provided!")
    user = request.user
    appointment = Appointment.objects.get(id=appointment_id)
    context = {
        'onPage': 'Appointments',
    }

    if staff_id:
        staff = Staff.objects.get(id=staff_id)

        Blockchain.load()
        blockchain = Blockchain._instance.chain
        has_medical_notes = False
        for block in blockchain:
            if ('appointment_id' in block.data) and (block.data['appointment_id'] == appointment.id):
                has_medical_notes = True
                break
        context['has_medical_notes'] = has_medical_notes

        if request.method == "POST":
            date = request.POST['date']
            time = request.POST['time']
            description = request.POST.get('description', None)

            AddEntity(
                request, AppointmentChangeRequest, 'for ' + appointment.pet.name + '(owner: ' + appointment.customer.name + ')',
                by=user,
                appointment=appointment,
                type=appointment.type,
                description=description,
                date=date,
                start_time=StaffScheduleSlotMapping.objects.get(
                    staff=staff,
                    ssm__schedule__date=date,
                    ssm__slot__start_time=time
                ).ssm.slot.start_time,
                end_time=StaffScheduleSlotMapping.objects.get(
                    staff=staff,
                    ssm__schedule__date=date,
                    ssm__slot__start_time=time
                ).ssm.slot.end_time
            )

            AddEntity(
                request, Notification, None,
                user=appointment.customer.user,
                module='AppointmentEditedCustomer',
                title='Edit for appointment on ' + date + ' at ' + time + ' for ' + appointment.customer.name,
                content='Dr. ' + staff.name + ' has edited your appointment for ' + appointment.pet.name + ' on ' + date + ' at ' + time + '. Please check your appointment page for more details.',
                data={
                    'appointment_id': appointment.id,
                    'customer_id': appointment.customer.id
                }
            )
            return redirect('vcmsapp:view-appointment-staff', appointment_id=appointment_id, staff_id=staff_id)

        change_request = AppointmentChangeRequest.objects.filter(
            appointment=appointment,
            is_approved=False,
            is_rejected=False,
            by__role='Customer' 
        ).latest('request_datetime') if AppointmentChangeRequest.objects.filter(
            appointment=appointment,
            is_approved=False,
            is_rejected=False,
            by__role='Customer'
        ) else None
        context['staff'] = staff
        if change_request:
            context['change_request'] = change_request
            context['attributes'] = {
                'type': [appointment.type, change_request.type] if change_request else [appointment.type, None],
                'date': [appointment.sssm.ssm.schedule.date, change_request.date] if change_request else [appointment.sssm.ssm.schedule.date, None],
                'time': [appointment.sssm.ssm.slot.start_time, change_request.start_time] if change_request else [appointment.sssm.ssm.slot.start_time, None],
                'description': [appointment.description, change_request.description] if change_request else [appointment.description, None],

            }
        context['types'] = [t.type for t in AppointmentType.objects.all()]
        context['slots'] = [sssm.ssm.slot.start_time for sssm in StaffScheduleSlotMapping.objects.filter(
            staff=appointment.sssm.staff,
            ssm__schedule__date=appointment.sssm.ssm.schedule.date,
            ssm__slot__type=appointment.type,
            ssm__slot__is_available=True
        )]
        context['pets'] = [pet.name for pet in Pet.objects.filter(customer=appointment.customer)]
        context['appointment'] = serialize_and_paginate(
            appointment,
            paginate=False,
            one=True,
            extra_fields=lambda apmt: {
                'pet': apmt.pet.name,
                'customer': apmt.customer.name,
                'date': apmt.sssm.ssm.schedule.date, 
                'start_time': apmt.sssm.ssm.slot.start_time, 
                'description': apmt.description,
                'type': apmt.type,
                'is_today': apmt.sssm.ssm.schedule.date == datetime.now().strftime("%Y-%m-%d")
            }
        )
        return render(request, 'ViewAppointment.html', context)
    elif customer_id:
        customer = Customer.objects.get(id=customer_id)

        if request.method == "POST":
            date = request.POST['date']
            time = request.POST['time']
            description = request.POST.get('description', None)

            staff = StaffScheduleSlotMapping.objects.get(
                ssm__schedule__date=date,
                ssm__slot__start_time=time,
            ).staff

            AddEntity(
                request, AppointmentChangeRequest, 'for ' + appointment.pet.name,
                by=user,
                appointment=appointment,
                type=appointment.type,
                description=description,
                date=date,
                start_time=StaffScheduleSlotMapping.objects.get(
                    staff=staff,
                    ssm__schedule__date=date,
                    ssm__slot__start_time=time
                ).ssm.slot.start_time,
                end_time=StaffScheduleSlotMapping.objects.get(
                    staff=staff,
                    ssm__schedule__date=date,
                    ssm__slot__start_time=time
                ).ssm.slot.end_time            
            )

            AddEntity(
                request, Notification, None,
                user=appointment.sssm.staff.user,
                module='AppointmentEditedStaff',
                title='Edit for appointment on ' + date + ' at ' + time + ' for ' + appointment.customer.name,
                content=appointment.customer.name + ' has edited their appointment for ' + appointment.pet.name + ' on ' + date + ' at ' + time + '. Please check your appointment page for more details.',
                data={
                    'appointment_id': appointment.id,
                    'staff_id': staff.id
                }
            )
            return redirect('vcmsapp:view-appointment-customer', appointment_id=appointment_id, customer_id=customer_id)

        change_request = AppointmentChangeRequest.objects.filter(
            appointment=appointment,
            is_approved=False,
            is_rejected=False,
            by__role='Staff' 
        ).latest('request_datetime') if AppointmentChangeRequest.objects.filter(
            appointment=appointment,
            is_approved=False,
            is_rejected=False,
            by__role='Staff'
        ) else None
        context['customer'] = customer
        if change_request:
            context['change_request'] = change_request
            context['attributes'] = {
                'type': [appointment.type, change_request.type] if change_request else [appointment.type, None],
                'date': [appointment.sssm.ssm.schedule.date, change_request.date] if change_request else [appointment.sssm.ssm.schedule.date, None],
                'time': [appointment.sssm.ssm.slot.start_time, change_request.start_time] if change_request else [appointment.sssm.ssm.slot.start_time, None],
                'description': [appointment.description, change_request.description] if change_request else [appointment.description, None],
            }
        context['slots'] = [sssm.ssm.slot.start_time for sssm in StaffScheduleSlotMapping.objects.filter(
            staff=appointment.sssm.staff,
            ssm__schedule__date=appointment.sssm.ssm.schedule.date,
            ssm__slot__type=appointment.type,
            ssm__slot__is_available=True
        )]
        context['pets'] = [pet.name for pet in Pet.objects.filter(customer=customer)]
        context['types'] = [t.type for t in AppointmentType.objects.all()]
        context['appointment'] = serialize_and_paginate(
            appointment,
            paginate=False,
            one=True,
            extra_fields=lambda apmt: {
                'pet': apmt.pet.name,
                'staff': apmt.sssm.staff.name,
                'date': apmt.sssm.ssm.schedule.date, 
                'start_time': apmt.sssm.ssm.slot.start_time, 
                'description': apmt.description,
                'type': apmt.type,
            }
        )
        return render(request, 'ViewAppointment.html', context)

@login_required
def CancelAppointment(request, staff_id=None, customer_id=None):
    if not staff_id and not customer_id:
        raise ValueError("Either staff_id or customer_id must be provided!")
    
    if request.method == "POST":
        appointment_id = request.POST['appointment_id']
        appointment = Appointment.objects.get(id=appointment_id)
        today = datetime.now()
        appointment_date = datetime.strptime(appointment.sssm.ssm.schedule.date, "%Y-%m-%d")

        if (appointment_date - today).days <= 1:
            messages.error(request, "Appointment cannot be cancelled the day before appointment time!")
            return redirect('vcmsapp:view-appointment-staff', appointment_id=appointment_id, staff_id=staff_id) if staff_id else redirect('vcmsapp:view-appointment-customer', appointment_id=appointment_id, customer_id=customer_id)
        
        AddEntity(
            request, AppointmentChangeRequest, 'for ' + appointment.pet.name + '(owner: ' + appointment.customer.name + ')',
            by=request.user,
            appointment=appointment,
            type=appointment.type,
            description=appointment.description,
            date=appointment.sssm.ssm.schedule.date,
            start_time=appointment.sssm.ssm.slot.start_time,
            end_time=appointment.sssm.ssm.slot.end_time,
            cancellation=True
        )
        return redirect('vcmsapp:staff', staff_id=staff_id) if staff_id else redirect('vcmsapp:customer', customer_id=customer_id)

@login_required    
def AcceptRejectChanges(request):
    user = request.user
    customer, staff = None, None
    
    if user.is_staff:
        staff = Staff.objects.get(user=user)
    else:
        customer = Customer.objects.get(user=user)
    
    if staff:        
        if request.method == "POST":
            appointment_id = request.POST['appointment_id']
            decision = request.POST['decision']
            appointment = Appointment.objects.get(id=appointment_id)
            change_request = AppointmentChangeRequest.objects.filter(appointment=appointment, is_approved=False, is_rejected=False).latest('request_datetime')

            if change_request:
                if decision == 'accept':
                    EditEntity(
                        request, Appointment, appointment_id, None,
                        type=change_request.type,
                        description=change_request.description,
                        sssm=StaffScheduleSlotMapping.objects.get(
                            staff=staff,
                            ssm__schedule__date=change_request.date,
                            ssm__slot__start_time=change_request.start_time,
                            ssm__slot__end_time=change_request.end_time
                        )
                    )

                    EditEntity(
                        request, AppointmentChangeRequest, change_request.id, None,
                        is_approved=True
                    )

                    messages.success(request, "Appointment updated successfully!")
                    return redirect('vcmsapp:view-appointment-staff', appointment_id=appointment_id, staff_id=staff.id)
                
                elif decision == 'reject':
                    EditEntity(
                        request, AppointmentChangeRequest, change_request.id, None,
                        is_rejected=True
                    )

                    messages.success(request, "Appointment change request rejected successfully!")
                    return redirect('vcmsapp:view-appointment-staff', appointment_id=appointment_id, staff_id=staff.id)
    
    elif customer:
        if request.method == "POST":
            appointment_id = request.POST['appointment_id']
            decision = request.POST['decision']
            appointment = Appointment.objects.get(id=appointment_id)
            change_request = AppointmentChangeRequest.objects.filter(appointment=appointment, is_approved=False, is_rejected=False).latest('request_datetime')

            if change_request:
                if decision == 'accept':
                    EditEntity(
                        request, Appointment, appointment_id, None,
                        type=change_request.type,
                        description=change_request.description,
                        sssm=StaffScheduleSlotMapping.objects.get(
                            staff=appointment.sssm.staff,
                            ssm__schedule__date=change_request.date,
                            ssm__slot__start_time=change_request.start_time,
                            ssm__slot__end_time=change_request.end_time
                        )
                    )

                    EditEntity(
                        request, AppointmentChangeRequest, change_request.id, None,
                        is_approved=True
                    )

                    messages.success(request, "Appointment updated successfully!")
                    return redirect('vcmsapp:view-appointment-customer', appointment_id=appointment_id, customer_id=customer.id)
                
                elif decision == 'reject':
                    EditEntity(
                        request, AppointmentChangeRequest, change_request.id, None,
                        is_rejected=True
                    )

                    messages.success(request, "Appointment change request rejected successfully!")
                    return redirect('vcmsapp:view-appointment-customer', appointment_id=appointment_id, customer_id=customer.id)

# Customer
@login_required
def CustomerPage(request, customer_id): # Appointments page
    user = request.user
    customer = Customer.objects.get(user=user)
    today = datetime.now().strftime("%Y-%m-%d")
    appointments = Appointment.objects.filter(
        Q(
            Q(sssm__ssm__schedule__date__gt=today) | 
            Q(sssm__ssm__schedule__date=today, sssm__ssm__slot__end_time__gt=datetime.now().strftime("%H:%M"))
        ),
        customer=customer,
        is_completed=False,
    )

    paginator = None
    if appointments:
        paginator = serialize_and_paginate(
            appointments, 
            extra_fields=lambda apmt: {
                'date': apmt.sssm.ssm.schedule.date, 
                'time': apmt.sssm.ssm.slot.start_time,
                'pet': apmt.pet.name,
                'staff': apmt.sssm.staff.name,
            }
        )

    context = {
        'customer': customer,
        'onPage': 'Appointments',
        'pages': paginator
    }

    if request.method == "POST":
        search_query = request.POST['search']
        paginator = None
        if (search_query.replace(" ", "") != '') and (search_query != None):
            pets = Pet.objects.filter(customer=customer, name__icontains=search_query)
            matched_appointments = Appointment.objects.filter(
                customer=customer, 
                pet__in=pets,
                is_completed=False,
                sssm__ssm__schedule__date__gte=today
            )

            paginator = serialize_and_paginate(
                matched_appointments, 
                extra_fields=lambda ma: {
                    'date': ma.sssm.ssm.schedule.date, 
                    'time': ma.sssm.ssm.slot.start_time
                }
            )

            context['query'] = search_query
            context['pages'] = paginator

        return render(request, "customer/Customer.html", context)
    return render(request, 'customer/Customer.html', context)

@login_required
def MakeAppointmentCustomer(request, customer_id):
    customer = Customer.objects.get(id=customer_id)
    types = AppointmentType.objects.all().values('type')
    pets = Pet.objects.filter(customer=customer).values('name')
    staff = Staff.objects.filter(is_active=True).values('name', 'staff_no')

    types = [type['type'] for type in types]
    pets = [pet['name'] for pet in pets]
    staff = [f"({stf['staff_no']}) {stf['name']}" for stf in staff]

    if request.method == "POST":
        pet = request.POST['pet']
        type = request.POST['type']
        staff = request.POST['staff'].split(" ")[0][1:-1]
        date = request.POST['date']
        time = request.POST['time']
        description = request.POST.get('description', None)
        is_completed = False

        staff = Staff.objects.get(staff_no=staff)
        slot = Slot.objects.get(id=time)
        ssm = ScheduleSlotMapping.objects.get(schedule__date=date, slot=slot)
        sssm = StaffScheduleSlotMapping.objects.get(staff=staff, ssm=ssm)
        pet = Pet.objects.get(name=pet, customer=customer)

        new_appointment = AddEntity(
            request, Appointment, None,
            customer=customer,
            pet=pet,
            sssm=sssm,
            type=type,
            description=description,
            is_completed=is_completed
        )

        EditEntity(
            request, Slot, slot.id, None,
            is_available=False,
            booked_by=customer
        )

        AddEntity(
            request, Notification, None,
            user=staff.user,
            module='AppointmentMade',
            title='Appointment on ' + date + ' at ' + slot.start_time + ' for ' + customer.name,
            content=customer.name + ' has made an appointment for ' + pet.name + ' on ' + date + ' at ' + slot.start_time + '. Please check your appointment page for more details.',
            data={
                'appointment_id': new_appointment.id,
                'staff_id': staff.id
            }
        )

        messages.success(request, "Appointment made successfully!")
        return redirect('vcmsapp:customer', customer_id=customer_id)

    context = {
        'customer': customer,
        'onPage': 'Appointments',
        'types': types,
        'pets': pets,
        'staff': staff
    }

    # use id for value of staff select field
    return render(request, 'customer/MakeAppointment.html', context)

@login_required
def HistoryPage(request, customer_id):
    user = request.user
    customer = Customer.objects.get(id=customer_id)

    today = datetime.now().strftime("%Y-%m-%d")
    history = Appointment.objects.filter(
        Q(customer=customer) & 
        Q(sssm__ssm__schedule__date__lt=today) | Q(is_completed=True)
    )

    paginator = None
    if history:
        paginator = serialize_and_paginate(
            history, 
            extra_fields=lambda apmt: {
                'pet': apmt.pet.name,
                'date': apmt.sssm.ssm.schedule.date, 
                'time': apmt.sssm.ssm.slot.start_time,
                'staff': apmt.sssm.staff.name,
            }
        )
    
    context = {
        'customer': customer,
        'onPage': 'History',
        'pages': paginator
    }

    # search bar would search for date
    return render(request, 'customer/History.html', context)

@login_required
def ViewHistory(request, customer_id, appointment_id):
    customer = Customer.objects.get(id=customer_id)
    appointment = Appointment.objects.get(id=appointment_id)
    blockchain = Blockchain.get_instance().chain
    medical_history = {
        'notes': None,
        'prescription': None
    }

    for block in blockchain:
        if 'appointment_id' in block.data and block.data['appointment_id'] == appointment_id:
            medical_history = block.data
            break

    context = {
        'customer': customer,
        'onPage': 'History',
        'appointment': appointment,
        'notes': medical_history['notes'],
        'prescription': medical_history['prescription']
    }
    return render(request, 'customer/ViewHistory.html', context)

@login_required
def PetPage(request, customer_id):
    customer = Customer.objects.get(id=customer_id)
    pets = Pet.objects.filter(customer=customer)

    paginator = None
    if pets:
        paginator = serialize_and_paginate(pets)

    context = {
        'customer': customer,
        'onPage': 'Pets',
        'pages': paginator
    }

    if request.method == "POST":
        search_query = request.POST['search']
        if (search_query.replace(" ", "") != '') and (search_query != None):
            matched_pets = Pet.objects.filter(customer=customer, name__icontains=search_query)
            paginator = serialize_and_paginate(matched_pets)

            context['query'] = search_query
            context['pages'] = paginator

        return render(request, "customer/Pet.html", context)
    return render(request, 'customer/Pet.html', context)

@login_required
def AddPet(request, customer_id):
    customer = Customer.objects.get(id=customer_id)

    if request.method == "POST":
        name = request.POST['name']
        animal = request.POST['animal']
        species = request.POST['species']
        gender = request.POST['gender']
        description = request.POST.get('description', None) # see if description is entered else set to None

        new_pet = AddEntity(
            request, Pet, name,
            customer=customer,
            animal=animal,
            name=name,
            species=species,
            gender=gender,
            description=description
        )

        image = request.POST.get('filename', None)
        
        if image:
            initial_path = os.path.join(settings.MEDIA_ROOT, customer.user.email.split('@')[0], image)
            final_dir = os.path.join(settings.MEDIA_ROOT, customer.user.email.split('@')[0], new_pet.name)
            
            os.makedirs(final_dir, exist_ok=True)
            
            final_path = os.path.join(final_dir, image)

            if not os.path.exists(final_path):
                shutil.move(initial_path, final_path)
            else:
                messages.error(request, "File already exists. Please change your file name or upload a different file.")
                return redirect('vcmsapp:add-pet', customer_id=customer_id)

            AddEntity(
                request, PetImage, None,
                pet=new_pet,
                image=os.path.join(customer.user.email.split('@')[0], new_pet.name, image)
            )            

        return redirect('vcmsapp:pet', customer_id=customer.id)
    
    context = {
        'customer': customer,
        'onPage': 'Pets'
    }

    return render(request, 'customer/AddPet.html', context)

@login_required
def UploadPetImage(request, customer_id):
    if request.method == 'POST':
        customer = Customer.objects.get(id=customer_id)
        filename = upload(request, customer.user.email.split('@')[0])
        return JsonResponse({'filename': filename})

@login_required
def RemovePetImage(request, customer_id):
    if request.method == 'POST':
        customer = Customer.objects.get(id=customer_id)
        filename = request.POST.get('filename', None)
        filename = remove(customer.user.email.split('@')[0], filename)
        
        if filename:
            return JsonResponse({'filename': filename})
        else:
            return JsonResponse({'filename': None})

@login_required
def ViewPet(request, customer_id, pet_id):
    customer = Customer.objects.get(id=customer_id)
    pet = Pet.objects.get(id=pet_id)
    image = PetImage.objects.get(pet=pet).image.url if PetImage.objects.filter(pet=pet) else None

    if request.method == "POST":
        newName = request.POST['name']
        newSpecies = request.POST['species']
        newGender = request.POST['gender']
        newDescription = request.POST.get('description', None)

        EditEntity(
            request, Pet, pet_id, newName,
            name=newName,
            species=newSpecies,
            gender=newGender,
            description=newDescription if newDescription else pet.description
        )

        newImage = request.POST.get('filename', None)

        if newImage:
            initial_path = os.path.join(settings.MEDIA_ROOT, customer.user.email.split('@')[0], newImage)
            final_dir = os.path.join(settings.MEDIA_ROOT, customer.user.email.split('@')[0], pet.name)
            
            os.makedirs(final_dir, exist_ok=True)
            
            final_path = os.path.join(final_dir, newImage)

            if not os.path.exists(final_path):
                shutil.move(initial_path, final_path)
            else:
                messages.error(request, "File already exists. Please change your file name or upload a different file.")
                return redirect('vcmsapp:view-pet', customer_id=customer.id, pet_id=pet.id)

            AddEntity(
                request, PetImage, None,
                pet=pet,
                image=os.path.join(customer.user.email.split('@')[0], pet.name, newImage)
            )

        return redirect('vcmsapp:view-pet', customer_id=customer.id, pet_id=pet.id)

    context = {
        'customer': customer,
        'pet': pet,
        'image': image,
        'onPage': 'Pets'
    }

    return render(request, 'customer/ViewPet.html', context)

@login_required
def DeletePetImage(request, customer_id, pet_id):
    if request.method == 'POST':
        customer = Customer.objects.get(id=customer_id)
        pet = Pet.objects.get(id=pet_id)
        image = PetImage.objects.get(pet=pet)

        filename = image.image.name
        filename = remove(filename, None)
        
        DeleteEntity(request, PetImage, image.id, None)
        
        if filename:
            messages.success(request, pet.name + " image removed successfully!")
        else:
            messages.error(request, "Error occurred while removing image!")
        return redirect('vcmsapp:view-pet', customer_id=customer.id, pet_id=pet.id)

@login_required
def AdoptPage(request):
    user = request.user
    staff, customer = None, None
    if user.is_authenticated:
        if user.is_staff:
            staff = Staff.objects.get(user=user)
        else:
            customer = Customer.objects.get(user=user)

    adopt = Pet.objects.filter(customer__isnull=True)
    adopt = serialize_and_paginate(adopt)

    context = {
        'onPage': 'Adopt',
        'pages': adopt,
        'staff': staff,
        'customer': customer
    }

    if request.method == "POST":
        search_query = request.POST['search']
        if (search_query.replace(" ", "") != '') and (search_query != None):
            matched_pets = Pet.objects.filter(customer__isnull=True, animal__icontains=search_query)
            paginator = serialize_and_paginate(matched_pets)

            context['query'] = search_query
            context['pages'] = paginator

        return render(request, "customer/Pet.html", context)
    return render(request, 'Adopt.html', context)

@login_required
def ViewAdopt(request, pet_id):
    user = request.user
    pet = Pet.objects.get(id=pet_id)
    image = PetImage.objects.get(pet=pet).image.url if PetImage.objects.filter(pet=pet) else None
    staff, customer = None, None
    if user.is_authenticated:
        if user.is_staff:
            staff = Staff.objects.get(user=user)
        else:
            customer = Customer.objects.get(user=user)

    if request.method == "POST":
        newName = request.POST['name']
        newSpecies = request.POST['species']
        newGender = request.POST['gender']
        newDescription = request.POST.get('description', None)

        EditEntity(
            request, Pet, pet_id, newName,
            name=newName,
            species=newSpecies,
            gender=newGender,
            description=newDescription if newDescription else pet.description
        )

        newImage = request.POST.get('filename', None)

        if newImage:
            initial_path = os.path.join(settings.MEDIA_ROOT, 'Adopt', newImage)
            final_dir = os.path.join(settings.MEDIA_ROOT, 'Adopt', str(pet.id))
            
            os.makedirs(final_dir, exist_ok=True)
            
            final_path = os.path.join(final_dir, newImage)

            if not os.path.exists(final_path):
                shutil.move(initial_path, final_path)
            else:
                messages.error(request, "File already exists. Please change your file name or upload a different file.")
                return redirect('vcmsapp:view-adopt', pet_id=pet.id)

            AddEntity(
                request, PetImage, None,
                pet=pet,
                image=os.path.join('Adopt', str(pet.id), newImage)
            )

        return redirect('vcmsapp:view-adopt', pet_id=pet.id)

    context = {
        'onPage': 'Adopt',
        'staff': staff,
        'customer': customer,
        'pet': pet,
        'image': image
    }
    return render(request, 'ViewAdopt.html', context)

@login_required
def RegisterAdopt(request):
    staff = Staff.objects.get(user=request.user) if request.user.is_staff else None

    if request.method == "POST":
        name = request.POST['name']
        animal = request.POST['animal']
        species = request.POST['species']
        gender = request.POST['gender']
        description = request.POST.get('description', None) # see if description is entered else set to None

        new_pet = AddEntity(
            request, Pet, name,
            animal=animal,
            name=name,
            species=species,
            gender=gender,
            description=description
        )

        image = request.POST.get('filename', None)
        
        if image:
            initial_path = os.path.join(settings.MEDIA_ROOT, 'Adopt', image)
            final_dir = os.path.join(settings.MEDIA_ROOT, 'Adopt', str(new_pet.id))
            
            os.makedirs(final_dir, exist_ok=True)
            
            final_path = os.path.join(final_dir, image)

            if not os.path.exists(final_path):
                shutil.move(initial_path, final_path)
            else:
                messages.error(request, "File already exists. Please change your file name or upload a different file.")
                return redirect('vcmsapp:register-adopt')

            AddEntity(
                request, PetImage, None,
                pet=new_pet,
                image=os.path.join('Adopt', str(new_pet.id), image)
            )            

        return redirect('vcmsapp:adopt')

    context = {
        'onPage': 'Adopt',
        'staff': staff,
    }
    return render(request, 'staff/RegisterAdopt.html', context)

@login_required
def UploadAdoptImage(request):
    if request.method == 'POST':
        filename = upload(request, 'Adopt')
        return JsonResponse({'filename': filename})

@login_required
def RemoveAdoptImage(request):
    if request.method == 'POST':
        filename = request.POST.get('filename', None)
        filename = remove('Adopt', filename)
        
        if filename:
            return JsonResponse({'filename': filename})
        else:
            return JsonResponse({'filename': None})

@login_required   
def DeleteAdoptImage(request, pet_id):
    if request.method == 'POST':
        pet = Pet.objects.get(id=pet_id)
        image = PetImage.objects.get(pet=pet)

        filename = image.image.name
        filename = remove(filename, None)
        
        DeleteEntity(request, PetImage, image.id, None)
        
        if filename:
            messages.success(request, pet.name + " image removed successfully!")
        else:
            messages.error(request, "Error occurred while removing image!")
        return redirect('vcmsapp:view-adopt', pet_id=pet.id)

# Admin
@login_required
def AdminPage(request, admin_id):
    user = request.user
    admin = Staff.objects.get(user=user)

    staff = Staff.objects.filter(is_active=True)
    paginator = None
    if staff:
        paginator = serialize_and_paginate(
            staff,
            extra_fields=lambda stf: {
                'email': stf.user.email,
                'password': FirstPassword.objects.get(staff=stf).password
            }
        )

    context = {
        'admin': admin,
        'onPage': 'Staff',
        'pages': paginator
    }

    if request.method == "POST":
        search_query = request.POST['search']
        paginator = None
        if (search_query.replace(" ", "") != '') and (search_query != None):
            staff = Staff.objects.filter(
                name__icontains=search_query,
                is_active=True
            )

            paginator = serialize_and_paginate(
                staff,
                extra_fields=lambda stf: {'email': stf.user.email}
            )

            context['query'] = search_query
            context['pages'] = paginator

        return render(request, "admin/Admin.html", context)
    return render(request, 'admin/Admin.html', context)

@login_required
def ViewStaff(request, admin_id, staff_no): #  with edit function
    admin = Staff.objects.get(id=admin_id)
    staff = Staff.objects.get(staff_no=staff_no)
    staff_user = staff.user
    view_staff = serialize_and_paginate(
        queryset=[staff],
        paginate=False,
        extra_fields=lambda stf: {'email': stf.user.email}
    )[0]

    if request.method == "POST":
        new_role = request.POST['role']
        new_name = request.POST['name']
        new_gender = request.POST['gender']
        new_email = request.POST['email']

        EditEntity(
            request, Staff, staff.id, staff.staff_no,
            role=new_role,
            name=new_name,
            gender=new_gender
        )

        EditEntity(
            request, User, staff_user.id, None,
            email=new_email
        )
        return redirect('vcmsapp:view-staff', admin_id=admin.id, staff_no=staff.staff_no)

    context = {
        'admin': admin,
        'view_staff': view_staff,
        'onPage': 'Staff'
    }

    return render(request, 'admin/ViewStaff.html', context)

@login_required
def RegisterStaff(request, admin_id):
    admin = Staff.objects.get(id=admin_id)

    if request.method == "POST":
        staff_no = get_with_consume('staff', 'STF')
        role = request.POST['role']
        name = request.POST['name']
        gender = request.POST['gender']
        email = request.POST['email']
        password = request.POST['password']

        new_user = AddEntity(
            request, User, None,
            email=email,
            password=password,
            is_staff=True,
            role=User.Role.S
        )

        new_staff = AddEntity(
            request, Staff, staff_no,
            user=new_user,
            staff_no=staff_no,
            role=Staff.Role.D if role == 'Doctor' else (Staff.Role.A if role == 'Admin' else Staff.Role.G),
            name=name,
            gender=gender
        )

        AddEntity(
            request, FirstPassword, None,
            staff=new_staff,
            password=password
        )

        return redirect('vcmsapp:admin', admin_id=admin.id)

    next_staff_no = get_without_consume('staff', 'STF')
    next_staff_password = generate_password()

    context = {
        'admin': admin,
        'onPage': 'Staff',
        'next_staff_no': next_staff_no,
        'next_staff_password': next_staff_password
    }

    return render(request, 'admin/RegisterStaff.html', context)

@login_required
def ApproveCustomer(request, admin_id):
    admin = Staff.objects.get(id=admin_id)
    customer = Customer.objects.filter(is_approved=False)

    if request.method == "POST":
        customer_id = request.POST['customer_id']
        to_approve = Customer.objects.get(id=customer_id)
        EditEntity(
            request, Customer, to_approve.id, to_approve.user.email,
            is_approved=True
        )

        AddEntity(
            request, EmailQueue, None,
            to=to_approve.user.email,
            module='CustomerApprovedEmail'
        )

        return redirect('vcmsapp:approve-customer', admin_id=admin.id)

    paginator = None
    if customer:
        paginator = serialize_and_paginate(
            customer,
            extra_fields=lambda cst: {'email': cst.user.email}
        )
    
    context = {
        'admin': admin,
        'onPage': 'Customer',
        'pages': paginator
    }

    return render(request, 'admin/ApproveCustomer.html', context)

# JS request endpoints
def get_slots_staff(request): # rewrite needed
    user = request.user
    staff = Staff.objects.get(user=user)
    date = request.POST['date']
    type = request.POST['type']
    if date > datetime.now().strftime("%Y-%m-%d"):
        slots = Slot.objects.filter(id__in=StaffScheduleSlotMapping.objects.filter(
            staff=staff,
            ssm__schedule__date=date,
            ssm__slot__type=type,
            ssm__slot__is_available=True
        ).values('ssm__slot'))
        slots = [{'id': slot.id, 'time': str(slot.start_time)} for slot in slots]
        return JsonResponse({'slots': slots})
    else:
        return JsonResponse({'slots': []})

def get_slots_customer(request):
    date = request.POST['date']
    type = request.POST['type']
    staff = request.POST['staff'].split(" ")[0][1:-1]
    staff = Staff.objects.get(staff_no=staff)
    if date > datetime.now().strftime("%Y-%m-%d"):
        slots = Slot.objects.filter(id__in=StaffScheduleSlotMapping.objects.filter(
            staff=staff,
            ssm__schedule__date=date,
            ssm__slot__type=type,
            ssm__slot__is_available=True
        ).values('ssm__slot'))
        slots = [{'id': slot.id, 'time': str(slot.start_time)} for slot in slots]
        return JsonResponse({'slots': slots})
    else:
        return JsonResponse({'slots': []})

def get_pets(request):
    customer_data = request.POST['customer_data']
    customer = Customer.objects.get(user__email=customer_data[:customer_data.index('(') - 1])
    pets = Pet.objects.filter(customer=customer).values('id', 'name')
    pets = [{'id': pet['id'], 'name': pet['name']} for pet in pets]

    return JsonResponse({'pets': pets})