document.addEventListener("DOMContentLoaded", function () {
  $("#body").fadeIn();
  $("#loader").fadeOut();
  $("#whitebg").fadeOut();
  $(".datatable").DataTable({
    language: {
      search: "_INPUT_",
      searchPlaceholder: "Filter table...",
    },
    dom: "fltipr",
  });
});
