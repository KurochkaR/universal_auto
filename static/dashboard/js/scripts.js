$(document).ready(function() {
	//	перехід на сторінку адмінки
	$("#admin-link").click(function() {
		var adminUrl = $(this).data("url");
		window.open(adminUrl, "_blank");
	});

	//	підтвердження оновлення бази даних
	$("#updateDatabaseContainer").click(function () {
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

	//	відправка перевірка статусу агрегатора (логін або логаут агрегаторів)
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

	if (sessionStorage.getItem('selectedOption')) {
		var selectedOption = sessionStorage.getItem('selectedOption');
		if (selectedOption !== 'driver-list') {
			sessionStorage.setItem('selectedOption', 'driver-list');
		}
	} else {
		sessionStorage.setItem('selectedOption', 'driver-list');
	}
	$('#DriverBtnContainers').on('click', function() {
		$('input[name="driver-info"][value="driver-list"]').prop('checked', true);
		sessionStorage.setItem('selectedOption', 'driver-list');
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
