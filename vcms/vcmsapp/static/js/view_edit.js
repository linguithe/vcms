function view_edit(formId, excludeFields = []) {
    var fields = Array.from(document.querySelectorAll('#' + formId + ' input, #' + formId + ' select, #' + formId + ' textarea'))
        .filter(field => !excludeFields.includes(field.id));
    var divs = Array.from(document.querySelectorAll('.form-group, .form-group-disabled'))
        .filter(div => !excludeFields.includes(div.id));
    var imgs = Array.from(document.querySelectorAll('.img-container, .img-container-disabled'));
    var dz = document.getElementById('imageUpload');
    var dzCover = document.getElementById('dropzone_cover');
    var dzContainer = document.getElementById('dropzone_container');
    var editBtn = document.getElementById('editBtn');
    var saveBtn = document.getElementById('saveBtn');
    var cancelBtn = document.getElementById('cancelBtn');
    var backBtn = document.getElementById('backBtn');
    var deleteBtn = document.getElementById('deleteBtn');

    editBtn.addEventListener('click', function() {
        fields.forEach(function(field) {
            field.disabled = false;
        });
        divs.forEach(function(div) {
            div.classList.remove('form-group-disabled');
            div.classList.add('form-group');
        });
        imgs.forEach(function(img) {
            img.classList.remove('img-container-disabled');
            img.classList.add('img-container');
        });

        if (dz && dzCover && dzContainer){
            dzContainer.classList.remove('dropzone-container-disabled');
            dzContainer.classList.add('dropzone-container');
            dzCover.style.display = 'none';
            dz.style.display = 'block';
        }
        
        editBtn.style.display = 'none';
        saveBtn.style.display = 'block';
        backBtn.style.display = 'none';
        cancelBtn.style.display = 'block';

        if (deleteBtn) {
            deleteBtn.style.display = 'block';
        }
    });

    cancelBtn.addEventListener('click', function() {
        fields.forEach(function(field) {
            field.disabled = true;
        });
        divs.forEach(function(div) {
            div.classList.remove('form-group');
            div.classList.add('form-group-disabled');
        });
        imgs.forEach(function(img) {
            img.classList.remove('img-container');
            img.classList.add('img-container-disabled');
        });

        if (dz && dzCover && dzContainer){
            dzContainer.classList.remove('dropzone-container');
            dzContainer.classList.add('dropzone-container-disabled');
            dzCover.style.display = 'block';
            dz.style.display = 'none';
        }
        
        editBtn.style.display = 'block';
        saveBtn.style.display = 'none';
        backBtn.style.display = 'block';
        cancelBtn.style.display = 'none';

        if (deleteBtn) {
            deleteBtn.style.display = 'none';
        }
    });

    saveBtn.addEventListener('click', function() {
        var form = document.getElementById(formId);
        if (form && form.reportValidity()) {
            form.submit();
        }
    });
}