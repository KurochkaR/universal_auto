var showOverlay = true
$(document).ajaxStart(function () {
	if (showOverlay) {
		$('#overlay').show();
	}
});

$(document).ajaxStop(function () {
	$('#overlay').hide();
});

$(document).ajaxError(function (event, xhr, settings) {
	console.error('Error:', xhr);
	var status = xhr.status;
	var error = xhr.responseJSON.error;
	if (status === 403) {
		window.location.href = '/';
	} else if (status === 400) {
		$('.modal-overlay').hide();
		$('#loadingModal').show();
		$('#loadingMessage').text(error);
		$("#loader").hide();
		setTimeout(function () {
			$('#loadingModal').hide();
		}, 3000);
	} else {
		console.error('Помилка запиту: ' + error);
	}
	return;
});

$(document).ready(function () {

	$("#admin-link").click(function () {
		var adminUrl = $(this).data("url");
		window.open(adminUrl, "_blank");
	});

	$(this).on('click', '.update-database', function (event) {
		event.stopPropagation();
		$(".confirmation-box h2").text("Бажаєте оновити базу даних?");
		$("#confirmation-btn-on").data("confirmUpdate", true)
		$(".confirmation-update-database").show();
	});

	$(this).on('click', "#confirmation-btn-on", function () {
		$(".confirmation-update-database").hide(0);

		if ($(this).data("confirmUpdate")) {
			$("#loadingModal, .loading-content").show(0);
			$("#loadingMessage").text(gettext("Зачекайте, будь ласка, поки оновлюється база даних..."));

			$.ajax({
				type: "POST",
				url: ajaxPostUrl,
				data: {
					csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
					action: "upd_database",
				},
				success: function (response) {
					checkTaskStatus(response.task_id)
						.then(function (response) {
							if (response.data === "SUCCESS") {
								$(".loading-content").css("display", "flex");
								$("#loadingMessage").text(gettext("Базу даних оновлено"));
								$("#loader").hide(0);
								$("#checkmark").show(0);
							} else {
								$("#loadingMessage").text(gettext("Помилка оновлення бази даних. Спробуйте пізніше"));
								$("#loader, #checkmark").hide(0);
							}
							setTimeout(function () {
								$("#loadingModal, #checkmark").hide(0);
							}, 3000);
						})
						.catch(function (error) {
							console.error('Error:', error);
						});
				},
			});
		}
	});

	$("#confirmation-btn-off").click(function () {
		$(".confirmation-update-database").hide();
	});

	const partnerForm = $("#partnerForm");
	const partnerLoginField = $("#partnerLogin");


	if (localStorage.getItem('Uber') === 'success') {
		hideAllShowConnect()
	}

	$("#settingBtnContainer").click(function () {
		sidebar.classList.remove("sidebar-responsive");
		$.ajax({
			url: ajaxGetUrl,
			type: "GET",
			data: {
				action: "aggregators"
			},
			success: function (response) {
				const aggregators = new Set(response.data);
				const fleets = new Set(response.fleets);
				fleets.forEach(fleet => {
					if (aggregators.has(fleet)) {
						localStorage.setItem(fleet, aggregators.has(fleet) ? 'success' : 'false');
						$('[name="partner"][value= "' + fleet + '"]').next('label').css("border", "2px solid #EC6323")
					} else {
						$('[name="partner"][value= "' + fleet + '"]').next('label').css("border", "2px solid #fff")
					}

				});
				$(".login-ok").hide();
				$("#partnerForm").show();
			},
		});
	});

	$(".login-btn").click(function () {
		const selectedPartner = partnerForm.find("input[name='partner']:checked").val();
		const partnerLogin = partnerForm.find("#partnerLogin").val();
		const partnerPassword = partnerForm.find("#partnerPassword").val();
		if (partnerForm[0].checkValidity() && selectedPartner) {
			showLoader(partnerForm);
			sendLoginDataToServer(selectedPartner, partnerLogin, partnerPassword);
		}
	});

	$(".logout-btn").click(function (e) {
		e.preventDefault();
		const selectedPartner = partnerForm.find("input[name='partner']:checked").val();
		sendLogautDataToServer(selectedPartner);
		localStorage.removeItem(selectedPartner);
	});

	$(this).on('click', '.opt-partnerForm span', function () {
		var passwordField = $('.partnerPassword');
		var fieldType = passwordField.attr('type');
		$(".circle-password").toggleClass('circle-active')
		if (fieldType === 'password') {
			passwordField.attr('type', 'text');
			$(".showPasswordText").text('Приховати пароль');
		} else {
			passwordField.attr('type', 'password');
			$(".showPasswordText").text('Показати пароль');
		}
	});

	function showLoader(form) {
		$(".opt-partnerForm").hide();
		form.find(".loader-login").show();
		$("input[name='partner']").prop("disabled", true);
	}

	function hideLoader(form) {
		form.find(".loader-login").hide();
		$("input[name='partner']").prop("disabled", false);
	}

	function hideAllShowConnect() {
		$("#partnerLogin, #loginErrorMessage, .opt-partnerForm, #partnerPassword, .helper-token").hide()
		$(".login-ok").show()
	}

	function showAllHideConnect(aggregator) {
		if (aggregator.toLowerCase() !== 'gps') {
			$("#partnerLogin, .circle-password, .showPasswordText").show();
			$(".helper-token").hide();
			partnerLoginField.attr('required', true)
			$("#partnerPassword").attr('placeholder', "Пароль")
		} else {
			$(".helper-token").show();
			$("#partnerLogin, .showPasswordText, .circle-password").hide();
			partnerLoginField.removeAttr('required')
			$("#partnerPassword").attr('placeholder', "Введіть токен gps")
		}
		$("#partnerPassword").show().val("")
		$(".opt-partnerForm").show()
		$(".login-ok").hide()
		$("#loginErrorMessage").hide()
		aggregator.toLowerCase() === 'uklon' ? partnerLoginField.val('+380') : partnerLoginField.val('');
	}

	$('[name="partner"]').click(function () {
		$('[name="partner"]').not(this).next('label').css({
			"background-color": "",
			"color": "",
		});
		let partner = $(this).val();
		let login = localStorage.getItem(partner);

		$(this).next('label').css({
			"background-color": "#EC6323",
			"color": "white",
		});
		login === "success" ? hideAllShowConnect() : showAllHideConnect(partner)
	})

	function sendLoginDataToServer(partner, login, password) {
		$.ajax({
			type: "POST",
			url: ajaxPostUrl,
			data: {
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
				aggregator: partner,
				action: "login",
				login: login,
				password: password,
			},
			success: function (response) {
				checkTaskStatus(response.task_id)
					.then(function (response) {
						if (response.data === "SUCCESS") {
							localStorage.setItem(partner, 'success');
							hideAllShowConnect();
						} else {
							$(".opt-partnerForm").show();
							partner === "Gps" ? $("#loginErrorMessage").text("Вказано неправильний токен") : $("#loginErrorMessage").text("Вказано неправильний логін або пароль");
							$("#loginErrorMessage").show();
						}
						hideLoader(partnerForm);
					})
					.catch(function (error) {
						console.error('Error:', error);
					});
			},
		});
	}


	function sendLogautDataToServer(partner) {
		$("#partnerLogin, #partnerPassword").val("")

		$.ajax({
			type: "POST",
			url: ajaxPostUrl,
			data: {
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
				action: "logout",
				aggregator: partner
			},
			success: function (response) {
				showAllHideConnect(partner)
			}
		});
	}


	$(this).on('click', '.shift-close-btn', function () {
		$(this).closest('form').hide();
		$('input[name="partner"]').removeAttr('checked');
		hideAllShowConnect();
		$('[name="partner"]').not(this).next('label').css({
			"background-color": "",
			"color": ""
		});
		$('.create-payment').css('background', '#a1e8b9')
		$('.modal-not-closed-payments').hide();
		$('.modal-overlay').hide();
	});

	$(this).on('click', '#add-bonus-btn, #add-penalty-btn', function (e) {
		e.preventDefault();
		var button = $(this)
		button.prop("disabled", true);
		$('#amount-bonus-error, #category-bonus-error, #vehicle-bonus-error').hide();
		var idPayments = $('#modal-add-bonus').data('id');
		var driverId = $('#modal-add-bonus').data('driver-id');
		var formDataArray = $('#modal-add-bonus :input').serializeArray();

		var formData = {};
		$.each(formDataArray, function (i, field) {
			formData[field.name] = field.value;
		});
		if ($(this).attr('id') === 'add-bonus-btn') {
			formData['action'] = 'add-bonus';
			formData['category_type'] = 'bonus'
		} else {
			formData['action'] = 'add-penalty';
			formData['category_type'] = 'penalty'
		}
		formData['idPayments'] = idPayments;
		formData['driver_id'] = driverId;
		formData['csrfmiddlewaretoken'] = $('input[name="csrfmiddlewaretoken"]').val()
		$.ajax({
			type: 'POST',
			url: ajaxPostUrl,
			data: formData,
			dataType: 'json',
			success: function (data) {
				$('#modal-add-bonus')[0].reset();
				$('#modal-add-bonus').hide();
				button.prop("disabled", false);
				if (idPayments === null) {
					window.location.reload();
				} else {
					driverPayment(null, null, null, paymentStatus = "on_inspection");
				}
			},
			error: function (xhr, textStatus, errorThrown) {
				button.prop("disabled", false);
				if (xhr.status === 400) {
					let errors = xhr.responseJSON.errors;
					$.each(errors, function (key, value) {
						$('#' + key + '-bonus-error').html(value).show();
					});
				} else {
					console.error('Помилка запиту: ' + textStatus);
				}

			},
		});
	});

	$(this).on('click', '#edit-button-bonus-penalty', function (e) {
		e.preventDefault();
		var $button = $(this);
		button.prop("disabled", true);
		$('#amount-bonus-error, #category-bonus-error, #vehicle-bonus-error').hide();
		var idBonus = $('#modal-add-bonus').data('bonus-penalty-id');
		var category = $('#modal-add-bonus').data('category-type');
		var driverId = $('#modal-add-bonus').data('driver-id');
		var paymentId = $('#modal-add-bonus').data('payment-id');
		var formDataArray = $('#modal-add-bonus :input').serializeArray();
		var formData = {};
		$.each(formDataArray, function (i, field) {
			formData[field.name] = field.value;
		});
		formData['action'] = 'upd_bonus_penalty';
		formData['bonus_id'] = idBonus;
		formData['category_type'] = category;
		formData['driver_id'] = driverId;
		formData['payment_id'] = paymentId;
		formData['csrfmiddlewaretoken'] = $('input[name="csrfmiddlewaretoken"]').val()
		$.ajax({
			type: 'POST',
			url: ajaxPostUrl,
			data: formData,
			dataType: 'json',
			success: function (data) {
				$('#modal-add-bonus')[0].reset();
				$('#modal-add-bonus').hide();
				button.prop("disabled", false);
				if (paymentId === undefined || paymentId === null) {
					window.location.reload();
				} else {
					driverPayment(null, null, null, paymentStatus = "on_inspection");
				}
			},
			error: function (xhr, textStatus, errorThrown) {
				button.prop("disabled", false);
				if (xhr.status === 400) {
					let errors = xhr.responseJSON.errors;
					$.each(errors, function (key, value) {
						$('#' + key + '-bonus-error').html(value).show();
					});
				} else {
					console.error('Помилка запиту: ' + textStatus);
				}
			},
		});
	});

	$(this).on('change', '#bonus-category', function () {
		if ($(this).val() === 'add_new_category') {
			$('.new-category-field').css('display', 'flex')
		} else {
			$('.new-category-field').hide()
		}
	});

	$(this).on('click', '.not-closed', function () {
	    selectedValue = $(".selected-option").data('value')
        if (!selectedValue) {
	        selectedValue = 'today'
	    }
	    if (selectedValue === 'custom') {
	        applyDateRange(function(selectedPeriod, startDate, endDate) {
                getNotCompletedPayments(selectedPeriod, startDate, endDate)

        });
	    } else {
	        getNotCompletedPayments(selectedValue)
	    }
		$('.modal-not-closed-payments').show();
	});

	$(this).on("click", ".selected-option, .fa-angle-down", function () {
		$(".custom-select").toggleClass("active");
	});


});

function initializeCustomSelect(callback) {
	$(document).on("click", ".options li", function () {
		const customSelect = $(".custom-select");
		const selectedOption = customSelect.find(".selected-option");
		const datePicker = $("#datePicker");
		const clickedValue = $(this).data("value");
		selectedOption.data("value", clickedValue);
		selectedOption.text($(this).text());
		customSelect.removeClass("active");
		if (clickedValue !== "custom") {
			datePicker.hide();
			callback(clickedValue);
		} else {
			if (window.innerWidth <= 768) {
				datePicker.show();
			} else {
				datePicker.css("display", "inline-block");
			}
		}
	});
}


function applyDateRange(callback) {
	const selectedPeriod = 'custom';
	let startDate = $("#start_report").val();
	let endDate = $("#end_report").val();
	if (!startDate || !endDate) {
		$("#error_message").text("Поле не може бути пустим, введіть дату").show();
		return;
	}
	if (startDate > endDate) {
		[startDate, endDate] = [endDate, startDate];
	}

	$("#error_message").hide();

	callback(selectedPeriod, startDate, endDate)
}

function openForm(paymentId, bonusPenaltyId, itemType, driverId) {
	$.ajax({
		url: ajaxGetUrl,
		type: 'GET',
		data: {
			action: 'render_bonus',
			payment: paymentId,
			bonus_penalty: bonusPenaltyId,
			type: itemType,
			driver_id: driverId
		},
		success: function (response) {
			$('#formContainer').html(response.data);
			const modalAddBonusData = {
				'id': paymentId,
				'bonus-penalty-id': bonusPenaltyId,
				'category-type': itemType,
				'driver-id': driverId,
				'payment-id': paymentId
			};
			const modalAddBonus = $('#modal-add-bonus');
			modalAddBonus.data(modalAddBonusData);
			const addBonusBtn = $('#add-bonus-btn');
			var headingText = itemType === 'bonus' ? (bonusPenaltyId ? 'Редагування бонуса' : 'Додавання бонуса') :
				(bonusPenaltyId ? 'Редагування штрафа' : 'Додавання штрафа');
			var buttonText = bonusPenaltyId ? 'Редагувати' : 'Додати';
			var buttonId = itemType === 'bonus' ? (bonusPenaltyId ? 'edit-button-bonus-penalty' : 'add-bonus-btn') :
				(bonusPenaltyId ? 'edit-button-bonus-penalty' : 'add-penalty-btn');
			addBonusBtn.text(buttonText);
			$('.title-form h2').text(headingText);
			addBonusBtn.prop('id', buttonId);
			modalAddBonus.show();
			var selectedValue = $('#bonus-category').val();
			if (selectedValue === 'add_new_category') {
				$('.new-category-field').css('display', 'flex');
			}
		},

		error: function (xhr, status, error) {
			var errorMessage = xhr.responseJSON.data
			$('#errorText').text(errorMessage);
			$('#errorModal').show();
			setTimeout(function () {
				$('#errorModal').hide();
			}, 5000);
		}
	});
}

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

		// Format the string as HH:mm:ss
		return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
	}
}


function sortTable(column, order) {
	let $tbody = $('.driver-efficiency-table').find('tbody');
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
		if (order === 'sorted-asc') {
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

function checkTaskStatus(taskId) {
	return new Promise(function (resolve, reject) {
		function pollTaskStatus() {
			$.ajax({
				type: "GET",
				url: ajaxGetUrl,
				data: {
					action: "check_task",
					task_id: taskId,
				},
				beforeSend: function () {
					showOverlay = false;
				},
				success: function (response) {
					if (response.data === "SUCCESS" || response.data === "FAILURE") {
						resolve(response);
					} else {
						setTimeout(pollTaskStatus, 3000);
					}
				},
				error: function (response) {
					console.error('Error checking task status');
					reject('Error checking task status');
				}
			});
		}

		pollTaskStatus();
	});
}

function validNumberInput(maxValue = 100, element) {
	var inputValue = element.val();
	var sanitizedValue = inputValue.replace(/[^0-9.]/g, '');
	var integerValue = parseFloat(sanitizedValue);
	if (isNaN(integerValue) || integerValue < 0) {
		integerValue = 0;
	}
	sanitizedValue = Math.min(Math.max(integerValue, 0), maxValue);
	element.val(sanitizedValue);
}

function getNotCompletedPayments(period, start=null, end=null) {
    let api_url
    if (period === 'custom') {
		apiUrl = `/api/not_complete_payments/${start}&${end}/`;
	} else {
		apiUrl = `/api/not_complete_payments/${period}/`;
	}
    $.ajax({
		url: apiUrl,
		type: 'GET',
		dataType: 'json',
		success: function (data) {
			const table = $('.driver-table');

			table.find('tbody').empty();

			data.forEach(driver => {
				const row = $('<tr></tr>');
				const totalAmount = parseFloat(driver.kasa || 0);

				row.append(`<td>${driver.full_name}</td>`);
				row.append(`<td>${parseInt(totalAmount)}</td>`);
				table.append(row);
			});
		}
		})
}


