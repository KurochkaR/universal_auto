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
            var addButtonBonus = '<button class="add-btn-bonus" title="Додати бонус"><i class="fa fa-plus"></i></button>';
            var addButtonPenalty = '<button class="add-btn-penalty" title="Додати штраф"><i class="fa fa-plus"></i></button>';
            var incorrectBtn = '<button class="incorrect-payment-btn">Перерахувати виплату</button>';
            var calculateBtn = '<button class="calculate-payment-btn">Розрахувати на зараз</button>';
            var confirmButton = '<button class="apply-btn" title="Відправити водію"></button>';
            var arrowBtn = '<button class="arrow-btn">Повернути на перевірку</button>';
            var payBtn = '<button class="pay-btn">Отримано</button>';
            var notPayBtn = '<button class="not-pay-btn">Не отримано</button>';
            var statusTh = $('th[data-sort="status"]');
            if (paymentStatus === 'closed') {
                $('th[data-sort="button"]').hide();
			    statusTh.text("Статус виплати");
            }
            if (paymentStatus === 'not_closed') {
                statusTh.text("Дії");
				$('th[data-sort="button"]').hide();
            }
			for (var i = 0; i < response.length; i++) {
				if ((paymentStatus === 'on_inspection' && (response[i].status === 'Перевіряється' || response[i].status === 'Потребує поправок')) ||
					(paymentStatus === 'not_closed' && response[i].status === 'Очікується') ||
					(paymentStatus === 'closed' && (response[i].status === 'Виплачений' || response[i].status === 'Не сплачений'))) {


					var dataId = response[i].id;
                    var responseDate = moment(response[i].report_to, "DD.MM.YYYY HH:mm");
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
						row.append('<td>' + '<div class="no-pencil-rate" style="display: flex;justify-content: space-evenly; align-items: center;">' + response[i].bonuses + '</div>' + '</td>');
						row.append('<td>' + '<div class="no-pencil-rate" style="display: flex;justify-content: space-evenly; align-items: center;">' + response[i].penalties + '</div>' + '</td>');
						row.append('<td><div style="display: flex;justify-content: space-evenly; align-items: center;"><span class="rate-payment no-pencil-rate" >' + response[i].rate + ' </span></div></td>')

					}
					row.append('<td class="payment-earning">' + response[i].earning + '</td>');
					var showAllButton = $('.send-all-button');
					showAllButton.hide(0);
					if (response[i].status === 'Очікується') {
						row.append('<td><div class="box-btn-upd">' + arrowBtn + payBtn + notPayBtn + '</div></td>');
						if (response[i].earning > 0) {
							row.find('.not-pay-btn').remove();
							row.find('.pay-btn').text('Сплатити');

						}
					}
					if (response[i].status === 'Перевіряється') {
						showAllButton.show(0);
						statusTh.text("Перерахування виплат");
						$('th[data-sort="button"]').show();
						if (response[i].payment_type === "DAY" && moment().startOf('day').isSame(responseDate.startOf('day'))) {
						    row.append('<td>' + calculateBtn + '</td>')
						} else {
						    row.append('<td></td>')
						}
						row.append('<td>' + confirmButton + '</td>');
					}
					if (response[i].status === 'Потребує поправок') {
					    row.addClass('incorrect');
					    showAllButton.show(0);
					    if (response[i].payment_type === "DAY" && moment().startOf('day').isSame(responseDate.startOf('day'))) {
						    row.append('<td>' + calculateBtn + '</td>');
						    row.append('<td>' + incorrectBtn + '</td>');
						} else {
						    row.append('<td></td>');
						    row.append('<td></td>')
						}
					}

					if (response[i].status === 'Виплачений' || response[i].status === 'Не сплачений') {
					    row.append('<td>' + response[i].status + '</td>');
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
	var itemId, actionType, itemType, drivers;

	$(this).on('click', '.driver-table tbody .driver-name', function () {
		var row = $(this).closest('tr');
		var bonusTable = row.next().find('.bonus-table');

		bonusTable.toggleClass('expanded');
		bonusTable.toggle();
		return false;
	});

    function populateButtons(filteredDrivers) {
        var createPaymentList = $(".create-payment-list");
        createPaymentList.empty();

        filteredDrivers.forEach(function(driver) {
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

	$("#search-driver").on("keyup", function() {

        var searchText = $(this).val().toLowerCase();

        var filteredDrivers = drivers.filter(function(driver) {
            return driver.name.toLowerCase().includes(searchText);
        });

        populateButtons(filteredDrivers);
    });

    $("#search-driver").on("keypress", function(e) {
        if (e.which === 13) {
            e.preventDefault();
            $(this).blur();
        }
    });

    $(this).on('click', '.driver-button, .calculate-payment-btn', function (e) {
        e.preventDefault();
        driverId = $(this).data('driver-id');
        paymentId = $(this).closest('tr').data('id');
        $('#payment-driver-list').hide();
		$('.create-payment').css('background', '#a1e8b9')
		$('.modal-overlay').hide();
		$("#loadingModal").show();
		$("#loadingMessage").text(gettext("Створюється нова виплата"));
		$("#loader").show();
		$.ajax({
			url: ajaxPostUrl,
			type: 'POST',
			data: {
			    driver_id: driverId,
			    payment_id: paymentId,
				action: 'create-new-payment',
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
			},
			success: function (response) {
                checkTaskStatus(response.task_id)
                .then( function (response) {
                    if (response.data === "SUCCESS") {
                        $("#loadingModal").hide();
                        if (response.result.status === 'incorrect' && response.result.order === false) {
                            $(".bolt-confirm-button").data("payment-id", response.result.id)
                            $("#bolt-confirmation-form").show();
                            $('.modal-overlay').show();
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
                .catch( function (error) {
                    console.error('Error:', error)
                })
			},
			error: function(xhr, textStatus, errorThrown) {
                if (xhr.status === 400) {
                    let error = xhr.responseJSON.error;
                    $('#loadingModal').show();
                    $('#loadingMessage').text(xhr.responseJSON.error)
                    $("#loader").hide();
                    setTimeout(function () {
                        $('#loadingModal').hide();
                    }, 3000);
                } else {
                    console.error('Помилка запиту: ' + textStatus);
                }
			},
        });
    })

    $(this).on('click', '.incorrect-payment-btn', function() {
        paymentId = $(this).closest('tr').data('id')
        $("#loadingModal").show();
		$("#loadingMessage").text(gettext("Перераховуємо виплату"));
		$("#loader").show();
        $.ajax({
			url: ajaxPostUrl,
			type: 'POST',
			data: {
			    payment_id: paymentId,
				action: 'update_incorrect_payment',
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
			},
			success: function (response) {
                checkTaskStatus(response.task_id)
                .then( function (response) {
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
                        }
                        else {
                            driverPayment(null, null, null, paymentStatus = "on_inspection");
                        }
                    }

                })
                .catch( function (error) {
                    console.error('Error:', error)
                })
			},
		});
    })

    $(this).on('click', '.bolt-confirm-button', function (e) {
        e.preventDefault();
        $("#bolt-confirmation-form").hide();
        itemId = $(this).data('payment-id');
        $("#bolt-amount, #bolt-cash").each(function() {
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
			error: function (xhr, textStatus, errorThrown) {
			    if (xhr.status === 400) {
                    $('.modal-overlay').hide();
                    let error = xhr.responseJSON.error;
                    $('#loadingModal').show();
                    $('#loadingMessage').text(xhr.responseJSON.error);
                    $("#loader").hide();
                    setTimeout(function () {
                        $('#loadingModal').hide();
                    }, 3000);
                } else {
                    console.error('Помилка запиту: ' + textStatus);
                }
			}
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

	$(this).on("input", "#bolt-cash, #bolt-amount", function() {
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
		$(".confirmation-btn-on").addClass('close-payment').removeClass('confirmation-btn-on');
	});

    $(this).on("click", ".close-payment", function () {
		var id = $(this).data('id');
		var status = $(this).data('status');
		updStatusDriverPayments(id, status, paymentStatus = "not_closed");
		$(".confirmation-update-database").hide();
		$(".close-payment").addClass('confirmation-btn-on').removeClass('close-payment');
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