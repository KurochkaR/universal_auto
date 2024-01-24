function fetchVehicleEarningsData(selectedValue, startDate, endDate) {
	console.log(selectedValue);
//	$.ajax({
//		url: "/dashboard/vehicle-earnings-data",
//		type: "GET",
//		data: {
//			"selectedValue": selectedValue,
//			"startDate": startDate,
//			"endDate": endDate
//		},
//		success: function(response) {
//			$("#vehicleEarningsChart").html(response);
//		}
//	});
}


$(document).ready(function() {
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
