// ---------- CHARTS ---------- //

var barChart = echarts.init(document.getElementById('bar-chart'));
window.addEventListener('resize', function () {
	barChart.resize();
	areaChart.resize();
	threeChart.resize();
	partnerAreaChart.resize();
	vehicleBarChart.resize();
});

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
		formatter: function (params) {
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
			data: [],
			markLine: {
				data: [
					{
						yAxis: 0,
						name: 'Another Value',
						lineStyle: {color: 'green', width: 3}
					},
					{
						yAxis: 0,
						name: 'Another Value',
						lineStyle: {color: 'orange', width: 3}
					},
					{
						yAxis: 0,
						name: 'Another Value',
						lineStyle: {color: 'red', width: 3}
					}
				]
			}
		},
		{
			name: 'vision_color',
			type: 'bar',
			stack: 'total',
			label: {
				focus: 'series'
			},
			itemStyle: {
				color: '#A1E8B9',
				borderColor: 'green',
				borderWidth: 5
			},
			data: [1, 1, 1, 1, 1]
		},
	]
};

barChart.setOption(barChartOptions);

var vehicleBarChart = echarts.init(document.getElementById('vehicle-bar-chart'));

// BAR CHART
let vehicleBarChartOptions = {
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
		formatter: function (params) {
			let category = params[0].axisValue;
			let cash = parseFloat(params[0].value);
			let cashColor = '#A1E8B9';
			return (
				category +
				':<br>' +
				'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background-color:' +
				cashColor +
				'"></span> Дохід: ' +
				cash +
				' грн.<br>'
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
				color: '#A1E8B9'
			},
			data: [],
		}
	]
};

vehicleBarChart.setOption(vehicleBarChartOptions);


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
		type: 'value',
		max: parseInt(BusinessVehicleEfficiency) + 2,
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
			name: 'efficiency',
			type: 'bar',
			stack: 'total',
			itemStyle: {
				color: '#A1E8B9'
			},
			data: [],
			markLine: {
				data: [
					{
						yAxis: 15,
						name: 'Another Value',
						lineStyle: {color: 'green', width: 3}
					},
					{
						yAxis: 12,
						name: 'Another Value',
						lineStyle: {color: 'red', width: 3}
					}
				]
			}
		},
		{
			name: 'vision_color',
			type: 'bar',
			stack: 'total',
			label: {
				focus: 'series'
			},
			itemStyle: {
				color: '#A1E8B9',
				borderColor: 'green',
				borderWidth: 5
			},
			data: []
		},
	],
	tooltip: {
		show: true,
		trigger: 'axis',
		axisPointer: {
			type: 'shadow'
		},
		formatter: function (params) {
			let carName = params[0].data['name'];
			let efficiency = params[0].data['value'];
			let tripsValue = params[0].data['trips'];
			let brand = params[0].data['brand'];
			return 'Автомобіль: ' + carName + '<br/>Ефективність: ' + efficiency +
				'<br/>Бренд: ' + brand + '<br/>Брендовані поїздки: ' + tripsValue;
		}

	}
}

threeChart.setOption(threeChartOptions);

var partnerAreaChart = echarts.init(document.getElementById('partner-area-chart'));
let partnerAreaChartOptions = {
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

partnerAreaChart.setOption(partnerAreaChartOptions);

// ---------- END CHARTS ---------- //

function fetchSummaryReportData(period, start, end) {
	let apiUrl;
	if (period === 'custom') {
		apiUrl = `/api/reports/${start}&${end}/`;
	} else {
		apiUrl = `/api/reports/${period}/`;
	}
	$.ajax({
		url: apiUrl,
		type: 'GET',
		dataType: 'json',
		success: function (data) {
			$(".apply-filter-button").prop("disabled", false);
			let startDate = data[0]['start'];
			let endDate = data[0]['end'];
			let totalDistance = data[0]['total_rent'];
			if (data[0]['drivers'].length !== 0) {
				$(".noDataMessage1").hide();
				$('#bar-chart').show();
				const driversData = data[0]['drivers'];
				driversData.sort((a, b) => b.total_kasa - a.total_kasa);
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
				const maxEarningsPeriod = calculateEarnings(startDate, endDate, parseInt(DriverDailyEarnings));
				const earnings6 = maxEarningsPeriod.earnings6;
				const earnings5 = maxEarningsPeriod.earnings5;
				const earnings4 = maxEarningsPeriod.earnings4;

				const total_card = driversData.map(driver => ({value: parseFloat(driver.total_card)}));
				const total_cash = driversData.map(driver => ({value: parseFloat(driver.total_cash)}));

				barChartOptions.series[1].data = total_card;
				barChartOptions.series[0].data = total_cash;
				barChartOptions.series[2].data = Array.from({length: total_card.length}, () => ({value: 1}));

				barChartOptions.xAxis.data = formattedNamesList;
				barChartOptions.series[1].markLine.data[0].yAxis = earnings6;
				barChartOptions.series[1].markLine.data[1].yAxis = earnings5;
				barChartOptions.series[1].markLine.data[2].yAxis = earnings4;

				for (var i = 0; i < total_card.length; i++) {
					var sum = total_card[i].value + total_cash[i].value;
					var color = getColor(sum, earnings6, earnings5, earnings4);
					barChartOptions.series[2].data[i].itemStyle = {
						borderColor: color
					};
				}
				barChart.setOption(barChartOptions);
			} else {
				$(".noDataMessage1").show();
				$('#bar-chart').hide();
			}
			if (startDate === endDate) {
				$('.weekly-income-dates').text(startDate);
			} else {
				$('.weekly-income-dates').text(gettext('З ') + startDate + ' ' + gettext('по') + ' ' + endDate);
			}
			$('.weekly-income-rent').text(parseInt(totalDistance) + " км");
			$('.weekly-income-amount').text(parseInt(data[0]["kasa"]) + " ₴");
			$('.not-closed-payments').text(parseInt(data[0]["total_payment"]) + " ₴");
			$('.weekly-spending-driver').text(parseInt(data[0]["total_driver_spending"]) + " ₴");
			$('.weekly-spending-vehicle').text(parseInt(data[0]["total_vehicle_spending"]) + " ₴");
			$('.rent-earning').text(parseInt(data[0]["rent_earnings"]) + " ₴");
			$('.unpaid-rent').text(parseInt(data[0]["total_distance"]) + " км");

			const driversWithPayments = data[0]['drivers'].filter(driver => {
				return driver.payment_amount !== null || driver.weekly_payments !== null;
			});
			const table = $('.driver-table');

			table.find('tbody').empty();

			driversWithPayments.forEach(driver => {
				const row = $('<tr></tr>');
				const totalAmount = parseFloat(driver.payment_amount || 0) + parseFloat(driver.weekly_payments || 0);

				row.append(`<td>${driver.full_name}</td>`);
				row.append(`<td>${parseInt(totalAmount)}</td>`);
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
	}

	$.ajax({
		url: apiUrl,
		type: 'GET',
		dataType: 'json',
		success: function (data) {
			if (data['dates'].length !== 0) {
				$(".noDataMessage2").hide();
				$('#area-chart').show();
				$('#bar-three-chart').show();
				$('#partner-area-chart').show();
				$('#vehicle-bar-chart').show();
				$('.car-select').show();

				let firstVehicleData = {
					name: vehicle_lc,
					data: data.efficiency
				};

				areaChartOptions.series = firstVehicleData;
				areaChartOptions.xAxis.data = data['dates'];
				areaChart.setOption(areaChartOptions);

				let vehicle_list = data['vehicle_list'];
				var dropdown = $('#vehicle-options');
				dropdown.empty();

				vehicle_list.sort((a, b) => {
					let nameA = Object.keys(a)[0];
					let nameB = Object.keys(b)[0];
					return nameA.localeCompare(nameB);
				});

				vehicle_list.forEach(function (vehicleInfo) {
					let carName = Object.keys(vehicleInfo)[0];
					let carId = vehicleInfo[carName].vehicle_id;

					dropdown.append($('<li></li>').attr('data-value', carId).text(carName));
				});

				let vehicleData = [];
				vehicle_list.forEach(function (vehicle) {
					let carName = Object.keys(vehicle)[0];
					let carInfo = vehicle[carName];

					let carData = {
						name: carName,
						efficiency: carInfo.average_eff,
						totalEarnings: carInfo.total_earnings || 0,
						trips: carInfo.branding_trips || 0,
						brand: carInfo.vehicle_brand || 'Відсутній'
					};
					vehicleData.push(carData);
				});


				let chartData = vehicleData.map(function (vehicle) {
					return {
						name: vehicle.name,
						value: vehicle.efficiency,
						trips: vehicle.trips,
						brand: vehicle.brand
					};
				});

				threeChartOptions.series[0].data = chartData;
				threeChartOptions.xAxis.data = vehicleData.map(function (vehicle) {
					return vehicle.name;
				});
				threeChartOptions.series[1].data = Array.from({length: chartData.length}, () => ({value: 0.1}));

				for (var i = 0; i < chartData.length; i++) {
					var value = chartData[i].value;
					var color = value < parseInt(ComfortVehicleEfficiency) ? 'red' : (value < parseInt(BusinessVehicleEfficiency) ? 'green' : 'violet');
					threeChartOptions.series[1].data[i].itemStyle = {
						borderColor: color
					};
				}
				threeChart.setOption(threeChartOptions);

				const totalMileage = data['mileage'];
				const partnerNames = Object.keys(totalMileage);
				const mileages = Object.values(totalMileage);

				partnerAreaChartOptions.yAxis.data = partnerNames;
				partnerAreaChartOptions.series[0].data = mileages;
				partnerAreaChart.setOption(partnerAreaChartOptions);

				var vehicleDate = vehicleData.map(function (vehicle) {
					return {
						name: vehicle.name,
						value: vehicle.totalEarnings,
					};
				});
				vehicleBarChartOptions.series[0].data = vehicleDate;
				vehicleBarChartOptions.xAxis.data = vehicleData.map(function (vehicle) {
					return vehicle.name;
				});
				vehicleBarChart.setOption(vehicleBarChartOptions);
			} else {
				$(".noDataMessage2").show();
				$('#area-chart').hide();
				$('#bar-three-chart').hide();
				$('#partner-area-chart').hide();
				$('#vehicle-bar-chart').hide();
				$('.car-select').css('display', 'none');
			}

			$('.weekly-clean-amount').text(parseInt(data["earning"]) + " ₴");
			$('.income-km').text(parseInt(data["total_mileage"]) + " км");
			$('.income-efficiency').text(parseInt(data["average_efficiency"]) + " грн/км");
		},
		error: function (error) {
			console.error(error);
		}
	});
}

$(document).ready(function () {
	fetchSummaryReportData('today');

	const firstVehicle = $(".custom-dropdown .dropdown-options li:first");
	const vehicleId = firstVehicle.data('value');
	const vehicle_lc = firstVehicle.text();

	fetchCarEfficiencyData('today', vehicleId, vehicle_lc);

	$(this).on('click', '.apply-filter-button', function () {
		applyDateRange(function (selectedPeriod, startDate, endDate) {
			fetchSummaryReportData(selectedPeriod, startDate, endDate);
			fetchCarEfficiencyData(selectedPeriod, vehicleId, vehicle_lc, startDate, endDate);
		});
	})

	initializeCustomSelect(function (clickedValue) {
		fetchSummaryReportData(clickedValue);
		fetchCarEfficiencyData(clickedValue, vehicleId, vehicle_lc);
	});

	$(".custom-dropdown .selected-option").click(function () {
		$(".custom-dropdown .dropdown-options").toggle();
	});

	$(this).on('click', '.custom-dropdown .dropdown-options li', function () {
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

function calculateEarnings(start, end, dailyWage) {
	const startDateParts = start.split('.');
	const endDateParts = end.split('.');
	const startDateFormatted = `${startDateParts[2]}-${startDateParts[1]}-${startDateParts[0]}`;
	const endDateFormatted = `${endDateParts[2]}-${endDateParts[1]}-${endDateParts[0]}`;
	const startDate = new Date(startDateFormatted);
	const endDate = new Date(endDateFormatted);

	const oneDay = 24 * 60 * 60 * 1000;
	const totalDays = Math.round(Math.abs((endDate - startDate) / oneDay)) + 1;

	const workDays6_1 = Math.floor(totalDays / 7) * 6 + Math.min(totalDays % 7, 6);
	const workDays5_2 = Math.floor(totalDays / 7) * 5 + Math.min(totalDays % 7, 5);
	const workDays4_3 = Math.floor(totalDays / 7) * 4 + Math.min(totalDays % 7, 4);

	const earnings6 = workDays6_1 * dailyWage;
	const earnings5 = workDays5_2 * dailyWage;
	const earnings4 = workDays4_3 * dailyWage;

	return {earnings6, earnings5, earnings4};
}

function getColor(value, earnings6, earnings5, earnings4) {
	if (value < earnings4) {
		return 'red';
	} else if (value >= earnings4 && value < earnings5) {
		return 'orange';
	} else if (value >= earnings5 && value < earnings6) {
		return 'green';
	} else {
		return 'violet';
	}
}

