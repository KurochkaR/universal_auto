$(document).ready(function () {

	$(document).on('click', 'th.sortable', function () {
		let column = $(this).data('sort');
		let sortOrder = $(this).hasClass('sorted-asc') ? 'sorted-desc' : 'sorted-asc';
		$('.driver-efficiency-table').find('th.sortable').removeClass('sorted-asc sorted-desc');
		$(this).addClass(sortOrder);
		sortTable(column, sortOrder);
	});

	initializeCustomSelect(function(clickedValue) {
        if (sessionStorage.getItem('selectedOption') === 'driver-efficiency') {
            var aggregatorsString = checkedAggregators()
            if (aggregatorsString === "shared") {
                $('th[data-sort="idling-mileage"]').show();
                fetchDriverEfficiencyData(clickedValue);
            } else {
                fetchDriverFleetEfficiencyData(clickedValue, aggregatorsString);
            }
        }
    });

    $(this).on('click', '.apply-filter-button', function() {
        if (sessionStorage.getItem('selectedOption') === 'driver-efficiency') {
            applyDateRange(function(selectedPeriod, startDate, endDate) {
            var aggregatorsString = checkedAggregators()
            if (aggregatorsString === "shared") {
                $('th[data-sort="idling-mileage"]').show();
                fetchDriverEfficiencyData(selectedPeriod, startDate, endDate);
            } else {
                fetchDriverFleetEfficiencyData(selectedPeriod, aggregatorsString, startDate, endDate);
            }
            });
        }
    })

	$(this).on('change', '.checkbox-container input[type="checkbox"]', function () {
		var checkboxId = $(this).attr('id');
        var sharedCheckbox = $('#sharedCheckbox');

		if (checkboxId === 'sharedCheckbox' && $(this).prop('checked')) {
			$('.checkbox-container input[type="checkbox"]').not(this).prop('checked', false);
		} else {
			$('#sharedCheckbox').prop('checked', false);
		}

		var anyOtherCheckboxChecked = $('.checkbox-container input[type="checkbox"]:not(#sharedCheckbox):checked').length > 0;
		if (!anyOtherCheckboxChecked) {
			sharedCheckbox.prop('checked', true);
		}
		checkSelection();
	});
});

function checkSelection() {
	var selectedPeriod = $('#period .selected-option').data('value');
	var startDate = $("#start_report").val();
	var endDate = $("#end_report").val();
    var aggregatorsString = checkedAggregators()
    if (aggregatorsString === "shared") {
		    $('th[data-sort="idling-mileage"]').show();
			fetchDriverEfficiencyData(selectedPeriod, startDate, endDate);
		} else {
			$('th[data-sort="idling-mileage"]').hide();
			fetchDriverFleetEfficiencyData(selectedPeriod, aggregatorsString, startDate, endDate);
		}
}

function checkedAggregators() {
    aggregators = $('.checkbox-container input[type="checkbox"]:checked').map(function () {
				return $(this).val();
			}).get();

	return aggregators.join('&');
}