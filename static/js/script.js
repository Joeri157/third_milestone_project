$(document).ready(function(){
// Materialize Jquery

    // Menu Dropdown trigger
    $(".dropdown-trigger").dropdown({
        coverTrigger: false
        });
    
    //Profile Tabs
    $('.tabs').tabs();

    // Counts characters in text area of upload and comment
    $('input#input_text, textarea#upload_description, textarea#comment_description').characterCounter();

    // Add Upload select
    $('select').formSelect();
    // Select Validate function from the Code Institute - tutorial
    validateMaterializeSelect();
    function validateMaterializeSelect() {
        let classValid = { "border-bottom": "1px solid #4caf50", "box-shadow": "0 1px 0 0 #4caf50" };
        let classInvalid = { "border-bottom": "1px solid #f44336", "box-shadow": "0 1px 0 0 #f44336" };
        if ($("select.validate").prop("required")) {
            $("select.validate").css({ "display": "block", "height": "0", "padding": "0", "width": "0", "position": "absolute" });
        }
        $(".select-wrapper input.select-dropdown").on("focusin", function () {
            $(this).parent(".select-wrapper").on("change", function () {
                if ($(this).children("ul").children("li.selected:not(.disabled)").on("click", function () { })) {
                    $(this).children("input").css(classValid);
                }
            });
        }).on("click", function () {
            if ($(this).parent(".select-wrapper").children("ul").children("li.selected:not(.disabled)").css("background-color") === "rgba(0, 0, 0, 0.03)") {
                $(this).parent(".select-wrapper").children("input").css(classValid);
            } else {
                $(".select-wrapper input.select-dropdown").on("focusout", function () {
                    if ($(this).parent(".select-wrapper").children("select").prop("required")) {
                        if ($(this).css("border-bottom") != "1px solid rgb(76, 175, 80)") {
                            $(this).parent(".select-wrapper").children("input").css(classInvalid);
                        }
                    }
                });
            }
        });
    }

    // Dropdown for the Comment (edit and delete function)
    $(".dropdown-trigger1").dropdown({
        coverTrigger: false,
        alignment: "right"
        });
    
    // Upload text inside button
    $('input[type="file"]').change(function(){
        var value = $("input[type='file']").val();
        $('.js-value').text(value);
    });
    // Upload preview url link
    $('input[type="file"]').change( function(event) {
        var tmppath = URL.createObjectURL(event.target.files[0]);
        $("img").fadeIn("fast").attr('src',URL.createObjectURL(event.target.files[0]));
    });

    // Search Overlay
    $('#close-btn').click(function() {
        $('#search-overlay').fadeOut();
        $('.nav-search-btn').show();
    });
    $('.nav-search-btn').click(function() {
        $(this).hide();
        $('#search-overlay').fadeIn();
    });

});