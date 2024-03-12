function driverPayment(period = null, start = null, end = null, paymentStatus = null) {
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
			$(".apply-filter-button_driver").prop("disabled", false);
			var tableBody = $('.driver-table tbody');
			tableBody.empty();

			for (var i = 0; i < response.length; i++) {
				if ((paymentStatus === 'on_inspection' && response[i].status === 'Перевіряється') ||
					(paymentStatus === 'not_closed' && response[i].status === 'Очікується') ||
					(paymentStatus === 'closed' && (response[i].status === 'Виплачений' || response[i].status === 'Не сплачений'))) {

					var addButtonBonus = '<button class="add-btn-bonus" title="Додати бонус"><i class="fa fa-plus"></i></button>';
					var addButtonPenalty = '<button class="add-btn-penalty" title="Додати штраф"><i class="fa fa-plus"></i></button>';

					var confirmButton = '<button class="apply-btn" title="Відправити водію"><i class="fa fa-mobile"></i></button>';
					var arrowBtn = '<button class="arrow-btn"><i class="fa fa-arrow-left"></i></button>';
					var payByn = '<button class="pay-btn">Отримано</button>';
					var notPayByn = '<button class="not-pay-btn">Не отримано</button>';
					var dataId = response[i].id;

					var rowBonus = '<tr class="tr-driver-payments" data-id="' + dataId + '">' +
						'<td colspan="11" class="bonus-table"><table class="bonus-penalty-table"><tr class="title-bonus-penalty">' +
						'<th class="edit-bonus-penalty">Тип</th>' +
						'<th class="edit-bonus-penalty">Сума</th>' +
						'<th class="edit-bonus-penalty">Категорія</th>' +
						'<th class="edit-bonus-penalty">Автомобіль</th>' +
						(response[i].status === 'Перевіряється' ? '<th class="edit-bonus-penalty">Дії</th>' : '') + '</tr>';

					function generateRow(items, type, editClass, deleteClass) {
						var rowBon = '';
						for (var j = 0; j < items.length; j++) {
							var item = items[j];
							rowBon += '<tr class="description-bonus-penalty">';
							rowBon += '<td class="' + type + '-type" data-bonus-penalty-id="' + item.id + '">' + (type === 'bonus' ? 'Бонус' : 'Штраф') + '</td>';
							rowBon += '<td class="' + type + '-amount">' + item.amount + '</td>';
							rowBon += '<td class="' + type + '-category">' + item.category + '</td>';
							rowBon += '<td class="' + type + '-car">' + item.vehicle + '</td>';
							if (response[i].status === 'Перевіряється' && item.category !== 'Бонуси Bolt') {
								rowBon += '<td><button class="edit-' + type + '-btn" data-bonus-penalty-id="' + item.id + '" data-type="edit"><i class="fa fa-pencil-alt"></i></button> <button class="delete-bonus-penalty-btn" data-bonus-penalty-id="' + item.id + '" data-type="delete"><i class="fa fa-times"></i></button></td>';
							}
							rowBon += '</tr>';
						}
						return rowBon;
					}

					rowBonus += generateRow(response[i].bonuses_list, 'bonus', 'edit-bonus-btn', 'delete-bonus-penalty-btn');
					rowBonus += generateRow(response[i].penalties_list, 'penalty', 'edit-penalty-btn', 'delete-bonus-penalty-btn');
					rowBonus += '</table></td></tr>';
					var row = $('<tr class="tr-driver-payments">');
					row.attr('data-id', response[i].id);
					row.append('<td>' + response[i].report_from + ' <br> ' + response[i].report_to + '</td>');
					row.append('<td class="driver-name cell-with-triangle" title="Натиснути для огляду бонусів та штрафів">' + response[i].full_name + ' <i class="fa fa-caret-down"></i></td>');
					row.append('<td>' + response[i].kasa + '</td>');
					row.append('<td>' + response[i].cash + '</td>');
					row.append('<td>' + response[i].rent + '</td>');
					if (response[i].status === 'Перевіряється') {
						row.append('<td>' + '<div style="display: flex;justify-content: space-evenly; align-items: center;">' + response[i].bonuses + addButtonBonus + '</div>' + '</td>');
						row.append('<td>' + '<div style="display: flex;justify-content: space-evenly; align-items: center;">' + response[i].penalties + addButtonPenalty + '</div>' + '</td>');
						row.append('<td class="driver-rate" title="Натиснути для зміни відсотка"><div style="display: flex; justify-content: space-evenly; align-items: center;"><span class="rate-payment">' + response[i].rate + '</span><input type="text" class="driver-rate-input" placeholder="100" style="display: none;"><i class="fa fa-check check-icon"></i><i class="fa fa-pencil-alt pencil-icon"></i></div></td>');
					} else {
						row.append('<td>' + '<div style="display: flex;justify-content: space-evenly; align-items: center;">' + response[i].bonuses + '</div>' + '</td>');
						row.append('<td>' + '<div style="display: flex;justify-content: space-evenly; align-items: center;">' + response[i].penalties + '</div>' + '</td>');
						row.append('<td><div style="display: flex;justify-content: space-evenly; align-items: center;"><span class="rate-payment" >' + response[i].rate + ' </span></div></td>')

					}
					row.append('<td class="payment-earning">' + response[i].earning + '</td>');
					row.append('<td>' + response[i].status + '</td>');
					var showAllButton = $('.send-all-button');
					showAllButton.hide(0);
					if (response[i].status === 'Очікується') {
						row.append('<td><div class="box-btn-upd">' + arrowBtn + '<div class="btnPay">' + payByn + notPayByn + '</div></div></td>');
						if (response[i].earning > 0) {
							row.find('.not-pay-btn').remove();
							row.find('.pay-btn').text('Сплатити');
						}
					}
					if (response[i].status === 'Перевіряється') {
						showAllButton.show(0);
						row.append('<td>' + confirmButton + '</td>');
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

$(document).on('click', function (event) {
	if (!$(event.target).closest('.driver-rate').length) {
		$('.driver-rate-input').hide();
		$('.rate-payment').show();
		$('.pencil-icon').show();
		$('.check-icon').hide();
	}
});

$(document).ready(function () {
	var itemId, actionType, itemType;

	$(this).on('click', '.driver-table tbody .driver-name', function () {
		var row = $(this).closest('tr');
		var bonusTable = row.next().find('.bonus-table');
		bonusTable.toggle();
		return false;
	});

	$(this).on('click', '.bonus-table .delete-bonus-penalty-btn', function () {
		var $button = $(this);
		if ($button.hasClass('disabled')) {
			return;
		}
		$button.addClass('disabled');
		itemId = $(this).data('bonus-penalty-id');
		dataToSend = {
			action: "delete_bonus_penalty",
			id: itemId,
			csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
		};
		$.ajax({
			url: ajaxPostUrl,
			type: 'POST',
			data: dataToSend,
			dataType: 'json',
			success: function (response) {
				driverPayment(null, null, null, paymentStatus = "on_inspection");
			}
		});
	});

	$(this).on('click', '.bonus-table .edit-bonus-btn, .bonus-table .edit-penalty-btn', function () {
		itemId = $(this).data('bonus-penalty-id');
		paymentId = $(this).closest('.tr-driver-payments').data('id');
		if ($(this).hasClass('edit-bonus-btn')) {
			itemType = 'bonus';
		} else if ($(this).hasClass('edit-penalty-btn')) {
			itemType = 'penalty';
		};
		openForm(paymentId=paymentId, bonusId = itemId, itemType, driverId = null);
		$('#modal-add-bonus').show();
	});

	driverPayment(null, null, null, paymentStatus = "on_inspection");
	var clickedDate = sessionStorage.getItem('clickedDate');
	var clickedId = sessionStorage.getItem('clickedId');
	if (clickedDate && clickedId) {
		var $targetElement = $('.tr-driver-payments[data-id="' + clickedId + '"]');
		$targetElement.find('.bonus-table').show();
	}
	$('input[name="payment-status"]').change(function () {
		if ($(this).val() === 'closed') {
			driverPayment(period = 'yesterday', null, null, paymentStatus = $(this).val());
			$('.filter-driver-payments').css('display', 'flex');
		} else {
			driverPayment(null, null, null, paymentStatus = $(this).val());
			$('.filter-driver-payments').hide();
			$('#datePickerDriver').hide();
		}
	});

	$(this).on("input", ".driver-rate-input", function () {
		var inputValue = $(this).val();
		var sanitizedValue = inputValue.replace(/[^0-9]/g, '');

		var integerValue = parseInt(sanitizedValue, 10);

		if (isNaN(integerValue) || integerValue < 0) {
			integerValue = 0;
		}
		sanitizedValue = Math.min(Math.max(integerValue, 0), 100);
		$(this).val(sanitizedValue);
	});

	$(this).on('click', '.check-icon', function () {
		var $rateInput = $(this).siblings('.driver-rate-input');
		var rate = 0;

		if ($rateInput.val() !== '') {
			rate = $rateInput.val();
		}

		var $row = $(this).closest('tr');
		var payment_id = $row.data('id');
		var earning = $row.find('td.payment-earning');
		var rateText = $row.find('.rate-payment');

		$.ajax({
			url: ajaxPostUrl,
			type: 'POST',
			data: {
				rate: rate,
				payment: payment_id,
				action: 'calculate-payments',
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
			},
			success: function (response) {
				earning.text(response.earning);
				rateText.text(response.rate);
				$rateInput.hide();
				rateText.show();
			},
			error: function (error) {
				console.error("Error:", error);
			}
		});
	});

	$(this).on("keypress", ".driver-rate-input", function (e) {
		if (e.which === 13) {
			$(this).siblings('.check-icon').click();
			$(this).blur();
		}
	});

	function initializeCustomPaymentsSelect(customSelect, selectedOption, optionsList, iconDown, datePicker) {
		iconDown.click(function () {
			customSelect.toggleClass("active");
		});

		selectedOption.click(function () {
			customSelect.toggleClass("active");
		});

		optionsList.on("click", "li", function () {
			const clickedValue = $(this).data("value");
			selectedOption.text($(this).text());
			customSelect.removeClass("active");

			if (clickedValue !== "custom") {
				driverPayment(clickedValue, null, null, paymentStatus = "closed");
			} else {
				datePicker.css("display", "block");
			}

			if (clickedValue === "custom") {
				datePicker.css("display", "block");
			} else {
				datePicker.css("display", "none");
			}
		});
	}

	const customSelectDriver = $(".custom-select-payments");
	const selectedOptionDriver = customSelectDriver.find(".selected-option-payments");
	const optionsListDriver = customSelectDriver.find(".options-payments");
	const iconDownDriver = customSelectDriver.find(".fas.fa-angle-down");
	const datePickerDriver = $("#datePickerPayments");

	initializeCustomPaymentsSelect(customSelectDriver, selectedOptionDriver, optionsListDriver, iconDownDriver, datePickerDriver);

	const driverTableTbody = $(".driver-table tbody");

	driverTableTbody.on('click', '.driver-rate', function (event) {
		console.log('click driver-rate');
		var $rateContainer = $(this);
		var $rateText = $rateContainer.find('.rate-payment');
		var $rateInput = $rateContainer.find('.driver-rate-input');
		var $pencilIcon = $rateContainer.find('.pencil-icon');
		var $checkIcon = $rateContainer.find('.check-icon');

		$rateText.toggle();
		$rateInput.toggle();
		$pencilIcon.toggle();
		$checkIcon.toggle();

		if ($rateInput.is(":visible")) {
			$rateInput.focus();
		}
	});

	driverTableTbody.on('click', '.add-btn-bonus, .add-btn-penalty', function () {
		var id = $(this).closest('tr').data('id');
		if ($(this).hasClass('add-btn-bonus')) {
			openForm(id, null, 'bonus', null);
		} else {
			openForm(id, null, 'penalty', null);
		}
	});


	driverTableTbody.on('click', '.apply-btn', function () {
		var id = $(this).closest('tr').data('id');
		$(this).closest('tr').find('.edit-btn, .apply-btn').hide();
		$(this).closest('tr').find('.box-btn-upd').css('display', 'flex');

		updStatusDriverPayments(id, status = 'pending', paymentStatus = "on_inspection");
	});

	driverTableTbody.on('click', '.arrow-btn', function () {
		var id = $(this).closest('tr').data('id');
		$(this).closest('tr').find('.edit-btn, .apply-btn').show()
		$(this).closest('tr').find('.box-btn-upd').hide();

		updStatusDriverPayments(id, status = 'checking', paymentStatus = "not_closed");
	});

	driverTableTbody.on('click', '.pay-btn, .not-pay-btn', function () {
		var id = $(this).closest('tr').data('id');
		if ($(this).hasClass('pay-btn')) {
			var status = 'completed';
		} else {
			var status = 'failed';
		}
		$(".confirmation-box h2").text("Ви впевнені, що хочете закрити платіж ?");
		$(".confirmation-update-database").show();
		$("#confirmation-btn-on").data('id', id).data('status', status);
	});

	$("#confirmation-btn-on").click(function () {
		var id = $(this).data('id');
		var status = $(this).data('status');
		updStatusDriverPayments(id, status, paymentStatus = "not_closed");
		$(".confirmation-update-database").hide();
	});

	$('.send-all-button').on('click', function () {
		var allDataIds = [];
		$('tr[data-id]').each(function () {
			var dataId = $(this).attr('data-id');
			allDataIds.push(dataId);
		});
		updStatusDriverPayments(null, status = 'pending', paymentStatus = "on_inspection", all = allDataIds);
	});

	$(this).on('click', '.driver-table tbody .driver-name', function () {
		var date = $(this).closest('.tr-driver-payments').find('td:first-child').text().trim();
		var id = $(this).closest('.tr-driver-payments').data('id');

		var clickedDate = sessionStorage.getItem('clickedDate');
		var clickedId = sessionStorage.getItem('clickedId');
		if (clickedDate === date && parseInt(clickedId) === id) {
			sessionStorage.removeItem('clickedDate');
			sessionStorage.removeItem('clickedId');
		} else {
			sessionStorage.setItem('clickedDate', date);
			sessionStorage.setItem('clickedId', id);
		}
	});
});

function updStatusDriverPayments(id, status, paymentStatus, all = null) {
	if (all !== null) {
		var allId = all.join(',');
	}
	$.ajax({
		url: ajaxPostUrl,
		type: 'POST',
		data: {
			id: id,
			action: 'upd-status-payment',
			status: status,
			allId: allId,
			csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
		},
		dataType: 'json',
		success: function (response) {
			driverPayment(null, null, null, paymentStatus = paymentStatus);
		}
	});
}