$(document).ready(function () {
	$.ajax({
		url: `/api/driver_info/`,
		type: 'GET',
		dataType: 'json',
		success: function(data) {

			data.forEach(function(driver) {
				var driverItem = $('<div class="driver-item"></div>');
				var driverInfo = $('<div class="driver-info"></div>');

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

	var selectedOption = sessionStorage.getItem('selectedOption');
	if (selectedOption) {
		$('input[name="driver-info"][value="' + selectedOption + '"]').prop('checked', true);
	}

	$('#DriverBtnContainers').on('click', function() {
		$('input[name="driver-info"][value="driver-list"]').prop('checked', true);
		sessionStorage.setItem('selectedOption', 'driver-list');
	});

	$('input[name="driver-info"]').change(function() {
		var selectedValue = $(this).val();
		sessionStorage.setItem('selectedOption', selectedValue);

		switch(selectedValue) {
			case 'driver-list':
				window.location.href = "/dashboard/drivers/";
				break;
			case 'driver-payments':
				window.location.href = "/dashboard/drivers-payment/";
				break;
			case 'driver-efficiency':
				window.location.href = "/dashboard/drivers-efficiency/";
				break;
			default:
				break;
		}
	});
});
