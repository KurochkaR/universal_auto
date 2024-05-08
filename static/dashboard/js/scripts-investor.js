// ---------- CHARTS ----------

var investorBarChart = echarts.init(document.getElementById('investor-bar-chart'));

// BAR CHART
let investorBarChartOptions = {
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
    name: 'Сума (грн.)',
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
  },
  series: [
    {
      name: 'Сума (грн.)',
      type: 'bar',
      stack: 'total',
      label: {
        focus: 'series'
      },
      itemStyle: {
        color: '#79C8C5'
      },
      data: []
    },
  ]
};

investorBarChart.setOption(investorBarChartOptions);


// AREA CHART
var investorAreaChart = echarts.init(document.getElementById('investor-area-chart'));
let investorAreaChartOptions = {
	grid: {
    height: '70%'
  },
  yAxis: {
    type: 'category',
    data: [],
    axisLabel: {
      rotate: 45
    }
  },
  xAxis: {
    type: 'value',
    name: 'Пробіг (км)',
    nameLocation: 'middle',
    nameGap: 60,
    nameTextStyle: {
      fontSize: 18,
    }
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'shadow'
    },
  },
  series: [
    {
      name: 'Пробіг (км)',
      type: 'bar',
      stack: 'total',
      label: {
        focus: 'series'
      },
      itemStyle: {
        color: '#18A64D'
      },
      data: []
    },
  ]
};

investorAreaChart.setOption(investorAreaChartOptions);


function fetchInvestorData(period, start, end) {
	let apiUrl;
	if (period === 'custom') {
		apiUrl = `/api/investor_info/${start}&${end}/`;
	} else {
		apiUrl = `/api/investor_info/${period}/`;
	};
	$.ajax({
		url: apiUrl,
		type: 'GET',
		dataType: 'json',
		success: function (data) {
			let totalEarnings = data[0]['totals']['total_earnings'];
			let totalMileage = data[0]['totals']['total_mileage'];
			let roi = data[0]['totals']['roi'];
//			let annualizedRoi = data[0]['totals']['annualized-roi'];
			let totalSpending = data[0]['totals']['total_spending'];
			let startDate = data[0]['start'];
			let endDate = data[0]['end'];
			const vehiclesData = data[0]['car_earnings'];
			const categories = vehiclesData.map(vehicle => vehicle.licence_plate);

			if (totalEarnings !== "0.00") {
				$(".noDataMessage1").hide();
				$('#investor-bar-chart').show();

				const values = vehiclesData.map(vehicle => vehicle.earnings);
				investorBarChartOptions.series[0].data = values;
				investorBarChartOptions.xAxis.data = categories;
				investorBarChart.setOption(investorBarChartOptions);

			} else {
				$(".noDataMessage1").show();
				$('#investor-bar-chart').hide()
			};

			if (totalMileage !== "0.00"){
				$(".noDataMessage2").hide();
				$('#investor-area-chart').show();

				const carValue = vehiclesData.map(vehicle => vehicle.mileage);
				investorAreaChartOptions.series[0].data = carValue;
				investorAreaChartOptions.yAxis.data = categories;
				investorAreaChart.setOption(investorAreaChartOptions);

			} else {
				$(".noDataMessage2").show();
				$('#investor-area-chart').hide();
			};

			if (startDate === endDate) {
				$('.weekly-income-dates').text(startDate);
			} else {
				$('.weekly-income-dates').text(gettext('З ') + startDate + ' ' + gettext('по') + ' ' + endDate);
			};
			$('.weekly-income-amount').text(totalEarnings + gettext(' грн'));
			$('.spending-all').text(totalSpending + gettext(' грн'));
			$('.income-km').text(totalMileage + gettext(' км'));
			$('.roi').text(roi + gettext(' %'));
//			$('.annualized-roi').text(annualizedRoi + gettext(' %'));
		},
		error: function (error) {
				console.error(error);
		}
	});
}

$(document).ready(function () {

    fetchInvestorData('yesterday');
	initializeCustomSelect(function(clickedValue) {
        fetchInvestorData(clickedValue);
    });

    applyDateRange(function(selectedPeriod, startDate, endDate) {
            fetchInvestorData(selectedPeriod, startDate, endDate);
        });

});
