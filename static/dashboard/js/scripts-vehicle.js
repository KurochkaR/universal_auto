function fetchVehicleEarningsData(period, start, end) {
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
		success: function(data) {

			var paybackCarContainer = $(".payback-car");
			paybackCarContainer.empty();

			data.forEach(function(vehicle) {

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
						"<div class='progress-period' style='left: " + vehicle.progress_percentage + "%;'>" +
						"</div>" +
						"</div>" +
						"</div>" +
						"<p>Вартість авто:<br><span class='vehicle-price'>₴ " + vehicle.price + "</span></p>");

				paybackCarContainer.append(carItem);

			});
		}
	});
}



$(document).ready(function() {

	fetchVehicleEarningsData("yesterday", null, null);

	function initializeCustomSelect(customSelect, selectedOption, optionsList, iconDown, datePicker) {

		iconDown.click(function() {
			customSelect.toggleClass("active");
		});

		selectedOption.click(function() {
			customSelect.toggleClass("active");
		});

		optionsList.on("click", "li", function() {

			const clickedValue = $(this).data("value");
			selectedOption.data("value", clickedValue);
			selectedOption.text($(this).text());
			customSelect.removeClass("active");

			if (clickedValue !== "custom") {
				fetchVehicleEarningsData(clickedValue, null, null);
			}

			if (clickedValue === "custom") {
				datePicker.css("display", "block");
			} else {
				datePicker.css("display", "none");
			}
		});
	}

	const customSelectDriver = $(".custom-select-drivers");
	const selectedOptionDriver = customSelectDriver.find(".selected-option-drivers");
	const optionsListDriver = customSelectDriver.find(".options-drivers");
	const iconDownDriver = customSelectDriver.find(".fas.fa-angle-down");
	const datePickerDriver = $("#datePickerDriver");

	initializeCustomSelect(customSelectDriver, selectedOptionDriver, optionsListDriver, iconDownDriver, datePickerDriver);
});
