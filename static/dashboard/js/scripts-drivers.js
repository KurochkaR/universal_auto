$(document).ready(function () {
    var selectedOption = sessionStorage.getItem('selectedOption');
	if (selectedOption && window.location.pathname === '/dashboard/drivers/') {
		$('input[name="driver-info"][value="' + selectedOption + '"]').prop('checked', true);
            switcherDriverPage(selectedOption)
	}

	$('#DriverBtnContainers').on('click', function () {
		$('input[name="driver-info"][value="driver-list"]').prop('checked', true);
		sessionStorage.setItem('selectedOption', 'driver-list');
	});

	$('input[name="driver-info"]').change(function () {
		var selectedValue = $(this).val();
		sessionStorage.setItem('selectedOption', selectedValue);
        switcherDriverPage(selectedValue)
	});

	$(this).on('click', '.driver-name-info', function () {
		var driverId = $(this).data('id');
		window.location.href = "/dashboard/driver/" + driverId;
	});
});

function loadDashboardContent(action, callback) {
    $.ajax({
        url: ajaxGetUrl,
        type: 'GET',
		data: {
            action: action,
        },
        success: function(response) {
            // Update the specific portion of the page with the fetched content
            $('.info-driver').html(response.data);
            if (callback && typeof callback === "function") {
                // Call the callback function
                callback();
            }
        },
        error: function(xhr, status, error) {
            // Handle errors
            console.error(error);
        }
    });
}

function switcherDriverPage(selectedOption) {
    switch (selectedOption) {
        case 'driver-list':
            loadDashboardContent("render_drivers_list", function() {
            getDriversList()
            });
            break;
        case 'driver-payments':
            paymentStatus = sessionStorage.getItem('paymentStatus') || "on_inspection"
            period = paymentStatus === 'closed' ? 'today': null
            loadDashboardContent("render_drivers_payments", function() {
            $('input[name="payment-status"][value="' + paymentStatus + '"]').prop('checked', true);
            driverPayment(period, null, null, paymentStatus);
            });
            break;
        case 'driver-efficiency':
            loadDashboardContent("render_drivers_efficiency", function() {
            $('#period .selected-option').data('value', 'today')
            fetchDriverEfficiencyData('today', null, null);
            });
            break;
        default:
            break;
    }
}

function getDriversList() {
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

function driverPayment(period = null, start = null, end = null, paymentStatus = null) {
	const url = period === null ? `/api/driver_payments/${paymentStatus}/` :
		period === 'custom' ? `/api/driver_payments/${start}&${end}/` :
			`/api/driver_payments/${period}/`;

	$.ajax({
		url: url,
		type: 'GET',
		dataType: 'json',
		success: function (response) {
            var statusTh = $('th[data-sort="status"]');

            if (paymentStatus === 'closed') {
                $('th[data-sort="button"]').hide();
                statusTh.text("Статус виплати");
            } else if (paymentStatus === 'not_closed') {
                statusTh.text("Дії");
                $('th[data-sort="button"]').hide();
                $('#datePicker').hide();
                $('.filter').hide();
            } else {
                $('#datePicker').hide();
                $('.filter').hide();
            }
			var tableBody = $('.driver-table tbody');
			tableBody.empty();
			var addButtonBonus = '<button class="add-btn-bonus" title="Додати бонус"><i class="fa fa-plus"></i></button>';
			var addButtonPenalty = '<button class="add-btn-penalty" title="Додати штраф"><i class="fa fa-plus"></i></button>';
			var incorrectBtn = '<button class="incorrect-payment-btn">Перерахувати виплату</button>';
			var calculateBtn = '<button class="calculate-payment-btn">Розрахувати на зараз</button>';
			var confirmButton = '<button class="apply-btn" title="Відправити водію"></button>';
			var arrowBtn = '<button class="arrow-btn">Повернути на перевірку</button>';
			var payBtn = '<button class="pay-btn">Отримано</button>';
			var notPayBtn = '<button class="not-pay-btn">Не отримано</button>';


			for (const payment of response) {
				const {
					id: dataId, status, payment_type, report_from, report_to, bonuses_list,
					penalties_list, full_name, kasa, cash, rent, rate, earning, bonuses, penalties, bolt_screen
				} = payment;
				if ((paymentStatus === 'on_inspection' && (status === 'Перевіряється' || status === 'Потребує поправок')) ||
					(paymentStatus === 'not_closed' && status === 'Очікується') ||
					(paymentStatus === 'closed' && (status === 'Виплачений' || status === 'Не сплачений'))) {
                    let bonusMainClass = status === 'Потребує поправок' ? '"tr-driver-payments incorrect"': "tr-driver-payments"

					var responseDate = moment(report_to, "DD.MM.YYYY HH:mm");
					var rowBonus = '<tr class=' + bonusMainClass + ' data-id="' + dataId + '">' +
						'<td colspan="11" class="bonus-table"><table class="bonus-penalty-table"><tr class="title-bonus-penalty">' +
						'<th class="edit-bonus-penalty">Тип</th>' +
						'<th class="edit-bonus-penalty">Сума</th>' +
						'<th class="edit-bonus-penalty">Категорія</th>' +
						'<th class="edit-bonus-penalty">Автомобіль</th>' +
						(status === 'Перевіряється' ? '<th class="edit-bonus-penalty">Дії</th>' : '') + '</tr>';

					function generateRow(items, type) {
						var rowBon = '';
						for (const item of items) {
							rowBon += '<tr class="description-bonus-penalty">';
							rowBon += '<td class="' + type + '-type" data-bonus-penalty-id="' + item.id + '">' + (type === 'bonus' ? 'Бонус' : 'Штраф') + '</td>';
							rowBon += '<td class="' + type + '-amount">' + item.amount + '</td>';
							rowBon += '<td class="' + type + '-category">' + item.category + '</td>';
							rowBon += '<td class="' + type + '-car">' + item.vehicle + '</td>';
							if (status === 'Перевіряється' && item.category !== 'Бонуси Bolt' && item.category !== 'Борг по виплаті') {
								rowBon += '<td><button class="edit-' + type + '-btn" data-bonus-penalty-id="' + item.id + '" data-type="edit"><i class="fa fa-pencil-alt"></i></button> <button class="delete-bonus-penalty-btn" data-bonus-penalty-id="' + item.id + '" data-type="delete"><i class="fa fa-times"></i></button></td>';
							}
							rowBon += '</tr>';
						}
						return rowBon;
					}

					rowBonus += generateRow(bonuses_list, 'bonus', 'edit-bonus-btn', 'delete-bonus-penalty-btn');
					rowBonus += generateRow(penalties_list, 'penalty', 'edit-penalty-btn', 'delete-bonus-penalty-btn');
					rowBonus += '</table></td></tr>';
					var row = $('<tr class="tr-driver-payments">');
					row.attr('data-id', dataId);
					row.append('<td>' + report_from + ' <br> ' + report_to + '</td>');
					row.append('<td class="driver-name cell-with-triangle" title="Натиснути для огляду бонусів та штрафів">' + full_name + ' <i class="fa fa-caret-down"></i></td>');
					row.append('<td>' + kasa + '</td>');
					row.append('<td>' + cash + '</td>');
					row.append('<td>' + rent + '</td>');
					if (status === 'Перевіряється') {


						row.append('<td>' + '<div style="display: flex;justify-content: space-evenly; align-items: center;">' + bonuses + addButtonBonus + '</div>' + '</td>');
						row.append('<td>' + '<div style="display: flex;justify-content: space-evenly; align-items: center;">' + penalties + addButtonPenalty + '</div>' + '</td>');
						row.append('<td class="driver-rate" title="Натиснути для зміни відсотка"><div style="display: flex; justify-content: space-evenly; align-items: center;"><span class="rate-payment">' + rate + '</span><input type="text" class="driver-rate-input" placeholder="100" style="display: none;"><i class="fa fa-check check-icon"></i><i class="fa fa-pencil-alt pencil-icon"></i></div></td>');
					} else {
						row.append('<td>' + '<div class="no-pencil-rate" style="display: flex;justify-content: space-evenly; align-items: center;">' + bonuses + '</div>' + '</td>');
						row.append('<td>' + '<div class="no-pencil-rate" style="display: flex;justify-content: space-evenly; align-items: center;">' + penalties + '</div>' + '</td>');
						row.append('<td><div style="display: flex;justify-content: space-evenly; align-items: center;"><span class="rate-payment no-pencil-rate" >' + rate + ' </span></div></td>')

					}
					row.append('<td class="payment-earning">' + earning + '</td>');
					var showAllButton = $('.send-all-button');
					showAllButton.hide(0);
					if (status === 'Очікується') {
						row.append('<td><div class="box-btn-upd">' + arrowBtn + payBtn + notPayBtn + '</div></td>');
						if (earning > 0) {
							row.find('.not-pay-btn').remove();
							row.find('.pay-btn').text('Сплатити');

						}
					}
					if (status === 'Перевіряється') {
						showAllButton.show(0);
						statusTh.text("Перерахування виплат");
						$('th[data-sort="button"]').show();
						if (payment_type === "DAY" && moment().startOf('day').isSame(responseDate.startOf('day'))) {
							row.append('<td class="calc-buttons">' + calculateBtn + '</td>')
						} else {
							row.append('<td></td>')
						}
						row.append('<td class="send-buttons">' + confirmButton + '</td>');
					}
					if (status === 'Потребує поправок') {
						row.addClass('incorrect');
						showAllButton.show(0);
						if (payment_type === "DAY" && moment().startOf('day').isSame(responseDate.startOf('day'))) {
							row.append('<td class="calc-buttons">' + calculateBtn + incorrectBtn +'</td>');

							if (bolt_screen) {
							    var correctButton = '<a class="correct-bolt-btn" href="' + bolt_screen + '" data-lightbox="payments"><i class="fa fa-camera"></i></a>'
							    row.append('<td class="send-buttons">'+ correctButton + '</td>')
							} else {
						        row.append('<td></td>') ;
						        }
						} else {
							row.append('<td></td>');
							row.append('<td></td>')
						}
					}

					if (status === 'Виплачений' || status === 'Не сплачений') {
						row.append('<td>' + status + '</td>');
					}

					tableBody.append(row);
					tableBody.append(rowBonus);
				}
			}
			if (clickedDate && clickedId) {
				var $targetElement = $('.tr-driver-payments[data-id="' + clickedId + '"]');
				$targetElement.find('.bonus-table').show();
			}
		}

	});
	var clickedDate = sessionStorage.getItem('clickedDate');
	var clickedId = sessionStorage.getItem('clickedId');
}

function fetchDriverEfficiencyData(period, start = null, end = null) {
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
			$(".aggregator").hide();
			let table = $('.info-driver table');
			let startDate = data[0]['start'];
			let endDate = data[0]['end'];
			table.find('tr:gt(0)').remove();
			if (data[0]['drivers_efficiency'].length !== 0) {
				data[0]['drivers_efficiency'].forEach(function (item) {
					let row = $('<tr></tr>');
					let formattedTime = formatTime(item.road_time);
					let time = formattedTime
					let rentDistance = isNaN(item.rent_distance) ? 0 : item.rent_distance
					row.append('<td class="driver">' + item.full_name + '</td>');
					row.append('<td class="kasa">' + Math.round(item.total_kasa) + '</td>');
					row.append('<td class="order_accepted">' + Math.round(item.total_orders_accepted) + '</td>');
					row.append('<td class="order_rejected">' + item.total_orders_rejected + '</td>');
					row.append('<td class="price">' + Math.round(item.average_price) + '</td>');
					row.append('<td class="mileage">' + Math.round(item.mileage) + '</td>');
					row.append('<td class="idling-mileage">' + Math.round(rentDistance) + '</td>');
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
					driverInfo.append('<p>' + gettext("Холостий пробіг, км: ") + Math.round(driver.rent_distance) + '</p>');
					driverInfo.append('<p>' + gettext("Ефективність, грн/км: ") + driver.efficiency + '</p>');
					driverInfo.append('<p>' + gettext("Час в дорозі: ") + formatTime(driver.road_time) + '</p>');

					driverBlock.append(driverName);
					driverBlock.append(driverInfo);

					// Add the driver block to the container
					$('.driver-container').append(driverBlock);
				});
			}
			if (startDate === endDate) {
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


function fetchDriverFleetEfficiencyData(period, aggregators, start = null, end = null) {
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

			if (startDate === endDate) {
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
