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

$(document).ready(function () {

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

	$("#changePassword").click(function () {
		$("#passwordChangeForm").toggle();
	});


	$("#submitPassword").click(function () {
		let password = $("#oldPassword").val();
		let newPassword = $("#newPassword").val();
		let confirmPassword = $("#confirmPassword").val();
        if (newPassword.trim() === "") {
            $("#EmptyPasswordError").show();
            $("#ChangeErrorMessage").hide();
        } else if (newPassword !== confirmPassword) {
			$("#ChangeErrorMessage").show();
			$("#EmptyPasswordError").hide();
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

});