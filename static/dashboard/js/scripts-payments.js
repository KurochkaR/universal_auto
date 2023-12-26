function driverPayment(period=null, start=null, end=null) {
	if (period === null) {
		var url = `/api/driver_payments/`;
	} else if (period === 'custom') {
		var url = `/api/driver_payments/${start}&${end}/`;
	} else {
		var url = `/api/driver_payments/${period}/`;
	}

	$.ajax({
		url: url,
		type: 'GET',
		dataType: 'json',
		success: function (response) {
			var tableBody = $('.driver-table tbody');
			tableBody.empty()


			for (var i = 0; i < response.length; i++) {
				var editButton = '<button class="edit-btn"><svg version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="35px" height="35px" viewBox="0 0 485.219 485.22" style="enable-background:new 0 0 485.219 485.22;" xml:space="preserve"><g><path d="M467.476,146.438l-21.445,21.455L317.35,39.23l21.445-21.457c23.689-23.692,62.104-23.692,85.795,0l42.886,42.897 C491.133,84.349,491.133,122.748,467.476,146.438z M167.233,403.748c-5.922,5.922-5.922,15.513,0,21.436 c5.925,5.955,15.521,5.955,21.443,0L424.59,189.335l-21.469-21.457L167.233,403.748z M60,296.54c-5.925,5.927-5.925,15.514,0,21.44 c5.922,5.923,15.518,5.923,21.443,0L317.35,82.113L295.914,60.67L60,296.54z M338.767,103.54L102.881,339.421 c-11.845,11.822-11.815,31.041,0,42.886c11.85,11.846,31.038,11.901,42.914-0.032l235.886-235.837L338.767,103.54z M145.734,446.572c-7.253-7.262-10.749-16.465-12.05-25.948c-3.083,0.476-6.188,0.919-9.36,0.919 c-16.202,0-31.419-6.333-42.881-17.795c-11.462-11.491-17.77-26.687-17.77-42.887c0-2.954,0.443-5.833,0.859-8.703 c-9.803-1.335-18.864-5.629-25.972-12.737c-0.682-0.677-0.917-1.596-1.538-2.338L0,485.216l147.748-36.986 C147.097,447.637,146.36,447.193,145.734,446.572z"/></g></svg></button>';
				var confirmButton = '<button class="apply-btn"><svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="35px" height="35px" viewBox="0,0,256,256"><g fill="#a1e8b9" fill-rule="nonzero" stroke="none" stroke-width="1" stroke-linecap="butt" stroke-linejoin="miter" stroke-miterlimit="10" stroke-dasharray="" stroke-dashoffset="0" font-family="none" font-weight="none" font-size="none" text-anchor="none" style="mix-blend-mode: normal"><g transform="scale(3.55556,3.55556)"><path d="M36,12c13.255,0 24,10.745 24,24c0,13.255 -10.745,24 -24,24c-13.255,0 -24,-10.745 -24,-24c0,-13.255 10.745,-24 24,-24zM46.018,31.464c0.901,-1.391 0.504,-3.248 -0.887,-4.149c-1.39,-0.901 -3.247,-0.503 -4.148,0.886l-7.134,11.011l-3.097,-3.519c-1.094,-1.243 -2.99,-1.364 -4.233,-0.271c-1.244,1.095 -1.365,2.99 -0.271,4.234l5.713,6.493c0.571,0.649 1.394,1.018 2.252,1.018c0.073,0 0.146,-0.002 0.22,-0.008c0.937,-0.069 1.787,-0.572 2.298,-1.36z"></path></g></g></svg></button>';


				var row = $('<tr>');
				row.attr('data-id', response[i].id);
				row.append('<td>' + response[i].report_from + ' - ' + response[i].report_to + '</td>');
				row.append('<td>' + response[i].full_name + '</td>');
				row.append('<td>' + response[i].kasa + '</td>');
				row.append('<td>' + response[i].cash + '</td>');
				row.append('<td>' + response[i].rent + '</td>');
				row.append('<td>' + response[i].bonuses + '</td>');
				row.append('<td>' + response[i].penalties + '</td>');
				row.append('<td>' + response[i].earning + '</td>');
				row.append('<td>' + response[i].status + '</td>');
				row.append('<td>' + editButton + confirmButton +'</td>');

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

  function initializeCustomSelect(customSelect, selectedOption, optionsList, iconDown, datePicker) {
		iconDown.click(function() {
			customSelect.toggleClass("active");
		});

		selectedOption.click(function() {
			customSelect.toggleClass("active");
		});

		optionsList.on("click", "li", function() {
			const clickedValue = $(this).data("value");
			selectedOption.text($(this).text());
			customSelect.removeClass("active");

//			if (clickedValue !== "custom") {
//				if (vehicle_lc) {
//					fetchSummaryReportData(clickedValue);
//					fetchCarEfficiencyData(clickedValue, vehicleId, vehicle_lc);
//				} else {
//					fetchDriverEfficiencyData(clickedValue);
//				}
//			}

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

	$('.shift-close-btn').off('click').on('click', function (e) {
  	e.preventDefault();
		$('#modal-upd-payments').hide();
	});

	$('.driver-table tbody').on('click', '.edit-btn', function () {
		var id = $(this).closest('tr').data('id');
		$('#modal-upd-payments').show();
		$('#modal-upd-payments').data('id', id);
		$(this).data('id', id);
	});

	$('#modal-upd-payments').on('click', '.upd-payments-btn', function () {
		var id = $('#modal-upd-payments').data('id');

		var bonusAmount = $('#bonus-amount').val();
		var bonusDescription = $('#bonus-description').val();
		var penaltyAmount = $('#penalty-amount').val();
		var penaltyDescription = $('#penalty-description').val();

		var dataToSend = {
			id: id,
			bonusAmount: bonusAmount,
			bonusDescription: bonusDescription,
			penaltyAmount: penaltyAmount,
			penaltyDescription: penaltyDescription,
			action: 'upd-payments',
			csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
		};

		$.ajax({
			url: ajaxPostUrl,
			type: 'POST',
			data: dataToSend,
			dataType: 'json',
			success: function (response) {
				$('#modal-upd-payments').hide();
				driverPayment();
			}
		});
	});
});