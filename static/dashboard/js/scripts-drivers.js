function formatTime(time) {
	let parts = time.match(/(\d+) (\d+):(\d+):(\d+)/);
	if (!parts) {
		return time;
	} else {
		let days = parseInt(parts[1]);
		let hours = parseInt(parts[2]);
		let minutes = parseInt(parts[3]);
		let seconds = parseInt(parts[4]);

		hours += days * 24;

		// Форматувати рядок у вигляді HH:mm:ss
		return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
	}
}


function fetchDriverEfficiencyData(period, start, end) {
	let apiUrl;
	if (period === 'custom') {
		apiUrl = `/api/drivers_info/${start}&${end}/`;
	} else {
		apiUrl = `/api/drivers_info/${period}/`;
	};
	$.ajax({
		url: apiUrl,
		type: 'GET',
		dataType: 'json',
		success: function (data) {
			$(".apply-filter-button_driver").prop("disabled", false);
			let table = $('.info-driver table');
			let driverBlock = $('.driver-block');
			let startDate = data[0]['start'];
			let endDate = data[0]['end'];
			table.find('tr:gt(0)').remove();
			if (data[0]['drivers_efficiency'].length !== 0) {
				data[0]['drivers_efficiency'].forEach(function (item) {
					let row = $('<tr></tr>');
					let formattedTime = formatTime(item.road_time);
					let time = formattedTime

					row.append('<td class="driver">' + item.full_name + '</td>');
					row.append('<td class="aggregator">"-----"</td>');
					row.append('<td class="kasa">' + item.total_kasa + '</td>');
					row.append('<td class="orders">' + item.orders + '</td>');
					row.append('<td class="accept">' + item.accept_percent + " %" + '</td>');
					row.append('<td class="price">' + item.average_price + '</td>');
					row.append('<td class="mileage">' + item.mileage + '</td>');
					row.append('<td class="efficiency">' + item.efficiency + '</td>');
					row.append('<td class="road">' + time + '</td>');

					table.append(row);

				});

				$('.driver-container').empty();

				data[0]['drivers_efficiency'].forEach(function (driver) {
					let driverBlock = $('<div class="driver-block"></div>');
					let driverName = $('<div class="driver-name"></div>');
					let driverInfo = $('<div class="driver-info"></div>');

					driverName.append('<h3>' + driver.full_name + '</h3>');
					driverName.append('<div class="arrow">▼</div>');

					driverName.on('click', function () {
						if (driverInfo.is(':hidden')) {
							driverInfo.slideDown();
						} else {
							driverInfo.slideUp();
						}
					});

					driverInfo.append('<p>' + gettext("Каса: ") + driver.total_kasa + gettext(" грн") + '</p>');
					driverInfo.append('<p>' + gettext("Кількість замовлень: ") + driver.orders + '</p>');
					driverInfo.append('<p>' + gettext("Відсоток прийнятих замовлень: ") + driver.accept_percent + '%' + '</p>');
					driverInfo.append('<p>' + gettext("Середній чек, грн: ") + driver.average_price + '</p>');
					driverInfo.append('<p>' + gettext("Пробіг, км: ") + driver.mileage + '</p>');
					driverInfo.append('<p>' + gettext("Ефективність, грн/км: ") + driver.efficiency + '</p>');
					driverInfo.append('<p>' + gettext("Час в дорозі: ") + formatTime(driver.road_time) + '</p>');

					driverBlock.append(driverName);
					driverBlock.append(driverInfo);

					// Додати блок водія до контейнера
					$('.driver-container').append(driverBlock);
				});
			}
			if (period === 'yesterday') {
				$('.income-drivers-date').text(startDate);
			} else {
				$('.income-drivers-date').text('З ' + startDate + ' ' + gettext('по') + ' ' + endDate);
			}
		},
		error: function (error) {
			console.error(error);
		}
	});
}


function fetchDriverFleetEfficiencyData(period, start, end, aggregators) {
	let apiUrl;
	if (period === 'custom') {
		apiUrl = `/api/drivers_info/${start}&${end}/${aggregators}/`;
	} else {
		apiUrl = `/api/drivers_info/${period}/${aggregators}/`;
	};
	$.ajax({
		url: apiUrl,
		type: 'GET',
		dataType: 'json',
		success: function (data) {
			$(".apply-filter-button_driver").prop("disabled", false);
			let table = $('.info-driver table');
			let startDate = data[0]['start'];
			let endDate = data[0]['end'];

			table.find('tr:gt(0)').remove();

			if (data.length !== 0) {
				data.forEach(function (item, index) {
					let efficiency = item.drivers_efficiency;

					efficiency.forEach(function (items, innerIndex) {
						let fleets = items.fleets;

						fleets.forEach(function (fleet, fleetIndex) {
							let row = $('<tr></tr>');

							if (fleetIndex === 0) {
								// Додати ім'я водія лише для першого рядка флоту
								row.append('<td class="driver" rowspan="' + fleets.length + '">' + items.full_name + '</td>');
							}

							row.append('<td class="fleet">' + Object.keys(fleet)[0] + '</td>');
							row.append('<td class="kasa">' + fleet[Object.keys(fleet)[0]].driver_total_kasa + '</td>');
							row.append('<td class="orders">' + fleet[Object.keys(fleet)[0]].orders + '</td>');
							row.append('<td class="accept">' + fleet[Object.keys(fleet)[0]].driver_accept_percent + " %" + '</td>');
							row.append('<td class="price">' + fleet[Object.keys(fleet)[0]].driver_average_price + '</td>');
							row.append('<td class="mileage">' + fleet[Object.keys(fleet)[0]].driver_mileage + '</td>');
							row.append('<td class="efficiency">' + fleet[Object.keys(fleet)[0]].driver_efficiency + '</td>');
							row.append('<td class="time">' + formatTime(fleet[Object.keys(fleet)[0]].driver_road_time) + '</td>');

							table.append(row);
						});
					});
				});
			}

			if (period === 'yesterday') {
					$('.income-drivers-date').text(startDate);
			} else {
					$('.income-drivers-date').text('З ' + startDate + ' ' + gettext('по') + ' ' + endDate);
			}
		},
		error: function (error) {
			console.error(error);
		}
	});
}

$(document).ready(function () {
	let $table = $('.driver-table');
	let $tbody = $table.find('tbody');

	function sortTable(column, order) {
		let rows = $tbody.find('tr').toArray();

		let collator = new Intl.Collator(undefined, {sensitivity: 'base'});

		rows.sort(function (a, b) {
			let valueA = $(a).find(`td.${column}`).text();
			let valueB = $(b).find(`td.${column}`).text();
			if (column === 'driver') {
				if (order === 'asc') {
					return collator.compare(valueA, valueB);
				} else {
					return collator.compare(valueB, valueA);
				}
				;
			} else {
				let floatA = parseFloat(valueA);
				let floatB = parseFloat(valueB);
				if (order === 'asc') {
					return floatA - floatB;
				} else {
					return floatB - floatA;
				}
				;
			}
		});

		$tbody.empty().append(rows);
	}

	// Attach click event handlers to the table headers for sorting
	$table.find('th.sortable').click(function () {

		let column = $(this).data('sort');
		let sortOrder = $(this).hasClass('sorted-asc') ? 'desc' : 'asc';

		// Reset sorting indicators
		$table.find('th.sortable').removeClass('sorted-asc sorted-desc');

		if (sortOrder === 'asc') {
			$(this).addClass('sorted-asc');
		} else {
			$(this).addClass('sorted-desc');
		}

		sortTable(column, sortOrder);
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
			selectedOption.data("value", clickedValue);
			selectedOption.text($(this).text());
			customSelect.removeClass("active");

			aggregators = $('.checkbox-container input[type="checkbox"]:checked').map(function() {
				return $(this).val();
			}).get();

			var aggregatorsString = aggregators.join('&');

			if (clickedValue !== "custom") {
				if (aggregatorsString === "shared") {
					fetchDriverEfficiencyData(clickedValue, null, null);
				} else {
					fetchDriverFleetEfficiencyData(clickedValue, null, null, aggregatorsString);
				}
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

	var sharedCheckbox = $('#sharedCheckbox');
	$('.checkbox-container input[type="checkbox"]').change(function() {
		var checkboxId = $(this).attr('id');

		if (checkboxId === 'sharedCheckbox' && $(this).prop('checked')) {
			$('.checkbox-container input[type="checkbox"]').not(this).prop('checked', false);
		} else {
			$('#sharedCheckbox').prop('checked', false);
		}

		var anyOtherCheckboxChecked = $('.checkbox-container input[type="checkbox"]:not(#sharedCheckbox):checked').length > 0;
		if (!anyOtherCheckboxChecked) {
			sharedCheckbox.prop('checked', true);
		}

		checkSelection();
	});
});

function checkSelection() {
  var selectedAggregators = [];
  $('.checkbox-container input[type="checkbox"]:checked').each(function() {
    selectedAggregators.push($(this).val());
  });
  var aggregatorsString = selectedAggregators.join('&');
  var selectedPeriod = $('#period .selected-option-drivers').data('value');
	var startDate = $("#start_report_driver").val();
	var endDate = $("#end_report_driver").val();

  if (selectedPeriod === "custom" && aggregatorsString === "shared") {
		fetchDriverEfficiencyData(selectedPeriod, startDate, endDate);
	} else {
		fetchDriverFleetEfficiencyData(selectedPeriod, startDate, endDate, aggregatorsString);
	}
}
