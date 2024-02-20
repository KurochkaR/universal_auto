function formatTime(time) {
	let parts = time.match(/(\d+) days?, (\d+):(\d+):(\d+)/);

	if (!parts) {
		return time;
	} else {
		let days = parseInt(parts[1]);
		let hours = parseInt(parts[2]);
		let minutes = parseInt(parts[3]);
		let seconds = parseInt(parts[4]);

		hours += days * 24;

		// Форматувати рядок у вигляді HH:mm:ss
		return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
	}
}

function applyDateRange() {
	let startDate = $("#start_report").val();
	let endDate = $("#end_report").val();

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
	const firstVehicle = $(".custom-dropdown .dropdown-options li:first");
	const vehicleId = firstVehicle.data('value');
	const vehicle_lc = firstVehicle.text();
	const selectedPeriod = 'custom';
	$(".apply-filter-button").prop("disabled", true);
	fetchSummaryReportData(selectedPeriod, startDate, endDate);
	fetchCarEfficiencyData(selectedPeriod, vehicleId, vehicle_lc, startDate, endDate);
}


// ---------- CHARTS ---------- //

var barChart = echarts.init(document.getElementById('bar-chart'));

// BAR CHART
let barChartOptions = {
  grid: {
    height: '70%'
  },
  xAxis: {
    type: 'category',
    data: [],
    axisLabel: {
      rotate: 45
    }
  },
  yAxis: {
    type: 'value',
    name: gettext('Сума (грн.)'),
    nameLocation: 'middle',
    nameRotate: 90,
    nameGap: 60,
    nameTextStyle: {
      fontSize: 18,
    }
  },
  dataZoom: [
    {
      type: 'slider',
      start: 1,
      end: 100,
      showDetail: false,
      backgroundColor: 'white',
      dataBackground: {
        lineStyle: {
          color: 'orange',
          width: 5
        }
      },
      selectedDataBackground: {
        lineStyle: {
          color: 'rgb(255, 69, 0)',
          width: 5
        }
      },
      handleStyle: {
        color: 'orange',
        borderWidth: 0
      },
    }
  ],
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'shadow'
    },
    formatter: function(params) {
      let category = params[0].axisValue;
      let cash = parseFloat(params[0].value);
			let card = parseFloat(params[1].value);
			let total = (cash + card).toFixed(2);
      let cashColor = '#EC6323';
      let cardColor = '#A1E8B9';
      return (
        category +
        ':<br>' +
        '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background-color:' +
        cardColor +
        '"></span> Карта: ' +
        card +
        ' грн.<br>' +
        '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background-color:' +
        cashColor +
        '"></span> Готівка: ' +
        cash +
        ' грн.<br>' +
        'Весь дохід: ' +
        total +
        ' грн.'
      );
    }
  },
  series: [
    {
      name: 'cash',
      type: 'bar',
      stack: 'total',
      label: {
        focus: 'series'
      },
      itemStyle: {
        color: '#EC6323'
      },
      data: []
    },
    {
      name: 'card',
      type: 'bar',
      stack: 'total',
      label: {
        focus: 'series'
      },
      itemStyle: {
        color: '#A1E8B9'
      },
      data: []
    },
  ]
};

barChart.setOption(barChartOptions);


// AREA CHART

var areaChart = echarts.init(document.getElementById('area-chart'));

let areaChartOptions = {
	xAxis: {
    type: 'category',
    boundaryGap: false,
    data: [],
  },
  yAxis: {
    type: 'value'
  },
  dataZoom: [
    {
      type: 'slider',
      start: 1,
      end: 100,
      showDetail: false,
      backgroundColor: 'white',
      dataBackground: {
        lineStyle: {
          color: 'orange',
          width: 5
        }
      },
      selectedDataBackground: {
        lineStyle: {
          color: 'rgb(255, 69, 0)',
          width: 5
        }
      },
      handleStyle: {
        color: 'orange',
        borderWidth: 0
      },
    }
  ],
  series: [
    {
      data: [],
      type: 'line',
      symbol: 'circle',
      symbolSize: 10,
      lineStyle: {
        color: '#79C8C5',
        width: 5
      },
      itemStyle: {
        color: '#18A64D'
      },
      areaStyle: {
        color: '#A1E8B9'
      }
    }
  ],
  tooltip: {
    trigger: 'axis',
    formatter: function (params) {
      return gettext('Дата: ') + params[0].name + '<br/>' + params[0].seriesName + ' : ' + params[0].value + gettext(' грн/км')
    }
  }
};

areaChart.setOption(areaChartOptions);

// BAR CHART 2
var threeChart = echarts.init(document.getElementById('bar-three-chart'));

let threeChartOptions = {
    grid: {
        height: '70%'
        },
	xAxis: {
  type: 'category',
  data: [],
  axisLabel: {
      rotate: 45
    }
  },
  yAxis: {
    type: 'value'
  },
  dataZoom: [
    {
      type: 'slider',
      start: 1,
      end: 100,
      showDetail: false,
      backgroundColor: 'white',
      dataBackground: {
        lineStyle: {
          color: 'orange',
          width: 5
        }
      },
      selectedDataBackground: {
        lineStyle: {
          color: 'rgb(255, 69, 0)',
          width: 5
        }
      },
      handleStyle: {
        color: 'orange',
        borderWidth: 0
      },
    }
  ],
  series: [
    {
      data: [],
      type: 'bar',
      itemStyle: {
        color: '#A1E8B9'
      }
    }
  ],
  tooltip: {
    show: true,
    trigger: 'axis',
    axisPointer: {
      type: 'shadow'
    },
    formatter: function (params) {
      return 'Автомобіль: ' + params[0].name + '<br/>Ефективність: ' + params[0].value;
    }
  }
}

threeChart.setOption(threeChartOptions);

// ---------- END CHARTS ---------- //

function fetchSummaryReportData(period, start, end) {
	let apiUrl;
	if (period === 'custom') {
		apiUrl = `/api/reports/${start}&${end}/`;
	} else {
		apiUrl = `/api/reports/${period}/`;
	};
	$.ajax({
		url: apiUrl,
		type: 'GET',
		dataType: 'json',
		success: function (data) {
			console.log(data[0]["kasa"]);
			$(".apply-filter-button").prop("disabled", false);
			let startDate = data[0]['start'];
			let endDate = data[0]['end'];
			let totalDistance = data[0]['total_rent'];
			if (data[0]['drivers'].length !== 0) {
				$(".noDataMessage1").hide();
				$('#bar-chart').show();
				const driversData = data[0]['drivers'];
				const categories = driversData.map(driver => driver.full_name);
				const formattedNamesList = [];
				categories.forEach(name => {
					if (name.includes('-')) {
							const formattedName = name.replace('-', '-\n');
							formattedNamesList.push(formattedName);
					} else if (name.length > 15) {
							const halfLength = Math.floor(name.length / 2);
							const formattedName = name.substring(0, halfLength) + '-\n' + name.substring(halfLength);
							formattedNamesList.push(formattedName);
					} else {
							formattedNamesList.push(name);
					}
			});
				const total_card = driversData.map(driver => driver.total_card);
				const total_cash = driversData.map(driver => driver.total_cash);
				barChartOptions.series[1].data = total_card;
				barChartOptions.series[0].data = total_cash;
				barChartOptions.xAxis.data = formattedNamesList;
				barChart.setOption(barChartOptions);
			} else {
				$(".noDataMessage1").show();
				$('#bar-chart').hide();
			}
			;
			if (period === 'yesterday') {
				$('.weekly-income-dates').text(startDate);
			} else {
				$('.weekly-income-dates').text(gettext('З ') + startDate + ' ' + gettext('по') + ' ' + endDate);
			}
			$('.weekly-income-rent').text(totalDistance);
			$('.weekly-income-amount').text(data[0]["kasa"]);
			$('.not-closed-payments').text(data[0]["total_payment"]);
			$('.weekly-spending-driver').text(data[0]["total_driver_spending"]);
			$('.weekly-spending-vehicle').text(data[0]["total_vehicle_spending"]);

			const driversWithPayments = data[0]['drivers'].filter(driver => driver.payment_amount !== null);
			const table = $('.driver-table');

			table.find('tbody').empty();

			driversWithPayments.forEach(driver => {
				const row = $('<tr></tr>');

				row.append(`<td>${driver.full_name}</td>`);
				row.append(`<td>${driver.payment_amount}</td>`);

				table.append(row);
			});
		},
		error: function (error) {
			console.error(error);
		}
	});
}

function fetchCarEfficiencyData(period, vehicleId, vehicle_lc, start, end) {
	let apiUrl;
	if (period === 'custom') {
		apiUrl = `/api/car_efficiencies/${start}&${end}/${vehicleId}`;
	} else {
		apiUrl = `/api/car_efficiencies/${period}/${vehicleId}`;
	};

	$.ajax({
		url: apiUrl,
		type: 'GET',
		dataType: 'json',
		success: function (data) {
			if (data['dates'].length !== 0) {
				$(".noDataMessage2").hide();
				$('#area-chart').show();
				$('#bar-three-chart').show();
				$('.car-select').show();

				let firstVehicleData = {
					name: vehicle_lc,
					data: data['vehicles'].efficiency
				};

				let seriesData = [firstVehicleData];

				areaChartOptions.series = seriesData;
				areaChartOptions.xAxis.data = data['dates'];
				areaChart.setOption(areaChartOptions);

				let averageEff = data['vehicles'].average_eff;
				let vehicleNames = Object.keys(averageEff);
				let vehicleEff = Object.values(averageEff);

				threeChartOptions.series[0].data = vehicleEff;
				threeChartOptions.xAxis.data = vehicleNames;
				threeChart.setOption(threeChartOptions);
			} else {
				$(".noDataMessage2").show();
				$('#area-chart').hide();
				$('#bar-three-chart').hide();
				$('.car-select').css('display', 'contents');
			};
			$('.weekly-clean-amount').text(data["earning"].toFixed(2));
			$('.income-km').text(data["total_mileage"].toFixed(2));
			$('.income-efficiency').text(data["average_efficiency"].toFixed(2));
		},
		error: function (error) {
			console.error(error);
		}
	});
}

function showDatePicker(periodSelectId, datePickerId) {
	let periodSelect = $("#" + periodSelectId);
	let datePicker = $("#" + datePickerId);

	if (periodSelect.val() === "custom") {
		datePicker.css("display", "block");
	} else {
		datePicker.css("display", "none");
	}
}

function getUrlCalendar(){
	let url = window.location.href;
	let urlArr = url.split('#');
	let urlCalendar = urlArr[urlArr.length - 1];
	return urlCalendar
}

$(document).ready(function () {

	$(".sidebar-list-item.admin").on("click", function () {

		let adminPanelURL = $(this).data("url");

		if (adminPanelURL) {
			window.open(adminPanelURL, "_blank");
		}
	});

	$("#logout-dashboard").click(function () {
		$.ajax({
			type: "POST",
			url: ajaxPostUrl,
			data: {
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
				action: "logout_invest",
			},
			success: function (response) {
				if (response.logged_out === true) {
					window.location.href = "/";
				}
			}
		});
	});

	function initializeCustomSelect(customSelect, selectedOption, optionsList, iconDown, datePicker, vehicleId, vehicle_lc) {
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
				if (vehicle_lc) {
					fetchSummaryReportData(clickedValue);
					fetchCarEfficiencyData(clickedValue, vehicleId, vehicle_lc);
				} else {
					fetchDriverEfficiencyData(clickedValue);
				}
			}

			if (clickedValue === "custom") {
				datePicker.css("display", "block");
			} else {
				datePicker.css("display", "none");
			}
		});
	}

	const customSelect = $(".custom-select");
	const selectedOption = customSelect.find(".selected-option");
	const optionsList = customSelect.find(".options");
	const iconDown = customSelect.find(".fas.fa-angle-down");
	const datePicker = $("#datePicker");

	const firstVehicle = $(".custom-dropdown .dropdown-options li:first");
	const vehicleId = firstVehicle.data('value');
	const vehicle_lc = firstVehicle.text();

	fetchSummaryReportData('yesterday');
	if (vehicleId !== undefined) {
	    fetchCarEfficiencyData('yesterday', vehicleId, vehicle_lc);
       }
	initializeCustomSelect(customSelect, selectedOption, optionsList, iconDown, datePicker, vehicleId, vehicle_lc);

	$(".custom-dropdown .selected-option").click(function () {
		$(".custom-dropdown .dropdown-options").toggle();
	});

	$(".custom-dropdown .dropdown-options li").click(function () {
		var selectedValue = $(this).data('value');
		var selectedText = $(this).text();
		let startDate = $("#start_report").val();
		let endDate = $("#end_report").val();
    $("#selected-vehicle").html('<span>' + selectedText + '</span><i class="fas fa-angle-down"></i>');
		$(".custom-dropdown .dropdown-options").hide();
		const selectedOption = $(".custom-select .selected-option").text();
    const dataValue = $(".custom-select .options li:contains('" + selectedOption + "')").data('value');

		fetchCarEfficiencyData(dataValue, selectedValue, selectedText, startDate, endDate);
	});

	$(document).mouseup(function (e) {
		var container = $(".custom-dropdown");
		if (!container.is(e.target) && container.has(e.target).length === 0) {
			$(".custom-dropdown .dropdown-options").hide();
		}
	});
});
