document.addEventListener("DOMContentLoaded", function() {
    const planTypeField = document.querySelector("#id_plan_type");
    if (!planTypeField) return;

    const teacherRow = document.querySelector(".field-max_teachers_allowed");
    const studentRow = document.querySelector(".field-max_students_allowed");

    function toggleFields() {
        if (planTypeField.value === "INDEPENDENT_STUDENT") {
            if (teacherRow) teacherRow.style.display = "none";
            if (studentRow) studentRow.style.display = "none";
        } else {
            if (teacherRow) teacherRow.style.display = "block";
            if (studentRow) studentRow.style.display = "block";
        }
    }

    // Run on load
    toggleFields();

    // Run on change
    planTypeField.addEventListener("change", toggleFields);
});