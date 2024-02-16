$(document).ready(function () {
	$.ajax({
		url: `/api/driver_info/`,
		type: 'GET',
		dataType: 'json',
		success: function(data) {
			data.forEach(function(driver) {
				var driverItem = $('<div class="driver-item"></div>');
        var driverInfo = $('<div class="driver-info" data-id="' + driver.id + '"></div>');

				driverInfo.append('<div class="driver-name-info"><p>' + driver.full_name + '</p></div>');
				driverInfo.append('<div class="driver-phone"><p>' + driver.phone_number + '</p></div>');
				driverInfo.append('<div class="driver-chat-id"><p>' + driver.chat_id + '</p></div>');
				driverInfo.append('<div class="driver-schedule"><p>' + driver.driver_schema + '</p></div>');
				driverInfo.append('<div class="driver-status"><p>' + driver.driver_status + '</p></div>');
				driverInfo.append('<div class="driver-car"><p>' + driver.vehicle + '</p></div>');

				driverItem.append(driverInfo);

				$('.drivers-list').append(driverItem);
			});
		}
	});

	$(this).on('click', '.driver-name-info', function() {
		var driverId = $(this).parent().data('id');
		window.location.href = "/dashboard/driver/" + driverId;
	});
});
