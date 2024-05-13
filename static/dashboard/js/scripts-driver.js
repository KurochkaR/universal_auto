// var circularChart = echarts.init(document.getElementById('graphic-cash'));
//
// var circularChartOptions = {
// 	tooltip: {
// 		trigger: 'item',
// 		formatter: '{b}: {c} ({d}%)'
// 	},
// 	legend: {
// 		show: false
// 	},
// 	series: [
// 		{
// 			type: 'pie',
// 			radius: ['40%', '70%'],
// 			avoidLabelOverlap: false,
// 			padAngle: 5,
// 			itemStyle: {
// 				borderRadius: 50
// 			},
// 			label: {
// 				show: false,
// 				position: 'center'
// 			},
// 			emphasis: {
// 				label: {
// 					show: true,
// 					fontSize: 40,
// 					fontWeight: 'bold'
// 				}
// 			},
// 			labelLine: {
// 				show: false
// 			},
// 			data: [
// 				{value: 1048, name: 'Готівка', itemStyle: {color: '#EC6323'}},
// 				{value: 735, name: 'Безготівка', itemStyle: {color: '#A1E8B9'}}
// 			],
// 		}
// 	]
// };
//
// circularChart.setOption(circularChartOptions);
$(document).ready(function () {
	checkCash();
	$('.debt-repayment-input').val(function (i, value) {
		return value.replace(',', '.');
	});
	const bonusRadio = document.getElementById('driver-bonus-radio');
	const penaltyRadio = document.getElementById('driver-penalty-radio');
	const bonusBlock = document.querySelector('.driver-bonus-item');
	const penaltyBlock = document.querySelector('.driver-penalty-item');

	bonusRadio.addEventListener('change', function () {
		bonusBlock.style.display = 'block';
		penaltyBlock.style.display = 'none';
		$('.driver-bonus-penalty-info').css('background', '#DEF7E7');
	});

	penaltyRadio.addEventListener('change', function () {
		penaltyBlock.style.display = 'block';
		bonusBlock.style.display = 'none';
		$('.driver-bonus-penalty-info').css('background', 'rgba(236, 99, 35, 0.2)');
	});

	$(this).on('click', '.back-page', function () {
		window.history.back();
	});

	$(this).on('click', '.add-button-bonus, .add-button-penalty', function () {
		var driver_id = $('.detail-driver-info').data('id');
		if ($(this).hasClass('add-button-bonus')) {
			openForm(null, null, 'bonus', driver_id);
		} else {
			openForm(null, null, 'penalty', driver_id);
		}
	});

	$(this).on('click', '.edit-bonus-btn, .edit-penalty-btn', function () {
		var itemId = $(this).data('id');
		var driver_id = $('.detail-driver-info').data('id');
		if ($(this).hasClass('edit-bonus-btn')) {
			itemType = 'bonus';
			openForm(null, itemId, itemType, driver_id);
		} else {
			itemType = 'penalty';
			openForm(null, itemId, itemType, driver_id);
		}
	});

	$(this).on('click', '.delete-bonus-penalty-btn', function () {
		var $button = $(this);
		if ($button.hasClass('disabled')) {
			return;
		}
		$button.addClass('disabled');
		itemId = $(this).data('id');
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
				window.location.reload();
			}
		});
	});

	const selectedButton = sessionStorage.getItem('selectedRadioButton');
	const defaultSelectedButton = localStorage.getItem('selectedRadioButton');
	if (!selectedButton && defaultSelectedButton) {
		sessionStorage.setItem('selectedRadioButton', defaultSelectedButton);
	} else if (!selectedButton && !defaultSelectedButton) {
		sessionStorage.setItem('selectedRadioButton', 'driver-bonus');
	}

	if (selectedButton) {
		$(`input[name="driver-statistics"][value="${selectedButton}"]`).click();
	}

	$('input[name="driver-statistics"]').on('change', function () {
		if ($(this).is(':checked')) {
			sessionStorage.setItem('selectedRadioButton', $(this).val());
		}
	});

	var previousState;
	var previousAutoState;

	$('#switch-cash').change(function () {
		var isChecked = $(this).prop('checked');
		previousState = !isChecked;
		previousAutoState = false
		var confirmationText = isChecked ? "Ви точно бажаєте вимкнути готівку?" :
			"Ви точно бажаєте увімкнути готівку";

		$('.confirmation-cash-control h2').text(confirmationText);
		$('#loader-confirmation-cash p').text(isChecked ? "Зачекайти поки вимкнеться готівка" : "Зачекайти поки увімкнеться готівка");
		$('.confirmation-cash-control').attr('id', 'cash').show();
	});

	$(this).on('click', '.cash-control-auto input[type="checkbox"]', function () {
		var isChecked = $(this).prop('checked');
		previousAutoState = !isChecked;
		if (isChecked) {
			$('.switch-control').hide()
			$('.status-cash').show();
			$('.confirmation-cash-control h2').text("Ви точно бажаєте увімкнути автоматичне слідкування за готівкою?");
			$('#loader-confirmation-cash p').text("Зачекайте поки увімкнеться автоматичне слідкування за готівкою");
		} else {
			$('.switch-control').show()
			$('.status-cash').hide();
			$('.confirmation-cash-control h2').text("Ви точно бажаєте вимкнути автоматичне слідкування за готівкою?");
			$('#loader-confirmation-cash p').text("Зачекайте поки вимкнеться автоматичне слідкування за готівкою");
		}
		$('.confirmation-cash-control').attr('id', 'cash-auto').show();
	});

	$(document).on('click', '#confirmation-btn-on', function () {
		const confirmationControl = $('.confirmation-cash-control');
		const checkBoxId = confirmationControl.attr('id');
		const isChecked = $('#switch-cash').prop('checked') ? 0 : 1;
		const isAutoChecked = $('.cash-control-auto input[type="checkbox"]').prop('checked') ? 1 : 0;
		confirmationControl.hide();
		$('#loader-confirmation-cash').show()
		$.ajax({
			url: ajaxPostUrl,
			type: 'POST',
			data: {
				action: checkBoxId === 'cash' ? 'switch_cash' : 'switch_auto_cash',
				driver_id: $('.detail-driver-info').data('id'),
				pay_cash: checkBoxId === 'cash' ? isChecked : isAutoChecked,
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
			},
			dataType: 'json',
			success: function (response) {
				if (response.task_id) {
					checkTaskStatus(response.task_id)
						.then(function (response) {
							if (response.data === 'SUCCESS') {
								// message
							} else {
								// message
							}
							checkCash();
							$('#loader-confirmation-cash').hide()
						})
						.catch(function (error) {
							console.error('Error:', error)
						})
				} else {
					checkCash();
					$('#loader-confirmation-cash').hide()
				}
			},

		});
	});


	$(document).on('click', '#confirmation-btn-off', function () {
		$('.confirmation-cash-control').hide();
		checkCash();
	});
});

function checkCash() {
	$.ajax({
		url: ajaxGetUrl,
		type: 'GET',
		data: {
			action: 'check_cash',
			driver_id: $('.detail-driver-info').data('id')
		},
		dataType: 'json',
		success: function (response) {
			$('#cash-percent').val(response.cash_rate);

			if (response.cash_control === true) {
				$('.switch-auto input[type="checkbox"]').prop('checked', true);
				$('.switch-control').hide()
				$('.status-cash').show();
				$('.status-cash .circle').css('background', response.pay_cash > 0 ? '#A1E8B9' : '#EC6323');
			} else {
				$('.switch-auto input[type="checkbox"]').prop('checked', false);
				$('.switch-control').show()
				$('.status-cash').hide();
			}
			$('#switch-cash').prop('checked', !response.pay_cash);
		}
	});
}


$(document).ready(function () {
	var cashPercent = $('#cash-percent');
	cashPercent.focus(function () {
		$('.confirm-button').css('display', 'block');
		$('.edit-icon').hide();
		$('.cansel-icon').show().css('color', '#EC6323');
	});

	cashPercent.blur(function (event) {
		setTimeout(function () {
			if (!$(event.relatedTarget).hasClass('confirm-button')) {
				$('.confirm-button').css('display', 'none');
				$('.edit-icon').show().css('color', '#A1E8B9');
				$('.cansel-icon').hide();
				checkCash();
			}
		}, 100);
	});

	$(this).on('click', '.confirm-button', function () {
		$.ajax({
			url: ajaxPostUrl,
			type: 'POST',
			data: {
				action: 'change_cash_percent',
				driver_id: $('.detail-driver-info').data('id'),
				cash_percent: cashPercent.val(),
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
			},
			dataType: 'json',
			success: function (response) {
				$('.confirm-button').css('display', 'none');
				$('.edit-icon').show()
				$('.cansel-icon').hide();
				checkCash();
			}
		});
	});

	$(this).on("keypress", "#cash-percent", function (e) {
		if (e.which === 13) {
			$('.confirm-button').click();
			cashPercent.blur();
		}
	});


	$(this).on('click', '.cansel-icon', function () {
		$('.confirm-button').css('display', 'none');
		$('.edit-icon').html('&#9998;').css('color', '#A1E8B9');
	});

	$(document).on('click', '.edit-icon', function () {
		cashPercent.focus();
	});

	$(this).on("input", ".debt-repayment-input", function () {
		var penaltyAmount = $(this).closest('.driver-bonus-penalty-info').find('.penalty-amount span').text();
		validNumberInput(parseFloat(penaltyAmount.replace(',', '.')), $(this));
	});

	$(this).on("input", "#cash-percent", function () {
		validNumberInput(100, $(this));
	});

	function getCategory(element) {
		return $(element).find('.penalty-category span').text();
	}

	$(document).on('click', function (event) {
		if (!$(event.target).closest('.debt-repayment-input-container').length) {
			var $input = $('.debt-repayment-input-container:visible');
			$input.hide();
			var category = $input.closest('.driver-bonus-penalty-info').find('.penalty-category span').text();
			if (category !== 'Борг по виплаті') {
				$input.closest('.driver-bonus-penalty-info').find('.edit-penalty-btn, .delete-bonus-penalty-btn').show();
			}
			$('.debt-repayment-btn').show();
		}
	});

	$(this).on('click', '.debt-repayment-btn', function (event) {
		event.stopPropagation();
		var $container = $(this).closest('.driver-bonus-penalty-info');

		$(this).hide();
		var $input = $('.debt-repayment-input-container:visible');
		$input.hide();
		var category = $input.closest('.driver-bonus-penalty-info').find('.penalty-category span').text();
		if (category !== 'Борг по виплаті') {
			$input.closest('.driver-bonus-penalty-info').find('.edit-penalty-btn, .delete-bonus-penalty-btn, .debt-repayment-btn').show();
		} else {
			$input.closest('.driver-bonus-penalty-info').find('.debt-repayment-btn').show();
		}
		$container.find('.debt-repayment-input-container').css('display', 'flex');
		$container.find('.edit-penalty-btn, .delete-bonus-penalty-btn').hide();
		$('.debt-repayment-input-container').find('input[type="text"]').focus();
	});

	$('.debt-repayment-input-container').find('input[type="text"]').on('keydown', function (event) {
		if (event.which === 13) {
			$(this).closest('.driver-bonus-penalty-info').find('.debt-repayment-input-container i').click();
		}
	});

	$('.driver-bonus-penalty-info').each(function () {
		var $this = $(this);
		var category = getCategory($this);

		$this.find('.debt-repayment-btn').show().css('width', category === 'Борг по виплаті' ? '165px' : 'auto');
		$this.find('.edit-penalty-btn, .delete-bonus-penalty-btn').toggle(category !== 'Борг по виплаті');
	});

	const confirmationDebt = $('.confirmation-debt-repayment');
	$(document).on('click', '.debt-repayment-input-container i', function () {
		const driversDebt = parseFloat($(this).closest('.driver-bonus-penalty-info').find('.penalty-amount span').text());
		const repaymentDebt = parseFloat($(this).closest('.debt-repayment-input-container').find('input').val());
		const penalty_id = $(this).closest('.driver-bonus-penalty-info').data('id');

		if (driversDebt === repaymentDebt) {
			$('.confirmation-debt-repayment h2').text('Ви впевнені, що хочете закрити штраф?');
		} else {
			$('.confirmation-debt-repayment h2').text('Водій повернув ' + repaymentDebt + ' ₴ штрафу?');
		}

		confirmationDebt.attr('data-repayment', driversDebt === repaymentDebt ? driversDebt : repaymentDebt);
		confirmationDebt.attr('data-penalty_id', penalty_id);
		confirmationDebt.show();
	});


	$('#debt-repayment-on').click(function () {
		$.ajax({
			url: ajaxPostUrl,
			type: 'POST',
			data: {
				action: 'debt_repayment',
				penalty_id: confirmationDebt.data('penalty_id'),
				debt_repayment: confirmationDebt.data('repayment'),
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
			},
			dataType: 'json',
			success: function (response) {
				window.location.reload();
			}
		});
	});

	$('#debt-repayment-off').click(function () {
		$('.confirmation-debt-repayment').hide();
	});

});


