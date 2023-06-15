var map, orderReject, orderGo, orderConfirm, orderData, markersTaxi,
  taxiMarkers = [];
var circle, intervalId, intervalTime, intervalTaxiMarker;

const FREE_DISPATCH = parseInt(parkSettings && parkSettings.FREE_CAR_SENDING_DISTANCE || 0);
const TARIFF_DISPATCH = parseInt(parkSettings && parkSettings.TARIFF_CAR_DISPATCH || 0);
const TARIFF_OUTSIDE_DISPATCH = parseInt(parkSettings && parkSettings.TARIFF_CAR_OUTSIDE_DISPATCH || 0);
const TARIFF_IN_THE_CITY = parseInt(parkSettings && parkSettings.TARIFF_IN_THE_CITY || 0);
const TARIFF_OUTSIDE_THE_CITY = parseInt(parkSettings && parkSettings.TARIFF_OUTSIDE_THE_CITY || 0);
const CENTRE_CITY_LAT = parseFloat(parkSettings && parkSettings.CENTRE_CITY_LAT || 0);
const CENTRE_CITY_LNG = parseFloat(parkSettings && parkSettings.CENTRE_CITY_LNG || 0);
const CENTRE_CITY_RADIUS = parseInt(parkSettings && parkSettings.CENTRE_CITY_RADIUS || 0);
const SEND_TIME_ORDER_MIN = parseInt(parkSettings && parkSettings.SEND_TIME_ORDER_MIN || 0);
const MINIMUM_PRICE_RADIUS = parseInt(parkSettings && parkSettings.MINIMUM_PRICE_RADIUS || 0);
const MAXIMUM_PRICE_RADIUS = parseInt(parkSettings && parkSettings.MAXIMUM_PRICE_RADIUS || 0);
const TIMER = parseInt(parkSettings && parkSettings.SEARCH_TIME || 0);
const userLanguage = navigator.language || navigator.userLanguage;

const city_boundaries = function () {
  return [
    [50.482433, 30.758250], [50.491685, 30.742045], [50.517374, 30.753721], [50.529704, 30.795370],
    [50.537806, 30.824810], [50.557504, 30.816837], [50.579778, 30.783808], [50.583684, 30.766494],
    [50.590833, 30.717995], [50.585827, 30.721184], [50.575221, 30.709590], [50.555702, 30.713665],
    [50.534572, 30.653589], [50.572107, 30.472565], [50.571557, 30.464734], [50.584574, 30.464120],
    [50.586367, 30.373054], [50.573406, 30.373049], [50.570661, 30.307423], [50.557272, 30.342127],
    [50.554324, 30.298128], [50.533394, 30.302445], [50.423057, 30.244148], [50.446055, 30.348753],
    [50.381271, 30.442675], [50.372075, 30.430830], [50.356963, 30.438040], [50.360358, 30.468252],
    [50.333520, 30.475291], [50.302393, 30.532814], [50.213270, 30.593929], [50.226755, 30.642478],
    [50.291609, 30.590369], [50.335279, 30.628839], [50.389522, 30.775925], [50.394966, 30.776293],
    [50.397798, 30.790669], [50.392594, 30.806395], [50.404878, 30.825881], [50.458385, 30.742751],
    [50.481657, 30.748158], [50.482454, 30.758345]
  ].map(function ([lat, lng]) {
    return {
      lat, lng
    }
  });
};

function toRadians(degrees) {
  return degrees * Math.PI / 180;
}

function haversine(lat1, lon1, lat2, lon2) {
  const earthRadiusKm = 6371;

  const dLat = toRadians(lat2 - lat1);
  const dLon = toRadians(lon2 - lon1);

  lat1 = toRadians(lat1);
  lat2 = toRadians(lat2);

  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.sin(dLon / 2) * Math.sin(dLon / 2) * Math.cos(lat1) * Math.cos(lat2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return earthRadiusKm * c;
}

function getAllPath(obj) {
  var allPaths = [];
  for (var i = 0; i < obj.length; i++) {
    var currentPath = obj[i].path;
    allPaths = allPaths.concat(currentPath);
  }
  return allPaths
}

function pathSeparation(obj) {
  var getCity = city_boundaries();
  var cityPolygon = new google.maps.Polygon({paths: getCity});

  var inCity = [], outOfCity = [];
  obj.forEach(function (path) {
    // Використовуємо метод containsLocation() для перевірки, чи точка входить у межі міста
    var isInCity = google.maps.geometry.poly.containsLocation(path, cityPolygon);
    // Якщо точка входить у межі міста, додаємо її до масиву inCity, інакше - до масиву outOfCity
    if (isInCity) {
      inCity.push(path);
    } else {
      outOfCity.push(path);
    }
  });
  return [inCity, outOfCity]
}

function getPathCoords(obj) {
  var coords = []
  for (var i = 0; i < obj.length; i++) {
    coords.push({lat: obj[i].lat(), lng: obj[i].lng()});
  }
  return coords
}

function calculateDistance(obj) {
  let Distance = 0;
  for (let i = 0; i < obj.length - 1; i++) {
    const {lat: lat1, lng: lon1} = obj[i];
    const {lat: lat2, lng: lon2} = obj[i + 1];
    const distance = haversine(lat1, lon1, lat2, lon2);
    Distance += distance;
  }
  return Distance;
}

function hidePaymentButtons() {
  $(".order-confirm").remove()
}

function addMarker(obj) {
  const marker = new google.maps.Marker(obj);
  if (Array.isArray(markersTaxi)) {
    markersTaxi.push(marker);
  } else {
    markersTaxi = [marker];
  }
  return marker;
}

function setAutoCenter(map) {
  var bounds = new google.maps.LatLngBounds();
  markersTaxi.forEach(marker => {
    bounds.extend(marker.getPosition());
  });
  map.fitBounds(bounds);
}

function getMarkerIcon(type) {
  return {
    url: 'static/app/images/icon_' + type + '.png',
    scaledSize: new google.maps.Size(32, 32),
  };
}

function createMap(address, to_address) {
  var modal = document.createElement('div');
  modal.id = 'order-modal';
  modal.innerHTML = '<div id="map"></div>';

  document.body.appendChild(modal);

  var mapCanvas = document.getElementById("map");
  var mapOpts = {
    zoom: 10,
    center: new google.maps.LatLng(50.4546600, 30.5238000)
  };
  map = new google.maps.Map(mapCanvas, mapOpts);

  // Додати from_address маркер
  addMarker({
    position: address[0].geometry.location,
    map,
    title: address[0].formatted_address,
    icon: getMarkerIcon('address'),
    animation: google.maps.Animation.DROP
  });

  // Додати to_address маркер
  addMarker({
    position: to_address[0].geometry.location,
    map,
    title: to_address[0].formatted_address,
    icon: getMarkerIcon('to_address'),
    animation: google.maps.Animation.DROP
  });

  var directionsService = new google.maps.DirectionsService();
  var request = {
    origin: address[0].formatted_address,
    destination: to_address[0].formatted_address,
    travelMode: google.maps.TravelMode.DRIVING
  };
  directionsService.route(request, function (result, status) {
    if (status == google.maps.DirectionsStatus.OK) {
      // Отримати відстань між точками
      var distanceInMeters = result.routes[0].legs[0]['steps'];

      var allPathsAddress = getAllPath(distanceInMeters)

      var inCitOrOutCityAddress = pathSeparation(allPathsAddress)
      var inCity = inCitOrOutCityAddress[0]
      var outOfCity = inCitOrOutCityAddress[1]

      var inCityCoords = getPathCoords(inCity)
      var outOfCityCoords = getPathCoords(outOfCity)


      let inCityDistance = parseInt(calculateDistance(inCityCoords));
      let outOfCityDistance = parseInt(calculateDistance(outOfCityCoords));
      let totalDistance = inCityDistance + outOfCityDistance;

      var tripAmount = Math.ceil((inCityDistance * TARIFF_IN_THE_CITY) + (outOfCityDistance * TARIFF_OUTSIDE_THE_CITY));
      setCookie('sumOder', tripAmount, 1)
      setCookie('distanceGoogle', totalDistance, 1)
      setAutoCenter(map);

      // Додати текст та таймер до елементу costDiv
      var costText = gettext("Оберіть метод оплати.");
      var costDiv = document.createElement('div');
      costDiv.innerHTML = '<div class="alert alert-primary mt-2" role="alert">' +
        '<h6 class="alert-heading alert-message mb-0">' + costText + '</h6><div id="timer"></div></div>';
      map.controls[google.maps.ControlPosition.TOP_CENTER].push(costDiv);

      // Додати кнопки оплати на карту
      var paymentDiv = document.createElement('div');
      var button1 = gettext('Готівка');
      var button2 = gettext('Картка');
      var button3 = gettext('Відмовитись');
      paymentDiv.innerHTML =
        "<div class='mb-3'>" +
        "<button class='order-confirm btn btn-primary'>" + button1 + "</button>" +
        // "<button class='order-confirm btn btn-primary ml-3'>" + button2 + "</button>" +
        "<button class='order-reject btn btn-danger ml-3'>" + button3 + "</button>" +
        "</div>";

      map.controls[google.maps.ControlPosition.BOTTOM_CENTER].push(paymentDiv);

      if (getCookie('idOrder') != null) {
        orderConfirm = paymentDiv.getElementsByClassName('order-confirm')[0];
        var Text = gettext("Заждіть поки ми підберемо вам автомобіль. Ваша ціна складає ") + tripAmount + gettext(" грн.");
        costDiv = document.createElement('div');
        costDiv.innerHTML = '<div class="alert alert-primary mt-2" role="alert">' +
          '<h6 class="alert-heading alert-message mb-0">' + Text + '</h6><div id="timer"></div></div>';
        map.controls[google.maps.ControlPosition.TOP_CENTER].clear();
        map.controls[google.maps.ControlPosition.TOP_CENTER].push(costDiv);
        intervalTaxiMarker = setInterval(updateTaxiMarkers, 10000);
        orderConfirm.remove()
        startTimer();

        // Додати обробник події для кнопки "Відмовитись" для перенаправлення на домашню сторінку
        orderReject = paymentDiv.getElementsByClassName('order-reject')[0];
        orderReject.addEventListener("click", onOrderReject);
      } else {
        // Додати обробник події для кнопки "Готівка" для відправлення POST-запиту до views.py
        orderConfirm = paymentDiv.getElementsByClassName('order-confirm')[0];
        orderConfirm.addEventListener("click", function () {
          costText = gettext("Заждіть поки ми підберемо вам автомобіль. Ваша ціна складає ") + tripAmount + gettext(" грн.");
          costDiv.innerHTML = '<div class="alert alert-primary mt-2" role="alert">' +
            '<h6 class="alert-heading alert-message mb-0">' + costText + '</h6><div id="timer"></div></div>';
          map.controls[google.maps.ControlPosition.TOP_CENTER].clear();
          map.controls[google.maps.ControlPosition.TOP_CENTER].push(costDiv);
          map.controls[google.maps.ControlPosition.BOTTOM_CENTER].clear();
          map.controls[google.maps.ControlPosition.BOTTOM_CENTER].push(paymentDiv);
          onOrderPayment('Готівка');
          hidePaymentButtons();
          startTimer();
        });

        // Додати обробник події для кнопки "Відмовитись" для перенаправлення на домашню сторінку
        orderReject = paymentDiv.getElementsByClassName('order-reject')[0];
        orderReject.addEventListener("click", onOrderReject);
      }
    }
  });
}

function orderUpdate(id_order) {
  intervalId = setInterval(function () {
    $.ajax({
      url: ajaxGetUrl,
      method: 'GET',
      data: {
        "action": "order_confirm",
        "id_order": id_order
      },
      success: function (response) {
        var driverOrder = JSON.parse(response.data)
        if (driverOrder.vehicle_gps) {
          clearInterval(intervalId);
          clearInterval(intervalTime);
          clearInterval(intervalTaxiMarker);

          clearTaxiMarkers();
          $('#timer').remove();

          const driverMarker = addMarker({
            position: new google.maps.LatLng(driverOrder.vehicle_gps[0].lat, driverOrder.vehicle_gps[0].lon),
            map,
            title: driverOrder.vehicle_gps[0].vehicle__licence_plate,
            icon: getMarkerIcon('taxi1'),
            animation: google.maps.Animation.DROP
          });

          var from = JSON.parse(getCookie('address'));
          var to = JSON.parse(getCookie('to_address'));

          const clientMarker = addMarker({
            position: from[0].geometry.location,
            map,
            title: from[0].formatted_address,
            icon: getMarkerIcon('address'),
            animation: google.maps.Animation.DROP
          });
          const destinationMarker = addMarker({
            position: to[0].geometry.location,
            map,
            title: to[0].formatted_address,
            icon: getMarkerIcon('to_address'),
            animation: google.maps.Animation.DROP
          });

          // Create a directions service object to get the route
          var directionsService = new google.maps.DirectionsService();

          // Create a directions renderer object to display the route
          var directionsRenderer = new google.maps.DirectionsRenderer();

          // Bind the directions renderer to the map
          directionsRenderer.setMap(map);
          directionsRenderer.setOptions({suppressMarkers: true})

          // Set the options for the route
          var routeOptions = {
            origin: driverMarker.position,
            waypoints: [
              {
                location: clientMarker.position,
                stopover: true,
              },
              {
                location: destinationMarker.position,
                stopover: true,
              },
            ],
            destination: destinationMarker.position,
            travelMode: google.maps.TravelMode.DRIVING,
            language: userLanguage,
          };

          // Call the directions service to get the route
          directionsService.route(routeOptions, function (result, status) {
            if (status == google.maps.DirectionsStatus.OK) {
              directionsRenderer.setDirections(result);

              var tripAmount = parseInt(getCookie('sumOder'));
              var cost = parseInt(driverOrder.car_delivery_price) + tripAmount;
              cost = Math.ceil(cost);

              var durationToA = result.routes[0].legs[0].duration.text;

              $('.alert-message').html(gettext('Ціна поїздки: ') + cost + gettext(' грн. Приблизний час прибуття авто: ') + durationToA);
              $('.order-confirm').remove();
              $('.order-reject').before('<button class="order-go btn btn-primary ml-3" onclick="consentTrip()">' + gettext("Погодитись") + '</button>');

              google.maps.event.trigger(map, 'resize');
            }
          });
        }
      }
    });
  }, 5000);
}


function onOrderPayment(paymentMethod) {
  var savedOrderData = getCookie('orderData');
  if (!savedOrderData) {
    alert('Помилка: дані замовлення не знайдені.');
    return;
  }

  var orderData = JSON.parse(savedOrderData);
  orderData.sum = getCookie('sumOder');
  orderData.distance_google= getCookie('distanceGoogle');
  orderData.latitude = getCookie('fromLat');
  orderData.longitude = getCookie('fromLon');
  orderData.to_latitude = getCookie('toLat');
  orderData.to_longitude = getCookie('toLon');
  orderData.payment_method = paymentMethod;
  orderData.status_order = 'Очікується';

  return new Promise((resolve, reject) => {
    $.ajax({
      url: ajaxPostUrl,
      method: 'POST',
      data: orderData,
      headers: {
        'X-CSRF-Token': $('input[name="csrfmiddlewaretoken"]').val()
      },
      success: function (response) {
        var idOrder = JSON.parse(response.data)
        setCookie("idOrder", idOrder.id, 1);
        orderUpdate(idOrder.id);
        resolve(idOrder)
      },
      error: function (error) {
        // Handle the error
        console.log("Сталася помилка при відправленні замовлення:", error);
        reject(error);
      }
    });
  });
}


function onOrderReject() {
  var idOrder = getCookie('idOrder')
  clearInterval(intervalTaxiMarker);
  destroyMap()
  $('#timer').remove();

  if (idOrder)
    $.ajax({
      url: ajaxPostUrl,
      method: 'POST',
      data: {
        csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
        action: 'user_opt_out',
        idOrder: idOrder,
      },
    })

  // Create an HTML window element with a comment form
  var modalText = gettext("Коментар про відмову від поїздки")
  var modalButton = gettext("Відправити")
  var commentForm = document.createElement("div");
  commentForm.innerHTML = `
    <div class="modal">
      <div class="modal-content">
        <span class="close">&times;</span>
        <h3>${modalText}</h3>
        <div class="form-group">
          <label for="reject_comment">${gettext("Залишіть, будь ласка, відгук")}</label>
          <textarea class="form-control" id="reject_comment" name="reject_comment" rows="3"></textarea>
        </div>
        <button class="btn btn-block btn-primary" onclick="sendComment()">${modalButton}</button>
      </div>
    </div>
  `;

  // Add a window to the page
  document.body.appendChild(commentForm);
  deleteCookie("address")

  // We attach an event to close the window when the cross is clicked
  var closeButton = commentForm.querySelector(".close");
  closeButton.addEventListener("click", function () {
    commentForm.parentNode.removeChild(commentForm);
    deleteAllCookies();
    location.reload();
  });
}

function sendComment() {
  // Send the comment to the server
  $.ajax({
    url: ajaxPostUrl,
    method: 'POST',
    data: {
      csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
      action: 'send_comment',
      comment: $('[name="reject_comment"]').val()
    },
    success: function (response) {
      // Process the response from the server
      $('.modal').remove();
      deleteAllCookies();
      location.reload();
    },
    error: function (error) {
      // Handle the error
      console.log("Сталася помилка при відправленні коментаря:", error);
    }
  });
}

function consentTrip() {
  destroyMap();
  var text1 = gettext('Ваша заявка прийнята. Очікуйте на автомобіль!');
  var applicationAccepted = document.createElement("div");
  applicationAccepted.innerHTML = `
    <div class="modal">
      <div class="modal-content">
        <h3>${text1}</h3>
      </div>
    </div>
  `;
  document.body.appendChild(applicationAccepted);
  deleteAllCookies();

  var modal = applicationAccepted.querySelector(".modal");

  setTimeout(function () {
    modal.parentNode.removeChild(modal);
    deleteAllCookies();
    location.reload();
  }, 5000);
}

function startTimer() {
  var duration = TIMER * 1000; // 3 хвилини
  // var duration = 10 * 1000; // 3 хвилини

  // Отримати збережений час початку таймера
  var startTime = getCookie('timerStartTime');
  if (startTime) {
    startTime = parseInt(startTime);
  } else {
    startTime = Date.now();
    // Зберегти час початку таймера в куках
    setCookie('timerStartTime', startTime, 1);
  }

  document.addEventListener('DOMContentLoaded', function () {
    var timer = document.createElement('div');
    timer.id = 'timer';

    var costDiv = document.getElementsByClassName('alert alert-primary mt-2')[0];
    costDiv.appendChild(timer);
  });

  // Зупинити попередній таймер, якщо він вже запущений
  clearInterval(intervalTime);

  var intervalTime = setInterval(function () {
    var elapsedTime = Date.now() - startTime;
    var remainingTime = duration - elapsedTime;

    // Перевірити, чи таймер закінчився
    if (remainingTime <= 0) {
      deleteCookie('timerStartTime');
      clearInterval(intervalTime);
      // var timerElement = document.getElementById('timer');
      // if (timerElement) {
      //   timerElement.remove();
      // }

      var modalContent = document.createElement('div');
      modalContent.innerHTML = '<div id="timer-modal" class="modal">\n' +
        '  <div class="modal-content">\n' +
        '    <p>Зараз спостерігається підвищений попит бажаєте збільшити ціну для прискорення пошуку?</p>\n' +
        '    <div class="slider-container">\n' +
        '      <input type="range" id="price-range" min="' + MINIMUM_PRICE_RADIUS + '" max="' + MAXIMUM_PRICE_RADIUS + '" step="1" value="' + MINIMUM_PRICE_RADIUS + '" class="price-range">\n' +
        '      <span id="slider-value">30 ₴</span>\n' +
        '    </div>\n' +
        '    <div class="button-group">\n' +
        '      <button class="btn btn-primary">Підвищити</button>\n' +
        '      <button class="btn btn-primary">Шукати далі</button>\n' +
        '      <button class="btn btn-danger">Відмовитись</button>\n' +
        '    </div>\n' +
        '  </div>\n' +
        '</div>';
      var modal = document.createElement('div');
      modal.id = 'timer-modal';
      modal.classList.add('modal');
      modal.appendChild(modalContent);
      document.body.appendChild(modal);

      var increasePrice = modal.getElementsByClassName('btn-primary')[0];
      var continueSearch = modal.getElementsByClassName('btn-primary')[1];
      var rejectSearch = modal.getElementsByClassName('btn-danger')[0];

      increasePrice.addEventListener('click', function () {
        setCookie("car_delivery_price", sliderElement.value, 1);
        onIncreasePrice();
        modal.remove();
      });
      continueSearch.addEventListener('click', function () {
        onContinueSearch();
        modal.remove();
      });
      rejectSearch.addEventListener('click', function () {
        onOrderReject();
        modal.remove();
      });

      var sliderElement = document.getElementById('price-range');
      var sliderValueElement = document.getElementById('slider-value');
      sliderElement.addEventListener('input', function () {
        sliderValueElement.textContent = sliderElement.value + '₴';
      });
    }

    // Обчислити хвилини та секунди
    var minutes = Math.floor(remainingTime / 60000);
    var seconds = Math.floor((remainingTime % 60000) / 1000);

    // Відобразити таймер у форматі "хвилини:секунди"
    var timerElements = document.getElementById('timer');
    if (timerElements) {
      timerElements.innerHTML = 'Приблизний час пошуку: ' + minutes + ' хв ' + seconds + ' сек';
    }
  }, 1000);
}


function onIncreasePrice() {
  var idOrder = getCookie('idOrder');
  var carDeliveryPrice = getCookie('car_delivery_price');

  // Розрахунок нового радіуса
  var newRadius = (FREE_DISPATCH * 1000) + (carDeliveryPrice / TARIFF_DISPATCH) * 1000;

  $.ajax({
    url: ajaxPostUrl,
    method: 'POST',
    data: {
      csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
      action: 'increase_price',
      idOrder: idOrder,
      carDeliveryPrice: carDeliveryPrice
    },
    success: function (response) {
      // Оновлення радіуса на карті
      updateCircleRadius(newRadius);
      startTimer();
    }
  });
}

function updateCircleRadius(radius) {
  // Перевірити, чи коло вже існує
  if (circle) {
    // Оновити радіус кола
    circle.setRadius(radius);
  }
}


function onContinueSearch() {
  var idOrder = getCookie('idOrder');

  $.ajax({
    url: ajaxPostUrl,
    method: 'POST',
    data: {
      csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
      action: 'continue_search',
      idOrder: idOrder
    },
    success: function (response) {
      startTimer()
    }
  });
}

function destroyMap() {
  map = null;
  orderData = null
  orderConfirm.removeEventListener('click', onOrderPayment)
  orderReject.removeEventListener('click', onOrderReject)
  document.getElementById('order-modal').remove()
}

$.mask.definitions['9'] = '';
$.mask.definitions['d'] = '[0-9]';

function intlTelInit(phoneEl) {
  var phoneSelector = $(phoneEl);

  if (phoneSelector.length) {
    phoneSelector.mask("+380 dd ddd-dd-dd");
  }
}

$(document).ready(function () {
  // if (csrfToken) setCookie("csrfToken", $.parseHTML(csrfToken)[0].value);

  $('#delivery_time').mask("dd:dd", {placeholder: gettext("00:00 (Вкажіть час)")});
  intlTelInit('#phone');

  $('input[name="radio"]').on('change', function () {
    var selectedValue = $('input[name="radio"]:checked').val();
    if (selectedValue === '2') {
      $('#order-time-field').removeClass('hidden');
      $('#order_time-error').removeClass('hidden');
    } else {
      $('#order-time-field').addClass('hidden');
    }

    if (selectedValue === '1') {
      $('#order_time-error').addClass('hidden');
    }
  });

  $('#order-form').on('submit', function (event) {
    event.preventDefault();

    var isLateOrder = $('input[name="radio"]:checked').val() === '2';
    var form = new FormData(this);
    var timeWrapper = $('#order-time-field');
    var noTime = timeWrapper.hasClass('hidden');

    if (isLateOrder && noTime) {
      timeWrapper.removeClass('hidden').next().html('');
      return;
    }

    if (!isLateOrder) {
      timeWrapper.addClass('hidden').next().html('');
      form.delete('order_time')
    }

    var fields = form.keys()
    var errorFields = 0;
    var errorMsgs = {
      'phone_number': gettext("Номер телефону обов'язковий"),
      'from_address': gettext("Адреса обов'язкова"),
      'to_the_address': gettext("Адреса обов'язкова"),
      'order_time': gettext("Час замовлення обов'язково")
    }

    for (const field of fields) {
      const err = $(`#${field}-error`);
      if (form.get(field).length === 0) {
        errorFields++;
        err.html(errorMsgs[field]);
      } else {
        err.html('');
      }
    }

    if (!errorFields && form.has('order_time')) {
      const formattedDeliveryTime = moment(form.get('order_time'), 'HH:mm').format('YYYY-MM-DD HH:mm:ss');
      const currentTime = moment();
      const minCurrentTime = moment(currentTime).add(SEND_TIME_ORDER_MIN, 'minutes');
      if (moment(formattedDeliveryTime, 'YYYY-MM-DD HH:mm:ss').isSameOrAfter(minCurrentTime)) {
        form.set('order_time', formattedDeliveryTime);
      } else {
        errorFields++;
        var orderTimeError1 = gettext('Виберіть час не менше ніж через ');
        var orderTimeError2 = gettext(' хвилин');
        $('#order_time-error').html(orderTimeError1 + SEND_TIME_ORDER_MIN + orderTimeError2)
      }
    }

    if (!errorFields) {
      // Додаємо перевірку валідності адрес
      var fromAddress = form.get('from_address');
      var toAddress = form.get('to_the_address');

      var geocoder = new google.maps.Geocoder();
      geocoder.geocode({'address': fromAddress}, function (fromGeocoded, status) {
        if (status !== 'OK') {
          $('#from_address-error').html(gettext('Некоректна адреса'));
          return;
        }
        geocoder.geocode({'address': toAddress}, function (toGeocoded, status) {
          if (status !== 'OK') {
            $('#to_the_address-error').html(gettext('Некоректна адреса'));
            return;
          }
          form.append('action', 'order');
          orderData = Object.fromEntries(form);
          orderData.phone_number = orderData.phone_number.replace(/[^+0-9]/gi, '');
          var fromGeocode = fromGeocoded[0].geometry.location
          var toGeocode = toGeocoded[0].geometry.location
          setCookie("fromLat", fromGeocode.lat().toFixed(6), 1);
          setCookie("fromLon", fromGeocode.lng().toFixed(6), 1);
          setCookie("toLat", toGeocode.lat().toFixed(6), 1);
          setCookie("toLon", toGeocode.lng().toFixed(6), 1);
          setCookie('orderData', JSON.stringify(orderData));

          if (form.has('order_time')) {
            // Отримання координат з куків
            var fromLat = parseFloat(getCookie("fromLat"));
            var fromLon = parseFloat(getCookie("fromLon"));
            var toLat = parseFloat(getCookie("toLat"));
            var toLon = parseFloat(getCookie("toLon"));

            // Створення об'єктів google.maps.LatLng на основі координат з куків
            var fromLocation = new google.maps.LatLng(fromLat, fromLon);
            var toLocation = new google.maps.LatLng(toLat, toLon);

            // Створення об'єкту запиту для DirectionsService
            var request = {
              origin: fromLocation,
              destination: toLocation,
              travelMode: google.maps.TravelMode.DRIVING
            };

            // Виклик DirectionsService для отримання маршруту та відстані
            var directionsService = new google.maps.DirectionsService();
            directionsService.route(request, function (result, status) {
              if (status === google.maps.DirectionsStatus.OK) {
                var distanceInMeters = result.routes[0].legs[0]['steps'];

                var allPathsAddress = getAllPath(distanceInMeters)

                var inCitOrOutCityAddress = pathSeparation(allPathsAddress)
                var inCity = inCitOrOutCityAddress[0]
                var outOfCity = inCitOrOutCityAddress[1]

                var inCityCoords = getPathCoords(inCity)
                var outOfCityCoords = getPathCoords(outOfCity)


                let inCityDistance = parseInt(calculateDistance(inCityCoords));
                let outOfCityDistance = parseInt(calculateDistance(outOfCityCoords));
                let totalDistance = inCityDistance + outOfCityDistance;


                var tripAmount = Math.ceil((inCityDistance * TARIFF_IN_THE_CITY) + (outOfCityDistance * TARIFF_OUTSIDE_THE_CITY));
                setCookie('sumOder', tripAmount, 1)
                setCookie('distanceGoogle', totalDistance, 1)


                var text2 = gettext('Дякуємо за замовлення. Очікуйте на автомобіль! Ваша вартість поїздки: ') +
                  '<span class="trip-amount">' + tripAmount + '</span>' + gettext(' грн.');
                var modal = $('<div class="modal">' +
                  '<div class="modal-content rounded">' +
                  '<h3 class="modal-title">' + text2 + '</h3>' +
                  '<div class="buttons-container">' +
                  '<button class="order-confirm btn btn-primary">Погодитися</button>' +
                  '<button class="order-reject btn btn-danger">Відмовитись</button>' +
                  '</div>' +
                  '</div>' +
                  '</div>');

                $('body').prepend(modal);

                modal.find('.order-confirm').on('click', function () {
                  onOrderPayment().then(function () {
                    deleteAllCookies();
                  });
                  modal.remove();
                  window.location.reload();
                });

                modal.find('.order-reject').on('click', function () {
                  modal.remove();
                  deleteAllCookies();
                  window.location.reload();
                });
              }
            });
          } else {
            $.ajax({
              url: ajaxGetUrl,
              method: 'GET',
              data: {
                "action": "active_vehicles_locations"
              },
              success: function (response) {
                var taxiArr = JSON.parse(response.data);

                if (taxiArr.length > 0) {
                  createMap(fromGeocoded, toGeocoded);
                  intervalTaxiMarker = setInterval(updateTaxiMarkers, 10000);
                } else {
                  var text3 = gettext('Вибачте але на жаль вільних водіїв нема. Скористайтеся нашою послугою замовлення на інший час!')
                  var noTaxiArr = document.createElement("div");
                  noTaxiArr.innerHTML = `
                    <div class="modal-taxi">
                    <div class="modal-content-taxi">
                    <span class="close">&times;</span>
                    <h3>${text3}</h3>
                    </div>
                    </div>`;
                  document.body.appendChild(noTaxiArr);
                  deleteCookie("address")

                  // We attach an event to close the window when the cross is clicked
                  var closeButton = noTaxiArr.querySelector(".close");
                  closeButton.addEventListener("click", function () {
                    noTaxiArr.parentNode.removeChild(noTaxiArr);
                  });
                }
              }
            });
            setCookie("address", JSON.stringify(fromGeocoded), 1);
            setCookie("to_address", JSON.stringify(toGeocoded), 1);
            setCookie("phone", form.get('phone_number'), 1);
          }
        });
      });
    }
  });
});

function updateTaxiMarkers() {
  $.ajax({
    url: ajaxGetUrl,
    method: 'GET',
    data: {
      "action": "active_vehicles_locations"
    },
    success: function (response) {
      var taxiArr = JSON.parse(response.data);
      // Clear previous taxi markers
      clearTaxiMarkers();
      // Add new taxi markers
      addTaxiMarkers(taxiArr);
    },
    error: function (error) {
      console.log("Error retrieving taxi data:", error);
    }
  });
}

function clearTaxiMarkers() {
  // Remove all taxi markers from the map
  taxiMarkers.forEach(function (marker) {
    marker.setMap(null);
  });
  // Clear the taxiMarkers array
  taxiMarkers = [];
}

function addTaxiMarkers(taxiArr) {
  taxiArr.forEach(taxi => {
    // Create a marker for each taxi with a custom icon
    var marker = new google.maps.Marker({
      position: new google.maps.LatLng(taxi.lat, taxi.lon),
      map: map,
      title: taxi.vehicle__licence_plate,
      icon: getMarkerIcon('taxi1'),
      animation: google.maps.Animation.SCALE
    });
    // Add the marker to the taxiMarkers array
    taxiMarkers.push(marker);
  });
}


$(document).ready(function () {
  $('[id^="sub-form-"]').on('submit', function (event) {
    event.preventDefault();
    const form = this;
    $.ajax({
      type: "POST",
      url: ajaxPostUrl,
      data: {
        'email': $(event.target).find('#sub_email').val(),
        'action': 'subscribe',
        'csrfmiddlewaretoken': $('input[name="csrfmiddlewaretoken"]').val()
      },
      success: function (data) {
        $('#email-error-1, #email-error-2').html('');
        form.reset();
      },
      error: function (xhr, textStatus, errorThrown) {
        if (xhr.status === 400) {
          var errors = xhr.responseJSON;
          $.each(errors, function (key, value) {
            $('#' + key + '-error-1, #' + key + '-error-2').html(value);
          });
        } else {
          console.error('Помилка запиту: ' + textStatus);
        }
      }
    });
  });
});

function initAutocomplete(inputID) {
  const inputField = document.getElementById(inputID);
  const autoComplete = new google.maps.places.Autocomplete(inputField, {
    bounds: new google.maps.Circle({
      center: {lat: CENTRE_CITY_LAT, lng: CENTRE_CITY_LNG},
      radius: CENTRE_CITY_RADIUS,
    }).getBounds(),
    strictBounds: true,
  });
  autoComplete.addListener('place_changed', function () {
    const place = autoComplete.getPlace();
    if (place && place.formatted_address) {
      inputField.value = place.formatted_address;
    } else {
      inputField.value = '';
      inputField.placeholder = gettext("Будь ласка, введіть коректну адресу");
    }
  });
}

$(document).ready(function () {

  if ($('#address').length || $('#to_address').length) {
    loadGoogleMaps(3, apiGoogle, userLanguage, '', 'geometry,places').then(function () {
      initAutocomplete('address');
      initAutocomplete('to_address');
      checkCookies()
    });
  }

  $(this).on('click', '.services-grid__item .btn', function () {
    var t = $(this);
    content = t.prev();

    if (content.hasClass('limited-lines')) {
      content.removeClass('limited-lines');
      t.text(gettext('Читайте менше <'));
    } else {
      content.addClass('limited-lines');
      t.text(gettext('Читати далі >'));
    }

    $('html, body').animate({scrollTop: $('.services-grid').offset().top}, 100);

    return false;
  });

  $("a[href='#order-now']").click(function () {
    $('html, body').animate({
      scrollTop: $("#order-now").offset().top
    }, 1000); // Час прокрутки в мілісекундах (1000 мс = 1 с)
  });

  if (userLanguage === "uk") {
    $(".img-box-en").addClass("hidden");
    $(".img-box-uk").removeClass("hidden");
  } else {
    $(".img-box-en").removeClass("hidden");
    $(".img-box-uk").addClass("hidden");
  }

  const $blocks = $('[data-block]');

  $blocks.on('mouseenter', function () {
    const $currentBlock = $(this);
    const initialHeight = $currentBlock.height();

    $currentBlock.animate({marginTop: -20}, 300);
  });

  $blocks.on('mouseleave', function () {
    const $currentBlock = $(this);
    $currentBlock.animate({marginTop: 0}, 300);
  });
});

$(window).on('load', function () {
  $('.loader').remove();
});