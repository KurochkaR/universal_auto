$(document).ready(function () {

	const today = new Date();
	const daysToShow = 14;

	let cachedCar = null;
	let carDate = null;

	function formatDateString(inputDateString) {
		const parts = inputDateString.split('-');

		if (parts.length === 3) {
			return moment(inputDateString).format('DD.MM.YYYY')
		}
		return inputDateString;
	}

	const formatDateForDatabase = (date) => moment(date).format('YYYY-MM-DD');
	const formatDate = (date) => moment(date).format('DD.MM');
	const formatTime = (date) => moment(date).format('HH:mm');

	function isYesterdayOrEarlier(date) {
		// replace it with moment js
		const todayDate = new Date();
		const yesterday = new Date(todayDate);
		yesterday.setDate(yesterday.getDate() - 1);
		return date < yesterday;

	}

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

						const driverImage = renderPhoto(driver);

						var startShiftFormatted = driver.start_shift.split(':').slice(0, 2).join(':');
						var endShiftFormatted = driver.end_shift.split(':').slice(0, 2).join(':');
						const driverInfo = $('<div>').addClass('driver-info-reshuffle');
						const driverDate = $('<p>').addClass('driver-date').text(driver.date);
						const driverName = $('<p>').addClass('driver-name').text(driver.driver_name);
						const driverTime = $('<p>').addClass('driver-time').text(startShiftFormatted + ' - ' + endShiftFormatted);

						driverInfo.append(driverDate, driverName, driverTime);
						driverPhoto.append(driverInfo, driverImage);
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

	function handleButtonClick(increaseDays, vehicleLC, renderCalendar) {
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

		apiUrl = `/api/reshuffle/${formattedStartDate}&${formattedEndDate}/`;
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

	function reshuffleHandler(data) {
		const driverCalendar = $('.driver-calendar');
		driverCalendar.empty();

		data.sort((a, b) => a.swap_licence.localeCompare(b.swap_licence));

		const calendarHTML = data.map(function (carData) {
			let brandImage = '';

			if (carData.vehicle_brand) {
				const vehicleBrand = carData.vehicle_brand.toLowerCase();
				const logos = {
					uklon: 'https://storage.googleapis.com/jobdriver-bucket/docs/brand-uklon.png',
					bolt: 'https://storage.googleapis.com/jobdriver-bucket/docs/brand-bolt.png',
					uber: 'https://storage.googleapis.com/jobdriver-bucket/docs/brand-uber.png',
				};

				brandImage = '<img class="brand-vehicle" src="' + logos[vehicleBrand] + '" alt="Бренд авто">';
			}

			return `
			<div class="calendar-container" id="${carData.swap_licence}">
				<div class="car-image">
					<img src="${VehicleImg}" alt="Зображення авто">
					<p class="vehicle-license-plate">${carData.swap_licence}</p>
					${brandImage}
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
			</div>`
		}).join('');

		driverCalendar.append(calendarHTML);

		$('.calendar-container', driverCalendar).each(function () {
			const calendarDetail = $('.calendar-detail', this);
			const investPrevButton = $('#investPrevButton', this);
			const investNextButton = $('#investNextButton', this);
			const vehicleLC = $(this).attr('id');

			const driverList = data.find(driver => driver.swap_licence === vehicleLC);

			function renderCalendar(startDate) {
				calendarDetail.empty();

				for (let i = 0; i < daysToShow; i++) {
					const day = new Date(startDate);
					day.setDate(startDate.getDate() + i);

					const card = $('<div>').addClass('calendar-card');
					const formattedDate = formatDateForDatabase(day);
					card.attr('id', formattedDate);

					const dayOfWeek = day.toLocaleDateString('uk-UA', {weekday: 'short'});

					const dayOfWeekElement = $('<div>').text(dayOfWeek).addClass('day-of-week');
					card.append(dayOfWeekElement);

					const dateElement = $('<div>').text(formatDate(day)).addClass('date');
					card.append(dateElement);

					const driverPhotoContainer = $('<div>').addClass('driver-photo-container');
					const isDriverPhotoVisible = driverList.reshuffles.some(function (driver) {
						return driver.date === formattedDate && driver.driver_photo || driver.date === formattedDate && driver.dtp_maintenance;
					});
					if (isDriverPhotoVisible) {

						driverList.reshuffles.forEach(function (driver) {
							if (driver.date === formattedDate) {

								const driverPhoto = $('<div>').addClass('driver-photo');
								driverPhoto.attr('data-name', driver.driver_name).attr('data-dtp-maintenance', driver.dtp_maintenance).attr('data-id-driver', driver.driver_id).attr('data-id-vehicle', driver.vehicle_id).attr('reshuffle-id', driver.reshuffle_id);
								const driverImage = renderPhoto(driver);

								const startTime = new Date('1970-01-01T' + driver.start_shift);
								const endTime = new Date('1970-01-01T' + driver.end_shift);

								const StartTimes = formatTime(startTime);
								const EndTimes = formatTime(endTime);

								const driverInfo = $('<div>').addClass('driver-info-reshuffle');
								const driverDate = $('<p>').addClass('driver-date').text(driver.date);
								const driverName = $('<p>').addClass('driver-name').text(driver.driver_name);
								const driverTime = $('<p>').addClass('driver-time').text(StartTimes + ' - ' + EndTimes);

								let additionalInfo = '';

								if (driver.dtp_maintenance === "accident") {
									additionalInfo = 'ДТП';
								} else if (driver.dtp_maintenance === "maintenance") {
									additionalInfo = 'Тех. обслуговування';
								}

								if (additionalInfo) {
									driverName.text(additionalInfo);
								}

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

					if (moment(day).isSame(new Date(), "day")) {
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
				}

				$('.driver-photo-container').each(function (index, container) {
					var photos = $(container).find('.driver-photo img');

					if (photos.length > 2) {
						$(container).addClass('photo-small-2');
					}
				});
			}

			renderCalendar(currentDate);

			investNextButton.on('click', function () {
				handleButtonClick(10, vehicleLC, renderCalendar);
			});

			investPrevButton.on('click', function () {
				handleButtonClick(-10, vehicleLC, renderCalendar);
			});
		});

		function updShiftForm(clickedDayId, calendarId, dataName, startTime, endTime, driverId, vehicleId, idReshuffle) {
			const modalShiftTitle = $('.modal-shift-title h2');
			const shiftForm = $('#modal-shift');
			const modalShiftDate = $('.modal-shift-date');
			const shiftDriver = $('#shift-driver');
			const startTimeInput = $('#startTime').css('background-color', '#fff');
			const endTimeInput = $('#endTime').css('background-color', '#fff');
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
			$('.modal-overlay').show();

			const deleteBtn = $('.delete-btn').show();
			const deleteAllBtn = $('.delete-all-btn').show();
			const updBtn = $('.upd-btn').show();
			const updAllBtn = $('.upd-all-btn').show();
			$('.shift-vehicle').show();
			$('.shift-btn').hide();
			shiftForm.show();
			validateInputTime(startTimeInput[0], 'startTime', endTimeInput[0]);
			validateInputTime(endTimeInput[0], 'endTime');

			function handleDelete(action) {
				$.ajax({
					url: ajaxPostUrl,
					type: 'POST',
					data: {action, ...ajaxData},
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
				$('.modal-overlay').hide();
				handleDelete('delete_shift');
			});

			deleteAllBtn.off('click').on('click', function (e) {
				e.preventDefault();
				$('.modal-overlay').hide();
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
						start_time: formatTimeWithSeconds(startTimeInput.val()),
						end_time: formatTimeWithSeconds(endTimeInput.val()),
						driver_id: selectedDriverId,
						reshuffle_id: idReshuffle,
						...ajaxData
					},
					success: function (response) {
						fetchCalendarData(formattedStartDate, formattedEndDate);
						if (response.data[0] === true) {
							filterCheck();
							showShiftMessage(response.data[0], response.data[1]);
						} else {
							showConflictMessage(response.data[0], response.data[1], response.data[1]);
						}
					},
				});
				shiftForm.hide();
			}

			updBtn.off('click').on('click', function (e) {
				e.preventDefault();
				$('.modal-overlay').hide();
				handleUpdate('update_shift');
			});

			updAllBtn.off('click').on('click', function (e) {
				e.preventDefault();
				$('.modal-overlay').hide();
				handleUpdate('update_all_shift');
			});
		}

		function openShiftForm(clickedDayId, calendarId) {
			$('.recurrence').show();
			$('.delete-btn').hide();
			$('.delete-all-btn').hide();
			$('.upd-btn').hide();
			$('.upd-all-btn').hide();
			$('.shift-vehicle').hide();
			const modalShiftTitle = $('.modal-shift-title h2');
			const shiftForm = $('#modal-shift');
			const shiftBtn = $('.shift-btn').show();
			const modalShiftDate = $('.modal-shift-date');
			const startTimeInput = $('#startTime');
			const endTimeInput = $('#endTime');
			const shiftDriver = $('#shift-driver');
			const csrfTokenInput = $('input[name="csrfmiddlewaretoken"]');
			$("#startTime").val("").css('background-color', '#fff')
			$("#endTime").val("").css('background-color', '#fff')
			$('.modal-overlay').show();
			modalShiftTitle.text("Створення зміни");
			modalShiftDate.text(formatDateString(clickedDayId));
			shiftForm.show();
			validateInputTime(startTimeInput[0], 'startTime', endTimeInput[0]);
			validateInputTime(endTimeInput[0], 'endTime');
			shiftBtn.off('click').on('click', function (e) {
				$('.shift-time-error').hide();
				e.preventDefault();
				const selectedDriverId = shiftDriver.val();
				const recurrence = $('#recurrence').val();
				let error = false;

				if (startTimeInput.val() === "" || startTimeInput.val() === ":" || startTimeInput.val().length !== 5) {
					$('#startTime').css('background-color', '#fba');
					$('.shift-startTime-error').text('Введіть час').show();
					error = true;
				} else {
					$('#startTime').css('background-color', '');
					$('.shift-startTime-error').text('').hide();
				}

				if (endTimeInput.val() === "" || endTimeInput.val() === ":" || endTimeInput.val().length !== 5) {
					$('#endTime').css('background-color', '#fba');
					$('.shift-endTime-error').text('Введіть час').show();
					error = true;
				} else {
					$('#endTime').css('background-color', '');
					$('.shift-endTime-error').text('').hide();
				}

				if (error) {
					return;
				}
				$.ajax({
					url: ajaxPostUrl,
					type: 'POST',
					data: {
						action: 'add_shift',
						vehicle_licence: calendarId,
						date: clickedDayId,
						start_time: formatTimeWithSeconds(startTimeInput.val()),
						end_time: formatTimeWithSeconds(endTimeInput.val()),
						driver_id: selectedDriverId,
						recurrence,
						csrfmiddlewaretoken: csrfTokenInput.val()
					},
					success: function (response) {
						$('.modal-overlay').hide();
						fetchCalendarData(formattedStartDate, formattedEndDate);
						if (response.data[0] === true) {
							filterCheck();
							showShiftMessage(response.data[0], response.data[1]);
						} else {
							showConflictMessage(response.data[0], response.data[1], response.data[1]);
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
					const idDriver = driverPh.data('id-driver') ? driverPh.data('id-driver') : driverPh.data('dtp-maintenance');
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
		apiUrl = `/api/reshuffle/${formattedStartDate}&${formattedEndDate}/`;

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
		apiUrl = `/api/reshuffle/${formattedStartDate}&${formattedEndDate}/`;

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

	let currentDate = new Date(today);
	currentDate.setDate(currentDate.getDate() - 6);
	let formattedStartDate = formatDateForDatabase(currentDate);

	let endDate = new Date(currentDate);
	endDate.setDate(endDate.getDate() + daysToShow - 1);
	let formattedEndDate = formatDateForDatabase(endDate);

	fetchCalendarData(formattedStartDate, formattedEndDate);

	handleSearchChange($("#search-vehicle-calendar"), "swap_licence", null, $("#search-shift-driver"));
	handleSearchChange($("#search-shift-driver"), null, "reshuffles", $("#search-vehicle-calendar"));

	$(".refresh-search").click(function () {
		$("#search-vehicle-calendar, #search-shift-driver").val("all").change();
	});

	// const timeList = document.getElementById('timeList');
	//
	// for (let i = 0; i < 24; i++) {
	// 	for (let j = 0; j < 60; j += 15) {
	// 		const hour = i.toString().padStart(2, '0');
	// 		const minute = j.toString().padStart(2, '0');
	// 		const option = document.createElement('option');
	// 		option.value = `${hour}:${minute}`;
	// 		timeList.appendChild(option);
	// 	}
	// }
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

function validateInputTime(input, field, nextInput) {
    $(input).on('input', function (event) {
        let inputValue = event.target.value;

        inputValue = inputValue.replace(/\D/g, '');

        if (inputValue.length >= 2) {
            inputValue = inputValue.slice(0, 2) + ':' + inputValue.slice(2);
        }

        input.value = input.value.slice(0, 5);
        event.target.value = inputValue;

		var isValid = /^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$/.test(input.value);

		if (isValid) {
			input.style.backgroundColor = '#bfa';
			$('.shift-' + field + '-error').text('').hide();
			blockBtn(false);
			if (nextInput) {
                $(nextInput).focus();
            }

			if (field === 'endTime') {
				if (input.value === '00:00') {
					input.value = '23:59';
				}
				const startTimeInput = $('#startTime').val();

				if (compareTimes(startTimeInput, input.value) > 0) {
					input.style.backgroundColor = '#fba';
					$('.shift-' + field + '-error').text('Введіть коректний час').show();
					blockBtn(true);
				}
			}
		} else {
			input.style.backgroundColor = '#fba';
			$('.shift-' + field + '-error').text('Введіть коректний час').show();
			blockBtn(true);
		}}).on('keydown', function(event) {
        if (event.key === 'Backspace') {
            let inputValue = $(this).val();
            let cursorPosition = this.selectionStart;


            if (inputValue.charAt(cursorPosition - 1) === ':' && cursorPosition === inputValue.length) {
                $(this).val(inputValue.slice(0, cursorPosition - 1));
                event.preventDefault();
            } else if (inputValue.charAt(cursorPosition - 1).match(/\D/g)) {
                $(this).val(inputValue.slice(0, cursorPosition - 1) + inputValue.slice(cursorPosition));
            }
        } else if ($(this).val().length >= 5 && event.key !== 'Backspace') {
            event.preventDefault();
        }
    });
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
		}, 2000);
	} else {
		$(".shift-success-message").show();
		if (time === undefined || time === null || time === "") {
			$(".shift-success-message h2").text(showText);
		} else {
			$(".shift-success-message h2").text("Помилка оновлення зміни, існує зміна " + time + " на авто " + vehicle);
		}
		setTimeout(function () {
			$(".shift-success-message").hide();
		}, 5000);
	}
}

function showConflictMessage(success, showText, messageList) {
	if (success) {
		$(".shift-success-message").show();
		$(".shift-success-message h2").text(showText);

		setTimeout(function () {
			$(".shift-success-message").hide();
		}, 2000);
	} else {
		$(".shift-success-message").show();
		let resultMessage = "Помилка, конфлікт змін:<br>";
		if (Array.isArray(messageList)) {
			const messages = messageList.map(conflict => `${conflict.licence_plate} - ${conflict.conflicting_time}`);
			resultMessage += messages.join('<br>');
		} else {
			resultMessage += messageList;
		}
		$(".shift-success-message h2").html(resultMessage);
		setTimeout(function () {
			$(".shift-success-message").hide();
		}, 5000);
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


function openModal() {
	document.getElementById('modal-shift').style.display = 'block';
	document.querySelector('.modal-overlay').style.display = 'block';
	document.body.style.overflow = 'hidden';
}

function closeModal() {
	document.getElementById('modal-shift').style.display = 'none';
	document.querySelector('.modal-overlay').style.display = 'none';
	document.body.style.overflow = '';
}

document.querySelector('.shift-close-btn').addEventListener('click', closeModal);

function formatTimeWithSeconds(time) {
	const parts = time.split(':');
	if (parts[1] === '59') {
		return parts[0] + ':' + parts[1] + ':59';
	} else {
		return parts[0] + ':' + parts[1] + ':00';
	}
}

function renderPhoto(driver) {
	let driverImage;
	if (driver.driver_photo) {
		driverImage = $('<img>').attr('src', 'https://storage.googleapis.com/jobdriver-bucket/' + driver.driver_photo).attr('alt', `Фото водія`);
	} else {
		if (driver.dtp_maintenance === "maintenance") {
			driverImage = $('<img>').attr('src', 'https://storage.googleapis.com/jobdriver-bucket/docs/service.png').attr('alt', `Фото водія`);
		} else {
			driverImage = $('<img>').attr('src', 'https://storage.googleapis.com/jobdriver-bucket/docs/accident.png').attr('alt', `Фото водія`);
		}
	}
	return driverImage;
}

