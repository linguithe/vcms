from datetime import datetime, timedelta
from django.db import transaction
from vcmsapp.models import *

import logging

def create():
    try:
        with transaction.atomic():
            today = datetime.today()
            if today.weekday() == 0:
                for i in range(0, 7):
                    date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
                    exists = Schedule.objects.filter(date=date).exists()
                    if not exists:
                        schedule = Schedule(date=date)
                        schedule.save()       
    except Exception as e:
        logging.error(str(e))