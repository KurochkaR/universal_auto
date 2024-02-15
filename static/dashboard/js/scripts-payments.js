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

					var rowBonus = '<tr class="tr-driver-payments"><td colspan="11" class="bonus-table"><table class="bonus-penalty-table"><tr class="title-bonus-penalty"><th class="edit-bonus-penalty">Тип</th><th class="edit-bonus-penalty">Сума</th><th class="edit-bonus-penalty">Опис</th>' + (response[i].status === 'Перевіряється' ? '<th class="edit-bonus-penalty">Дії</th>' : '') + '</tr>';

					function generateRow(items, type, editClass, deleteClass) {
						var rowBon = '';
						for (var j = 0; j < items.length; j++) {
							var item = items[j];
							var desc = item.description ? item.description : "";
							rowBon += '<tr class="description-bonus-penalty">';
							rowBon += '<td class="' + type + '-type" data-bonus-penalty-id="' + item.id + '">' + (type === 'bonus' ? 'Бонус' : 'Штраф') + '</td>';
							rowBon += '<td class="' + type +'-amount">' + item.amount + '</td>';
							rowBon += '<td class="' + type +'-description">' + desc + '</td>';
							if (response[i].status === 'Перевіряється') {
								rowBon += '<td><button class="edit-' + type + '-btn" data-bonus-penalty-id="' + item.id + '" data-type="edit"><i class="fa fa-pencil-alt"></i></button> <button class="delete-bonus-penalty-btn" data-bonus-penalty-id="' + item.id + '" data-type="delete"><i class="fa fa-times"></i></button></td>';
							}
							rowBon += '</tr>';
						}
						return rowBon;
					}

					rowBonus += generateRow(response[i].bonuses_list, 'bonus', 'edit-bonus-btn', 'delete-bonus-penalty-btn');
					rowBonus += generateRow(response[i].penalties_list, 'penalty', 'edit-penalty-btn', 'delete-bonus-penalty-btn');
					rowBonus += '</table></td></tr>';
					var salary = response[i].salary;
					if (response[i].salary <= 0) {
						salary = "0.00";
					}
					var row = $('<tr class="tr-driver-payments">');
					row.attr('data-id', response[i].id);
					row.append('<td>' + response[i].report_from + ' <br> ' + response[i].report_to + '</td>');
					row.append('<td class="driver-name cell-with-triangle" title="Натиснути для огляду бонусів та штрафів">' + response[i].full_name + ' <i class="fa fa-caret-down"></i></td>');
					row.append('<td>' + response[i].kasa + '</td>');
					row.append('<td>' + response[i].cash + '</td>');
					row.append('<td>' + response[i].rent + '</td>');
					if (response[i].status === 'Перевіряється') {
						row.append('<td>' + '<div style="display: flex;justify-content: space-evenly; align-items: center;">' + response[i].bonuses  + addButtonBonus + '</div>' + '</td>');
						row.append('<td>' + '<div style="display: flex;justify-content: space-evenly; align-items: center;">' + response[i].penalties + addButtonPenalty + '</div>' + '</td>');
					} else {
						row.append('<td>' + '<div style="display: flex;justify-content: space-evenly; align-items: center;">' + response[i].bonuses + '</div>' + '</td>');
						row.append('<td>' + '<div style="display: flex;justify-content: space-evenly; align-items: center;">' + response[i].penalties + '</div>' + '</td>');
					}
					row.append('<td>' + response[i].earning + '</td>');
					row.append('<td>' + salary + '</td>');
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
						row.append('<td>' + confirmButton +'</td>');
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

	$(this).on('click', '.bonus-table .delete-bonus-penalty-btn', function () {
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
				driverPayment(null, null, null, paymentStatus="on_inspection");
			}
		});
	});

	$(this).on('click', '.bonus-table .edit-bonus-btn, .bonus-table .edit-penalty-btn', function () {
	    itemId = $(this).data('bonus-penalty-id');
		if ($(this).hasClass('edit-bonus-btn')) {
			itemType = 'bonus';
		} else if ($(this).hasClass('edit-penalty-btn')){
			itemType = 'penalty';
		}
		openForm(paymentId=null, bonusId=itemId, itemType, driverId=null);
		$('#modal-add-bonus').data('bonus-penalty-id', itemId);
		$('#modal-add-bonus').show();
	});

	driverPayment(null, null, null, paymentStatus="on_inspection");

	$('input[name="payment-status"]').change(function() {
    if ($(this).val() === 'closed') {
      driverPayment(period='yesterday', null, null, paymentStatus=$(this).val());
      $('.filter-driver-payments').css('display', 'flex');
    } else {
      driverPayment(null, null, null, paymentStatus=$(this).val());
      $('.filter-driver-payments').hide();
      $('#datePickerDriver').hide();
    }
  });

  function initializeCustomPaymentsSelect(customSelect, selectedOption, optionsList, iconDown, datePicker) {
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

	const customSelectDriver = $(".custom-select-payments");
	const selectedOptionDriver = customSelectDriver.find(".selected-option-payments");
	const optionsListDriver = customSelectDriver.find(".options-payments");
	const iconDownDriver = customSelectDriver.find(".fas.fa-angle-down");
	const datePickerDriver = $("#datePickerPayments");

	initializeCustomPaymentsSelect(customSelectDriver, selectedOptionDriver, optionsListDriver, iconDownDriver, datePickerDriver);

	$('.driver-table tbody').on('click', '.add-btn-bonus, .add-btn-penalty', function () {
		var id = $(this).closest('tr').data('id');
		if ($(this).hasClass('add-btn-bonus')){
		    openForm(id, null, 'bonus', null);
		} else {
		    openForm(id, null, 'penalty', null);
		}
	});
	$(this).on('change', '#bonus-category', function(){
	if ($(this).val() === 'add_new_category'){
		$('.new-category-field').css('display', 'flex')
	} else {
		$('.new-category-field').hide()
	}
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

	$('.driver-table tbody').on('click', '.pay-btn, .not-pay-btn', function () {
    var id = $(this).closest('tr').data('id');
    if ($(this).hasClass('pay-btn')){
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