function driverPayment(period=null, start=null, end=null) {
	  if (period === null) {
			var url = `/api/driver_payments/`;
		} elif (period === 'custom') {
			var url = `/api/driver_payments/${start}&${end}/`;
		} else {
			var url = `/api/driver_payments/${period}/`;
		}

		$.ajax({
				url: url,
				type: 'GET',
				dataType: 'json',
				success: function (response) {
					console.log(response);
					var tableBody = $('.driver-table tbody');
      		tableBody.empty()

      		for (var i = 0; i < response.length; i++) {
						var row = $('<tr>');
						row.append('<td>' + response[i].report_from + ' - ' + response[i].report_to + '</td>');
						row.append('<td>' + response[i].full_name + '</td>');
						row.append('<td>' + response[i].kasa + '</td>');
						row.append('<td>' + response[i].cash + '</td>');
						row.append('<td>' + response[i].rent + '</td>');
						row.append('<td>' + response[i].bonuses + '</td>');
						row.append('<td>' + response[i].fines + '</td>');
						row.append('<td>' + response[i].earning + '</td>');
						row.append('<td>' + response[i].status + '</td>');
						tableBody.append(row);
					}
				}
		});
}

$(document).ready(function () {
	driverPayment();

	$('input[name="payment-status"]').change(function() {
    if ($(this).val() === 'closed') {
      driverPayment('current_quarter');
    } else {
      driverPayment();
    }
  });

});