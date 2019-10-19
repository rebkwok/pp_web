//http://xdsoft.net/jqplugins/datetimepicker/
Date.parseDate = function( input, format ){
  return moment(input,format).toDate();
};
Date.prototype.dateFormat = function( format ){
  return moment(this).format(format);
};

jQuery(document).ready(function () {
    jQuery('form.dirty-check').areYouSure();

    jQuery('#dobdatepicker').datetimepicker({
        format:'DD MMM YYYY',
        formatTime:'HH:mm',
        timepicker: false,
        defaultDate: '1990/01/01',
        closeOnDateSelect: true,
        scrollMonth: false,
        scrollTime: false,
        scrollInput: false
    });

    jQuery('#logdatepicker').datetimepicker({
        format:'DD MMM YYYY',
        formatTime:'HH:mm',
        timepicker: false,
        closeOnDateSelect: true,
        scrollMonth: false,
        scrollTime: false,
        scrollInput: false
    });


    //http://tablesorter.com/docs/
    jQuery("#sortTable").tablesorter();

    jQuery('#select-all').click(function (event) {  //on click
        if (this.checked) { // check select status
            jQuery('.select-checkbox').each(function () { //loop through each checkbox
                this.checked = true;  //select all checkboxes with class "select-checkbox"
            });
        } else {
            jQuery('.select-checkbox').each(function () { //loop through each checkbox
                this.checked = false; //deselect all checkboxes with class "select-checkbox"
            });
        }
    });

    jQuery('#semifinals').on('hidden.bs.collapse', function() {
        jQuery("#toggle-icon").addClass('fa-plus-square').removeClass('fa-minus-square');
      });

    jQuery('#semifinals').on('shown.bs.collapse', function() {
        jQuery("#toggle-icon").addClass('fa-minus-square').removeClass('fa-plus-square');
      });

});