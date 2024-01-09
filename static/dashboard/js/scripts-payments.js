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

					var editButton = '<button class="edit-btn" title="Редагувати"><svg version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="35px" height="35px" viewBox="0 0 485.219 485.22" style="enable-background:new 0 0 485.219 485.22;" xml:space="preserve"><g><path d="M467.476,146.438l-21.445,21.455L317.35,39.23l21.445-21.457c23.689-23.692,62.104-23.692,85.795,0l42.886,42.897 C491.133,84.349,491.133,122.748,467.476,146.438z M167.233,403.748c-5.922,5.922-5.922,15.513,0,21.436 c5.925,5.955,15.521,5.955,21.443,0L424.59,189.335l-21.469-21.457L167.233,403.748z M60,296.54c-5.925,5.927-5.925,15.514,0,21.44 c5.922,5.923,15.518,5.923,21.443,0L317.35,82.113L295.914,60.67L60,296.54z M338.767,103.54L102.881,339.421 c-11.845,11.822-11.815,31.041,0,42.886c11.85,11.846,31.038,11.901,42.914-0.032l235.886-235.837L338.767,103.54z M145.734,446.572c-7.253-7.262-10.749-16.465-12.05-25.948c-3.083,0.476-6.188,0.919-9.36,0.919 c-16.202,0-31.419-6.333-42.881-17.795c-11.462-11.491-17.77-26.687-17.77-42.887c0-2.954,0.443-5.833,0.859-8.703 c-9.803-1.335-18.864-5.629-25.972-12.737c-0.682-0.677-0.917-1.596-1.538-2.338L0,485.216l147.748-36.986 C147.097,447.637,146.36,447.193,145.734,446.572z"/></g></svg></button>';
					var confirmButton = '<button class="apply-btn" title="Відправити водію"><svg fill="#000000" version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="35px" height="35px" viewBox="0 0 540.588 540.588"xml:space="preserve"><g><g><path d="M420.588,503.896V36.682C420.588,16.457,404.131,0,383.906,0H156.682C136.457,0,120,16.457,120,36.682v467.215c0,20.225,16.457,36.691,36.682,36.691h227.224C404.131,540.588,420.588,524.131,420.588,503.896z M406.244,503.896c0,12.326-10.012,22.348-22.338,22.348H156.682c-12.307,0-22.338-10.021-22.338-22.348V36.682c0-12.307,10.031-22.338,22.338-22.338h227.224c12.326,0,22.338,10.031,22.338,22.338V503.896L406.244,503.896z"/><path d="M388.468,59.651H152.13c-1.979,0-3.586,1.606-3.586,3.586V473.41c0,1.98,1.606,3.586,3.586,3.586h236.337c1.979,0,3.586-1.605,3.586-3.586V63.237C392.054,61.257,390.447,59.651,388.468,59.651z M375.319,469.824H165.279c-5.279,0-9.562-4.283-9.562-9.562V76.385c0-5.279,4.284-9.562,9.562-9.562h210.041c5.278,0,9.562,4.284,9.562,9.562v383.876C384.882,465.541,380.598,469.824,375.319,469.824z"/><path d="M250.127,37.81h40.344c1.979,0,3.586-1.606,3.586-3.586s-1.606-3.586-3.586-3.586h-40.344c-1.979,0-3.586,1.606-3.586,3.586S248.147,37.81,250.127,37.81z"/><path d="M290.949,485.191h-41.311c-8.481,0-15.386,6.904-15.386,15.377v2.467c0,8.482,6.914,15.387,15.386,15.387h41.311c8.481,0,15.386-6.914,15.386-15.387v-2.467C306.345,492.096,299.431,485.191,290.949,485.191z M299.173,503.035c0,4.533-3.682,8.215-8.214,8.215h-41.311c-4.522,0-8.214-3.691-8.214-8.215v-2.467c0-4.523,3.7-8.205,8.214-8.205h41.311c4.542,0,8.214,3.691,8.214,8.205V503.035z"/><path d="M210.328,327.268c-1.635,4.857-5.221,8.836-5.977,10.193c-0.498,0.908-0.564,1.893-0.382,2.715c0.172,0.709,0.994,3.012,4.293,3.012c3.461,0,22.156-3.805,33.364-13.348c4.025-3.424,7.478-7.373,9.122-7.545c1.654-0.182,5.25,3.318,9.037,7c7.774,7.572,18.962,13.07,31.91,15.566c5.183,0.994,11.666,5.068,15.815,8.33c10.031,7.869,25.609,11.035,28.573,11.035c2.582,0,3.863-1.551,4.198-3.004c0.191-0.803,0.134-1.768-0.345-2.658c-0.707-1.338-3.844-4.781-5.211-8.836c-1.368-4.055,1.932-8.758,6.636-11.158c15.645-8.004,25.293-21.248,25.293-35.641c0-23.943-26.594-43.432-59.259-43.432c-0.287,0-0.583,0.009-0.87,0.019c-0.479,0.019-2.133-3.529-4.647-7.401c-1.463-2.267-3.193-4.447-5.173-6.531c-12.384-12.986-33.23-20.75-55.75-20.75c-36.959,0-67.052,21.984-67.052,49.008c0,16.686,11.523,31.996,30.103,40.928C208.788,317.045,211.953,322.408,210.328,327.268z M308.611,270.18c-0.163-1.798,3.872-3.262,9.094-2.526c23.657,3.329,41.511,17.883,41.511,35.276c0,14.594-12.584,27.656-32.082,33.27c-1.903,0.553-3.041,2.484-2.592,4.398c0.622,2.715,1.253,5.201,1.894,7.439c1.167,4.082-1.74,6.195-6.531,3.996c-5.909-2.715-11.102-6.416-12.899-10.881c-0.526-1.35-1.808-2.258-3.252-2.334c-13.837-0.68-26.153-4.781-34.894-11.369c-4.217-3.176-2.668-7.508,2.295-9.305c22.616-8.176,37.601-25.494,37.601-44.705C308.755,272.359,308.707,271.27,308.611,270.18z M291.341,250.709c6.427,6.761,9.64,14.697,9.229,22.941c-1.062,22.232-24.882,40.123-55.396,41.625c-1.435,0.066-2.726,0.984-3.271,2.324c-2.391,5.957-9.84,10.547-17.232,13.627c-4.877,2.027-7.449-0.729-6.034-5.633c0.775-2.678,1.54-5.662,2.295-8.941c0.449-1.922-0.688-3.863-2.592-4.408c-22.472-6.475-36.959-21.555-36.959-38.422c0-22.921,26.728-41.568,59.594-41.568C261.496,232.273,280.325,239.158,291.341,250.709z"/><path d="M207.163,287.535c-1.951-0.545-3.596-0.746-3.882,0.162c-0.287,0.908,1.052,2.611,3.222,3.137c1.282,0.307,2.668,0.496,4.007,0.496c7.172,0,10.605-4.102,10.605-8.787c0-4.455-2.582-6.941-7.717-8.922c-4.198-1.615-6.053-3.021-6.053-5.862c0-2.065,1.587-4.552,5.737-4.552c1.109,0,2.104,0.144,2.955,0.345c1.597,0.382,3.002,0.382,3.299-0.507c0.296-0.88-0.832-2.372-2.706-2.754c-0.995-0.201-2.142-0.325-3.423-0.325c-5.9,0-9.821,3.509-9.821,8.243c0,4.237,3.06,6.856,8.033,8.655c4.092,1.539,5.718,3.203,5.718,5.996c0,3.068-2.333,5.182-6.35,5.182C209.524,288.041,208.291,287.859,207.163,287.535z"/><path d="M230.619,271.105c0.163-3.709,0.937-4.044,1.922-0.783c0.564,1.865,1.195,3.824,1.874,5.871c0,0,1.109,3.242,2.478,7.238c1.367,3.998,3.136,7.24,3.958,7.24c0.823,0,2.688-3.299,4.18-7.373l2.687-7.373c0.727-1.998,1.387-3.91,1.989-5.746c1.052-3.185,1.912-2.85,2.085,0.773c0.104,2.219,0.22,4.494,0.334,6.561c0,0,0.163,2.982,0.363,6.664c0.201,3.682,1.233,6.666,2.295,6.666c1.071,0,1.664-4.275,1.339-9.543l-0.698-11.285c-0.324-5.268-1.711-9.543-3.098-9.543s-3.71,3.29-5.202,7.344l-2.696,7.343c-0.641,1.799-1.215,3.48-1.731,5.088c-0.908,2.82-2.161,2.84-3.031,0.01c-0.497-1.625-1.042-3.318-1.645-5.098c0,0-1.157-3.289-2.592-7.343c-1.424-4.055-3.71-7.344-5.087-7.344s-2.802,4.275-3.175,9.543l-0.793,11.293c-0.373,5.27,0.163,9.545,1.195,9.545s2.056-2.918,2.276-6.514l0.411-6.512C230.409,275.619,230.523,273.324,230.619,271.105z"/><path d="M265.646,287.535c-1.95-0.545-3.586-0.746-3.873,0.162c-0.286,0.908,1.053,2.611,3.223,3.137c1.272,0.307,2.668,0.496,4.007,0.496c7.153,0,10.586-4.102,10.586-8.787c0-4.455-2.582-6.941-7.717-8.922c-4.188-1.615-6.034-3.021-6.034-5.862c0-2.065,1.568-4.552,5.719-4.552c1.118,0,2.113,0.144,2.964,0.345c1.606,0.392,3.013,0.382,3.309-0.507c0.297-0.88-0.832-2.372-2.706-2.754c-0.994-0.201-2.151-0.325-3.433-0.325c-5.9,0-9.821,3.509-9.821,8.243c0,4.237,3.079,6.856,8.033,8.655c4.111,1.539,5.718,3.203,5.718,5.996c0,3.068-2.333,5.182-6.35,5.182C267.999,288.041,266.775,287.859,265.646,287.535z"/></g></g></svg></button>';
					var arrowBtn = '<button class="arrow-btn"><svg version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="35px" height="35px" viewBox="0 0 459 459" style="enable-background:new 0 0 459 459;" xml:space="preserve"><g><g id="reply"><path d="M178.5,140.25v-102L0,216.75l178.5,178.5V290.7c127.5,0,216.75,40.8,280.5,130.05C433.5,293.25,357,165.75,178.5,140.25z" fill="#EC6323"/></g></g></svg></button>';
					var payByn = '<button class="pay-btn">Отримано</button>';
					var notPayByn = '<button class="not-pay-btn">Не отримано</button>';

					var buttonsColumn =
						'<div class="box-btn-upd">' + arrowBtn + '<div class="btnPay">' + payByn + notPayByn + '</div>' + '</div>';
					var rowBonus =
						'<td colspan="10" class="bonus-table"><table><tr><th>Тип</th><th>Сума</th><th>Опис</th><th>Дії</th></tr>';

					function generateRow(items, type, editClass, deleteClass) {
						var row = '';
						for (var j = 0; j < items.length; j++) {
							var item = items[j];
							row += '<tr>';
							row += '<td class="' + type + '-type" data-' + type + '-id="' + item.id + '">' + type.charAt(0).toUpperCase() + type.slice(1) + '</td>';
							row += '<td class="' + type +'-amount">' + item.amount + '</td>';
							row += '<td class="' + type +'-description">' + item.description + '</td>';
							row += '<td><button class="edit-' + type + '-btn" data-' + type + '-id="' + item.id + '" data-type="edit"><i class="fa fa-pencil-alt"></i></button> <button class="delete-' + type + '-btn" data-' + type + '-id="' + item.id + '" data-type="delete"><i class="fa fa-times"></i></button></td>';
							row += '</tr>';
						}
						return row;
					}

					rowBonus += generateRow(response[i].bonuses_list, 'bonus', 'edit-bonus-btn', 'delete-bonus-btn');
					rowBonus += generateRow(response[i].penalties_list, 'penalty', 'edit-penalty-btn', 'delete-penalty-btn');

					var row = $('<tr>');
					row.attr('data-id', response[i].id);
					row.append('<td>' + response[i].report_from + ' - ' + response[i].report_to + '</td>');
					row.append('<td class="driver-name">' + response[i].full_name + '</td>');
					row.append('<td>' + response[i].kasa + '</td>');
					row.append('<td>' + response[i].cash + '</td>');
					row.append('<td>' + response[i].rent + '</td>');
					row.append('<td>' + response[i].bonuses + '</td>');
					row.append('<td>' + response[i].penalties + '</td>');
					row.append('<td>' + response[i].earning + '</td>');
					row.append('<td>' + response[i].status + '</td>');
					row.append('<td>' + editButton + confirmButton + buttonsColumn + '</td>');

					tableBody.append(row);
					tableBody.append(rowBonus);

					$('.send-all-button').show();
					if (response[i].status === 'Очікується') {
						if (response[i].earning < 0) {
							row.find('.edit-btn, .apply-btn').hide();
							row.find('.box-btn-upd').css('display', 'flex');
						} else {
							row.find('.edit-btn, .apply-btn').hide();
							row.find('.box-btn-upd').css('display', 'flex');
							row.find('.not-pay-btn').hide();
							row.find('.pay-btn').text('Сплатити');
						}
						$('.send-all-button').hide();
					} else if (response[i].status === 'Виплачений' || response[i].status === 'Не сплачений') {
						row.find('.edit-btn, .apply-btn').hide();
						row.find('.box-btn-upd').hide();
						row.find('.arrow-btn').hide();
						$('.send-all-button').hide();
					}
				}
			}

			$('.bonus-table').on('click', '.edit-bonus-btn, .delete-bonus-btn, .edit-penalty-btn, .delete-penalty-btn', function () {
				var itemId, actionType, itemType;

				if ($(this).hasClass('edit-bonus-btn') || $(this).hasClass('edit-penalty-btn')) {
					actionType = 'edit';
					itemAmount = $(this).closest('tr').find('.bonus-amount').text();
					itemDescription = $(this).closest('tr').find('.bonus-description').text();
				} else if ($(this).hasClass('delete-bonus-btn') || $(this).hasClass('delete-penalty-btn')) {
					actionType = 'delete';
				}

				if ($(this).hasClass('edit-bonus-btn') || $(this).hasClass('delete-bonus-btn')) {
					itemId = $(this).data('bonus-id');
					itemType = 'bonus';
				} else if ($(this).hasClass('edit-penalty-btn') || $(this).hasClass('delete-penalty-btn')) {
					itemId = $(this).data('penalty-id');
					itemType = 'penalty';
				}
				if (actionType === 'delete') {
					processAction(actionType, itemId, itemType, null, null);
				} else {
				$('#modal-upd-bonus').show();
				$('#modal-upd-bonus .modal-content').attr('data-id', itemId);
				$('#modal-upd-bonus .modal-content').attr('data-type', itemType);
				$('#modal-upd-bonus .modal-content').attr('data-action', actionType);
				$('#modal-upd-bonus').find('.bonus-amount').val(itemAmount);
				$('#modal-upd-bonus').find('.bonus-description').val(itemDescription);
				}
			});
		}
	});

	$('.driver-table tbody').on('click', '.driver-name', function () {
		var row = $(this).closest('tr');
		var bonusTable = row.next('.bonus-table');

		if (bonusTable.is(':visible')) {
			bonusTable.hide();
		} else {
			$('.bonus-table').hide();
			bonusTable.show();
		}
	});
}

$(document).ready(function () {
	driverPayment(null, null, null, paymentStatus="on_inspection");

	$('input[name="payment-status"]').change(function() {
    if ($(this).val() === 'closed') {
      driverPayment(period='current_quarter', null, null, paymentStatus=$(this).val());
      $('.filter-driver-payments').css('display', 'flex');
    } else {
      driverPayment(null, null, null, paymentStatus=$(this).val());
      $('.filter-driver-payments').hide();
    }
  });

  function initializeCustomSelect(customSelect, selectedOption, optionsList, iconDown, datePicker) {
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

	const customSelectDriver = $(".custom-select-drivers");
	const selectedOptionDriver = customSelectDriver.find(".selected-option-drivers");
	const optionsListDriver = customSelectDriver.find(".options-drivers");
	const iconDownDriver = customSelectDriver.find(".fas.fa-angle-down");
	const datePickerDriver = $("#datePickerDriver");

	initializeCustomSelect(customSelectDriver, selectedOptionDriver, optionsListDriver, iconDownDriver, datePickerDriver);

	$('.shift-close-btn').off('click').on('click', function (e) {
  	e.preventDefault();
		$('#modal-upd-payments').hide();
		$('#modal-upd-bonus').hide();
	});

	$('.driver-table tbody').on('click', '.edit-btn', function () {
		var id = $(this).closest('tr').data('id');
		$('#modal-upd-payments').show();
		$('#modal-upd-payments').data('id', id);
		$(this).data('id', id);
	});

	$('#modal-upd-payments').on('click', '.upd-payments-btn', function () {
		var id = $('#modal-upd-payments').data('id');

		var bonusAmount = $('#bonus-amount').val();
		var bonusDescription = $('#bonus-description').val();
		var penaltyAmount = $('#penalty-amount').val();
		var penaltyDescription = $('#penalty-description').val();

		var dataToSend = {
			id: id,
			bonusAmount: bonusAmount,
			bonusDescription: bonusDescription,
			penaltyAmount: penaltyAmount,
			penaltyDescription: penaltyDescription,
			action: 'upd-payments',
			csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
		};

		$.ajax({
			url: ajaxPostUrl,
			type: 'POST',
			data: dataToSend,
			dataType: 'json',
			success: function (response) {
				$('#modal-upd-payments').hide();
				driverPayment(null, null, null, paymentStatus="on_inspection");
			}
		});
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

	$('.driver-table tbody').on('click', '.pay-btn', function () {
    var id = $(this).closest('tr').data('id');
    var status = 'completed';
    $(".confirmation-box h2").text("Ви впевнені, що хочете закрити платіж ?");
    $(".confirmation-update-database").show();
    $("#confirmation-btn-on").data('id', id).data('status', status);
	});


	$('.driver-table tbody').on('click', '.not-pay-btn', function () {
		var id = $(this).closest('tr').data('id');
		var status = 'failed';
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

  $('#edit-button-bonus-penalty').on('click', function () {
  	var id = $('#modal-upd-bonus .modal-content').data('id');
		var type = $('#modal-upd-bonus .modal-content').data('type');
		var action = $('#modal-upd-bonus .modal-content').data('action');
		var amount = $('#modal-upd-bonus .bonus-amount').val();
		var description = $('#modal-upd-bonus .bonus-description').val();

		var dataToSend = {
			action: "upd_delete_bonus_penalty",
			id: id,
			type: type,
			action_type: action,
			amount: amount,
			description: description,
			csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
		};

		updBonusPenalty(dataToSend);
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

function updBonusPenalty(dataToSend) {
	$.ajax({
		url: ajaxPostUrl,
		type: 'POST',
		data: dataToSend,
		dataType: 'json',
		success: function (response) {
			$('#modal-upd-bonus').hide();
			driverPayment(null, null, null, paymentStatus="on_inspection");
		}
	});
}

function processAction(actionType, itemId, itemType) {
	dataToSend = {
		action: "upd_delete_bonus_penalty",
		id: itemId,
		type: itemType,
		action_type: actionType,
		csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
	};

	updBonusPenalty(dataToSend);
}