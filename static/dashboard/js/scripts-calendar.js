$(document).ready(function () {

	const today = new Date();
	const daysToShow = 14;

	function formatDateForDatabase(date) {
		const year = date.getFullYear();
		const month = (date.getMonth() + 1).toString().padStart(2, '0');
		const day = date.getDate().toString().padStart(2, '0');

		const formattedDate = `${year}-${month}-${day}`;
		return formattedDate;
	}

	function formatDateString(inputDateString) {
    var parts = inputDateString.split('-');
    if (parts.length === 3) {
        var formattedDate = parts[2] + '.' + parts[1] + '.' + parts[0];
        return formattedDate;
    }
    return inputDateString;
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

		data.sort((a, b) => {
			if (a.swap_licence < b.swap_licence) {
				return -1;
			}
			if (a.swap_licence > b.swap_licence) {
				return 1;
			}
			return 0;
    });
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

//		const totalPages = Math.ceil(data.length / 5);
//		let currentPage = 1;

//		const paginationContainer = `
//			<div class="pagination">
//				<button id="prevPageBtn">
//					<svg version="1.0" xmlns="http://www.w3.org/2000/svg" width="50px" height="50px" viewBox="0 0 1280.000000 1280.000000" preserveAspectRatio="xMidYMid meet">
//						<metadata>Created by potrace 1.15, written by Peter Selinger 2001-2017</metadata>
//						<g transform="translate(1280.000000,0.000000) scale(-0.100000,0.100000)" fill="#EC6323" stroke="none">
//							<path d="M1422 12134 c3 -10 416 -1279 917 -2819 l912 -2801 -916 -2813 c-504 -1547 -914 -2815 -912 -2817 3 -4 10215 5612 10230 5625 4 4 -907 511 -2025 1126 -3792 2086 -5300 2916 -6748 3712 -795 438 -1449 798 -1454 801 -5 3 -7 -3 -4 -14z"/>
//						</g>
//				</svg>
//				</button>
//				<span id="pageInfo">Сторінка ${currentPage} з ${totalPages}</span>
//				<button id="nextPageBtn">
//					<svg version="1.0" xmlns="http://www.w3.org/2000/svg" width="50px" height="50px" viewBox="0 0 1280.000000 1280.000000" preserveAspectRatio="xMidYMid meet">
//						<metadata>Created by potrace 1.15, written by Peter Selinger 2001-2017</metadata>
//						<g transform="translate(0.000000,1280.000000) scale(0.100000,-0.100000)" fill="#EC6323" stroke="none">
//							<path d="M1422 12134 c3 -10 416 -1279 917 -2819 l912 -2801 -916 -2813 c-504 -1547 -914 -2815 -912 -2817 3 -4 10215 5612 10230 5625 4 4 -907 511 -2025 1126 -3792 2086 -5300 2916 -6748 3712 -795 438 -1449 798 -1454 801 -5 3 -7 -3 -4 -14z"/>
//						</g>
//					</svg>
//				</button>
//			</div>
//		`;
//
//
//		$('.driver-calendar').append(paginationContainer);


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

					if (photos.length > 3) {
						$(container).addClass('photo-small-2');
					} else if (photos.length > 2) {
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

					if (photos.length > 3) {
						$(container).addClass('photo-small-2');
					} else if (photos.length > 2) {
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
			modalShiftDate.text(formatDateString(clickedDayId));
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
			validateInputTime(startTimeInput[0], 'startTime');
			validateInputTime(endTimeInput[0], 'endTime');

			function handleDelete(action) {
				$.ajax({
					url: ajaxPostUrl,
					type: 'POST',
					data: { action, ...ajaxData },
					success: function (response) {
						fetchCalendarData(formattedStartDate, formattedEndDate);
						filterCheck()
						showShiftMessage(true, response.data[1]);
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
						date: clickedDayId,
						start_time: startTimeInput.val(),
						end_time: endTimeInput.val(),
						driver_id: selectedDriverId,
						reshuffle_id: idReshuffle,
						...ajaxData
					},
					success: function (response) {
						if (response.data[0] === true) {
							fetchCalendarData(formattedStartDate, formattedEndDate);
							filterCheck();
							showShiftMessage(true, response.data[1]);
						} else {
							showShiftMessage(response.data[0], false, response.data[1]['conflicting_time'], response.data[1]['licence_plate']);
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

			modalShiftTitle.text("Створення зміни");
			modalShiftDate.text(formatDateString(clickedDayId));
			shiftForm.show();
			validateInputTime(startTimeInput[0], 'startTime');
			validateInputTime(endTimeInput[0], 'endTime');
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
							if (response.data[0] === true) {
								fetchCalendarData(formattedStartDate, formattedEndDate);
								filterCheck();
								showShiftMessage(response.data[0], response.data[1]);
							} else {
								showShiftMessage(response.data[0], response.data[1], response.data[1]['conflicting_time'], response.data[1]['licence_plate']);
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

//		function showCalendars(page) {
//			$('.calendar-container').hide();
//
//			const startIndex = (page - 1) * 4;
//			const endIndex = Math.min(startIndex + 3, data.length - 1);
//
//			const calendarsToShow = $('.calendar-container').filter(function (index) {
//					return index >= startIndex && index <= endIndex;
//			});
//
//			if (calendarsToShow.length > 0) {
//					calendarsToShow.show();
//			} else {
//					$('.driver-calendar').html('<p>Немає календарів для відображення.</p>');
//			}
//
//			$('#pageInfo').text(`Сторінка ${page} з ${totalPages}`);
//		}
//
//
//		$('#prevPageBtn').on('click', function () {
//			if (currentPage > 1) {
//				currentPage--;
//				showCalendars(currentPage);
//			}
//		});
//
//		$('#nextPageBtn').on('click', function () {
//			if (currentPage < totalPages) {
//				currentPage++;
//				showCalendars(currentPage);
//			}
//		});

//		showCalendars(currentPage);
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

	function fetchDataAndHandle(filterProperty, reshuffleProperty) {
		var selectedValue = $(this).val();
		var selectedText = $(this).find("option:selected").text();
		apiUrl = `/api/reshuffle/${formattedStartDate}/${formattedEndDate}/`;

		return $.ajax({
			url: apiUrl,
			type: 'GET',
			dataType: 'json',
		}).then(function (data) {
			var filteredData = data;
			if (selectedValue !== "all") {
				filteredData = data.filter(function (item) {
					return item[filterProperty] === selectedText ||
						(item[reshuffleProperty] && item[reshuffleProperty].some(function (reshuffle) {
							return reshuffle.driver_name === selectedText;
						}));
				});
			}
			return filteredData;
		});
	}

	function handleSearchChange($element, filterProperty, reshuffleProperty, $otherElement) {
    $element.change(function () {
			fetchDataAndHandle.call(this, filterProperty, reshuffleProperty)
				.then(function (filteredData) {
					reshuffleHandler(filteredData);
				});
			if ($otherElement) {
				$otherElement.val("all");
			}
    });
	}


	handleSearchChange($("#search-vehicle-calendar"), "swap_licence", null, $("#search-shift-driver"));
	handleSearchChange($("#search-shift-driver"), null, "reshuffles", $("#search-vehicle-calendar"));

	$(".refresh-search").click(function () {
		$("#search-vehicle-calendar, #search-shift-driver").val("all").change();
	});

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



function compareTimes(time1, time2) {
  const [hours1, minutes1] = time1.split(':').map(Number);
  const [hours2, minutes2] = time2.split(':').map(Number);

  if (hours1 !== hours2) {
    return hours1 - hours2;
  }

  return minutes1 - minutes2;
}

function validateInputTime(input, field) {
  $(input).on('input', function () {
    let numericValue = input.value.replace(/\D/g, '');

    let hours = numericValue.slice(0, 2);
    let minutes = numericValue.slice(2, 4);

    input.value = hours + ':' + minutes;

    input.value = input.value.slice(0, 5);

    var isValid = /^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$/.test(input.value);

    if (isValid) {
      input.style.backgroundColor = '#bfa';
      blockBtn(false);

      if (field === 'endTime') {
        if (input.value === '00:00') {
          input.value = '23:59';
        }
        const startTimeInput = $('#startTime').val();

        if (compareTimes(startTimeInput, input.value) > 0) {
          input.style.backgroundColor = '#fba';
          blockBtn(true);
        }
      }
    } else {
      input.style.backgroundColor = '#fba';
      blockBtn(true);
    }
  });
  $(input).attr('inputmode', 'numeric');
}

function blockBtn(arg) {
	if (arg === true) {
		$('delete-all-btn').attr('disabled', true);
		$('.delete-btn').attr('disabled', true);
		$('.upd-btn').attr('disabled', true);
		$('.upd-all-btn').attr('disabled', true);
		$('.shift-btn').attr('disabled', true);
	} else {
		$('delete-all-btn').attr('disabled', false);
		$('.delete-btn').attr('disabled', false);
		$('.upd-btn').attr('disabled', false);
		$('.upd-all-btn').attr('disabled', false);
		$('.shift-btn').attr('disabled', false);
	}
}

function showShiftMessage(success, showText, time, vehicle) {
	if (success) {
		$(".shift-success-message").show();
		$(".shift-success-message h2").text(showText);

		setTimeout(function () {
			$(".shift-success-message").hide();
		}, 5000);
	} else {
		$(".shift-success-message").show();
		if (time === undefined || time === null || time === "") {
			$(".shift-success-message h2").text(showText);
		} else {
			$(".shift-success-message h2").text("Помилка оновлення зміни, існує зміна в " + time + " на авто " + vehicle);
		}
		setTimeout(function () {
			$(".shift-success-message").hide();
		}, 8000);
	}
}

function filterCheck() {
	const vehicleFilter = $("#search-vehicle-calendar").val();
	const driverFilter = $("#search-shift-driver").val();

	if (vehicleFilter !== "all") {
		$("#search-vehicle-calendar").change();
	}

	if (driverFilter !== "all") {
		$("#search-shift-driver").change();
	}
}
