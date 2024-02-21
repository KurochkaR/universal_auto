$(document).ready(function() {

	$("#admin-link").click(function() {
		var adminUrl = $(this).data("url");
		window.open(adminUrl, "_blank");
	});

	$(this).on('click', '#updateDatabaseContainer', function() {
		$(".confirmation-box h2").text("Бажаєте оновити базу даних?");
		$(".confirmation-update-database").show();
		$("#confirmation-btn-on").data('confirmUpd', true);
	});

	$("#confirmation-btn-on").click(function () {
		if ($(this).data('confirmUpd')) {
			$(".confirmation-update-database").hide();
			$("#loadingModal").css("display", "block")
			$(".loading-content").css("display", "block");

			$.ajax({
				type: "POST",
				url: ajaxPostUrl,
				data: {
					csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
					action: "upd_database",
				},
				success: function (response) {
					let task_id = response.task_id
					let interval = setInterval(function () {
						$.ajax({
							type: "GET",
							url: ajaxGetUrl,
							data: {
								action: "check_task",
								task_id: task_id,
							},
							success: function (response) {
								if (response.data === true) {
									$(".loading-content").css("display", "flex");
									$("#loadingMessage").text(gettext("Базу даних оновлено"));
									$("#loader").css("display", "none");
									$("#checkmark").css("display", "block");
									setTimeout(function () {
										$("#loadingModal").css("display", "none");
										window.location.reload();
									}, 3000);
									clearInterval(interval);
								} if (response.data === false) {
									$("#loadingMessage").text(gettext("Помилка оновлення бази даних. Спробуйте пізніше"));
									$("#loader").css("display", "none");
									$("#checkmark").css("display", "none");
									setTimeout(function () {
										$("#loadingModal").css("display", "none");
									}, 3000);
									clearInterval(interval);
								};
							}
						});
					}, 5000);
				}
			});
		}
	});

	$("#confirmation-btn-off").click(function () {
		$(".confirmation-update-database").hide();
	});

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
				localStorage.setItem(fleet, aggregators.has(fleet) ? 'success' : 'false');
			});
		}
	});
	const partnerForm = $("#partnerForm");
	const partnerLoginField = $("#partnerLogin");
	const partnerRadioButtons = $("input[name='partner']");

	let uklonStatus = localStorage.getItem('Uklon');
	let boltStatus = localStorage.getItem('Bolt');
	let uberStatus = localStorage.getItem('Uber');

	if ((uklonStatus === 'success' || boltStatus === 'success' || uberStatus === 'success')) {
		$("#updateDatabaseContainer").show();
	} else {
		$("#updateDatabaseContainer").hide();
	}

	partnerRadioButtons.change(function () {
		const selectedPartner = $("input[name='partner']:checked").val();
		updateLoginField(selectedPartner);
	});

	function updateLoginField(partner) {
		if (partner === 'Uklon') {
			partnerLoginField.val('+380');
		} else {
			partnerLoginField.val('');
			$("#partnerPassword").val("");
		}
	}

	if (sessionStorage.getItem('settings') === 'true') {
		$("#settingsWindow").fadeIn();
	}

	if (localStorage.getItem('Uber') === 'success') {
		$("#partnerLogin").hide()
		$("#partnerPassword").hide()
		$(".opt-partnerForm").hide()
		$(".login-ok").show()
		$("#loginErrorMessage").hide()
	}


	$("#settingBtnContainer").click(function () {
		sessionStorage.setItem('settings', 'true');
		$("#settingsWindow").fadeIn();
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

	$(".logout-btn").click(function () {
		const selectedPartner = partnerForm.find("input[name='partner']:checked").val();
		sendLogautDataToServer(selectedPartner);
		localStorage.removeItem(selectedPartner);
		$("#partnerLogin").show()
		$("#partnerPassword").show()
		$(".opt-partnerForm").show()
		$(".login-ok").hide()
		$("#loginErrorMessage").hide()
	});

	$("#showPasswordPartner").click(function () {
		let $checkbox = $(this);
		let $passwordField = $checkbox.closest('.settings-content').find('.partnerPassword');
		let change = $checkbox.is(":checked") ? "text" : "password";
		$passwordField.prop('type', change);
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


	$('[name="partner"]').change(function () {
		let partner = $(this).val()
		let login = localStorage.getItem(partner)

		if (login === "success") {
			$("#partnerLogin").hide()
			$("#partnerPassword").hide()
			$(".opt-partnerForm").hide()
			$(".login-ok").show()
			$("#loginErrorMessage").hide()
		} else {
			$("#partnerLogin").show()
			$("#partnerPassword").show()
			$(".opt-partnerForm").show()
			$(".login-ok").hide()
			$("#loginErrorMessage").hide()
		}
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
				let task_id = response.task_id;
				let interval = setInterval(function () {
					$.ajax({
						type: "GET",
						url: ajaxGetUrl,
						data: {
							action: "check_task",
							task_id: task_id,
						},
						success: function (response) {
							if (response.data === true) {
								localStorage.setItem(partner, 'success');
								$("#partnerLogin").hide();
								$("#partnerPassword").hide().val('');
								$(".opt-partnerForm").hide();
								$(".login-ok").show();
								$("#loginErrorMessage").hide();
								hideLoader(partnerForm);
								clearInterval(interval);
							}
							if (response.data === false) {
								$(".opt-partnerForm").show();
								$("#loginErrorMessage").show();
								$("#partnerLogin").val("").addClass("error-border");
								$("#partnerPassword").val("").addClass("error-border");
								hideLoader(partnerForm);
								clearInterval(interval);
							}
						},
					});
				}, 5000);
			},
		});
	}


	function sendLogautDataToServer(partner) {
		$("#partnerLogin").val("")
		$("#partnerPassword").val("")
		$.ajax({
			type: "POST",
			url: ajaxPostUrl,
			data: {
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
				action: "logout",
				aggregator: partner
			},
			success: function (response) {
				if (response.data === true) {
					localStorage.setItem(partner, 'false');
					$("#partnerLogin").show()
					$("#partnerPassword").show()
					$(".opt-partnerForm").show()
					$(".login-ok").hide()
				}
			}
		});
	}

	var selectedOption = sessionStorage.getItem('selectedOption');
	if (selectedOption) {
		$('input[name="driver-info"][value="' + selectedOption + '"]').prop('checked', true);
	}

	$('#DriverBtnContainers').on('click', function() {
		$('input[name="driver-info"][value="driver-list"]').prop('checked', true);
		sessionStorage.setItem('selectedOption', 'driver-list');
	});

	$('input[name="driver-info"]').change(function() {
		var selectedValue = $(this).val();
		sessionStorage.setItem('selectedOption', selectedValue);

		switch(selectedValue) {
			case 'driver-list':
				window.location.href = "/dashboard/drivers/";
				break;
			case 'driver-payments':
				window.location.href = "/dashboard/drivers-payment/";
				break;
			case 'driver-efficiency':
				window.location.href = "/dashboard/drivers-efficiency/";
				break;
			default:
				break;
		}
	});

	$(this).on('click', '.shift-close-btn', function () {
		$('#modal-add-bonus').hide();
		$('#modal-upd-bonus').hide();
		$('#modal-add-penalty').hide();
		$('.modal-not-closed-payments').hide();
	});

	$(this).on('click', '#add-bonus-btn, #add-penalty-btn', function (e) {
		e.preventDefault();
		$('#amount-bonus-error, #category-bonus-error, #vehicle-bonus-error').hide();
		var idPayments = $('#modal-add-bonus').data('id');
		var driverId = $('#modal-add-bonus').data('driver-id');
		var formDataArray = $('#modal-add-bonus :input').serializeArray();

		var formData = {};
		$.each(formDataArray, function(i, field){
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
				console.log(idPayments);
				$('#modal-add-bonus')[0].reset();
				$('#modal-add-bonus').hide();
				if (idPayments === null) {
					window.location.reload();
				} else {
					driverPayment(null, null, null, paymentStatus="on_inspection");
				}
			},
			error: function (xhr, textStatus, errorThrown) {
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
		$('#amount-bonus-error, #category-bonus-error, #vehicle-bonus-error').hide();
		var idBonus = $('#modal-add-bonus').data('bonus-penalty-id');
		var category = $('#modal-add-bonus').data('category-type');
		var driverId = $('#modal-add-bonus').data('driver-id');
		var paymentId = $('.tr-driver-payments').data('id');
		var formDataArray = $('#modal-add-bonus :input').serializeArray();
		var formData = {};
		$.each(formDataArray, function(i, field){
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
				if (paymentId === undefined) {
					window.location.reload();
				} else {
					driverPayment(null, null, null, paymentStatus="on_inspection");
				}
			},
			error: function (xhr, textStatus, errorThrown) {
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

	$(this).on('change', '#bonus-category', function(){
		if ($(this).val() === 'add_new_category'){
			$('.new-category-field').css('display', 'flex')
		} else {
			$('.new-category-field').hide()
		}
	});

	$(this).on('click', '.not-closed', function () {
		$('.modal-not-closed-payments').show();
	});

});

function applyCustomDateRange(item) {
	let startDate = $("#start_report_driver").val();
	let endDate = $("#end_report_driver").val();
	const dateRegex = /^\d{4}-\d{2}-\d{2}$/;

	if (!startDate.match(dateRegex) || !endDate.match(dateRegex)) {
		$("#error_message").text("Дата повинна бути у форматі YYYY-MM-DD").show();
		return;
	}

	if (startDate > endDate) {
		$("#error_message").text("Кінцева дата повинна бути більшою або рівною початковій даті").show();
		return;
	}

	$("#error_message").hide();
	const selectedPeriod = 'custom';

	if (item === 'driver') {
		$(".apply-filter-button_driver").prop("disabled", true);
		aggregator = $('.checkbox-container input[type="checkbox"]:checked').map(function() {
			return $(this).val();
		}).get();
		var aggregatorsString = aggregator.join('&');

		if (aggregatorsString === 'shared') {
			fetchDriverEfficiencyData(selectedPeriod, startDate, endDate);
		} else {
			fetchDriverFleetEfficiencyData(selectedPeriod, startDate, endDate, aggregatorsString);
		}
	}

	if (item === 'vehicle') {
		$(".apply-filter-button_vehicle").prop("disabled", true);
		fetchVehicleEarningsData(selectedPeriod, startDate, endDate);
	}

	if (item === 'payments') {
		$(".apply-filter-button_driver").prop("disabled", true);
		driverPayment(selectedPeriod, startDate, endDate, paymentStatus="closed");
	}
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
			$('#modal-add-bonus').data('id', paymentId);
			$('#modal-add-bonus').data('bonus-penalty-id', bonusPenaltyId);
			$('#modal-add-bonus').data('category-type', itemType);
			$('#modal-add-bonus').data('driver-id', driverId);
			var headingText = itemType === 'bonus' ? (bonusPenaltyId ? 'Редагування бонуса' : 'Додавання бонуса') :
																							 (bonusPenaltyId ? 'Редагування штрафа' : 'Додавання штрафа');
			var buttonText = bonusPenaltyId ? 'Редагувати' : 'Додати';
			var buttonId = itemType === 'bonus' ? (bonusPenaltyId ? 'edit-button-bonus-penalty' : 'add-bonus-btn') :
																						(bonusPenaltyId ? 'edit-button-bonus-penalty' : 'add-penalty-btn');
			$('#add-bonus-btn').text(buttonText);
			$('.title-add-bonus h2').text(headingText);
			$('#add-bonus-btn').prop('id', buttonId);
			$('#modal-add-bonus').show();
			var selectedValue = $('#bonus-category').val();
			if (selectedValue === 'add_new_category') {
				$('.new-category-field').css('display', 'flex');
			}
		},

		error: function(xhr, status, error) {
			var errorMessage = xhr.responseJSON.data
      $('#errorText').text(errorMessage);
  		$('#errorModal').show();
  		setTimeout(function() {
				$('#errorModal').hide();
			}, 5000);
    }
  });
}
