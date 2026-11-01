
$(window).scroll(function () {
    const scroll = $(window).scrollTop();
    if (scroll >= 200) {
        $(".main-header").addClass("fixed-top").fadeIn();
    } else {
        $(".main-header").removeClass("fixed-top");
    }
});
