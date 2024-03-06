var circularChart = echarts.init(document.getElementById('graphic-cash'));

var circularChartOptions = {
	tooltip: {
		trigger: 'item',
		formatter: '{b}: {c} ({d}%)'
	},
	legend: {
		show: false
	},
	series: [
		{
			type: 'pie',
			radius: ['40%', '70%'],
			avoidLabelOverlap: false,
			padAngle: 5,
			itemStyle: {
				borderRadius: 50
			},
			label: {
				show: false,
				position: 'center'
			},
			emphasis: {
				label: {
					show: true,
					fontSize: 40,
					fontWeight: 'bold'
				}
			},
			labelLine: {
				show: false
			},
			data: [
				{value: 1048, name: 'Готівка', itemStyle: {color: '#EC6323'}},
				{value: 735, name: 'Безготівка', itemStyle: {color: '#A1E8B9'}}
			],
		}
	]
};

circularChart.setOption(circularChartOptions);
$(document).ready(function () {
	checkCash();
	const bonusRadio = document.getElementById('driver-bonus-radio');
	const penaltyRadio = document.getElementById('driver-penalty-radio');
	const bonusBlock = document.querySelector('.driver-bonus-item');
	const penaltyBlock = document.querySelector('.driver-penalty-item');

	bonusRadio.addEventListener('change', function () {
		bonusBlock.style.display = 'block';
		penaltyBlock.style.display = 'none';
	});

	penaltyRadio.addEventListener('change', function () {
		penaltyBlock.style.display = 'block';
		bonusBlock.style.display = 'none';
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
		var confirmationText = isChecked ? "Ви точно бажаєте вимкнути готівку та автоматичне слідкування за нею?" :
			"Ви точно бажаєте увімкнути готівку та вимкнути автоматичне слідкування за нею?";

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
			$('.confirmation-cash-control h2').text("Ви точно бажаєте увімкнути автоматичне слібкування за готівкою?");
			$('#loader-confirmation-cash p').text("Зачекайти поки увімкнеться автоматичне слідкування за готівкою");
			$('.confirmation-cash-control').attr('id', 'cash-auto').show();
		} else {
			$('.switch-control').show()
			$('.status-cash').hide();
			$('.confirmation-cash-control h2').text("Ви точно бажаєте вимкнути автоматичне слібкування за готівкою?");
			$('#loader-confirmation-cash p').text("Зачекайти поки вимкнеться автоматичне слідкування за готівкою");
			$('.confirmation-cash-control').attr('id', 'cash-auto').show();
		}
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
				let interval = setInterval(function () {
					if (response.task_id) {
						$.ajax({
							url: ajaxGetUrl,
							type: 'GET',
							data: {
								action: 'check_task',
								task_id: response.task_id,
							},
							dataType: 'json',
							success: function (response) {
								if (response.data === 'success') {
									checkCash();
									clearInterval(interval);
									$('#loader-confirmation-cash').hide()
								}
							}
						});
					} else {
						checkCash();
						clearInterval(interval);
						$('#loader-confirmation-cash').hide()
					}
				}, 5000);
			}
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
