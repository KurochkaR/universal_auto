function fetchVehicleEarningsData(period, start = null, end = null) {
	let apiUrl;
	if (period === 'custom') {
		apiUrl = `/api/vehicles_info/${start}&${end}/`;
	} else {
		apiUrl = `/api/vehicles_info/${period}/`;
	}

	$.ajax({
		url: apiUrl,
		type: "GET",
		dataType: "json",
		success: function (data) {
			console.log(data);
			var paybackCarContainer = $(".payback-car");
			paybackCarContainer.empty();

			var startDate = data[0].start_date;
			var endDate = data[0].end_date;
			if (startDate === endDate) {
				$('.weekly-income-dates').text(startDate);
			} else {
				$('.weekly-income-dates').text(gettext('З ') + startDate + ' ' + gettext('по') + ' ' + endDate);
			}

			$(".main-container .weekly-income-dates").css({
				position: "absolute",
				top: "17%",
				right: "3%"
			});

			data.forEach(function (vehicle) {

				var carItem = $("<div class='car-item'></div>");

				carItem.append("<div class='car-image'>" +
					"<img src='" + VehicleImg + "' alt='Зображення авто'>" +
					"<p class='licence-plate'>" + vehicle.licence_plate + "</p>" +
					"</div>");

				carItem.append("<div class='car-details'>" +
					"<p>Заробіток:<br><span class='vehicle-earning'>₴ " + vehicle.kasa + "</span></p>" +
					"<p>Витрати:<br><span class='vehicle-expenses'>₴ " + vehicle.spending + "</span></p>" +
					"<div class='progress-bar'>" +
					"<div class='progress' style='width: " + vehicle.total_progress_percentage + "%; max-width: 100%'>" +
					"<div class='progress-label' style='color: #0a0a0a'>" + vehicle.total_progress_percentage + "%</div>" +
					//						"<div class='progress-period' style='left: " + vehicle.progress_percentage + "%;'>" +
					//						"</div>" +
					"</div>" +
					"</div>" +
					"<p>Вартість авто:<br><span class='vehicle-price'>₴ " + vehicle.price + "</span></p>");

				paybackCarContainer.append(carItem);

			});
		}
	});
}


$(document).ready(function () {
	fetchVehicleEarningsData("today");

	initializeCustomSelect(function (clickedValue) {
		fetchVehicleEarningsData(clickedValue);
	});

	$(this).on('click', '.apply-filter-button', function () {
		applyDateRange(function (selectedPeriod, startDate, endDate) {
			fetchVehicleEarningsData(selectedPeriod, startDate, endDate);
		});
	})
});
