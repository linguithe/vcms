from datetime import datetime, timedelta
from django.db import transaction
from vcmsapp.models import *

import logging

def create():
    try:
        today = datetime.today()
        triduum = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        appointments = Appointment.objects.filter(
            sssm__ssm__schedule__date_lte=triduum,
            sssm__ssm__schedule__date_gte=today,
        )

        for apmt in appointments:
            with transaction.atomic():
                notifications = Notification.objects.filter(
                    user=apmt.customer.user,
                    module='AppointmentUpcoming',
                )
                for ntf in notifications:
                    data = ntf.data
                    if data['appointment_id'] == apmt.id:
                        notification_exists = True
                        break
                    else:
                        notification_exists = False
                        
                if not notification_exists:
                    notification = Notification(
                        user=apmt.customer.user,
                        module='AppointmentUpcoming',
                        title='Appointment upcoming on ' + datetime.strptime(apmt.sssm.ssm.schedule.date, "%Y-%m-%d").strftime("%d %b %Y") + ' for ' + apmt.pet.name,
                        content='Appointment upcoming on ' + datetime.strptime(apmt.sssm.ssm.schedule.date, "%Y-%m-%d").strftime("%d %b %Y") + ' for ' + apmt.pet.name + '. Please check your appointment page for more details.',
                        data={
                            'appointment_id': apmt.id,
                            'customer_id': apmt.customer.id,
                        }
                    )
                    notification.save()
    except Exception as e:
        logging.error(str(e))