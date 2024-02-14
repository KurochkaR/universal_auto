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
		if ($(this).hasClass('add-button-bonus')) {
			var driver_id = $('.detail-driver-info').data('id');
			console.log(driver_id);
			openForm(null, null, 'bonus', driver_id);
		} else {
			openForm(null, null, 'penalty', driver_id);
		}
	});
});