function validate_name(id='name') {
    var name = document.getElementById(id);
    if (name) {
        name.addEventListener('input', function() {
            if (/[^a-zA-Z /.]/.test(name.value)){
                name.setCustomValidity('Name can only contain alphabets, spaces, and forward slashes.');
            } else {
                name.setCustomValidity('');
            }
        });
    }
}

function validate_dob(id='dob') {
    var dob = document.getElementById(id);
    if (dob) {
        dob.addEventListener('input', function() {
            var dobInput = new Date(dob.value);
            var age = (Date.now() - dobInput) / 31557600000;

            if (age < 18) {
                dob.setCustomValidity('You must be at least 18 years old to register.');
            } else {
                dob.setCustomValidity('');
            }

            if (age > 100) {
                dob.setCustomValidity('Age cannot be greater than 100.');
            } else {
                dob.setCustomValidity('');
            }

            if (dobInput > Date.now()) {
                dob.setCustomValidity('Date of birth cannot be in the future.');
            } else {
                dob.setCustomValidity('');
            }
        });
    }
}

function validate_password(id='password', id2='confirmPassword') {
    var password = document.getElementById(id);
    var confirmPassword = document.getElementById(id2);
    if (password) {
        password.addEventListener('input', function() {
            var passwordInput = password.value;
            if (
                /[A-Z]/.test(passwordInput) &&
                /[a-z]/.test(passwordInput) &&
                /[0-9]/.test(passwordInput) &&
                /[^A-Za-z0-9]/.test(passwordInput) &&
                passwordInput.length >= 8
            ) {
                password.setCustomValidity('');
            } else {
                password.setCustomValidity(
                    'Password must contain at least the following:' +
                    '\n- One lowercase character' +
                    '\n- One uppercase character' +
                    '\n- One digit' +
                    '\n- One special character' +
                    '\n- 8 characters in total'
                );
            }
        });
    }

    if (password && confirmPassword) {
        confirmPassword.addEventListener('input', function() {
            if (confirmPassword.value !== password.value) {
                confirmPassword.setCustomValidity('Passwords must match.');
            } else {
                confirmPassword.setCustomValidity('');
            }
        });
    }
}

function validate_phone(id='phone') {
    var phone = document.getElementById(id);
    if (phone) {
        phone.addEventListener('input', function() {
            var phoneRegex = /^01\d{8,9}$/;
            if (!phoneRegex.test(phone.value)) {
                phone.setCustomValidity('Phone number must be in the format 01x-xxxxxxx or 01x-xxxxxxxx and contain only digits.');
            } else {
                phone.setCustomValidity('');
            }

            if (/^01\d$/.test(phone.value)) {
                phone.value += '-';
            }
        });
    }
}

function validate_date_future(id='date') {
    var date = document.getElementById(id);
    if (date) {
        date.addEventListener('input', function() {
            var dateInput = new Date(date.value);
            var today = new Date();

            if (dateInput < today) {
                date.setCustomValidity('');
            } else {
                date.setCustomValidity('Date cannot be in the future.');
            }
        });
    }
}

function validate_date_past(id='date') {
    var date = document.getElementById(id);
    if (date) {
        date.addEventListener('input', function() {
            var dateInput = new Date(date.value);
            var today = new Date();

            if (dateInput > today) {
                date.setCustomValidity('');
            } else {
                date.setCustomValidity('Date cannot be in the past.');
            }
        });
    }
}

function validate_time(id='start_time', id2='end_time') {
    var startTime = document.getElementById(id);
    var endTime = document.getElementById(id2);
    if (startTime && endTime) {
        startTime.addEventListener('input', validate);
        endTime.addEventListener('input', validate);

        function validate() {
            var startTimeInput = new Date("1970-01-01 " + startTime.value);
            var endTimeInput = new Date("1970-01-01 " + endTime.value);
            
            if (endTimeInput - startTimeInput >= 900000) {
                startTime.setCustomValidity('');
                endTime.setCustomValidity('');
            } else {
                startTime.setCustomValidity('Slot must be at least 15 minutes.');
                endTime.setCustomValidity('Slot must be at least 15 minutes.');
            }

            if (startTimeInput < endTimeInput) {
                startTime.setCustomValidity('');
                endTime.setCustomValidity('');
            } else {
                startTime.setCustomValidity('Start time must be before end time.');
                endTime.setCustomValidity('End time must be after start time.');
            }

        }
    }
}