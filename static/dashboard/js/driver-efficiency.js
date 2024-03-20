function fetchDriverEfficiencyData(period, start, end) {
	let apiUrl;
	if (period === 'custom') {
		apiUrl = `/api/drivers_efficiency/${start}&${end}/`;
	} else {
		apiUrl = `/api/drivers_efficiency/${period}/`;
	}

	$.ajax({
		url: apiUrl,
		type: 'GET',
		dataType: 'json',
		success: function (data) {
			$('th[data-sort="fleet"]').hide();
			$(".aggregator").css("display", "none");
			$(".apply-filter-button_driver").prop("disabled", false);
			let table = $('.info-driver table');
			let startDate = data[0]['start'];
			let endDate = data[0]['end'];
			table.find('tr:gt(0)').remove();
			if (data[0]['drivers_efficiency'].length !== 0) {
				data[0]['drivers_efficiency'].forEach(function (item) {
					let row = $('<tr></tr>');
					let formattedTime = formatTime(item.road_time);
					let time = formattedTime

					row.append('<td class="driver">' + item.full_name + '</td>');
					row.append('<td class="kasa">' + Math.round(item.total_kasa) + '</td>');
					row.append('<td class="order_accepted">' + Math.round(item.total_orders_accepted) + '</td>');
					row.append('<td class="order_rejected">' + item.total_orders_rejected + '</td>');
					row.append('<td class="price">' + Math.round(item.average_price) + '</td>');
					row.append('<td class="mileage">' + Math.round(item.mileage) + '</td>');
					row.append('<td class="idling-mileage">' + Math.round(item.idling_mileage) + '</td>');
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

					driverInfo.append('<p>' + gettext("Каса: ") + Math.round(driver.total_kasa) + gettext(" грн") + '</p>');
					driverInfo.append('<p>' + gettext("Виконано замовлень: ") + driver.total_orders_accepted + '</p>');
					driverInfo.append('<p>' + gettext("Скасованих замовлень: ") + driver.total_orders_rejected + '</p>');
					driverInfo.append('<p>' + gettext("Середній чек, грн: ") + Math.round(driver.average_price) + '</p>');
					driverInfo.append('<p>' + gettext("Пробіг, км: ") + Math.round(driver.mileage) + '</p>');
					driverInfo.append('<p>' + gettext("Холостий пробіг, км: ") + Math.round(driver.idling_mileage) + '</p>');
					driverInfo.append('<p>' + gettext("Ефективність, грн/км: ") + driver.efficiency + '</p>');
					driverInfo.append('<p>' + gettext("Час в дорозі: ") + formatTime(driver.road_time) + '</p>');

					driverBlock.append(driverName);
					driverBlock.append(driverInfo);

					// Add the driver block to the container
					$('.driver-container').append(driverBlock);
				});
			}
			if (period === 'yesterday') {
				$('.income-drivers-date').text(startDate);
			} else {
				$('.income-drivers-date').text('З ' + startDate + ' ' + gettext('по') + ' ' + endDate);
			}
			sortTable('kasa', 'desc');
		},
		error: function (error) {
			$(".apply-filter-button_driver").prop("disabled", false);
			console.error(error);
		}
	});
}


function fetchDriverFleetEfficiencyData(period, start, end, aggregators) {
	let apiUrl;
	if (period === 'custom') {
		apiUrl = `/api/drivers_efficiency/${start}&${end}/${aggregators}/`;
	} else {
		apiUrl = `/api/drivers_efficiency/${period}/${aggregators}/`;
	}

	$.ajax({
		url: apiUrl,
		type: 'GET',
		dataType: 'json',
		success: function (data) {
			$('th[data-sort="fleet"]').show();
			$(".aggregator").css("display", "block");
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
							if (fleetIndex !== fleets.length - 1) {
								row.addClass('tr-aggregators'); // Додати клас тільки до рядків, крім останнього
							}
							if (fleetIndex === 0) {
								// Add the driver's name for the first line of the fleet only
								row.append('<td class="driver" rowspan="' + fleets.length + '">' + items.full_name + '</td>');
							}

							row.append('<td class="fleet">' + Object.keys(fleet)[0] + '</td>');
							row.append('<td class="kasa">' + Math.round(fleet[Object.keys(fleet)[0]].total_kasa) + '</td>');
							row.append('<td class="order_accepted">' + fleet[Object.keys(fleet)[0]].total_orders_accepted + '</td>');
							row.append('<td class="order_rejected">' + fleet[Object.keys(fleet)[0]].total_orders_rejected + '</td>');
							row.append('<td class="price">' + Math.round(fleet[Object.keys(fleet)[0]].average_price) + '</td>');
							row.append('<td class="mileage">' + Math.round(fleet[Object.keys(fleet)[0]].mileage) + '</td>');
							row.append('<td class="efficiency">' + fleet[Object.keys(fleet)[0]].efficiency + '</td>');
							row.append('<td class="time">' + formatTime(fleet[Object.keys(fleet)[0]].road_time) + '</td>');

							table.append(row);
						});
					});
					$('.driver-container').empty();

					// Create an object to store drivers by name
					let driversMap = {};

					data.forEach(function (item, index) {
						let efficiency = item.drivers_efficiency;

						efficiency.forEach(function (items, innerIndex) {
							let driverName = items.full_name;

							// Check if a driver with this name already exists
							if (!driversMap.hasOwnProperty(driverName)) {

								driversMap[driverName] = {
									'driverBlock': $('<div class="driver-block"></div>'),
									'driverName': $('<div class="driver-name"></div>'),
									'driverInfoContainer': $('<div class="driver-info-container"></div>')
								};


								driversMap[driverName].driverName.append('<h3>' + driverName + '</h3>');
								driversMap[driverName].driverName.append('<div class="arrow">▼</div>');

								driversMap[driverName].driverBlock.append(driversMap[driverName].driverName);
								driversMap[driverName].driverBlock.append(driversMap[driverName].driverInfoContainer);
								$('.driver-container').append(driversMap[driverName].driverBlock);

								// Set the click event on the driver's name
								driversMap[driverName].driverName.on('click', function () {
									let infoContainer = driversMap[driverName].driverInfoContainer;
									if (infoContainer.is(':hidden')) {
										infoContainer.slideDown();
										driversMap[driverName].driverName.find('.arrow').html('▲');
									} else {
										infoContainer.slideUp();
										driversMap[driverName].driverName.find('.arrow').html('▼');
									}
								});
							}

							let fleets = items.fleets;

							fleets.forEach(function (fleet, fleetIndex) {
								// Create an information block for each fleet and add it to the corresponding driver block
								let driverInfo = $('<div class="driver-info "></div>');
								driverInfo.append('<p>' + gettext("Флот: ") + Object.keys(fleet)[0] + '</p>');
								driverInfo.append('<p>' + gettext("Каса: ") + Math.round(fleet[Object.keys(fleet)[0]].total_kasa) + gettext(" грн") + '</p>');
								driverInfo.append('<p>' + gettext("Виконано замовлень: ") + fleet[Object.keys(fleet)[0]].total_orders_accepted + '</p>');
								driverInfo.append('<p>' + gettext("Кількість відмов: ") + fleet[Object.keys(fleet)[0]].total_orders_rejected + '</p>');
								driverInfo.append('<p>' + gettext("Середній чек, грн: ") + Math.round(fleet[Object.keys(fleet)[0]].driver_average_price) + '</p>');
								driverInfo.append('<p>' + gettext("Пробіг, км: ") + Math.round(fleet[Object.keys(fleet)[0]].mileage) + '</p>');
								driverInfo.append('<p>' + gettext("Ефективність, грн/км: ") + fleet[Object.keys(fleet)[0]].efficiency + '</p>');
								driverInfo.append('<p>' + gettext("Час в дорозі: ") + formatTime(fleet[Object.keys(fleet)[0]].road_time) + '</p><br>');

								driversMap[driverName].driverInfoContainer.append(driverInfo);
							});
						});
					});
				});
			}

			if (period === 'yesterday') {
				$('.income-drivers-date').text(startDate);
			} else {
				$('.income-drivers-date').text('З ' + startDate + ' ' + gettext('по') + ' ' + endDate);
			}
			sortTable('kasa', 'desc');
		},
		error: function (error) {
			console.error(error);
		}
	});
}

let $table = $('.driver-table');
let $tbody = $table.find('tbody');

function sortTable(column, order) {
	var groups = [];
	var group = [];

	$('tr:not(.table-header)').each(function () {
		if ($(this).find('.driver').length > 0) {
			if (group.length > 0) {
				groups.push(group);
			}
			group = [$(this)];
		} else {
			group.push($(this));
		}
	});

	if (group.length > 0) {
		groups.push(group);
	}

	groups.sort(function (a, b) {
		var sumA = 0;
		a.forEach(function (row) {
			sumA += parseFloat($(row).find(`td.${column}`).text());
		});
		var sumB = 0;
		b.forEach(function (row) {
			sumB += parseFloat($(row).find(`td.${column}`).text());
		});
		// return sumA - sumB;
		if (order === 'asc') {
			return sumA - sumB;
		} else {
			return sumB - sumA;
		}
	});

	$tbody.empty();
	groups.forEach(function (group) {
		group.forEach(function (row) {
			$tbody.append(row);
		});
	});
}


$(document).ready(function () {
	fetchDriverEfficiencyData('yesterday', null, null);

	$(document).on('click', 'th.sortable', function () {
		let column = $(this).data('sort');
		let sortOrder = $(this).hasClass('sorted-asc') ? 'desc' : 'asc';
		$table.find('th.sortable').removeClass('sorted-asc sorted-desc');

		if (sortOrder === 'asc') {
			$(this).addClass('sorted-asc');
		} else {
			$(this).addClass('sorted-desc');
		}
		sortTable(column, sortOrder);
	});

	function initializeCustomSelect(customSelect, selectedOption, optionsList, iconDown, datePicker) {
		iconDown.click(function () {
			customSelect.toggleClass("active");
		});

		selectedOption.click(function () {
			customSelect.toggleClass("active");
		});

		optionsList.on("click", "li", function () {

			const clickedValue = $(this).data("value");
			selectedOption.data("value", clickedValue);
			selectedOption.text($(this).text());
			customSelect.removeClass("active");

			aggregators = $('.checkbox-container input[type="checkbox"]:checked').map(function () {
				return $(this).val();
			}).get();

			var aggregatorsString = aggregators.join('&');

			if (clickedValue !== "custom") {
				if (aggregatorsString === "shared") {
					$('th[data-sort="idling-mileage"]').show();
					fetchDriverEfficiencyData(clickedValue, null, null);
				} else {
					console.log("aggregatorsString: ", aggregatorsString);
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
	$('.checkbox-container input[type="checkbox"]').change(function () {
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

	$('.checkbox-container input[type="checkbox"]:checked').each(function () {
		selectedAggregators.push($(this).val());
	});

	var aggregatorsString = selectedAggregators.join('&');
	var selectedPeriod = $('#period .selected-option-drivers').data('value');
	var startDate = $("#start_report_driver").val();
	var endDate = $("#end_report_driver").val();

	if (selectedPeriod !== "custom" && aggregatorsString === "shared") {
		$('th[data-sort="idling-mileage"]').show();
		fetchDriverEfficiencyData(selectedPeriod, startDate, endDate);
	} else {
		if (aggregatorsString === "shared") {
			fetchDriverEfficiencyData(selectedPeriod, startDate, endDate);
		} else {
			$('th[data-sort="idling-mileage"]').hide();
			fetchDriverFleetEfficiencyData(selectedPeriod, startDate, endDate, aggregatorsString);
		}
	}
}