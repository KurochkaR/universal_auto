var showOverlay = true
$(document).ajaxStart(function() {
    if (showOverlay) {
        $('#overlay').show();
    }
});

$(document).ajaxStop(function() {
    $('#overlay').hide();
});

$(document).ready(function () {

	$("#admin-link").click(function () {
		var adminUrl = $(this).data("url");
		window.open(adminUrl, "_blank");
	});

	$(this).on('click', '.update-database', function () {
		$(".confirmation-box h2").text("Бажаєте оновити базу даних?");
		$("#confirmation-btn-on").data("confirmUpdate", true)
		$(".confirmation-update-database").show();
	});

	$("#confirmation-btn-on").click(function () {
        $(".confirmation-update-database").hide();
        if ($(this).data("confirmUpdate", true)) {
            $("#loadingModal").css("display", "block");
            $(".loading-content").css("display", "block");
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
                            $("#loader").css("display", "none");
                            $("#checkmark").css("display", "block");
                        } else {
                            $("#loadingMessage").text(gettext("Помилка оновлення бази даних. Спробуйте пізніше"));
                            $("#loader").css("display", "none");
                            $("#checkmark").css("display", "none");
                        }
                        setTimeout(function() {
                        $("#loadingModal").css("display", "none");
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
                    if (aggregators.has(fleet))  {
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

        if (fieldType === 'password') {
            passwordField.attr('type', 'text');
            $(".showPasswordText").text('Приховати пароль');
            $(".circle-password").addClass('circle-active')
        } else {
            passwordField.attr('type', 'password');
            $(".showPasswordText").text('Показати пароль');
            $(".circle-password").removeClass('circle-active')
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
	        $("#partnerLogin").hide()
			$(".helper-token").hide()
			$("#partnerPassword").hide()
			$(".opt-partnerForm").hide()
			$(".login-ok").show()
			$("#loginErrorMessage").hide()
	}

	function showAllHideConnect(aggregator) {
	        if (aggregator !== 'Gps') {
				$("#partnerLogin").show();
				$(".helper-token").hide();
				$(".showPasswordText").show();
				$(".circle-password").show();
				partnerLoginField.attr('required', true)
			    $("#partnerPassword").attr('placeholder', "Пароль")
			} else {
                $(".helper-token").show();
                $("#partnerLogin").hide();
                $(".showPasswordText").hide();
                $(".circle-password").hide();
                partnerLoginField.removeAttr('required')
                $("#partnerPassword").attr('placeholder', "Введіть токен gps")
			}
			$("#partnerPassword").show().val("")
			$(".opt-partnerForm").show()
			$(".login-ok").hide()
			$("#loginErrorMessage").hide()
			aggregator === 'Uklon' ? partnerLoginField.val('+380') : partnerLoginField.val('');
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
				.then( function (response) {
                    if (response.data === "SUCCESS") {
                        localStorage.setItem(partner, 'success');
                        hideAllShowConnect();
                    } else {
                        $(".opt-partnerForm").show();
                        partner === "Gps" ? $("#loginErrorMessage").text("Вказано неправильний токен") : $("#loginErrorMessage").text("Вказано неправильний логін або пароль");
                        $("#loginErrorMessage").show();

//                        $("#partnerLogin").val("").addClass("error-border");
//                        $("#partnerPassword").val("").addClass("error-border");
                    }
                    hideLoader(partnerForm);
                })
                .catch( function (error) {
                        console.error('Error:', error);
                    });
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
                showAllHideConnect(partner)
			}
		});
	}

	var selectedOption = sessionStorage.getItem('selectedOption');
	if (selectedOption) {
		$('input[name="driver-info"][value="' + selectedOption + '"]').prop('checked', true);
	}

	$('#DriverBtnContainers').on('click', function () {
		$('input[name="driver-info"][value="driver-list"]').prop('checked', true);
		sessionStorage.setItem('selectedOption', 'driver-list');
	});

	$('input[name="driver-info"]').change(function () {
		var selectedValue = $(this).val();
		sessionStorage.setItem('selectedOption', selectedValue);

		switch (selectedValue) {
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
		var $button = $(this);
		if ($button.hasClass('disabled')) {
			return;
		}
		$button.addClass('disabled');
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
				$button.removeClass('disabled');
				if (idPayments === null) {
					window.location.reload();
				} else {
					driverPayment(null, null, null, paymentStatus = "on_inspection");
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
				$button.removeClass('disabled');
			},
		});
	});

	$(this).on('click', '#edit-button-bonus-penalty', function (e) {
		e.preventDefault();
		var $button = $(this);
		if ($button.hasClass('disabled')) {
			return;
		}
		$button.addClass('disabled');
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
				$button.removeClass('disabled');
				if (paymentId === undefined) {
					window.location.reload();
				} else {
					driverPayment(null, null, null, paymentStatus = "on_inspection");
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
				$button.removeClass('disabled');
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
		aggregator = $('.checkbox-container input[type="checkbox"]:checked').map(function () {
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
		driverPayment(selectedPeriod, startDate, endDate, paymentStatus = "closed");
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
			$('#modal-add-bonus').data('payment-id', paymentId);
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
                beforeSend: function() {
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

