$(document).ready(function(){
	const bonusRadio = document.getElementById('driver-bonus-radio');
  const penaltyRadio = document.getElementById('driver-penalty-radio');
  const bonusBlock = document.querySelector('.driver-bonus-item');
  const penaltyBlock = document.querySelector('.driver-penalty-item');

  bonusRadio.addEventListener('change', function() {
    bonusBlock.style.display = 'block';
    penaltyBlock.style.display = 'none';
  });

  penaltyRadio.addEventListener('change', function() {
    penaltyBlock.style.display = 'block';
    bonusBlock.style.display = 'none';
  });

  $(this).on('click', '.back-page', function() {
  	window.history.back();
  });

	$(this).on('click', '.add-button-bonus, .add-button-penalty', function() {
		var driver_id = $('.detail-driver-info').data('id');
		if ($(this).hasClass('add-button-bonus')) {
			openForm(null, null, 'bonus', driver_id);
		} else {
			openForm(null, null, 'penalty', driver_id);
		}
	});

	$(this).on('click', '.edit-bonus-btn, .edit-penalty-btn', function() {
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

  $('input[name="driver-statistics"]').on('change', function() {
    if ($(this).is(':checked')) {
      sessionStorage.setItem('selectedRadioButton', $(this).val());
    }
  });
});