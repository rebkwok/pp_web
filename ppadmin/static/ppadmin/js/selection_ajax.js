/*
  This file must be imported immediately-before the close-</body> tag,
  and after JQuery and Underscore.js are imported.
*/
/**
  The number of milliseconds to ignore clicks on the *same* like
  button, after a button *that was not ignored* was clicked. Used by
  `$(document).ready()`.
  Equal to <code>500</code>.
 */
var MILLS_TO_IGNORE = 500;

/**
   Executes a toggle click. Triggered by clicks on the selected button.
 */
var processToggleSelected = function()  {

   //In this scope, "this" is the button just clicked on.
   //The "this" in processResult is *not* the button just clicked
   //on.
   var $button_just_clicked_on = $(this);

   //The value of the "data-entry_id" attribute.
   var entry_id = $button_just_clicked_on.data('entry_id');

   var processResult = function(
       result, status, jqXHR)  {
      console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "', entry_id='" + entry_id + "'");
      $('#selection_status_' + entry_id).html(result);
   }

   $.ajax(
       {
          url: '/ppadmin/entries/' + entry_id + '/toggle_selection/selected/',
          dataType: 'html',
          type : "POST", // http method
          success: processResult
          //Should also have a "fail" call as well.
       }
    );
};

/**
   Executes a toggle click. Triggered by clicks on the selected button.
 */
var processToggleRejected = function()  {

   //In this scope, "this" is the button just clicked on.
   //The "this" in processResult is *not* the button just clicked
   //on.
   var $button_just_clicked_on = $(this);

   //The value of the "data-entry_id" attribute.
   var entry_id = $button_just_clicked_on.data('entry_id');

   var processResult = function(
       result, status, jqXHR)  {
      console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "', entry_id='" + entry_id + "'");
      $('#selection_status_' + entry_id).html(result);
   }

   $.ajax(
       {
          url: '/ppadmin/entries/' + entry_id + '/toggle_selection/rejected/',
          dataType: 'html',
          type : "POST", // http method
          success: processResult
          //Should also have a "fail" call as well.
       }
    );
};

/**
   Executes a toggle click. Triggered by clicks on the selected button.
 */
var processToggleUndecided = function()  {

   //In this scope, "this" is the button just clicked on.
   //The "this" in processResult is *not* the button just clicked
   //on.
   var $button_just_clicked_on = $(this);

   //The value of the "data-entry_id" attribute.
   var entry_id = $button_just_clicked_on.data('entry_id');

   var processResult = function(
       result, status, jqXHR)  {
      //console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "', entry_id='" + entry_id + "'");
      $('#selection_status_' + entry_id).html(result);
   }

   $.ajax(
       {
          url: '/ppadmin/entries/' + entry_id + '/toggle_selection/undecided/',
          dataType: 'html',
          type : "POST", // http method
          success: processResult
          //Should also have a "fail" call as well.
       }
    );
};

/**
   Executes a toggle click. Triggered by clicks on the reset button.
 */
var processToggleReset = function()  {

   //In this scope, "this" is the button just clicked on.
   //The "this" in processResult is *not* the button just clicked
   //on.
   var $button_just_clicked_on = $(this);

   //The value of the "data-entry_id" attribute.
   var entry_id = $button_just_clicked_on.data('entry_id');

   var processResult = function(
       result, status, jqXHR)  {
      //console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "', entry_id='" + entry_id + "'");
      $('#reset_' + entry_id).html(result);
   }

   $.ajax(
       {
          url: '/ppadmin/entries/' + entry_id + '/notified_selection_reset/',
          type : "POST", // http method
          dataType: 'html',
          success: processResult
          //Should also have a "fail" call as well.
       }
    );
};

/**
   The Ajax "main" function. Attaches the listeners to the elements on
   page load, each of which only take effect every
   <link to MILLS_TO_IGNORE> seconds.

   This protection is only against a single user pressing buttons as fast
   as they can. This is in no way a protection against a real DDOS attack,
   of which almost 100% bypass the client (browser) (they instead
   directly attack the server). Hence client-side protection is pointless.

   - http://stackoverflow.com/questions/28309850/how-much-prevention-of-rapid-fire-form-submissions-should-be-on-the-client-side

   The protection is implemented via Underscore.js' debounce function:
  - http://underscorejs.org/#debounce

   Using this only requires importing underscore-min.js. underscore-min.map
   is not needed.
 */
$(document).ready(function()  {
  /*
    There are many buttons having the class

      toggle_selected_button
      toggle_rejected_button
      toggle_undecided_button

    This attaches a listener to *every one*. Calling this again
    would attach a *second* listener to every button, meaning each
    click would be processed twice.
   */
  $('.toggle_selected_button').click(_.debounce(processToggleSelected,
      MILLS_TO_IGNORE, true));
  $('.toggle_rejected_button').click(_.debounce(processToggleRejected,
      MILLS_TO_IGNORE, true));
  $('.toggle_undecided_button').click(_.debounce(processToggleUndecided,
      MILLS_TO_IGNORE, true));
  $('.reset_button').click(_.debounce(processToggleReset,
      MILLS_TO_IGNORE, true));
  /*
    Warning: Placing the true parameter outside of the debounce call:

    $('#color_search_text').keyup(_.debounce(processSearch,
        MILLS_TO_IGNORE_SEARCH), true);

    results in "TypeError: e.handler.apply is not a function".
   */

  $(function() {

        // This function gets cookie with a given name
        function getCookie(name) {
            var cookieValue = null;
            if (document.cookie && document.cookie != '') {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var cookie = jQuery.trim(cookies[i]);
                    // Does this cookie string begin with the name we want?
                    if (cookie.substring(0, name.length + 1) == (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        var csrftoken = getCookie('csrftoken');

        /*
        The functions below will create a header with csrftoken
        */

        function csrfSafeMethod(method) {
            // these HTTP methods do not require CSRF protection
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }
        function sameOrigin(url) {
            // test that a given url is a same-origin URL
            // url could be relative or scheme relative or absolute
            var host = document.location.host; // host + port
            var protocol = document.location.protocol;
            var sr_origin = '//' + host;
            var origin = protocol + sr_origin;
            // Allow absolute or scheme relative URLs to same origin
            return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
                (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
                // or any other URL that isn't scheme relative or absolute i.e relative.
                !(/^(\/\/|http:|https:).*/.test(url));
        }

        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!csrfSafeMethod(settings.type) && sameOrigin(settings.url)) {
                    // Send the token to same-origin, relative URLs only.
                    // Send the token only if the method warrants CSRF protection
                    // Using the CSRFToken value acquired earlier
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                }
            }
        });

    });


});