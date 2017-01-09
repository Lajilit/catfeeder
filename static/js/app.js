$.fn.serializeObject = function()
{
    var o = {};
    var a = this.serializeArray();
    $.each(a, function() {
        if (o[this.name] !== undefined) {
            if (!o[this.name].push) {
                o[this.name] = [o[this.name]];
            }
            o[this.name].push(this.value || '');
        } else {
            o[this.name] = this.value || '';
        }
    });
    return o;
};

$(function(){
  var lastFed = $('#lastFed');

  $.ajax({
      url: "/lastFed",
      type: "GET",
      contentType: 'application/json; charset=utf-8',
      dataType: 'json',
      success: function (response) {
          lastFed.html(response.lastFed)
      },
      error: function (response) {
          console.error(response.status, response.responseText);
      },
  });

  var $form = $('#feedForm');
  var submitButton = $('#feedSubmit');
  var statusText = $('#feedStatus');

    submitButton.on('click', function(e){
        e.preventDefault(); // prevent the default form submit action
        submitButton.prop('disabled', true);

        $.ajax({
            url: $form.attr("action"),
            type: $form.attr("method"),
            data: JSON.stringify($form.serializeObject()),
            contentType: 'application/json; charset=utf-8',
            dataType: 'json',
            success: function (response) {
                statusText.removeClass('danger');
                statusText.html(response.status);
                lastFed.html(response.lastFed)
                submitButton.prop('disabled', false);
            },
            error: function (response) {
                console.error(response.status, response.responseText);
                statusText.addClass('danger');
                statusText.html(response.status);
                submitButton.prop('disabled', false);
            },
        });
    });
});
