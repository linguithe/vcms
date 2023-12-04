from django.contrib import messages

# Add, Edit, Delete entities
# Pass None for success_message_identifier if no message wanted to be shown after success
def AddEntity(request, model, success_message_identifier, **kwargs):
    try:
        new_entry = model(**kwargs)
        new_entry.save()
        if success_message_identifier:
            messages.success(request, "New " + model.__name__.lower() + " " + success_message_identifier + " created successfully!")
    except Exception as e:
        messages.error(request, "Error occurred with the message " + str(e))

def EditEntity(request, model, entity_id, success_message_identifier, **kwargs):
    try:
        to_edit = model.objects.get(entity_id)
        for key, value in kwargs.items():
            if hasattr(to_edit, key):
                setattr(to_edit, key, value)
            else:
                raise AttributeError(f"'{to_edit.__class__.__name__}' object has no attribute '{key}'")
        to_edit.save()
        if success_message_identifier:
            messages.success(request, model.__name__ + " " + success_message_identifier + " edited successfully!")
    except Exception as e:
        messages.error(request, "Error occurred with the message " + str(e))

def DeleteEntity(request, model, entity_id, success_message_identifier, **kwargs):
    try:
        to_delete = model.objects.get(entity_id)
        to_delete.delete()
        if success_message_identifier:
            messages.success(request, model.__name__ + " " + success_message_identifier + " deleted successfully!")
    except Exception as e:
        messages.error(request, "Error occurred with the message " + str(e))
