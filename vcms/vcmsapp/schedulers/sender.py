from apscheduler.schedulers.background import BackgroundScheduler

def start():
    from vcmsapp.schedulers import CustomerApprovedEmail, CreateSchedule, ReminderEmail
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(CustomerApprovedEmail.send, 'interval', seconds=5)
    scheduler.add_job(CreateSchedule.create, 'interval', seconds=5)
    scheduler.add_job(ReminderEmail.send, 'interval', seconds=5)

    scheduler.start()