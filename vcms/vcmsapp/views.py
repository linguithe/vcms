import random
from django.shortcuts import render
from django.contrib import messages
from sequences import *

from .models import *
from .utils import *
from .serializers import *

# Create your views here.
# Staff
def StaffPage(request):
    
    return render(request, "Staff.html")

def AddStaff(request):
    if request.method == "POST":
        user        = request.user
        staff_no    = "STF" + str(get_next_value("staff_no")).zfill(5)
        role        = request.POST['role']
        name        = request.POST['name']
        gender      = request.POST['gender']
        AddEntity(
            request, Staff, staff_no, 
            user=user, 
            staff_no=staff_no, 
            role=role, 
            name=name, 
            gender=gender
        )
        return render(request, "AddStaff.html")
    return render(request, "AddStaff.html")

def EditStaff(request, staff_id):
    if request.method == "POST":
        # staff_no is not editable
        newRole     = request.POST['role']
        newName     = request.POST['name']
        newGender   = request.POST['gender']

        EditEntity(
            request, Staff, staff_id, staff_id,
            role=newRole,
            name=newName,
            gender=newGender
        )
        return render(request, "EditStaff.html")
    return render(request, "EditStaff.html")

def DeleteStaff(request, staff_id):
    if request.method == "POST":
        DeleteEntity(
            request, Staff, staff_id, staff_id
        )
        return render(request, "Staff.html")
    return render(request, "Staff.html")


# Customer
def CustomerPage(request):
    user = request.user
    customer = Customer.get(user=user)
    appointments = Appointment.objects.filter(customer=customer)

    apmt_prepped = []
    if appointments:
        for apmt in appointments:
            date = apmt.slot.schedule.date
            serializer = AppointmentSerializer(apmt, context={'date': date})
            apmt_prepped.append(serializer.data)
    
    context = {
        'appointments': apmt_prepped
    }

    if request.method == "POST":
        search_query = request.POST['search']
        staff = Staff.objects.filter(name__icontains=search_query)
        filtered_appointments = []
        for s in staff:
            matched_appointments = Appointment.objects.filter(
                customer=customer,
                staff=s,
            )
            if matched_appointments:
                for ma in matched_appointments:
                    date = ma.slot.schedule.date
                    serializer = AppointmentSerializer(ma, context={'date': date})
                    filtered_appointments.append(serializer.data)
        context = {
            'appointments': filtered_appointments,
            'query': search_query
        }

        return render(request, "Customer.html", context)
    return render(request, 'Customer.html', context)

def AddCustomer(request):
    if request.method == "POST":
        user        = request.user
        name        = request.POST['name']
        gender      = request.POST['gender']
        AddEntity(
            request, Customer, name, 
            user=user, 
            name=name, 
            gender=gender
        )
        return render(request, "AddCustomer.html")
    return render(request, "AddCustomer.html")

def EditCustomer(request, customer_id):
    if request.method == "POST":
        toEditUserId = Customer.objects.get(customer_id).user

        newEmail = request.POST['email']
        EditEntity(
            request, User, toEditUserId, None,
            email=newEmail
        )

        newName = request.POST['name']
        newGender = request.POST['gender']
        EditEntity(
            request, Customer, customer_id, newName,
            name=newName,
            gender=newGender
        )
        return render(request, "EditCustomer.html")
    return render(request, "EditCustomer.html")

def DeleteCustomer(request, customer_id):
    if request.method == "POST":
        customer = Customer.objects.get(customer_id)
        DeleteEntity(request, Customer, customer_id, customer.name)
        return render(request, "Customer.html")
    return render(request, "Customer.html")