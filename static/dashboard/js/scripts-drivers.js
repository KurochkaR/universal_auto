$(document).ready(function () {
    getDriversList()
	$(this).on('click', '.driver-name-info', function () {
		var driverId = $(this).data('id');
		window.location.href = "/dashboard/driver/" + driverId;
	});
});

function getDriversList(){
    $.ajax({
		url: `/api/driver_info/`,
		type: 'GET',
		dataType: 'json',
		success: function (data) {
			data.forEach(function (driver) {
				var driverItem = $('<div class="driver-item"></div>');

				driverItem.append('<div class="driver-name-info" data-id="' + driver.id + '"><p>' + driver.full_name + '</p></div>');
				driverItem.append('<div class="driver-phone"><p>' + driver.phone_number + '</p></div>');
				driverItem.append('<div class="driver-chat-id"><p>' + driver.chat_id + '</p></div>');
				if (driver.driver_schema === null) {
					driverItem.append('<div class="driver-schedule"><p>Схема відсутня</p></div>');
				} else {
					driverItem.append('<div class="driver-schedule"><p>' + driver.driver_schema + '</p></div>');
				}
				driverItem.append('<div class="driver-status"><p>' + driver.driver_status + '</p></div>');
				driverItem.append('<div class="driver-car"><p>' + driver.vehicle + '</p></div>');

				$('.drivers-list').append(driverItem);
			});
		}
	});
}
