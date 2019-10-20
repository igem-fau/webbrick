
/**
    Sticky Header
 */
$(window).on('scroll', function(event) {
    var scrollValue = $(window).scrollTop();

    var headerHeight = $("header").height();

    if (scrollValue > headerHeight) {
        $('.sticky-header').removeClass("sticky-off").addClass("sticky-on");
    } else {
        $('.sticky-header').removeClass("sticky-on").addClass("sticky-off");
    }
});