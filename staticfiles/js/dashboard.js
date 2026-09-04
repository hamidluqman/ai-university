document.addEventListener("DOMContentLoaded", function () {

    const toggle = document.getElementById("sidebarToggle");

    const sidebar = document.querySelector(".sidebar");

    if(toggle){

        toggle.addEventListener("click", function(){

            sidebar.classList.toggle("show");

        });

    }

});