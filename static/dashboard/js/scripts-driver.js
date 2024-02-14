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
});