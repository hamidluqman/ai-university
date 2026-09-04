(function ($) {
    "use strict";

    console.log("[Question Dependencies] JavaScript loaded.");

    // ==========================================================
    // FIELD REFERENCES
    // ==========================================================

    function getFields() {

        return {
            library: $("#id_assessment_library"),

            schoolClass: $("#id_school_class"),
            subject: $("#id_subject"),
            chapter: $("#id_chapter"),
            topic: $("#id_topic"),
            subtopic: $("#id_subtopic"),

            assessmentSubject: $("#id_assessment_subject"),
            module: $("#id_module"),
            submodule: $("#id_submodule"),
        };
    }


    // ==========================================================
    // GET ROW
    // ==========================================================

    function getRow(field) {

        if (!field || !field.length) {
            return $();
        }

        return (
            field.closest(".form-row").length
                ? field.closest(".form-row")
                : field.closest(".fieldBox")
        );
    }


    // ==========================================================
    // SHOW FIELD
    // ==========================================================

    function showField(field) {

        const row = getRow(field);

        if (!row.length) {
            console.warn(
                "[Question Dependencies] Cannot find row for:",
                field
            );
            return;
        }

        row
            .removeClass("section-hidden")
            .css("display", "block");

        console.log(
            "[Question Dependencies] SHOW:",
            field.attr("id")
        );
    }


    // ==========================================================
    // HIDE FIELD
    // ==========================================================

    function hideField(field) {

        const row = getRow(field);

        if (!row.length) {
            return;
        }

        row
            .addClass("section-hidden")
            .css("display", "none");

        console.log(
            "[Question Dependencies] HIDE:",
            field.attr("id")
        );
    }


    // ==========================================================
    // CLEAR FIELD
    // ==========================================================

    function clearField(field) {

        if (!field || !field.length) {
            return;
        }

        field.empty();

        field.append(
            $("<option>", {
                value: "",
                text: "---------"
            })
        );

        field.val("");
    }


    // ==========================================================
    // BOARD RESET
    // ==========================================================

    function resetBoard() {

        const fields = getFields();

        clearField(fields.schoolClass);
        clearField(fields.subject);
        clearField(fields.chapter);
        clearField(fields.topic);
        clearField(fields.subtopic);
    }


    // ==========================================================
    // COMPETITIVE RESET
    // ==========================================================

    function resetCompetitive() {

        const fields = getFields();

        clearField(fields.assessmentSubject);
        clearField(fields.module);
        clearField(fields.submodule);
    }


    // ==========================================================
    // HIDE BOARD
    // ==========================================================

    function hideBoard() {

        const fields = getFields();

        hideField(fields.schoolClass);
        hideField(fields.subject);
        hideField(fields.chapter);
        hideField(fields.topic);
        hideField(fields.subtopic);
    }


    // ==========================================================
    // SHOW BOARD
    // ==========================================================

    function showBoard() {

        const fields = getFields();

        showField(fields.schoolClass);
        showField(fields.subject);
        showField(fields.chapter);
        showField(fields.topic);
        showField(fields.subtopic);
    }


    // ==========================================================
    // HIDE COMPETITIVE
    // ==========================================================

    function hideCompetitive() {

        const fields = getFields();

        hideField(fields.assessmentSubject);
        hideField(fields.module);
        hideField(fields.submodule);
    }


    // ==========================================================
    // SHOW COMPETITIVE
    // ==========================================================

    function showCompetitive() {

        const fields = getFields();

        showField(fields.assessmentSubject);
        showField(fields.module);
        showField(fields.submodule);
    }


    // ==========================================================
    // API URL
    // ==========================================================

    function getApiUrl() {

        const pathname = window.location.pathname;

        if (pathname.endsWith("/add/")) {

            return pathname.replace(
                /\/add\/$/,
                "/dependent-options/"
            );
        }

        if (pathname.endsWith("/change/")) {

            return pathname.replace(
                /\/change\/$/,
                "/dependent-options/"
            );
        }

        return pathname.replace(
            /\/$/,
            "/dependent-options/"
        );
    }


    // ==========================================================
    // LOAD OPTIONS
    // ==========================================================

    function loadOptions(
        fieldName,
        value,
        targetField,
        callback
    ) {

        if (!targetField || !targetField.length) {

            console.warn(
                "[Question Dependencies] Target field missing:",
                fieldName
            );

            return;
        }

        clearField(targetField);

        if (!value) {

            if (callback) {
                callback([]);
            }

            return;
        }


        console.log(
            "[Question Dependencies] Loading:",
            fieldName,
            "value:",
            value
        );


        $.ajax({

            url: getApiUrl(),

            type: "GET",

            data: {
                field: fieldName,
                value: value
            },

            dataType: "json",

            success: function (data) {

                console.log(
                    "[Question Dependencies] API:",
                    fieldName,
                    data
                );

                const results =
                    data.results || [];


                results.forEach(function (item) {

                    targetField.append(
                        $("<option>", {
                            value: item.id,
                            text: item.text
                        })
                    );

                });


                if (callback) {
                    callback(results);
                }
            },

            error: function (xhr) {

                console.error(
                    "[Question Dependencies] API ERROR:",
                    fieldName,
                    xhr.status,
                    xhr.responseText
                );

                if (callback) {
                    callback([]);
                }
            }
        });
    }


    // ==========================================================
    // GET CATEGORY
    // ==========================================================

    function getCategory(
        libraryId,
        callback
    ) {

        if (!libraryId) {

            callback(null);

            return;
        }


        console.log(
            "[Question Dependencies] Getting category for:",
            libraryId
        );


        $.ajax({

            url: getApiUrl(),

            type: "GET",

            data: {
                field: "assessment_category",
                value: libraryId
            },

            dataType: "json",

            success: function (data) {

                console.log(
                    "[Question Dependencies] CATEGORY:",
                    data
                );

                callback(
                    data.category || null
                );
            },

            error: function (xhr) {

                console.error(
                    "[Question Dependencies] CATEGORY ERROR:",
                    xhr.status,
                    xhr.responseText
                );

                callback(null);
            }
        });
    }


    // ==========================================================
    // LOAD SCHOOL CLASSES
    // ==========================================================

    function loadSchoolClasses() {

        const fields = getFields();

        loadOptions(
            "school_class",
            "all",
            fields.schoolClass,
            function (results) {

                console.log(
                    "[Question Dependencies] Classes loaded:",
                    results
                );

                if (results.length === 1) {

                    fields.schoolClass
                        .val(results[0].id)
                        .trigger("change");
                }
            }
        );
    }


    // ==========================================================
    // LOAD BOARD HIERARCHY
    // ==========================================================

    function loadBoardHierarchy() {

        const fields = getFields();

        console.log(
            "[Question Dependencies] Loading Board hierarchy."
        );


        loadSchoolClasses();
    }


    // ==========================================================
    // LOAD COMPETITIVE HIERARCHY
    // ==========================================================

    function loadCompetitiveHierarchy() {

        const fields = getFields();

        const libraryId =
            fields.library.val();


        console.log(
            "[Question Dependencies] Loading Competitive hierarchy.",
            "Library:",
            libraryId
        );


        if (!libraryId) {
            return;
        }


        // ------------------------------------------------------
        // Assessment Subject
        // ------------------------------------------------------

        loadOptions(
            "assessment_subject",
            libraryId,
            fields.assessmentSubject,
            function (subjects) {

                console.log(
                    "[Question Dependencies] Assessment Subjects:",
                    subjects
                );


                if (subjects.length === 1) {

                    fields.assessmentSubject
                        .val(subjects[0].id)
                        .trigger("change");
                }
            }
        );
    }


    // ==========================================================
    // LIBRARY CHANGED
    // ==========================================================

    function libraryChanged() {

        const fields = getFields();

        const libraryId =
            fields.library.val();


        console.log(
            "[Question Dependencies] Library changed:",
            libraryId
        );


        // ------------------------------------------------------
        // Reset everything
        // ------------------------------------------------------

        resetBoard();
        resetCompetitive();

        hideBoard();
        hideCompetitive();


        if (!libraryId) {
            return;
        }


        // ------------------------------------------------------
        // Determine category
        // ------------------------------------------------------

        getCategory(
            libraryId,
            function (category) {

                console.log(
                    "[Question Dependencies] CATEGORY:",
                    category
                );


                if (category === "board") {

                    showBoard();

                    hideCompetitive();

                    loadBoardHierarchy();

                    return;
                }


                if (category === "competitive") {

                    hideBoard();

                    showCompetitive();

                    loadCompetitiveHierarchy();

                    return;
                }


                console.warn(
                    "[Question Dependencies] Unknown category:",
                    category
                );
            }
        );
    }


    // ==========================================================
    // SCHOOL CLASS CHANGED
    // ==========================================================

    function schoolClassChanged() {

        const fields = getFields();

        const value =
            fields.schoolClass.val();


        clearField(fields.subject);
        clearField(fields.chapter);
        clearField(fields.topic);
        clearField(fields.subtopic);


        if (!value) {
            return;
        }


        loadOptions(
            "subject",
            value,
            fields.subject
        );
    }


    // ==========================================================
    // SUBJECT CHANGED
    // ==========================================================

    function subjectChanged() {

        const fields = getFields();

        const value =
            fields.subject.val();


        clearField(fields.chapter);
        clearField(fields.topic);
        clearField(fields.subtopic);


        if (!value) {
            return;
        }


        loadOptions(
            "chapter",
            value,
            fields.chapter
        );
    }


    // ==========================================================
    // CHAPTER CHANGED
    // ==========================================================

    function chapterChanged() {

        const fields = getFields();

        const value =
            fields.chapter.val();


        clearField(fields.topic);
        clearField(fields.subtopic);


        if (!value) {
            return;
        }


        loadOptions(
            "topic",
            value,
            fields.topic
        );
    }


    // ==========================================================
    // TOPIC CHANGED
    // ==========================================================

    function topicChanged() {

        const fields = getFields();

        const value =
            fields.topic.val();


        clearField(fields.subtopic);


        if (!value) {
            return;
        }


        loadOptions(
            "subtopic",
            value,
            fields.subtopic
        );
    }


    // ==========================================================
    // ASSESSMENT SUBJECT CHANGED
    // ==========================================================

    function assessmentSubjectChanged() {

        const fields = getFields();

        const value =
            fields.assessmentSubject.val();


        console.log(
            "[Question Dependencies] Assessment Subject changed:",
            value
        );


        clearField(fields.module);
        clearField(fields.submodule);


        if (!value) {
            return;
        }


        // IMPORTANT:
        // Module field must be visible BEFORE loading.

        showField(fields.module);


        loadOptions(
            "module",
            value,
            fields.module,
            function (results) {

                console.log(
                    "[Question Dependencies] Modules:",
                    results
                );


                if (results.length === 1) {

                    fields.module
                        .val(results[0].id)
                        .trigger("change");
                }
            }
        );
    }


    // ==========================================================
    // MODULE CHANGED
    // ==========================================================

    function moduleChanged() {

        const fields = getFields();

        const value =
            fields.module.val();


        console.log(
            "[Question Dependencies] Module changed:",
            value
        );


        clearField(fields.submodule);


        if (!value) {

            hideField(fields.submodule);

            return;
        }


        // IMPORTANT:
        // Show Submodule BEFORE API call.

        showField(fields.submodule);


        loadOptions(
            "submodule",
            value,
            fields.submodule,
            function (results) {

                console.log(
                    "[Question Dependencies] Submodules:",
                    results
                );


                // If no submodules exist,
                // keep the field visible but empty.

                if (!results.length) {

                    console.log(
                        "[Question Dependencies] No submodules for module:",
                        value
                    );
                }
            }
        );
    }


    // ==========================================================
    // INITIALIZE
    // ==========================================================

    function initialize() {

        console.log(
            "[Question Dependencies] Initializing."
        );


        const fields = getFields();


        if (!fields.library.length) {

            console.error(
                "[Question Dependencies] Assessment Library not found."
            );

            return;
        }


        // ------------------------------------------------------
        // Initially hide dependent sections
        // ------------------------------------------------------

        hideBoard();
        hideCompetitive();


        // ------------------------------------------------------
        // Existing selected library
        // ------------------------------------------------------

        const libraryId =
            fields.library.val();


        console.log(
            "[Question Dependencies] Existing library:",
            libraryId
        );


        if (!libraryId) {
            return;
        }


        getCategory(
            libraryId,
            function (category) {

                if (category === "board") {

                    showBoard();

                    hideCompetitive();

                    loadBoardHierarchy();

                }

                else if (
                    category === "competitive"
                ) {

                    hideBoard();

                    showCompetitive();

                    loadCompetitiveHierarchy();

                }

            }
        );
    }


    // ==========================================================
    // EVENTS
    // ==========================================================

    $(document).on(
        "change",
        "#id_assessment_library",
        libraryChanged
    );


    $(document).on(
        "change",
        "#id_school_class",
        schoolClassChanged
    );


    $(document).on(
        "change",
        "#id_subject",
        subjectChanged
    );


    $(document).on(
        "change",
        "#id_chapter",
        chapterChanged
    );


    $(document).on(
        "change",
        "#id_topic",
        topicChanged
    );


    $(document).on(
        "change",
        "#id_assessment_subject",
        assessmentSubjectChanged
    );


    $(document).on(
        "change",
        "#id_module",
        moduleChanged
    );


    // ----------------------------------------------------------
    // DOM READY
    // ----------------------------------------------------------

    $(function () {

        console.log(
            "[Question Dependencies] DOM ready."
        );

        initialize();

    });


})(django.jQuery);