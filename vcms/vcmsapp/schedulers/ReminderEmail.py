from datetime import datetime
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
from vcmsapp.models import *
from vcmsapp.utils import *

import logging

def send():
    try:
        appointments = Appointment.objects.filter(
            sssm__ssm__schedule__date__gte=datetime.now().strftime('%Y-%m-%d'),
            is_completed=False,
        )

        for appointment in appointments:
            days = (datetime.strptime(appointment.sssm.ssm.schedule.date, '%Y-%m-%d').date() - datetime.now().date()).days - 1
            if days == 1:
                if not EmailQueue.objects.filter(
                    module='ReminderEmail_1_' + appointment.pet.name + '_' + str(appointment.id),
                    void=False
                ).exists():
                    AddEntity(
                        None, EmailQueue, None,
                        to=appointment.customer.user.email,
                        module='ReminderEmail_1_' + appointment.pet.name + '_' + str(appointment.id),
                    )

        emails = EmailQueue.objects.filter(
            is_sent=False,
            module__contains='ReminderEmail_',
            void=False
        )
        if emails:
            for email in emails:
                try:
                    if User.objects.filter(email=email.to).exists():
                        if User.objects.filter(email=email.to).count() <= 1:
                            email_to_send = emails.get(id=email.id)
                            if email_to_send.retry_count < settings.RETRY_LIMIT:
                                try:
                                    days = int(email_to_send.module.split('_')[1])
                                    customer = Customer.objects.get(user__email=email.to)
                                    pet = Pet.objects.get(name=email_to_send.module.split('_')[2], customer=customer)
                                    relative_url = reverse('vcmsapp:login')
                                    absolute_url = settings.HOST_ADDRESS + relative_url
                                    site = settings.HOST_ADDRESS

                                    context = {
                                        'customer': customer,
                                        'pet': pet,
                                        'login_url': absolute_url,
                                        'days': days,
                                    }

                                    html_template = render_to_string('email/ReminderEmail.html', context)

                                    data = {
                                        'email_body': '',
                                        'to_email': email.to,
                                        'email_subject': 'Upcoming Appointment',
                                    }

                                    send_status = send_email(data, html_template)

                                    if send_status:
                                        email_to_send.is_sent = True
                                        email_to_send.send_datetime = datetime.now()
                                        email_to_send.save()
                                    else:
                                        email_to_send.retry_count += 1
                                        email_to_send.save()
                                except Exception as e:
                                    logging.error(str(e))
                            else:
                                email_to_send.void = True
                                email_to_send.save()
                        else:
                            f'Found multiple users binded to {email.to} in the system.'
                    else:
                        f'User {email.to} does not exist in the system.'
                except Exception as e:
                    logging.error(str(e))
    except Exception as e:
        logging.error(e)