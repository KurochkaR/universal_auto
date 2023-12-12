// SIDEBAR TOGGLE

let sidebarOpen = false;
let sidebar = document.getElementById("sidebar");

// Визначте змінну для стану бічного бару

function toggleSidebar() {
	const sidebar = document.getElementById("sidebar");

	if (sidebarOpen) {
		// Закрити бічний бар
		sidebar.classList.remove("sidebar-responsive");
		sidebarOpen = false;
	} else {
		// Відкрити бічний бар
		sidebar.classList.add("sidebar-responsive");
		sidebarOpen = true;
	}
}

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

function applyCustomDateRange() {
	$(".apply-filter-button").prop("disabled", true);

	let startDate = $("#start_report").val();
	let endDate = $("#end_report").val();
	const firstVehicle = $(".custom-dropdown .dropdown-options li:first");
	const vehicleId = firstVehicle.data('value');
	const vehicle_lc = firstVehicle.text();

	const selectedPeriod = 'custom'

	fetchSummaryReportData(selectedPeriod, startDate, endDate);
	fetchCarEfficiencyData(selectedPeriod, vehicleId, vehicle_lc, startDate, endDate);
}

function applyCustomDateRangeVehicle() {
	$(".apply-filter-button_driver").prop("disabled", true);

	let startDate = $("#start_report_driver").val();
	let endDate = $("#end_report_driver").val();

	const selectedPeriod = 'custom'

	fetchDriverEfficiencyData(selectedPeriod, startDate, endDate);
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
			$(".apply-filter-button").prop("disabled", false);
			let startDate = data[0]['start'];
			let endDate = data[0]['end'];
			let totalDistance = data[0]['total_rent'];
			if (data[0]['drivers'].length !== 0) {
				$(".noDataMessage1").hide();
				$('#bar-chart').show();
				const driversData = data[0]['drivers'];
				const categories = driversData.map(driver => driver.full_name);
				const total_card = driversData.map(driver => driver.total_card);
				const total_cash = driversData.map(driver => driver.total_cash);
				barChartOptions.series[1].data = total_card;
				barChartOptions.series[0].data = total_cash;
				barChartOptions.xAxis.data = categories;
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
			;
			$('.weekly-income-rent').text(totalDistance + ' ' + gettext('км'));
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
				$('.car-select').hide();
			};
			$('.weekly-income-amount').text(data["kasa"] + ' ' + gettext('грн'));
			$('.income-km').text(data["total_mileage"] + ' ' + gettext("км"));
			$('.income-efficiency').text(data["average_efficiency"].toFixed(2) + ' ' + gettext('грн/км'));
		},
		error: function (error) {
			console.error(error);
		}
	});
}


function fetchDriverEfficiencyData(period, start, end) {
	let apiUrl;
	if (period === 'custom') {
		apiUrl = `/api/drivers_info/${start}&${end}/`;
	} else {
		apiUrl = `/api/drivers_info/${period}/`;
	};
	$.ajax({
		url: apiUrl,
		type: 'GET',
		dataType: 'json',
		success: function (data) {
			$(".apply-filter-button").prop("disabled", false);
			let table = $('.info-driver table');
			let driverBlock = $('.driver-block');
			let startDate = data[0]['start'];
			let endDate = data[0]['end'];
			table.find('tr:gt(0)').remove();
			if (data[0]['drivers_efficiency'].length !== 0) {
				data[0]['drivers_efficiency'].forEach(function (item) {
					let row = $('<tr></tr>');
					let time = item.road_time
					let parts = time.match(/(\d+) (\d+):(\d+):(\d+)/);
					if (!parts) {
						time = time
					} else {
						let days = parseInt(parts[1]);
						let hours = parseInt(parts[2]);
						let minutes = parseInt(parts[3]);
						let seconds = parseInt(parts[4]);

						hours += days * 24;

						// Форматувати рядок у вигляді HH:mm:ss
						let formattedTime = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

						time = formattedTime
					}

					row.append('<td class="driver">' + item.full_name + '</td>');
					row.append('<td class="kasa">' + item.total_kasa + '</td>');
					row.append('<td class="orders">' + item.orders + '</td>');
					row.append('<td class="accept">' + item.accept_percent + " %" + '</td>');
					row.append('<td class="price">' + item.average_price + '</td>');
					row.append('<td class="mileage">' + item.mileage + '</td>');
					row.append('<td class="efficiency">' + item.efficiency + '</td>');
					row.append('<td class="road">' + time + '</td>');

					table.append(row);

				});

				$('.driver-container').empty();

				data[0]['drivers_efficiency'].forEach(function (driver) {
					let driverBlock = $('<div class="driver-block"></div>');
					let driverName = $('<div class="driver-name"></div>');
					let driverInfo = $('<div class="driver-info"></div>');

					driverName.append('<h3>' + driver.full_name + '</h3>');
					driverName.append('<div class="arrow">▼</div>');

					driverName.on('click', function () {
						if (driverInfo.is(':hidden')) {
							driverInfo.slideDown();
						} else {
							driverInfo.slideUp();
						}
					});

					driverInfo.append('<p>' + gettext("Каса: ") + driver.total_kasa + gettext(" грн") + '</p>');
					driverInfo.append('<p>' + gettext("Кількість замовлень: ") + driver.orders + '</p>');
					driverInfo.append('<p>' + gettext("Відсоток прийнятих замовлень: ") + driver.accept_percent + '%' + '</p>');
					driverInfo.append('<p>' + gettext("Середній чек, грн: ") + driver.average_price + '</p>');
					driverInfo.append('<p>' + gettext("Пробіг, км: ") + driver.mileage + '</p>');
					driverInfo.append('<p>' + gettext("Ефективність, грн/км: ") + driver.efficiency + '</p>');
					driverInfo.append('<p>' + gettext("Час в дорозі: ") + formatTime(driver.road_time) + '</p>');

					driverBlock.append(driverName);
					driverBlock.append(driverInfo);

					// Додати блок водія до контейнера
					$('.driver-container').append(driverBlock);
				});
			}
			if (period === 'yesterday') {
				$('.income-drivers-date').text(startDate);
			} else {
				$('.income-drivers-date').text('З ' + startDate + ' ' + gettext('по') + ' ' + endDate);
			}
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

function customDateRange() {
	$(".apply-filter-button").prop("disabled", true);

	let startDate = $("#start_date").val();
	let endDate = $("#end_date").val();

	const selectedPeriod = periodSelect.val();
	fetchDriverEfficiencyData(selectedPeriod, startDate, endDate);
}


$(document).ready(function () {
	let $table = $('.driver-table');
	let $tbody = $table.find('tbody');

	function sortTable(column, order) {
		let rows = $tbody.find('tr').toArray();

		let collator = new Intl.Collator(undefined, {sensitivity: 'base'});

		rows.sort(function (a, b) {
			let valueA = $(a).find(`td.${column}`).text();
			let valueB = $(b).find(`td.${column}`).text();
			if (column === 'driver') {
				if (order === 'asc') {
					return collator.compare(valueA, valueB);
				} else {
					return collator.compare(valueB, valueA);
				}
				;
			} else {
				let floatA = parseFloat(valueA);
				let floatB = parseFloat(valueB);
				if (order === 'asc') {
					return floatA - floatB;
				} else {
					return floatB - floatA;
				}
				;
			}
		});

		$tbody.empty().append(rows);
	}

	// Attach click event handlers to the table headers for sorting
	$table.find('th.sortable').click(function () {

		let column = $(this).data('sort');
		let sortOrder = $(this).hasClass('sorted-asc') ? 'desc' : 'asc';

		// Reset sorting indicators
		$table.find('th.sortable').removeClass('sorted-asc sorted-desc');

		if (sortOrder === 'asc') {
			$(this).addClass('sorted-asc');
		} else {
			$(this).addClass('sorted-desc');
		}

		sortTable(column, sortOrder);
	});

	$(".sidebar-list-item.admin").on("click", function () {

		let adminPanelURL = $(this).data("url");

		if (adminPanelURL) {
			window.open(adminPanelURL, "_blank");
		}
	});

	$("#updateDatabaseContainer").click(function () {

		$("#loadingModal").css("display", "block")
		$(".loading-content").css("display", "block");

		$.ajax({
			type: "POST",
			url: ajaxPostUrl,
			data: {
				csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
				action: "upd_database",
			},
			success: function (response) {
				let task_id = response.task_id
				let interval = setInterval(function () {
					$.ajax({
						type: "GET",
						url: ajaxGetUrl,
						data: {
							action: "check_task",
							task_id: task_id,
						},
						success: function (response) {
							if (response.data === true) {
								$(".loading-content").css("display", "flex");
								$("#loadingMessage").text(gettext("Базу даних оновлено"));
								$("#loader").css("display", "none");
								$("#checkmark").css("display", "block");
								setTimeout(function () {
									$("#loadingModal").css("display", "none");
									window.location.reload();
								}, 3000);
								clearInterval(interval);
							} if (response.data === false) {
								$("#loadingMessage").text(gettext("Помилка оновлення бази даних. Спробуйте пізніше"));
								$("#loader").css("display", "none");
								$("#checkmark").css("display", "none");

								setTimeout(function () {
									$("#loadingModal").css("display", "none");
								}, 3000);
								clearInterval(interval);
							};
						}
					});
				}, 5000);
			}
		});
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

	// change-password

	$("#changePassword").click(function () {
		$("#passwordChangeForm").toggle();
	});


	$("#submitPassword").click(function () {
		let password = $("#oldPassword").val();
		let newPassword = $("#newPassword").val();
		let confirmPassword = $("#confirmPassword").val();

		if (newPassword !== confirmPassword) {
			$("#ChangeErrorMessage").show();
		} else {
			$.ajax({
				url: ajaxPostUrl,
				type: 'POST',
				data: {
					action: 'change_password',
					password: password,
					newPassword: newPassword,
					csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
				},
				success: function (response) {
					if (response.data['success'] === true) {
						$("#passwordChangeForm").hide();
						window.location.href = "/";
					} else {
						$("#oldPasswordMessage").show();
					}
				}
			});
		}
	});

	$(".close-btn").click(function () {
		$("#settingsWindow").fadeOut();
		sessionStorage.setItem('settings', 'false');
		location.reload();
	});

	// burger-menu
	$('.burger-menu').click(function () {
		$('.burger-menu').toggleClass('open');
	});

	$('#VehicleBtnContainer').click(function () {
		$('.payback-car').css('display', 'flex');
		$('.charts').hide();
		$('.main-cards').hide();
		$('.info-driver').hide();
		$('.common-period').hide();
		$('#datePicker').hide()
		$('.driver-container').hide()
		$('.driver-calendar').hide()
		$('#sidebar').removeClass('sidebar-responsive');
		$('.main-title h2').text(gettext('Автомобілі'));
	});

	$('#DriverBtnContainer').click(function () {
		fetchDriverEfficiencyData('yesterday');
		$('.info-driver').show();
		$('.payback-car').hide();
		$('.charts').hide();
		$('.main-cards').hide();
		$('.common-period').hide();
		$('#datePicker').hide()
		$('.driver-calendar').hide()
		$('#sidebar').removeClass('sidebar-responsive');
		if (window.innerWidth <= 900) {
			$('.driver-container').css('display', 'block');
		}
		$('.main-title h2').text(gettext('Водії'));
	});

	const resetButton = $("#reset-button");

	resetButton.on("click", function () {
		areaChart.resetSeries();
	});

  const gridContainer = $(".grid-container");
  const sidebarToggle = $("#sidebar-toggle");
  const sidebarTitle = $(".sidebar-title");
  const sidebarListItems = $("#sidebar .sidebar-list-item span");
  const sidebarToggleIcon = sidebarToggle.find("i");

  let isSidebarOpen = false;

  function toggleSidebar() {
    isSidebarOpen = !isSidebarOpen;

    if (isSidebarOpen) {
      gridContainer.css("grid-template-columns", "300px 1fr 1fr 1fr");
      sidebarTitle.css("padding", "10px 30px 0px 30px");
      sidebarToggleIcon.removeClass("fa-angle-double-right").addClass("fa-angle-double-left");

      $(".logo-1").hide();
      $(".logo-2").show();

      setTimeout(function() {
        sidebarListItems.each(function(index) {
          $(this).css("display", "block");
          $(this).css("transition-delay", `${0.1 * (index + 1)}s`);
          $(this).css("opacity", 1);
        });
      }, 500);
    } else {
      gridContainer.css("grid-template-columns", "60px 1fr 1fr 1fr");
      sidebarTitle.css("padding", "30px 30px 50px 30px");
      sidebarToggleIcon.removeClass("fa-angle-double-left").addClass("fa-angle-double-right");

      $(".logo-1").show();
      $(".logo-2").hide();

      sidebarListItems.each(function() {
        $(this).css("display", "none");
        $(this).css("transition-delay", "0s");
        $(this).css("opacity", 0);
      });
    }
  }

  sidebarToggle.click(toggleSidebar);

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
	fetchCarEfficiencyData('yesterday', vehicleId, vehicle_lc);

	initializeCustomSelect(customSelect, selectedOption, optionsList, iconDown, datePicker, vehicleId, vehicle_lc);


	const customSelectDriver = $(".custom-select-drivers");
	const selectedOptionDriver = customSelectDriver.find(".selected-option-drivers");
	const optionsListDriver = customSelectDriver.find(".options-drivers");
	const iconDownDriver = customSelectDriver.find(".fas.fa-angle-down");
	const datePickerDriver = $("#datePickerDriver");

	initializeCustomSelect(customSelectDriver, selectedOptionDriver, optionsListDriver, iconDownDriver, datePickerDriver);

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

	//calendar

	$('#workCalendarBtnContainer').click(function () {
		$('.driver-calendar').show();
		$('.charts').hide();
		$('.main-cards').hide();
		$('.info-driver').hide();
		$('.payback-car').hide();
		$('.common-period').hide();
		$('#datePicker').hide()
		$('#sidebar').removeClass('sidebar-responsive');
		$('.main-title h2').text(gettext('Розклад водіїв'));

		const today = new Date();
		const daysToShow = 14;

		function formatDateForDatabase(date) {
			const year = date.getFullYear();
			const month = (date.getMonth() + 1).toString().padStart(2, '0');
			const day = date.getDate().toString().padStart(2, '0');

			const formattedDate = `${year}-${month}-${day}`;
			return formattedDate;
		}

		const formatTime = (date) => {
			const hours = date.getHours().toString().padStart(2, '0');
			const minutes = date.getMinutes().toString().padStart(2, '0');
			return hours + ':' + minutes;
		};

		let currentDate = new Date(today);
		currentDate.setDate(currentDate.getDate() - 3);
		let formattedStartDate = formatDateForDatabase(currentDate);

		let endDate = new Date(currentDate);
		endDate.setDate(endDate.getDate() + daysToShow - 1);
		let formattedEndDate = formatDateForDatabase(endDate);

		fetchCalendarData(formattedStartDate, formattedEndDate);

		function reshuffleHandler (data) {
			$('.driver-calendar').empty();

			const calendarHTML = data.map(function (carData) {
				return `
				<div class="calendar-container" id="${carData.swap_licence}">
					<div class="car-image">
						<img src="${VehicleImg}" alt="Зображення авто">
						<p class="vehicle-license-plate">${carData.swap_licence}</p>
					</div>
					<div class="investButton" id="investPrevButton">
						<svg xmlns="http://www.w3.org/2000/svg" width="12" height="24" viewBox="0 0 12 24" fill="none">
							<path d="M9 7L4 12L9 17V7Z" fill="#141E17" stroke="#141E17" stroke-width="5"/>
						</svg>
					</div>
					<div class="calendar-detail" id="calendarDetail">
						<div class="calendar-card">
							<div class="change-date">
								<p class="calendar-day"></p>
								<p class="calendar-date"></p>
							</div>
							<div class="driver-photo-container">
								<div class="driver-photo">
									<img src="${logoImageUrl}" alt="Зображення водія 1">
									<img src="${logoImageUrl}" alt="Зображення водія 2">
								</div>
							</div>
						</div>
					</div>
					<div class="investButton" id="investNextButton">
						<svg xmlns="http://www.w3.org/2000/svg" width="12" height="24" viewBox="0 0 12 24" fill="none">
							<path d="M3 17L8 12L3 7V17Z" fill="#141E17" stroke="#141E17" stroke-width="5"/>
						</svg>
					</div>
				</div>
				`
			}).join('');
			$('.driver-calendar').append(calendarHTML);

			$('.calendar-container').each(function () {
				const calendarDetail = $(this).find('.calendar-detail');
				const investPrevButton = $(this).find('#investPrevButton');
				const investNextButton = $(this).find('#investNextButton');
				const vehicleLC = $(this).attr('id');

				const driverList = data.find(carDate => carDate.swap_licence === vehicleLC);

				function renderCalendar(startDate) {
					calendarDetail.empty();

					for (let i = 0; i < daysToShow; i++) {
						const day = new Date(startDate);
						day.setDate(startDate.getDate() + i);

						const card = $('<div>').addClass('calendar-card');
						const formattedDate = formatDateForDatabase(day);
						card.attr('id', formattedDate);

						const dayOfWeek = day.toLocaleDateString('uk-UA', { weekday: 'short' });

						const dayOfWeekElement = $('<div>').text(dayOfWeek).addClass('day-of-week');
						card.append(dayOfWeekElement);

						const dateElement = $('<div>').text(formatDate(day)).addClass('date');
						card.append(dateElement);

						const driverPhotoContainer = $('<div>').addClass('driver-photo-container');
						const isDriverPhotoVisible = driverList.reshuffles.some(function (driver) {
							return driver.date === formattedDate && driver.driver_photo;
						});

						if (isDriverPhotoVisible) {

							driverList.reshuffles.forEach(function (driver) {
								if (driver.date === formattedDate) {

									const driverPhoto = $('<div>').addClass('driver-photo');
									driverPhoto.attr('data-name', driver.driver_name).attr('data-id-driver', driver.driver_id).attr('data-id-vehicle', driver.vehicle_id).attr('reshuffle-id', driver.reshuffle_id);
									const driverImage = $('<img>').attr('src', 'https://storage.googleapis.com/jobdriver-bucket/'+ driver.driver_photo).attr('alt', `Фото водія`)

									const startTime = new Date('1970-01-01T' + driver.start_shift);
									const endTime = new Date('1970-01-01T' + driver.end_shift);

									const StartTimes = formatTime(startTime);
									const EndTimes = formatTime(endTime);

									const driverInfo = $('<div>').addClass('driver-info-reshuffle');
									const driverDate = $('<p>').addClass('driver-date').text(driver.date);
									const driverName = $('<p>').addClass('driver-name').text(driver.driver_name);
									const driverTime = $('<p>').addClass('driver-time').text(StartTimes + ' - ' + EndTimes);

									driverInfo.append(driverDate, driverName, driverTime);

									driverPhoto.append(driverImage);
									driverPhoto.append(driverInfo);
									driverPhotoContainer.append(driverPhoto);
									card.append(driverPhotoContainer);

								}
							});
						} else {
							const driverPhoto = $('<div>').addClass('driver-photo');
							const driverImage = $('<img>').attr('src', logoImageUrl).attr('alt', `Фото водія`)

							driverPhoto.append(driverImage);
							driverPhotoContainer.append(driverPhoto);

							card.append(driverPhotoContainer);
						}

						if (isToday(day)) {
							card.addClass('today');
						} else if (isYesterdayOrEarlier(day)) {
							card.addClass('yesterday');
						}

						calendarDetail.append(card);
						$(".driver-photo").hover(function () {
							$(this).find(".driver-info-reshuffle").css("display", "flex");
						}, function () {
							$(this).find(".driver-info-reshuffle").css("display", "none");
						});
					};
					$('.driver-photo-container').each(function(index, container) {
						var photos = $(container).find('.driver-photo img');

						if (photos.length > 2) {
							$(container).addClass('photo-small');
						}
					});
				};

				function formatDate(date) {
					const day = String(date.getDate()).padStart(2, '0');
					const month = String(date.getMonth() + 1).padStart(2, '0');
					return `${day}.${month}`;
				}

				function isToday(someDate) {
					const todayDate = new Date();
					return (
						someDate.getDate() === todayDate.getDate() &&
						someDate.getMonth() === todayDate.getMonth() &&
						someDate.getFullYear() === todayDate.getFullYear()
					);
				}

				function isYesterdayOrEarlier(someDate) {
					const todayDate = new Date();
					return someDate < todayDate;
				}

				renderCalendar(currentDate);

				let cachedCar = null;
				let carDate = null;

				function renderDriverPhotos(currentCar, carDate, daysToShow) {
					for (let i = 0; i < daysToShow; i++) {
						const day = new Date(carDate);
						day.setDate(carDate.getDate() + i);
						const formattedDate = formatDateForDatabase(day);

						const isDriverPhotoVisible = currentCar.reshuffles.some(function (driver) {
							return driver.date === formattedDate && driver.driver_photo;
						});

						if (isDriverPhotoVisible) {
							const driverPhotoContainer = $(`#${currentCar.swap_licence}`).find(`#${formattedDate}`).find('.driver-photo-container').empty();

							currentCar.reshuffles.forEach(function (driver) {
								if (driver.date === formattedDate) {
									const driverPhoto = $('<div>').addClass('driver-photo');
									driverPhoto.attr('data-name', driver.driver_name).attr('data-id-driver', driver.driver_id).attr('data-id-vehicle', driver.vehicle_id).attr('reshuffle-id', driver.reshuffle_id);

									const driverImage = $('<img>').attr('src', 'https://storage.googleapis.com/jobdriver-bucket/' + driver.driver_photo).attr('alt', `Фото водія`);

									const driverInfo = $('<div>').addClass('driver-info-reshuffle');
									const driverDate = $('<p>').addClass('driver-date').text(driver.date);
									const driverName = $('<p>').addClass('driver-name').text(driver.driver_name);
									const driverTime = $('<p>').addClass('driver-time').text(driver.start_shift + ' - ' + driver.end_shift);

									driverInfo.append(driverDate, driverName, driverTime);
									driverPhoto.append(driverInfo);
									driverPhoto.append(driverImage);
									driverPhotoContainer.append(driverPhoto);
								}
							});
						}
					}

					$(".driver-photo").hover(function () {
						$(this).find(".driver-info-reshuffle").css("display", "flex");
					}, function () {
						$(this).find(".driver-info-reshuffle").css("display", "none");
					});

					$('.driver-photo-container').each(function (index, container) {
						var photos = $(container).find('.driver-photo img');

						if (photos.length > 2) {
							$(container).addClass('photo-small');
						}
					});
				}

				function handleButtonClick(increaseDays) {
					if (cachedCar && cachedCar === vehicleLC) {
						carDate.setDate(carDate.getDate() + increaseDays);
					} else {
						carDate = new Date();
						carDate.setDate(carDate.getDate() + (increaseDays > 0 ? 4 : -10));
						cachedCar = vehicleLC;
					}

					const formattedStartDate = formatDateForDatabase(carDate);

					let endDate = new Date(carDate);
					endDate.setDate(endDate.getDate() + daysToShow - 1);
					let formattedEndDate = formatDateForDatabase(endDate);

					renderCalendar(carDate);

					apiUrl = `/api/reshuffle/${formattedStartDate}/${formattedEndDate}/`;

					$.ajax({
						url: apiUrl,
						type: 'GET',
						dataType: 'json',
						success: function (data) {
							if (!data.length || !(currentCar = data.find(car => car.swap_licence === vehicleLC))) {
								return;
							}

							renderDriverPhotos(currentCar, carDate, daysToShow);
						},
						error: function (error) {
							console.error(error);
						}
					});
				}

				investNextButton.on('click', function () {
					handleButtonClick(7);
				});

				investPrevButton.on('click', function () {
					handleButtonClick(-7);
				});
			});

			function updShiftForm(clickedDayId, calendarId, dataName, startTime, endTime, driverId, vehicleId, idReshuffle) {
				const modalShiftTitle = $('.modal-shift-title h2');
				const shiftForm = $('#modal-shift');
				const modalShiftDate = $('.modal-shift-date');
				const shiftDriver = $('#shift-driver');
				const startTimeInput = $('#startTime');
				const endTimeInput = $('#endTime');
				const shiftVehicleInput = $('#shift-vehicle');
				const csrfTokenInput = $('input[name="csrfmiddlewaretoken"]');
				const ajaxData = {
					csrfmiddlewaretoken: csrfTokenInput.val(),
					reshuffle_id: idReshuffle
				};

				modalShiftTitle.text("Редагування зміни");
				modalShiftDate.text(clickedDayId);
				shiftDriver.val(driverId);
				startTimeInput.val(startTime);
				endTimeInput.val(endTime);
				shiftVehicleInput.val(vehicleId);

				const shiftBtn = $('.shift-btn').hide();
				const recurrence = $('.recurrence').hide();
				const deleteBtn = $('.delete-btn').show();
				const deleteAllBtn = $('.delete-all-btn').show();
				const updBtn = $('.upd-btn').show();
				const updAllBtn = $('.upd-all-btn').show();
				const shiftVehicle = $('.shift-vehicle').show();
				shiftForm.show();

				function handleDelete(action) {
					$.ajax({
						url: ajaxPostUrl,
						type: 'POST',
						data: { action, ...ajaxData },
						success: function (response) {
							fetchCalendarData(formattedStartDate, formattedEndDate);
						},
					});
					shiftForm.hide();
				}

				deleteBtn.off('click').on('click', function (e) {
					e.preventDefault();
					handleDelete('delete_shift');
				});

				deleteAllBtn.off('click').on('click', function (e) {
					e.preventDefault();
					handleDelete('delete_all_shift');
				});

				function handleUpdate(action) {
					const date = modalShiftDate.text();
					const selectedDriverId = shiftDriver.val();
					const vehicleId = shiftVehicleInput.val();

					$.ajax({
						url: ajaxPostUrl,
						type: 'POST',
						data: {
							action,
							vehicle_licence: vehicleId,
							date,
							start_time: startTimeInput.val(),
							end_time: endTimeInput.val(),
							driver_id: selectedDriverId,
							reshuffle_id: idReshuffle,
							...ajaxData
						},
						success: function (response) {
							if (response.data === true) {
								fetchCalendarData(formattedStartDate, formattedEndDate);
								showShiftMessage(true, true);
							} else {
								showShiftMessage(response.data[0], response.data[1]['conflicting_time'], response.data[1]['licence_plate']);
							}
						},
					});
					shiftForm.hide();
				}

				updBtn.off('click').on('click', function (e) {
					e.preventDefault();
					handleUpdate('update_shift');
				});

				updAllBtn.off('click').on('click', function (e) {
					e.preventDefault();
					handleUpdate('update_all_shift');
				});
			}

			function openShiftForm(clickedDayId, calendarId) {
				const modalShiftTitle = $('.modal-shift-title h2');
				const shiftForm = $('#modal-shift');
				const shiftBtn = $('.shift-btn').show();
				const recurrence = $('.recurrence').show();
				const deleteBtn = $('.delete-btn').hide();
				const deleteAllBtn = $('.delete-all-btn').hide();
				const updBtn = $('.upd-btn').hide();
				const updAllBtn = $('.upd-all-btn').hide();
				const shiftVehicle = $('.shift-vehicle').hide();
				const modalShiftDate = $('.modal-shift-date');
				const startTimeInput = $('#startTime');
				const endTimeInput = $('#endTime');
				const shiftDriver = $('#shift-driver');
				const csrfTokenInput = $('input[name="csrfmiddlewaretoken"]');

				modalShiftTitle.text("Створення змінни");
				modalShiftDate.text(clickedDayId);
				shiftForm.show();

				shiftBtn.off('click').on('click', function (e) {
					e.preventDefault();
					const startTime = startTimeInput.val();
					const endTime = endTimeInput.val();
					const selectedDriverId = shiftDriver.val();
					const recurrence = $('#recurrence').val();

						$.ajax({
							url: ajaxPostUrl,
							type: 'POST',
							data: {
								action: 'add_shift',
								vehicle_licence: calendarId,
								date: clickedDayId,
								start_time: startTime,
								end_time: endTime,
								driver_id: selectedDriverId,
								recurrence,
								csrfmiddlewaretoken: csrfTokenInput.val()
							},
							success: function (response) {
							  if (response.data === true) {
									fetchCalendarData(formattedStartDate, formattedEndDate);
									showShiftMessage(true);
							  } else {
							  	showShiftMessage(response.data[0], false, response.data[1]['conflicting_time'], response.data[1]['licence_plate']);
							  }
							},
						});
						shiftForm.hide();
				});
			}

			const calendarContainers = $('.calendar-container');

			calendarContainers.each(function () {
				const calendarDetail = $(this).find('.calendar-detail');

				calendarDetail.on('click', '.calendar-card', function () {
					const clickedCard = $(this);
					const clickedDayId = clickedCard.attr('id');
					const calendarId = clickedCard.closest('.calendar-container').attr('id');

					if (!clickedCard.hasClass('yesterday')) {
						openShiftForm(clickedDayId, calendarId);
					}
				});

					calendarDetail.on('click', '.driver-photo', function (event) {
						event.stopPropagation();
						const clickedCard = $(this).closest('.calendar-card');
						const clickedDayId = clickedCard.attr('id');
						const calendarId = clickedCard.closest('.calendar-container').attr('id');

						if (!clickedCard.hasClass('yesterday')) {
							const driverPh = $(this);
							const dataName = driverPh.data('name');
							const idDriver = driverPh.data('id-driver');
							const idVehicle = driverPh.data('id-vehicle');
							const idReshuffle = driverPh.attr('reshuffle-id');
							const driverPhoto = $(this).find('img');
							const photoSrc = driverPhoto.attr('src');

							if (photoSrc.endsWith('logo-2.svg')) {
								openShiftForm(clickedDayId, calendarId);
							} else {
								const driverInfo = driverPh.find('.driver-info-reshuffle');
								const startTime = driverInfo.find('.driver-time').text().split(' - ')[0];
								const endTime = driverInfo.find('.driver-time').text().split(' - ')[1];
								updShiftForm(clickedDayId, calendarId, dataName, startTime, endTime, idDriver, idVehicle, idReshuffle);
							}
						}
				});
			});
		}
		function fetchCalendarData(formattedStartDate, formattedEndDate) {

			apiUrl = `/api/reshuffle/${formattedStartDate}/${formattedEndDate}/`;
			$.ajax({
				url: apiUrl,
				type: 'GET',
				dataType: 'json',
				success: function (data) {
					reshuffleHandler(data);
				},
				error: function (error) {
					console.error(error);
				}
			});
		}
	});

//modal-shift

	const timeList = document.getElementById('timeList');

  for (let i = 0; i < 24; i++) {
    for (let j = 0; j < 60; j += 15) {
      const hour = i.toString().padStart(2, '0');
      const minute = j.toString().padStart(2, '0');
      const option = document.createElement('option');
      option.value = `${hour}:${minute}`;
      timeList.appendChild(option);
    }
  }
  $('.shift-close-btn').off('click').on('click', function (e) {
  	e.preventDefault();
		$('#modal-shift').hide();
	});
});

function validateInputTime(input) {
  input.addEventListener('input', function () {
    let valueWithoutColon = input.value.replace(/:/g, '');
    if (valueWithoutColon.length < 2) {
      return;
    }
    let hours = valueWithoutColon.slice(0, 2);
    input.value = hours + ':' + valueWithoutColon.slice(2, 5);

    input.value = input.value.slice(0, 5);

    var isValid = /^([0-1]?[0-9]|2[0-4]):([0-5][0-9])(:[0-5][0-9])?$/.test(input.value);

    if (isValid) {
      input.style.backgroundColor = '#bfa';
    } else {
      input.style.backgroundColor = '#fba';
    }
  });
}

function showShiftMessage(success, upd, time, vehicle) {
	if (success) {
		$(".shift-success-message").show();
		if (upd) {
			$(".shift-success-message h2").text("Зміна успішно оновлена");
		} else {
			$(".shift-success-message h2").text("Зміна успішно створена");
		}
		setTimeout(function () {
			$(".shift-success-message").hide();
		}, 5000);
	} else {
		$(".shift-success-message").show();
		$(".shift-success-message h2").text("Помилка створення зміни. У водія існує зміна в " + time + " на авто " + vehicle);
		setTimeout(function () {
			$(".shift-success-message").hide();
		}, 8000);
	}
}

