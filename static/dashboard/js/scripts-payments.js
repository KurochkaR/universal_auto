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

					var editButton = '<button class="edit-btn" title="Редагувати"><i class="fa fa-pencil-alt"></i></button>';
					var confirmButton = '<button class="apply-btn" title="Відправити водію"><i class="fa fa-mobile"></i></button>';
					var arrowBtn = '<button class="arrow-btn"><i class="fa fa-arrow-left"></i></button>';
					var payByn = '<button class="pay-btn">Отримано</button>';
					var notPayByn = '<button class="not-pay-btn">Не отримано</button>';

					var rowBonus = '<tr><td colspan="10" class="bonus-table"><table><tr><th>Тип</th><th>Сума</th><th>Опис</th>' + (response[i].status === 'Перевіряється' ? '<th>Дії</th>' : '') + '</tr>';

					function generateRow(items, type, editClass, deleteClass) {
						var rowBon = '';
						for (var j = 0; j < items.length; j++) {
							var item = items[j];
							rowBon += '<tr>';
							rowBon += '<td class="' + type + '-type" data-' + type + '-id="' + item.id + '">' + (type === 'bonus' ? 'Бонус' : 'Штраф') + '</td>';
							rowBon += '<td class="' + type +'-amount">' + item.amount + '</td>';
							rowBon += '<td class="' + type +'-description">' + item.description + '</td>';
							if (response[i].status === 'Перевіряється') {
								rowBon += '<td><button class="edit-' + type + '-btn" data-' + type + '-id="' + item.id + '" data-type="edit"><i class="fa fa-pencil-alt"></i></button> <button class="delete-' + type + '-btn" data-' + type + '-id="' + item.id + '" data-type="delete"><i class="fa fa-times"></i></button></td>';
							}
							rowBon += '</tr>';
						}
						return rowBon;
					}

					rowBonus += generateRow(response[i].bonuses_list, 'bonus', 'edit-bonus-btn', 'delete-bonus-btn');
					rowBonus += generateRow(response[i].penalties_list, 'penalty', 'edit-penalty-btn', 'delete-penalty-btn');
					rowBonus += '</table></td></tr>';

					var row = $('<tr>');
					row.attr('data-id', response[i].id);
					row.append('<td>' + response[i].report_from + ' - ' + response[i].report_to + '</td>');
					row.append('<td class="driver-name cell-with-triangle">' + response[i].full_name + ' <i class="fa fa-caret-down"></i></td>');
					row.append('<td>' + response[i].kasa + '</td>');
					row.append('<td>' + response[i].cash + '</td>');
					row.append('<td>' + response[i].rent + '</td>');
					row.append('<td>' + response[i].bonuses + '</td>');
					row.append('<td>' + response[i].penalties + '</td>');
					row.append('<td>' + response[i].earning + '</td>');
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
						row.append('<td>' + editButton + confirmButton +'</td>');
					}

					tableBody.append(row);
					tableBody.append(rowBonus);
				}
			}
		}
	});
}

$(document).ready(function () {

	var itemId, actionType, itemType;

	$(this).on('click', '.driver-table tbody .driver-name', function () {
		var row = $(this).closest('tr');
		var bonusTable = row.next().find('.bonus-table');
		bonusTable.toggle();
		return false;
	});

	$(this).on('click', '.bonus-table .edit-bonus-btn, .bonus-table .delete-bonus-btn, .bonus-table .edit-penalty-btn, .bonus-table .delete-penalty-btn', function () {
		if ($(this).hasClass('edit-bonus-btn') || $(this).hasClass('edit-penalty-btn')) {
			actionType = 'edit';
			itemAmount = $(this).closest('tr').find('.bonus-amount').text();
			itemDescription = $(this).closest('tr').find('.bonus-description').text();
		} else if ($(this).hasClass('delete-bonus-btn') || $(this).hasClass('delete-penalty-btn')) {
			actionType = 'delete';
		}

		if ($(this).hasClass('edit-bonus-btn') || $(this).hasClass('delete-bonus-btn')) {
			itemId = $(this).data('bonus-id');
			itemType = 'bonus';
		} else if ($(this).hasClass('edit-penalty-btn') || $(this).hasClass('delete-penalty-btn')) {
			itemId = $(this).data('penalty-id');
			itemType = 'penalty';
			itemAmount = $(this).closest('tr').find('.penalty-amount').text();
      itemDescription = $(this).closest('tr').find('.penalty-description').text();
		}

		itemId = itemId;
    actionType = actionType;
    itemType = itemType;

		if (actionType === 'delete') {
			processAction(actionType, itemId, itemType, null, null);
		} else {
		$('#modal-upd-bonus').show();
		$('#modal-upd-bonus .modal-content').attr('data-id', itemId);
		$('#modal-upd-bonus .modal-content').attr('data-type', itemType);
		$('#modal-upd-bonus .modal-content').attr('data-action', actionType);
		$('#modal-upd-bonus').find('.bonus-amount').val(itemAmount);
		$('#modal-upd-bonus').find('.bonus-description').val(itemDescription);
		}
	});

	$(this).on('click', '#edit-button-bonus-penalty', function () {
  	var amount = $('#modal-upd-bonus').find('.bonus-amount').val();
  	var description = $('#modal-upd-bonus').find('.bonus-description').val();
		var dataToSend = {
			action: "upd_delete_bonus_penalty",
			id: itemId,
			type: itemType,
			action_type: actionType,
			amount: amount,
			description: description,
			csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
		};

		updBonusPenalty(dataToSend);
	});

	driverPayment(null, null, null, paymentStatus="on_inspection");

	$('input[name="payment-status"]').change(function() {
    if ($(this).val() === 'closed') {
      driverPayment(period='current_quarter', null, null, paymentStatus=$(this).val());
      $('.filter-driver-payments').css('display', 'flex');
    } else {
      driverPayment(null, null, null, paymentStatus=$(this).val());
      $('.filter-driver-payments').hide();
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

			if (clickedValue !== "custom") {
				driverPayment(clickedValue, null, null, paymentStatus="closed");
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

	const customSelectDriver = $(".custom-select-drivers");
	const selectedOptionDriver = customSelectDriver.find(".selected-option-drivers");
	const optionsListDriver = customSelectDriver.find(".options-drivers");
	const iconDownDriver = customSelectDriver.find(".fas.fa-angle-down");
	const datePickerDriver = $("#datePickerDriver");

	initializeCustomSelect(customSelectDriver, selectedOptionDriver, optionsListDriver, iconDownDriver, datePickerDriver);

	$('.shift-close-btn').off('click').on('click', function (e) {
  	e.preventDefault();
		$('#modal-upd-payments').hide();
		$('#modal-upd-bonus').hide();
	});

	$('.driver-table tbody').on('click', '.edit-btn', function () {
		$('#bonus-amount').val('');
    $('#bonus-description').val('');
    $('#penalty-amount').val('');
    $('#penalty-description').val('');
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
				driverPayment(null, null, null, paymentStatus="on_inspection");
			}
		});
	});

	$('.driver-table tbody').on('click', '.apply-btn', function () {
    var id = $(this).closest('tr').data('id');
    $(this).closest('tr').find('.edit-btn, .apply-btn').hide();
    $(this).closest('tr').find('.box-btn-upd').css('display', 'flex');

    updStatusDriverPayments(id, status='pending', paymentStatus="on_inspection");
	});

	$('.driver-table tbody').on('click', '.arrow-btn', function () {
    var id = $(this).closest('tr').data('id');
    $(this).closest('tr').find('.edit-btn, .apply-btn').show()
    $(this).closest('tr').find('.box-btn-upd').hide();

		updStatusDriverPayments(id, status='checking', paymentStatus="not_closed");
	});

	$('.driver-table tbody').on('click', '.pay-btn', function () {
    var id = $(this).closest('tr').data('id');
    var status = 'completed';
    $(".confirmation-box h2").text("Ви впевнені, що хочете закрити платіж ?");
    $(".confirmation-update-database").show();
    $("#confirmation-btn-on").data('id', id).data('status', status);
	});


	$('.driver-table tbody').on('click', '.not-pay-btn', function () {
		var id = $(this).closest('tr').data('id');
		var status = 'failed';
		$(".confirmation-box h2").text("Ви впевнені, що хочете закрити платіж ?");
		$(".confirmation-update-database").show();
		$("#confirmation-btn-on").data('id', id).data('status', status);
	});

	$("#confirmation-btn-on").click(function () {
    var id = $(this).data('id');
    var status = $(this).data('status');
    updStatusDriverPayments(id, status, paymentStatus="not_closed");
    $(".confirmation-update-database").hide();
	});

	$('.send-all-button').on('click', function () {
    var allDataIds = [];
    $('tr[data-id]').each(function () {
      var dataId = $(this).attr('data-id');
      allDataIds.push(dataId);
    });
		updStatusDriverPayments(null, status='pending', paymentStatus="on_inspection", all=allDataIds);
  });

	$('#bonus-amount, #penalty-amount, #upd-bonus-amount').on('input', function () {
		var inputValue = $(this).val();
		$(this).val(inputValue.replace(/[^0-9.]/g, ''));

		if (!/^[\d.]*$/.test($(this).val())) {
			$(this).addClass('error');
		} else {
			$(this).removeClass('error');
		}
	});
});

function updStatusDriverPayments(id, status, paymentStatus, all=null) {
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
			driverPayment(null, null, null, paymentStatus=paymentStatus);
		}
	});
}

function updBonusPenalty(dataToSend) {
	$.ajax({
		url: ajaxPostUrl,
		type: 'POST',
		data: dataToSend,
		dataType: 'json',
		success: function (response) {
			$('#modal-upd-bonus').hide();
			driverPayment(null, null, null, paymentStatus="on_inspection");
		}
	});
}

function processAction(actionType, itemId, itemType) {
	dataToSend = {
		action: "upd_delete_bonus_penalty",
		id: itemId,
		type: itemType,
		action_type: actionType,
		csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
	};

	updBonusPenalty(dataToSend);
}