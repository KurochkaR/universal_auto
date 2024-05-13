$(document).on('click', function (event) {
	if (!$(event.target).closest('.driver-rate').length) {
		$('.driver-rate-input').hide();
		$('.rate-payment').show();
		$('.pencil-icon').show();
		$('.check-icon').hide();
	}
});

$(document).ready(function () {
	var itemId, actionType, itemType, drivers;

	$(this).on('click', '.driver-table tbody .driver-name, .correct-bolt-btn', function () {
		var row = $(this).closest('tr');
		var bonusTable = row.next().find('.bonus-table');

		bonusTable.toggleClass('expanded');
		bonusTable.toggle();
		return false;
	});

//    $(this).on('click', '.correct-bolt-btn', function () {
//		var row = $(this).closest('tr');
//		var bonusTable = row.next().find('.bonus-table');
//
//		bonusTable.toggleClass('expanded');
//		bonusTable.toggle();
//		return false;
//	});
	function populateButtons(filteredDrivers) {
		var createPaymentList = $(".create-payment-list");
		createPaymentList.empty();

		filteredDrivers.forEach(function (driver) {
			var button = $('<button>', {
				'text': driver.name,
				'data-driver-id': driver.id,
				'class': 'driver-button',
			});
			createPaymentList.append(button);
		});
	}

	$(this).on('click', '.create-payment', function () {
		$.ajax({
			url: ajaxPostUrl,
			type: 'POST',
			data: {
				action: 'payment-driver-list',
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
			},
			success: function (response) {
				drivers = response.drivers;
				if (drivers.length !== 0) {
					populateButtons(drivers);
					$("#search-driver").val("");
					$('#payment-driver-list').show();
					$('.modal-overlay').show();
					$('.create-payment').css('background', '#ec6323')
				} else {
					$("#loadingModal").show();
					$("#loader").hide();
					$("#loadingMessage").text(gettext("Сьогодні відсутні водії з денним розрахунком"));
					setTimeout(function () {
						$('#loadingModal').hide();
					}, 3000);
				}
			},
			error: function (error) {
				console.error("Error:", error);
			}
		});

	});

	$("#search-driver").on("keyup", function (e) {

		var searchText = $(this).val().toLowerCase();

		var filteredDrivers = drivers.filter(function (driver) {
			return driver.name.toLowerCase().includes(searchText);
		});

		populateButtons(filteredDrivers);

		if (e.which === 13) {
			e.preventDefault();
			$(this).blur();
		}
	});

	$(this).on('click', '.driver-button, .calculate-payment-btn', function (e) {
        e.stopPropagation();
		e.preventDefault();
		const driverId = $(this).data('driver-id');
		const paymentId = $(this).closest('tr').data('id');
		var confirmationBoxText = $(".confirmation-box h2");
        const confirmationText = $(this).hasClass('calculate-payment-btn') ?
			"Ви справді хочете розрахувати на зараз?" :
			"Ви впевнені, що хочете створити нову виплату?";
		confirmationBoxText.text(confirmationText);
		$("#confirmation-btn-on").data({
            'driver-id': driverId,
            'payment-id': paymentId
        }).addClass('confirm-yes').removeClass('confirmation-btn-on');
		$(".confirmation-update-database").show();
	});

	$(this).on('click','.confirm-yes', function () {
        var confirmationBtnOn = $("#confirmation-btn-on")
        var driverId = confirmationBtnOn.data('driver-id');
        var paymentId = confirmationBtnOn.data('payment-id');
        $(".confirmation-update-database").hide();
        confirmationBtnOn.addClass('confirmation-btn-on').removeClass('confirm-yes');
        $('#payment-driver-list').hide();
        $('.create-payment').css('background', '#a1e8b9')
        $('.modal-overlay').hide();
        $("#loadingModal").show();
        $("#loadingMessage").text(gettext("Створюється нова виплата"));
        $("#loader").show();
        var ajaxData = {
                driver_id: driverId,
                payment_id: paymentId,
                action: 'create-new-payment',
                csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
            };
        calculate_payment_ajax(ajaxData)
    });

	$(this).on('click', '.incorrect-payment-btn', function () {
		paymentId = $(this).closest('tr').data('id')
		$("#loadingModal").show();
		$("#loadingMessage").text(gettext("Перераховуємо виплату"));
		$("#loader").show();
        var ajaxData = {
                        payment_id: paymentId,
                        action: 'update_incorrect_payment',
                        csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
                        };
		calculate_payment_ajax(ajaxData)
	})

	$(this).on('click', '.bolt-confirm-button', function (e) {
		e.preventDefault();
		$("#bolt-confirmation-form").hide();
		itemId = $(this).data('payment-id');
		$("#bolt-amount, #bolt-cash").each(function () {
			var sanitizedValue = $(this).val();
			if (sanitizedValue === "" || sanitizedValue === ".") {
				sanitizedValue = "0";
			}
			$(this).val(sanitizedValue);
		});
		boltKasa = $("#bolt-amount").val();
		boltCash = $("#bolt-cash").val();
		$.ajax({
			url: ajaxPostUrl,
			type: 'POST',
			data: {
				action: "correction_bolt_payment",
				payment_id: itemId,
				bolt_kasa: boltKasa,
				bolt_cash: boltCash,
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
			},
			success: function (response) {
				$('.modal-overlay').hide();
				driverPayment(null, null, null, paymentStatus = "on_inspection");
			},
		});
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
		}
		openForm(paymentId = paymentId, bonusId = itemId, itemType, driverId = null);
		$('#modal-add-bonus').show();
	});

	var clickedDate = sessionStorage.getItem('clickedDate');
	var clickedId = sessionStorage.getItem('clickedId');
	if (clickedDate && clickedId) {
		var $targetElement = $('.tr-driver-payments[data-id="' + clickedId + '"]');
		$targetElement.find('.bonus-table').show();
	}

	$(this).on('change', 'input[name="payment-status"]', function () {
	    sessionStorage.setItem('paymentStatus', $(this).val());
		if ($(this).val() === 'closed') {
			driverPayment(period = 'today', null, null, paymentStatus = $(this).val());
			$('.filter').css('display', 'flex');
		} else {
			driverPayment(null, null, null, paymentStatus = $(this).val());
			$('.filter').hide();
			$('#datePicker').hide();
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

	$(this).on("input", "#bolt-cash, #bolt-amount", function () {
		var inputValue = $(this).val();
		var sanitizedValue = inputValue.replace(/[^\d.]/g, '');
		var dotIndex = sanitizedValue.indexOf('.');
		if (dotIndex !== -1) {
			var remainingValue = sanitizedValue.substring(dotIndex + 1);
			sanitizedValue = sanitizedValue.substring(0, dotIndex) + '.' + remainingValue.replace('.', '');
		}

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
		});
	});

	$(this).on("keypress", ".driver-rate-input", function (e) {
		if (e.which === 13) {
			$(this).siblings('.check-icon').click();
			$(this).blur();
		}
	});

    initializeCustomSelect(function(clickedValue) {
        if (sessionStorage.getItem('selectedOption') === 'driver-payments') {
            driverPayment(period = clickedValue, null, null, paymentStatus = "closed");
        }
    });

    $(this).on('click', '.apply-filter-button', function(){
        if (sessionStorage.getItem('selectedOption') === 'driver-payments') {
            applyDateRange(function(selectedPeriod, startDate, endDate) {
                driverPayment(selectedPeriod, startDate, endDate, paymentStatus = "closed");
            });
        }
    })

	$(this).on('click', '.driver-rate', function (event) {
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

	$(this).on('click', '.add-btn-bonus, .add-btn-penalty', function () {
		var id = $(this).closest('tr').data('id');
		if ($(this).hasClass('add-btn-bonus')) {
			openForm(id, null, 'bonus', null);
		} else {
			openForm(id, null, 'penalty', null);
		}
	});


	$(this).on('click', '.apply-btn', function () {
		var id = $(this).closest('tr').data('id');
		$(this).closest('tr').find('.edit-btn, .apply-btn').hide();
		$(this).closest('tr').find('.box-btn-upd').css('display', 'flex');

		updStatusDriverPayments(id, status = 'pending', paymentStatus = "on_inspection");
	});

	$(this).on('click', '.arrow-btn', function () {
		var id = $(this).closest('tr').data('id');
		$(this).closest('tr').find('.edit-btn, .apply-btn').show()
		$(this).closest('tr').find('.box-btn-upd').hide();

		updStatusDriverPayments(id, status = 'checking', paymentStatus = "not_closed");
	});

	$(this).on('click', '.pay-btn, .not-pay-btn', function (e) {
		e.stopPropagation();
		var $closestTr = $(this).closest('tr');
		var id = $closestTr.data('id');
		var $confirmationBox = $(".confirmation-box");
		var $confirmationBtnOn = $("#confirmation-btn-on");
		var $confirmationBtnOff = $("#confirmation-btn-off");
		var $confirmationInput = $(".confirmation-box input");
		var amountValue = $closestTr.find('.payment-earning').text();
		var maxValue = Math.abs(parseFloat(amountValue));
		var status, confirmationTextOn, confirmationTextOff;

		if ($(this).hasClass('pay-btn')) {
			status = 'completed';
			$confirmationBox.find("h2").text("Ви впевнені, що хочете закрити платіж ?");
			$("#confirmation-btn-on").text("Так")
			$("#confirmation-btn-off").text("Ні");
			$(".confirmation-box input").hide();
		} else {
			status = 'failed';
			confirmationTextOn = "Водій не розрахувався";
			confirmationTextOff = "Підтвердити";
			$confirmationBox.find("h2").text("Вкажіть суму яку повернув водій?");
			$confirmationInput.data('maxVal', maxValue).val(maxValue).show();
			$confirmationBtnOff.data('id', id).data('status', status).addClass('close-payment-with-debt').removeClass('confirmation-btn-off');
		}

		$confirmationBtnOn.text(confirmationTextOn).data('id', id).data('status', status).addClass('close-payment').removeClass('confirmation-btn-on');
		$confirmationBtnOff.text(confirmationTextOff);
		$(".confirmation-update-database").show();
	});

	$(document).on('click', function (event) {
		if (!$(event.target).closest('.confirmation-update-database').length) {
			$(".confirmation-update-database").hide();
			$("#confirmation-btn-on").text("Так")
			$("#confirmation-btn-off").text("Ні");
			$(".confirmation-box input").hide();
		}
	});


//	$(this).on("click", ".close-payment", function () {
//		var id = $(this).data('id');
//		var status = $(this).data('status');
//		updStatusDriverPayments(id, status, paymentStatus = "not_closed");
//		$(".confirmation-update-database").hide();
//		$(".close-payment").addClass('confirmation-btn-on').removeClass('close-payment');
//		$(".close-payment-with-debt").addClass('confirmation-btn-off').removeClass('close-payment-with-debt');
//	});

	$(this).on("input", "#amount", function () {
		validNumberInput($(this).data("maxVal"), $(this))
	});

	$(this).on("click", ".close-payment-with-debt, .close-payment", function () {
		var id = $(this).data('id');
		var status = $(this).data('status');
		if ($(this).hasClass("close-payment-with-debt")) {
            var amount = $("#amount").val()
            $.ajax({
                url: ajaxPostUrl,
                type: 'POST',
                data: {
                    amount: amount,
                    payment: id,
                    action: 'add-debt-payment',
                    csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
                },
//			success: function (response) {
//				updStatusDriverPayments(id, status, paymentStatus = "not_closed");
//				$(".confirmation-update-database").hide();
//				$(".close-payment-with-debt").addClass('confirmation-btn-off').removeClass('close-payment-with-debt');
//				$(".close-payment").addClass('confirmation-btn-on').removeClass('close-payment');
//			},
		});
		}
		updStatusDriverPayments(id, status, paymentStatus = "not_closed");
		$(".confirmation-update-database").hide();
		$(".close-payment").addClass('confirmation-btn-on').removeClass('close-payment');
		$(".close-payment-with-debt").addClass('confirmation-btn-off').removeClass('close-payment-with-debt');
	});

	$(this).on('click', '.send-all-button', function () {
		var allDataIds = [];
		$('tr[data-id]').each(function () {
		if (!$(this).hasClass('incorrect')) {
		    var dataId = $(this).attr('data-id');
		    if (!allDataIds.includes(dataId)){
                allDataIds.push(dataId);
            }
		}
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


function calculate_payment_ajax(ajaxData) {
    $.ajax({
			url: ajaxPostUrl,
			type: 'POST',
            data: ajaxData,
			success: function (response) {
				checkTaskStatus(response.task_id)
					.then(function (response) {
						if (response.data === "SUCCESS") {
							$("#loadingModal").hide();
							if (response.result.status === 'incorrect' && response.result.order === false) {
								$(".bolt-confirm-button").data("payment-id", response.result.id)
								$("#bolt-confirmation-form").show();
								$('.modal-overlay').show();
							} else if (response.result.order === true) {
								$("#loadingMessage").text(gettext("Вибачте, не всі замовлення розраховані агрегатором, спробуйте пізніше"));
								$("#loader").hide();
								$("#loadingModal").show();
								setTimeout(function () {
									$('#loadingModal').hide();
								}, 3000);
							} else if (response.result.status === 'error') {
									$('#loadingModal').show();
									$('#loadingMessage').text("Немає звітів по водію за цей період")
									$("#loader").hide();
									setTimeout(function () {
										$('#loadingModal').hide();
									}, 3000);
							} else {
								driverPayment(null, null, null, paymentStatus = "on_inspection");
							}
						}

					})
					.catch(function (error) {
						console.error('Error:', error)
					})
			},
		});
	return
}