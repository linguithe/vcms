// var defaultValue = 'a fixed value' OR
// var defaultValue = {{value|escapejs}}

function default_selected(defaultValue, selectId) {
    var selectElement = document.getElementById(selectId);
    
    for (var i = 0; i < selectElement.options.length; i++) {
        if (selectElement.options[i].value === defaultValue) {
            selectElement.options[i].selected = true;
            break;
        }
    }
}
