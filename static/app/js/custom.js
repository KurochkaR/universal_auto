$.scrollTop = () => Math.max(document.documentElement.scrollTop, document.body.scrollTop);
$(document).ready(function () {
	$('[id^="sub-form-"]').on('submit', function (event) {
		event.preventDefault();
		const form = this;
		$.ajax({
			type: "POST",
			url: ajaxPostUrl,
			data: {
				'email': $(event.target).find('#sub_email').val(),
				'action': 'subscribe',
				'csrfmiddlewaretoken': $('input[name="csrfmiddlewaretoken"]').val()
			},
			success: function (data) {
				$('#email-error-1, #email-error-2').html('');
				form.reset();
			},
			error: function (xhr, textStatus, errorThrown) {
				if (xhr.status === 400) {
					let errors = xhr.responseJSON;
					$.each(errors, function (key, value) {
						$('#' + key + '-error-1, #' + key + '-error-2').html(value);
					});
				} else {
					console.error('Помилка запиту: ' + textStatus);
				}
			}
		});
	});
});

//$(window).on('load', function () {
//	$('.loader').remove();
//});

$(document).ready(function () {

	// js for header

	$("#loginBtn").click(function () {
		$("#loginForm").fadeIn();
		$("#loginRadio").hide();
		$("label[for='loginRadio']").hide();
	});

	$("#loginBtn2").click(function () {
		$("#loginForm").fadeIn();
		$("#loginRadio").hide();
		$("label[for='loginRadio']").hide();
	});

	$('.nav-item-social').click(function (event) {
		if ($('.social-icons').is(':visible')) {
			$('.social-icons').hide();
		} else {
			$('.social-icons').show();
		}
		event.stopPropagation();
	});

	$(document).click(function (event) {
		if (!$(event.target).closest('.nav-item-social').length) {
			$('.social-icons').hide();
		}
	});

	$('.stripes').click(function () {
		$('.sub-menu').slideToggle();
	});

	let pagesLink = $("#pagesLink");
	let pagesList = $("#pagesList");

	pagesLink.click(function () {
		if (pagesList.is(":visible")) {
			pagesList.hide();
		} else {
			pagesList.show();
		}
	});

	$(".close-btn").click(function () {
		$("#loginForm").fadeOut();
		$(".forgot-password-form").fadeOut();
		$(".reset-password-form").fadeOut();
	});

	$("#login-invest").click(function () {
		let login = $("#login").val();
		let password = $("#password").val();

		$.ajax({
			url: ajaxPostUrl,
			type: 'POST',
			data: {
				action: 'login_invest',
				login: login,
				password: password,
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
			},
			success: function (response) {
				if (response.data['success'] === true) {
					$("#loginBtn").hide();
					window.location.href = "/dashboard/";
					$("#loginForm").fadeOut();

				} else {
					$("#loginErrorMessage").show();
					$("#login").val("")
					$("#password").val("");
				}
			}
		});
	});

	let urlParams = new URLSearchParams(window.location.search);
	let signedIn = urlParams.get('signed_in');

	if (signedIn === 'false') {
		let modal = document.createElement('div');
		modal.id = 'modal-signed-in-false';
		modal.className = 'modal-signed-in-false';

		let modalContent = document.createElement('div');
		modalContent.className = 'modal-content-false';

		let closeBtn = document.createElement('span');
		closeBtn.className = 'close';
		closeBtn.innerHTML = '&times;';
		closeBtn.onclick = function () {
			document.body.removeChild(modal);
			window.location.href = '/';
		};

		let modalText = document.createElement('p');
		modalText.innerHTML = gettext('Вхід не вдався:') + '<br>' +
			'<ol><li>' + gettext('Будь ласка, перевірте, чи ви використовуєте електронну адресу, яку вказували під час реєстрації.') + '</li>' +
			'<li>' + gettext('Також, переконайтеся, що ви є партнером компанії Ninja Taxi.') + '</li>' +
			'<li>' + gettext('Якщо ви впевнені в правильності введених даних, але не можете увійти в систему, зверніться до нашого менеджера для отримання допомоги.') + '</li>' +
			'</ol>';


		modalContent.appendChild(closeBtn);
		modalContent.appendChild(modalText);
		modal.appendChild(modalContent);

		document.body.appendChild(modal);
	}

	const forgotPasswordForm = $('#forgotPasswordForm');
	const loginRadioForm = $('#loginForm');
	const sendResetCodeBtn = $('#sendResetCode');

	$('#forgotPasswordRadio').click(function () {
		forgotPasswordForm.show();
		loginRadioForm.hide();
	});

	sendResetCodeBtn.click(function () {
		const email = $('#forgotEmail').val();

		$.ajax({
			url: ajaxPostUrl,
			type: 'POST',
			data: {
				action: 'send_reset_code',
				email: email,
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
			},
			success: function (response) {
				if (response['success'] === true) {
					let resetCode = response['code'][1];
					sendResetCodeBtn.data('resetCode', resetCode);
					forgotPasswordForm.hide();
					$('#resetPasswordForm').show();
				} else {
					$('#forgotPasswordError').show();
					$('#forgotEmail').val('');
				}
			}
		});
	});

	$('#updatePassword').click(function () {
		const email = $('#forgotEmail').val();
		const activeCode = $('#activationCode').val();
		const newPassword = $('#newPassword').val();
		const confirmPassword = $('#confirmPassword').val();
		const resetCode = sendResetCodeBtn.data('resetCode');

		if (newPassword !== confirmPassword || activeCode !== resetCode || newPassword.trim() === "") {
			if (newPassword !== confirmPassword) {
				$('#passwordError').text(gettext('Паролі не співпадають')).addClass('error-message').show();
			} else {
				$('#passwordError').hide()
			}
			if (newPassword.trim() === "") {
				$('#emptyPassError').text(gettext('Пароль не може бути пустим')).addClass('error-message').show();
			} else {
				$('#emptyPassError').hide()
			}

			if (activeCode !== resetCode) {
				$('#activationError').text(gettext('Невірний код активації')).addClass('error-message').show();
			} else {
				$('#activationError').hide()
			}
		} else {

			$.ajax({
				url: ajaxPostUrl,
				type: 'POST',
				data: {
					action: 'update_password',
					email: email,
					newPassword: newPassword,
					csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
				},
				success: function (response) {
					if (response['success'] === true) {
						$('#resetPasswordForm').hide();
						$('#loginForm').show();
					}
				}
			});
		}
	});

	// js for index
	const contactOpenBtn = $('.contact-me-button');
	const formSection = $('#contact-me-form');
	const contactForm = $("#contact-form");
	const detailsRadio = $('#detailsRadio');
	const howItWorksRadio = $('#howItWorksRadio');
	const detailRadio1 = $('#detail-radio-1');
	const detailRadio2 = $('#detail-radio-2');

	detailsRadio.change(function () {
		if (this.checked) {
			detailRadio1.show();
			detailRadio2.hide();
		}
	});

	howItWorksRadio.change(function () {
		if (this.checked) {
			detailRadio1.hide();
			detailRadio2.show();
		}
	});

	let videos = $('a[data-youtube]');
	videos.each(function () {
		let video = $(this);
		let href = video.attr('href');
		let id = new URL(href).searchParams.get('v');

		video.attr('data-youtube', id);
		video.attr('role', 'button');

		video.html(`
			<img alt="" src="https://storage.googleapis.com/jobdriver-bucket/docs/index-youtube-img.png" style="border-radius: 25px" width="552" height="310" loading="lazy"><br>
			${video.text()}
		`);
	});

	function clickHandler(event) {
		let link = $(event.target).closest('a[data-youtube]');
		if (!link) return;

		event.preventDefault();

		let id = link.attr('data-youtube');
		let player = $(`
      <div>
        <iframe width="560" height="315" src="https://www.youtube-nocookie.com/embed/${id}?autoplay=1" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
      </div>
    `);
		link.replaceWith(player);
	}

	$(document).on('click', 'a[data-youtube]', clickHandler);

	$(window).scroll(function () {
		var h = $(".header_section")
		if ($.scrollTop() > 32) {
			h.addClass("fx");
		} else {
			h.removeClass("fx");
		}
	});

	contactOpenBtn.click(function () {
		console.log('click');
		formSection.show();
		thankYouMessage.hide();
	});

	contactForm.on("submit", function (e) {
		e.preventDefault();
		let formData = contactForm.serialize();
		let phoneInput = contactForm.find('#phone').val();
		let nameInput = contactForm.find('#name').val();
		$(".error-message").hide();
		$(".error-name").hide();

		if (!/^\+\d{1,3} \d{2,3} \d{2,3}-\d{2,3}-\d{2,3}$/.test(phoneInput)) {
			$(".error-message").show();
			return;
		}

		if (nameInput.trim() === "") {
			$(".error-name").show();
			return;
		}

		submitForm(formData);
	});


	// js for park page

	const openButtonsFree = $(".free-access-button");
	const openButtonsConnect = $(".connect-button");
	const openButtonsConsult = $(".consult-button");
	const formSectionFree = $("#contact-me-form");
	const accessForm = $("#access-form");
	const thankYouMessage = $("#thank-you-message");
	const existingYouMessage = $("#existing-you-message")

	function hideFormAndShowThankYou(success) {
		formSectionFree.hide();
		formSection.hide();


		if (success) {
			thankYouMessage.show();
			setTimeout(function () {
				thankYouMessage.hide();
			}, 5000);
		} else {
			existingYouMessage.show();
			setTimeout(function () {
				existingYouMessage.hide();
			}, 5000);
		}
	}


	function submitForm(formData) {
		formData += "&action=free_access_or_consult";
		$.ajax({
			type: "POST",
			url: ajaxPostUrl,
			data: formData,
			success: function (response) {
				hideFormAndShowThankYou(response.success);
			},
			error: function () {
				console.log("Помилка під час відправки форми.");
			}
		});
	}

	openButtonsConnect.on("click", function () {
		$("#free-access-form h2").text(gettext("Зв’язатися з нами"));
		$("#access-form input[type='submit']").val(gettext("Зв’язатися з нами"));
		formSectionFree.show();
		thankYouMessage.hide();
	});

	openButtonsConsult.on("click", function () {
		$("#free-access-form h2").text(gettext("Проконсультуватися"));
		$("#access-form input[type='submit']").val(gettext("Проконсультуватися"));
		formSectionFree.show();
		thankYouMessage.hide();
	});

	accessForm.on("submit", function (e) {
		e.preventDefault();
		let formData = accessForm.serialize();
		let phoneInput = accessForm.find('#phone').val();
		let nameInput = accessForm.find('#name').val();
		$(".error-message").hide();
		$(".error-name").hide();

		if (!/^\+\d{1,3} \d{2,3} \d{2,3}-\d{2,3}-\d{2,3}$/.test(phoneInput)) {
			$(".error-message").show();
			return;
		}

		if (nameInput.trim() === "") {
			$(".error-name").show();
			return;
		}

		submitForm(formData);
	});
});

$.mask.definitions['9'] = '';
$.mask.definitions['d'] = '[0-9]';

function intlTelInit(phoneEl) {
	let phoneSelector = $(phoneEl);

	if (phoneSelector.length) {
		phoneSelector.mask("+380 dd ddd-dd-dd");
	}
}

$(document).ready(function () {
	intlTelInit('#phone');
	intlTelInit('#client-phone');

//  js investment page
	if ($(".investment-slider").length) {
		var investmentSlider = new Splide('.investment-slider', {
			type: 'loop',
			perPage: 1,
			autoplay: true,
		});

		investmentSlider.mount();

		var investmentParkSlider = new Splide('.investment-park-slider', {
			type: 'loop',
			perPage: 1,
			autoplay: true,
			arrows: false,
			pagination: false
		});

		investmentParkSlider.mount();
	}

	$(".learn-more-button").click(function (e) {
		sendData("#email-input");
		e.preventDefault();
	});

	function isValidEmail(email) {
		var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		return emailRegex.test(email);
	}

	function sendData(emailInputSelector) {
		var email = $(emailInputSelector).val();
		var emailError = $(".invest-btn-box .email-error");
		var modalEmailError = $(".modal-email-error");

		if (!isValidEmail(email)) {
			emailError.show();
			modalEmailError.show();
			return;
		}

		emailError.hide();
		modalEmailError.hide();

		$.ajax({
			type: "POST",
			url: ajaxPostUrl,
			data: {
				email: email,
				sender: 'investment',
				action: 'subscribe',
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
			},
			success: function (response) {
				if (response.success === true) {
					$("#thank-you-message").show();
					$("#InvestModal").hide();
					setTimeout(function () {
						$("#thank-you-message").hide();
					}, 5000);
				} else {
					$("#existing-you-message").show();
					$("#InvestModal").hide();
					setTimeout(function () {
						$("#existing-you-message").hide();
					}, 5000);
				}
			},
		});
	}
});

$(document).ready(function () {
	var consultationButton = $(".consultation-button button");
	var learnMoreButton = $(".investment-offer-section button");
	var investModal = $("#InvestModal");

	function openInvestModal() {
		investModal.show();
	}

	consultationButton.on("click", openInvestModal);
	learnMoreButton.on("click", openInvestModal);

	var closeFormAccessButton = $("#close-form-access");
	closeFormAccessButton.on("click", function () {
		investModal.hide();
	});

	var passwordInput = $('#password');
	var showPasswordCheckbox = $('#showPassword');

	showPasswordCheckbox.change(function () {
		if (showPasswordCheckbox.is(':checked')) {
			passwordInput.attr('type', 'text');
		} else {
			passwordInput.attr('type', 'password');
		}
	});

	$(this).on('click', '.free-access-button', function (event) {
		event.preventDefault();
		$.ajax(
			{
				type: "GET",
				url: ajaxGetUrl,
				data: {
					action: 'render_subscribe_form'
				},
				success: function (response) {
					$('#subscribeModalForm').html(response.data);
					$('#contact-me-form').show();
				}
			}
		);
	});

	$(this).on('click', '.subscribe-client', function (event) {
		console.log('click');
		event.preventDefault();
		const form = $(this).closest('form');
		const nameInput = form.find('#name').val();
		const phoneInput = form.find('#phone').val();
		const emailInput = form.find('#email').val();
		const theme = $(this).text();


		const fields = [
			{input: nameInput, error: '.error-name'},
			{input: phoneInput, error: '.error-phone'},
			{input: emailInput, error: '.error-email'}
		];

		for (const field of fields) {
			const input = field.input;
			const errorBlock = form.find(field.error);

			if (!input) {
				errorBlock.text("Це поле обов'язкове");
				errorBlock.show();
				return;
			} else {
				errorBlock.hide();
			}

			if (field.error === '.error-phone' && input.length !== 13 && input.length !== 17) {
				errorBlock.text("Введіть коректний номер телефону");
				errorBlock.show();
				return;
			}
		}

		$.ajax(
			{
				type: "POST",
				url: ajaxPostUrl,
				data: {
					action: 'subscribe_to_client',
					name: nameInput,
					phone: phoneInput,
					email: emailInput,
					theme: theme,
					csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
				},
				success: function (response) {
					console.log(response);
				}
			}
		);
	});

	$(this).on('click', '#close-form-contact', function (event) {
		event.preventDefault();
		$('#contact-me-form').hide();
	});
});